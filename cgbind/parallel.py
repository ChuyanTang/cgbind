import os
import numpy as np
from .log import logger
from .config import Config
from multiprocessing import Pool
from .cage import Cage
from .linker import Linker
from .substrate import Substrate
from .input_output import xyzs2xyzfile
from .input_output import xyzfile2xyzs
from .ORCAio import singlepointenergy
from .constants import Constants
from .plotting import plot_heatmap
from .input_output import print_binding_affinities


def calc_n_cores_pp(dict1, dict2=None):
    """
    Calculate the optimum number of cores to use for each process, as ORCA doesn't quite scale linearly it's best
    to use just 1 core jobs if the total number of calculations exceeds the
    :param dict1: Dictionary of names and smiles strings - to calculate the number of calculations that need to be run
    :param dict2:
    :return:
    """

    n_cores_pp = 1
    if dict2:
        n_calcs = int(len(dict1) * len(dict2))
    else:
        n_calcs = len(dict1)

    if n_calcs < Config.n_cores:
        n_cores_pp = int(Config.n_cores / n_calcs)

    if not Config.suppress_print:
        print('Have', n_calcs, 'calculation(s) to do and', Config.n_cores,
              'core(s). Splitting into', int(Config.n_cores / n_cores_pp), 'thread(s)...')

    return n_cores_pp


def gen_cage(linker_name, linker_smiles, opt_linker=False, opt_cage=False, metal_label='Pd',
             metal_charge=2, n_cores_pp=Config.n_cores, sp_cage=False, arch='m2l4'):
    """
    Generate a cage for a specific linker (L) and print the .xyz file

    Has options to optimise the structure, which will set cage.energy using that level of theory. For a more accurate
    energy one can perform a single point calculation with sp_cage=True, which will set cage.energy.

    :param linker_name:
    :param linker_smiles:
    :param n_cores_pp: Number of cores to use (per process, if called with mp.pool).
    Only will be applied if Config.code  == 'orca'. Both PM7 and XTB are fast enough in serial
    :param opt_cage:
    :param opt_linker:
    :param metal_charge:
    :param metal_label:
    :param arch: Architecture of the cage
    :param sp_cage: Do a single point energy calculation
    :return: Cage object
    """

    linkerx = Linker(linker_smiles, name=linker_name, opt=opt_linker, n_cores=n_cores_pp, arch=arch)

    if arch == 'm2l4':
        total_charge = int(2 * metal_charge + 4 * linkerx.charge)
    elif arch == 'm4l6':
        total_charge = int(4 * metal_charge + 6 * linkerx.charge)
    else:
        logger.critical('Couldn\'t build a cage with this architecture')
        return exit()

    cage_obj = Cage(linkerx, name=('cage_' + linker_name), total_charge=total_charge, metal=metal_label, arch=arch)
    if Config.path_to_opt_struct:
        path_to_opt_geom = os.path.join(Config.path_to_opt_struct, cage_obj.name + '.xyz')
        if os.path.exists(path_to_opt_geom):
            if not Config.suppress_print:
                print('Found an optimised geometry in path_to_opt_struct')
            cage_obj.xyzs = xyzfile2xyzs(xyz_filename=path_to_opt_geom)
    else:
        if opt_cage:
            cage_obj.optimise(n_cores=n_cores_pp)
        pass

    if sp_cage:
        cage_obj.energy = singlepointenergy(cage_obj.xyzs, cage_obj.name, Config.sp_keywords, Config.sp_solvent,
                                            cage_obj.charge, n_cores=n_cores_pp)

    if cage_obj.reasonable_geometry:
        param_string = ('Pd-Pd dist. = ' + str(np.round(cage_obj.get_m_m_dist(), 3)) + ' Å, ' +
                        'Cavity vol. = ' + str(np.round(cage_obj.get_cavity_vol(), 3)) + ' Å^3'
                        )
        xyzs2xyzfile(cage_obj.xyzs, basename=cage_obj.name, title_line=param_string)

    return cage_obj


def gen_cages_parallel(linker_dict, opt_linker=False, opt_cage=False, metal_label='Pd', metal_charge=2,
                       sp_cage=False, arch='m2l4'):
    """
    Parallel generation of cages to optimise efficiency cf. serial execution on a large number of cores, which is less
    efficient as ORCA does not scale linearly. Will use all the cores set in Config.n_cores

    :param linker_dict: Dictionary of linker names and smiles strings. Examples are given in library/
    :param opt_cage:
    :param opt_linker:
    :param metal_charge:
    :param metal_label:
    :param sp_cage:
    :param arch: Architecture of the cage
    :return: List of cage objects
    """

    n_cores_per_process = calc_n_cores_pp(linker_dict)

    with Pool(processes=int(Config.n_cores / n_cores_per_process)) as pool:

        results = [pool.apply_async(gen_cage, (linker_name, linker_smiles, opt_linker, opt_cage, metal_label,
                                               metal_charge, n_cores_per_process, sp_cage, arch))
                   for linker_name, linker_smiles in linker_dict.items()]

        cages = [res.get(timeout=None) for res in results]

    return cages


def gen_cage_subst_complex(linker_name=None, linker_smiles=None, substrate_name=None, substrate_smiles=None,
                           substrate_charge=0, opt_linker=False, opt_cage=False, opt_substrate=False,
                           opt_cage_subst=False, fix_cage_geom=False, metal_label='Pd', metal_charge=2,
                           n_cores_pp=None, sp_cage=False, sp_substrate=False, sp_cage_subst=False,
                           cage_obj=None, subst_obj=None, arch='m2l4'):
    """
    Generate a cage-substrate complex for a specific linker. Can be called with  cage and substrate objects defined
    or initialised in this function in which cage all(linker_name, linker_smiles, substrate_name, substrate_smiles)
    must be defined

    :return: A list of the cage object and the substrate object
    """
    if not n_cores_pp:
        n_cores_pp = Config.n_cores

    if not cage_obj:
        cage_obj = gen_cage(linker_name, linker_smiles, opt_linker, opt_cage, metal_label,
                            metal_charge, n_cores_pp, sp_cage, arch)

    if not subst_obj:
        subst_obj = Substrate(substrate_smiles, substrate_name, opt=opt_substrate,
                              charge=substrate_charge, n_cores=n_cores_pp)
        if sp_substrate:
            subst_obj.energy = singlepointenergy(subst_obj.xyzs, subst_obj.name, Config.sp_keywords, Config.sp_solvent,
                                                 subst_obj.charge, n_cores=n_cores_pp)

    cage_obj.add_substrate(subst_obj)
    cage_obj.charge = cage_obj.charge + substrate_charge

    if opt_cage_subst:
        if fix_cage_geom:
            cage_obj.optimise_cage_substrate(opt_atom_ids=cage_obj.substrate_atom_ids)
        else:
            cage_obj.optimise_cage_substrate(n_cores=n_cores_pp)

    if sp_cage_subst:
        cage_obj.cage_substrate_energy = singlepointenergy(cage_obj.cage_substrate_xyzs, cage_obj.cage_substrate_name,
                                                           Config.sp_keywords, Config.sp_solvent, cage_obj.charge,
                                                           n_cores=n_cores_pp)

    xyzs2xyzfile(cage_obj.cage_substrate_xyzs, basename=(cage_obj.name + '_' + subst_obj.name))

    return [cage_obj, subst_obj]


def gen_cage_subst_complexes_parallel(linker_dict, substrate_dict, substrate_charge=0, opt_linker=False, opt_cage=False,
                                      opt_substrate=False, opt_cage_subst=False, fix_cage_geom=False,
                                      metal_label='Pd', metal_charge=2, sp_cage=False, sp_substrate=False,
                                      sp_cage_subst=False, arch='m2l4'):
    """
    Parallel generation of cages-substrate complexes.

    This function assumes all the cages have the same metal, the linkers the same charge and the substrates the same
    charge. This is so the dictionaries can be of the form name : smiles.

    :param linker_dict: Dictionary of linker names and smiles strings. Examples are given in library/
    :param substrate_dict: Dictionary of substrate names and smiles strings. Examples are given in library/
    :return: A list of list lists in the form:
        [
         [[c_1, s_1], [c_1, s_2] ... [c_1, s_n]],
         [[c_2, s_1], [c_2, s_2] ... [c_2, s_n]],
         ...
        ]
    """

    # Generate Cage objects
    cages = gen_cages_parallel(linker_dict, opt_linker, opt_cage, metal_label, metal_charge, sp_cage, arch)

    # Generate Substrate objects
    n_cores_per_process = calc_n_cores_pp(substrate_dict)
    with Pool(processes=int(Config.n_cores / n_cores_per_process)) as pool:

        results = [pool.apply_async(Substrate, (subst_smiles, subst_name, 50,
                                                opt_substrate, substrate_charge, n_cores_per_process))
                   for subst_name, subst_smiles in substrate_dict.items()]

        subst_objs = [res.get(timeout=None) for res in results]

        if sp_substrate:
            results = [pool.apply_async(singlepointenergy, (substrate.xyzs, substrate.name, Config.sp_keywords,
                                                            Config.sp_solvent, substrate.charge, 1,
                                                            n_cores_per_process))
                       for substrate in subst_objs]

            subst_energies = [res.get(timeout=None) for res in results]
            for i in range(len(subst_energies)):
                subst_objs[i].energy = subst_energies[i]

    # Generate cage substrate structures
    n_cores_per_process = calc_n_cores_pp(linker_dict, substrate_dict)
    with Pool(processes=int(Config.n_cores / n_cores_per_process)) as pool:

        results = [[pool.apply_async(gen_cage_subst_complex,
                                     (None, None, None, None, substrate_charge, opt_linker, opt_cage, opt_substrate,
                                      opt_cage_subst, fix_cage_geom, metal_label, metal_charge, n_cores_per_process,
                                      sp_cage, sp_substrate, sp_cage_subst, cage, substrate, arch)
                                     )
                    for substrate in subst_objs] for cage in cages]

        cage_objs_subst_objs = [[res.get(timeout=None) for res in res1] for res1 in results]

    return cage_objs_subst_objs


def calc_binding_affinity(linker_name=None, linker_smiles=None, substrate_name=None, substrate_smiles=None,
                          substrate_charge=0, opt_linker=True, opt_cage=True, opt_substrate=True, opt_cage_subst=True,
                          fix_cage_geom=False, metal_label='Pd', metal_charge=2, n_cores_pp=None, sp_cage=True,
                          sp_substrate=True, sp_cage_subst=True, units_kcal_mol=True, units_kj_mol=False,
                          cage_obj=None, subst_obj=None, arch='m2l4'):
    """
    Calculate the binding affinity (in kcal mol-1 by default)
            ∆E = E_cage.substrate - (E_cage + E_substrate)
    First generate all the xyz files, then single point at some level of dft theory. Requires an ORCA install
    :return:
    """

    if not n_cores_pp:
        n_cores_pp = Config.n_cores

    if not cage_obj and not subst_obj:
        cage_obj, subst_obj = gen_cage_subst_complex(linker_name, linker_smiles, substrate_name, substrate_smiles,
                                                     substrate_charge, opt_linker, opt_cage, opt_substrate,
                                                     opt_cage_subst, fix_cage_geom, metal_label,
                                                     metal_charge, n_cores_pp, sp_cage, sp_substrate, sp_cage_subst,
                                                     cage_obj, subst_obj, arch)

    try:
        binding_affinity_ha = cage_obj.cage_substrate_energy - (cage_obj.energy + subst_obj.energy)
    except ValueError or TypeError or AttributeError:
        binding_affinity_ha = 999.9

    if units_kcal_mol:
        return binding_affinity_ha * Constants.ha2kcalmol
    if units_kj_mol:
        return binding_affinity_ha * Constants.ha2kJmol


def calc_binding_affinities_parallel(linker_dict, substrate_dict, substrate_charge=0, opt_linker=True, opt_cage=True,
                                     opt_substrate=True, opt_cage_subst=True, metal_label='Pd', metal_charge=2,
                                     fix_cage_geom=False, sp_cage=True, sp_substrate=True, sp_cage_subst=True,
                                     units_kcal_mol=True, units_kj_mol=False, heatplot=True, arch='m2l4'):
    """
        Parallel calculation of binding affinities.

        ∆E = E_cage_substrate - (E_cage + E_substrate)

        :param linker_dict: Dictionary of linker names and smiles strings. Examples are given in library/
        :param substrate_dict: Dictionary of substrate names and smiles strings. Examples are given in library/
        :return: Matrix of binding affinity values in the form:

        # substrate1    substrate 2
        [[     a,            b      ],      # linker 1
         [     c,            d      ],]     # linker 2
    """

    cage_objs_subst_objs = gen_cage_subst_complexes_parallel(linker_dict, substrate_dict, substrate_charge,
                                                             opt_linker, opt_cage, opt_substrate, opt_cage_subst,
                                                             fix_cage_geom, metal_label, metal_charge, sp_cage,
                                                             sp_substrate, sp_cage_subst, arch)

    if not Config.suppress_print:
        print("{:<30s}{:<50s}{:<10s}".format('Calculation of binding affinities', ' ', 'Running'))
    binding_affinities = np.zeros((len(linker_dict.keys()), len(substrate_dict.keys())))

    for i in range(len(linker_dict.keys())):
        for j in range(len(substrate_dict.keys())):
            binding_affinities[i, j] = calc_binding_affinity(cage_obj=cage_objs_subst_objs[i][j][0],
                                                             subst_obj=cage_objs_subst_objs[i][j][1],
                                                             units_kcal_mol=units_kcal_mol, units_kj_mol=units_kj_mol)
    if not Config.suppress_print:
        print("{:<30s}{:<50s}{:>10s}".format('', '', 'Done'))

    if heatplot:
        plot_heatmap(linker_dict.keys(), substrate_dict.keys(), binding_affinities, units_kcal_mol, units_kj_mol)

    print_binding_affinities(list(linker_dict.keys()), list(substrate_dict.keys()), binding_affinities,
                             units_kj_mol=units_kj_mol)

    return binding_affinities