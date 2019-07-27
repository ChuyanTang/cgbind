import os
from .log import logger
from datetime import date
from .config import Config


def print_binding_affinities(ligand_names, substrate_names, binding_affinities, units_kj_mol=False):
    """
    For an array of binding affinities print it to a formatted file

    :param ligand_names:
    :param substrate_names:
    :param binding_affinities:
    :param units_kj_mol:
    :return:
    """
    logger.info('Printing binding affinities as txt file')

    with open('binding_affinities.txt', 'w') as out_file:

        units = 'kcal mol^-1'
        if units_kj_mol:
            units = 'kJ mol^-1'

        print('Binding affinities (∆E) in', units, 'generated by cgbind on', str(date.today()),
              end='\n\n', file=out_file)
        [print(',' + substrate_name, end='', file=out_file) for substrate_name in substrate_names]
        for i in range(len(ligand_names)):
            print('\n', ligand_names[i], end=',', file=out_file)
            [print(binding_affinities[i, j], end=',', file=out_file) for j in range(len(substrate_names))]

    return 0


def xyzs2xyzfile(xyzs, filename=None, basename=None, title_line=''):
    """
    For a list of xyzs in the form e.g [[C, 0.0, 0.0, 0.0], ...] convert create a standard .xyz file

    :param xyzs: List of xyzs
    :param filename: Name of the generated xyz file
    :param basename: Name of the generated xyz file without the file extension
    :param title_line: String to print on the title line of an xyz file
    :return: The filename
    """
    if basename:
        filename = basename + '.xyz'

    if filename is None:
        logger.error('Could not print an .xyz. Filename was None')
        return 1

    if filename.endswith('.xyz'):
        with open(filename, 'w') as xyz_file:
            if xyzs is not None:
                print(len(xyzs), '\n', title_line, sep='', file=xyz_file)
            else:
                logger.error('No xyzs to print')
                return 1
            [print('{:<3}{:^10.5f}{:^10.5f}{:^10.5f}'.format(*line), file=xyz_file) for line in xyzs]

    return filename


def xyzfile2xyzs(xyz_filename):
    """
    Convert a standard xyz file into a list of xyzs
    :param xyz_filename:
    :return: List of xyzs
    """
    logger.info('Converting {} to list of xyzs'.format(xyz_filename))

    xyzs = []

    if os.path.exists(xyz_filename) and xyz_filename.endswith('.xyz'):
        with open(xyz_filename, 'r') as xyz_file:
            xyz_lines = xyz_file.readlines()[2:]
            for line in xyz_lines:
                atom_label, x, y, z = line.split()
                xyzs.append([atom_label, float(x), float(y), float(z)])

    else:
        logger.error('Could not read .xyz file')
        return None

    if len(xyzs) == 0:
        logger.error('Could not read xyz lines in {}'.format(xyz_filename))
        return None

    return xyzs


def print_output(process, name, state):

    if not Config.suppress_print:
        print("{:<30s}{:<50s}{:>10s}".format(process, name, state))

    return None
