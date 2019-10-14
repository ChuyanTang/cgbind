import os
from datetime import date
from cgbind.log import logger
from cgbind.config import Config


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


def xyzfile2xyzs(filename):
    """
    Convert a standard xyz file into a list of xyzs
    :param filename:
    :return: List of xyzs
    """
    logger.info('Converting {} to list of xyzs'.format(filename))

    xyzs = []

    if os.path.exists(filename) and filename.endswith('.xyz'):
        with open(filename, 'r') as xyz_file:
            xyz_lines = xyz_file.readlines()[2:]
            for line in xyz_lines:
                atom_label, x, y, z = line.split()
                xyzs.append([atom_label, float(x), float(y), float(z)])

    else:
        logger.error('Could not read .xyz file')
        return None

    if len(xyzs) == 0:
        logger.error('Could not read xyz lines in {}'.format(filename))
        return None

    return xyzs


def mol2file_to_xyzs(filename):
    """
    Convert a .mol file into a standard set of xyzs in the form e.g [[C, 0.0, 0.0, 0.0], ...]

    :param filename: (str) name of the .mol file
    :return: (lis(list)) xyzs
    """
    logger.info('Converting .mol2 file to xyzs')

    try:
        mol_file_lines = open(filename, 'r').readlines()
    except IOError:
        logger.error('.mol2 file does not exist')
        return

    # Get the unformatted xyzs from the .mol2 file. The atom labels will not be standard
    unformat_xyzs, xyz_block = [], False
    for n_line, line in enumerate(mol_file_lines):

        if '@' in line and xyz_block:
            break

        if xyz_block:
            try:
                atom_label, x, y, z = line.split()[1:5]
                try:
                    unformat_xyzs.append([atom_label, float(x), float(y), float(z)])
                except TypeError:
                    logger.error('There was a problem with the .mol2 file')
                    return
            except IndexError:
                logger.error('There was a problem with the .mol2 file')

        # e.g.   @<TRIPOS>ATOM
        #        1 Pd1     -2.1334  12.0093  11.5778   Pd        1 RES1   2.0000
        if '@' in line and 'ATOM' in line and len(mol_file_lines[n_line+1].split()) == 9:
            xyz_block = True

    xyzs = []
    for xyz_line in unformat_xyzs:
        atom_label = xyz_line[0]

        # e.g. Pd1 or C58
        if atom_label[0].isalpha() and not atom_label[1].isalpha():
            xyzs.append([atom_label[0]] + xyz_line[1:])

        # e.g. Pd10
        elif atom_label[0].isalpha() and atom_label[1].isalpha():
            xyzs.append([atom_label[:2]] + xyz_line[1:])

        else:
            logger.error('Unrecognised atom type')
            return

    return xyzs


def print_output(process, name, state):

    if not Config.suppress_print:
        print("{:<30s}{:<50s}{:>10s}".format(process, name, state))

    return None
