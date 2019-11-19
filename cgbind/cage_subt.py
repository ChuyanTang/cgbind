from cgbind.log import logger
from cgbind import add_substrate
from cgbind.input_output import print_output
from cgbind.geom import is_geom_reasonable
from cgbind import calculations
from cgbind.input_output import xyzs2xyzfile
from cgbind.add_substrate import energy_funcs


class CageSubstrateComplex:

    def print_xyzfile(self, force=False):
        if self.reasonable_geometry or force:
            xyzs2xyzfile(xyzs=self.xyzs, basename=self.name)

    def singlepoint(self, method, keywords, n_cores=1, max_core_mb=1000):
        return calculations.singlepoint(self, method, keywords, n_cores, max_core_mb)

    def optimise(self, method, keywords, n_cores=1, max_core_mb=1000, cartesian_constraints=None):
        return calculations.optimise(self, method, keywords, n_cores, max_core_mb, cartesian_constraints)

    def _get_energy_func(self, energy_method):

        energy_method_names = [func.__name__ for func in energy_funcs]
        if energy_method not in energy_method_names:
            logger.critical(f'Could not generate a cage-susbtrate complex with the {energy_method} method')
            print(f'Available methods are {energy_method_names}')
            exit()

        else:
            return [func for func in energy_funcs if func.__name__ == energy_method][0]

    def _reasonable_cage_substrate(self, cage, substrate):

        if cage is None or substrate is None:
            logger.error(f'Cannot build a cage-substrate complex for {self.name} either cage or substrate was None')
            return False

        attrs = [cage.charge, substrate.charge, cage.xyzs, substrate.xyzs, cage.m_ids, cage.n_atoms]
        if not all([attr is not None for attr in attrs]):
            logger.error(f'Cannot build a cage-substrate complex for {self.name} a required attribute was None')
            return False

        return True

    def _add_substrate(self):
        """
        Add a substrate to a cage.
        The binding mode will be determined by the number of heteroatoms etc. in the case of an M2L4 cage,
        :return:
        """
        print_output('Addition of', self.substrate.name, 'Running')
        logger.info('Adding the substrate to the center of the cage defined by the COM')

        self.xyzs = add_substrate.add_substrate_com(self)

        if self.xyzs is not None:
            self.reasonable_geometry = is_geom_reasonable(self.xyzs)
        else:
            logger.error('Cage-substrate xyzs are None')
            self.reasonable_geometry = False

        print_output('', self.substrate.name, 'Done')

    def __init__(self, cage, substrate, solvent=None, mult=1, n_subst_confs=1, n_init_geom=1, energy_method='repulsion'):
        """
        Generate a cage-substrate complex. It will be generated by minimising the energy given an energy method

        :param cage: (object)
        :param substrate: (object)
        :param solvent: (str)
        :param mult: (int) Multiplicity
        :param n_subst_confs: (int) Number of substrate conformations to try and fit
        :param n_init_geom: (int) Number of initial geometries to minimise the energy from - generated from rotations
        :param energy_method: (str) Energy method to use to minimise the energy
        """

        self.name = cage.name + '_' + substrate.name
        self.solvent = solvent
        self.mult = mult
        self.xyzs = None
        self.energy = None
        self.reasonable_geometry = False

        self.energy_func = self._get_energy_func(energy_method)

        self.n_subst_confs = n_subst_confs
        self.n_init_geom = n_init_geom

        if not self._reasonable_cage_substrate(cage, substrate):
            return

        self.cage = cage
        self.substrate = substrate
        self.charge = cage.charge + substrate.charge

        self._add_substrate()
