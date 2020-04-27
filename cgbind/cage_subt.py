from cgbind.log import logger
from cgbind import add_substrate
from cgbind.molecule import BaseStruct
from cgbind.add_substrate import energy_funcs
from cgbind.exceptions import CgbindCritical
from cgbind.exceptions import CannotBuildCSComplex


class CageSubstrateComplex(BaseStruct):

    def _set_energy_func(self, energy_method):
        """
        From an energy_method string get the corresponding function

        :param energy_method: (str) Name of the energy method to build a cage-substrate complex
        :return: (function) Energy function
        """

        energy_method_names = [func.__name__ for func in energy_funcs]
        if energy_method not in energy_method_names:
            logger.critical(f'Could not generate a cage-susbtrate complex with the {energy_method} method')
            raise CgbindCritical(message=f'Not a valid energy method. Available methods are {energy_method_names}')

        # Set the energy function to generate this cage substrate complex
        for func in energy_funcs:
            if func.__name__ == energy_method:
                self.energy_func = func

        return None

    def _check_reasonable_cage_substrate(self, cage, substrate):
        """
        Determine if the cage and substrate are 'reasonable' i.e. both exist and they have the appropriate attributes

        :param cage: (Cage object)
        :param substrate: (Substrate object)
        :return: (bool)
        """

        if cage is None or substrate is None:
            logger.error(f'Cannot build a cage-substrate complex for {self.name} either cage or substrate was None')
            raise CannotBuildCSComplex

        attrs = [cage.charge, substrate.charge, cage.atoms, substrate.atoms, cage.m_ids, cage.n_atoms]
        if not all([attr is not None for attr in attrs]) or (substrate.mol_obj is None and self.n_subst_confs > 1):
            logger.error(f'Cannot build a cage-substrate complex for {self.name} a required attribute was None')
            raise CannotBuildCSComplex

    def _add_substrate(self):
        """
        Add a substrate to a cage by minimising the energy from self.energy_func

        :return: None
        """
        logger.info('Adding the substrate to the center of the cage defined by the COM')
        logger.info(f'Using {self.energy_func.__name__}')

        # For electrostatic addition need partial atomic charges
        if self.energy_func.__name__ in ['electrostatic', 'electrostatic_fast']:

            estimate = True if self.energy_func.__name__ == 'electrostatic_fast' else False
            self.cage.charges = self.cage.get_charges(estimate=estimate)
            self.substrate.charges = self.substrate.get_charges(estimate=estimate)

            if self.cage.charges is None or self.substrate.charges is None:
                logger.error('Could not get partial atomic charges')
                return None

        xyzs = add_substrate.add_substrate_com(self)
        self.set_atoms(xyzs)

        return None

    def __init__(self, cage, substrate, solvent=None, mult=1, n_subst_confs=1, n_init_geom=50, energy_method='repulsion'):
        """
        Cage-substrate complex. Generated by minimising the energy given an energy method.
        Inherits from cgbind.molecule.BaseStruct

        :ivar self.energy_func: (function)
        :ivar self.binding_energy_kcal: (float) Binding energy of the substrate in kcal mol-1
        :ivar self.n_subst_confs: (int)
        :ivar self.n_init_geom: (int)
        :ivar self.name: (str) cage.name + '_' + substrate.name
        :ivar self.cage: (Cage object)
        :ivar self.substrate: (Substrate object)

        :param cage: (Cage object)
        :param substrate: (Substrate object)
        :param solvent: (str)
        :param mult: (int) Spin multiplicity of the cage-substrate complex
        :param n_subst_confs: (int) Number of substrate conformations to iterate over while minimising the energy
        :param n_init_geom: (int) Number of initial geometries to minimise the energy from (generated by random rotation)
        :param energy_method: (str) Name of the energy method to build the structure from
        """
        super(CageSubstrateComplex, self).__init__(name='cage_subst', charge=0, mult=mult, filename=None, solvent=solvent)

        self.reasonable_geometry = False
        self._set_energy_func(energy_method)
        self.binding_energy_kcal = None

        self.n_subst_confs = n_subst_confs
        self.n_init_geom = n_init_geom

        self._check_reasonable_cage_substrate(cage, substrate)
        self.name = f'{cage.name}_{substrate.name}'
        self.cage = cage
        self.substrate = substrate
        self.charge = cage.charge + substrate.charge

        self._add_substrate()
