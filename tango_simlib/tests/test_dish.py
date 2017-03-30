import unittest
import pkg_resources

from mock import Mock, call

from tango_simlib import tango_sim_generator
from tango_simlib.testutils import ClassCleanupUnittestMixin

from PyTango import DevFailed

DISH_ELEMENT_MASTER_COMMAND_LIST = frozenset([
    'Capture', 'ConfigureAttenuation', 'ConfigureBand1', 'ConfigureBand2',
    'ConfigureBand3', 'ConfigureBand4', 'ConfigureBand5', 'ConfigureNoiseDiode',
    'EnableEngInterface', 'LowPower', 'FlushCmdQueue', 'Scan', 'Slew',
    'SetMaintenanceMode', 'SetOperateMode', 'SetStandbyFPMode', 'SetStandbyLPMode',
    'SetStowMode', 'SetPntModelPars', 'Synchronise', 'Track'])

DISH_ELEMENT_MASTER_ATTRIBUTE_LIST = frozenset([
    'adminMode', 'band1CapabilityHealthStatus', 'band1CapabilityState',
    'band2CapabilityHealthStatus', 'band2CapabilityState',
    'band3CapabilityHealthStatus', 'band3CapabilityState',
    'band4CapabilityHealthStatus', 'band4CapabilityState',
    'band5CapabilityHealthStatus', 'band5CapabilityState',
    'centralLogLevel', 'configurationDelayExpected',
    'configurationProgress', 'controlMode', 'elementLogLevel',
    'healthState', 'obsMode', 'obsState', 'pointingState', 'powerState',
    'simulationMode', 'storageLogLevel', 'dishMode', 'achievedAzimuth',
    'achievedElevation', 'desiredAzimuth', 'desiredElevation', 'pointModelPars',
    'desiredPointing', 'achievedPointing'])

class test_DishElementMaster(ClassCleanupUnittestMixin, unittest.TestCase):

    longMessage = True

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.data_descr_files = []
        cls.data_descr_files.append(
            pkg_resources.resource_filename('tango_simlib.tests',
                                            'DishElementMaster.xmi'))
        cls.data_descr_files.append(pkg_resources.resource_filename(
            'tango_simlib.tests', 'DishElementMaster_SIMDD.json'))
        cls.device_name = 'test/nodb/tangodeviceserver'
        cls.model = tango_sim_generator.configure_device_model(
            cls.data_descr_files, cls.device_name)

    def setUp(self):
        super(test_DishElementMaster, self).setUp()

    def test_attribute_list(self):
        """Test device attribute list.

        Check whether the attributes specified in the POGO generated xmi file
        are added to the TANGO device

        """
        attributes = set(self.model.sim_quantities.keys())
        self.assertEqual(DISH_ELEMENT_MASTER_ATTRIBUTE_LIST, attributes,
                         "Actual tango device attribute list differs from expected "
                         "list! \n\n Missing attributes: \n {}".format(
                            DISH_ELEMENT_MASTER_ATTRIBUTE_LIST - attributes))

    def test_command_list(self):
        """Testing device command list.

        Check that the command list in the Tango device matches with the one
        specified in the SIMDD data description file.

        """
        actual_device_commands = set(self.model.sim_actions.keys())
        self.assertEquals(actual_device_commands,
                          DISH_ELEMENT_MASTER_COMMAND_LIST,
                         "Actual TANGO device command list differs from expected "
                         "list! \n\n Missing commands: \n {}".format(
                            DISH_ELEMENT_MASTER_COMMAND_LIST - actual_device_commands))

    def test_configure_band_x(self):
        timestamp = '2134231.30131'
        dish_mode_quant = self.model.sim_quantities['dishMode']
        dish_mode_enum_labels = dish_mode_quant.meta['enum_labels']
        # Pick one of the allowed modes ('OPERATE', 'STANDBY-FP') to test the successful
        # execution of the command.
        set_mode = dish_mode_enum_labels.index('OPERATE')
        dish_mode_quant.last_val = set_mode
        mock_time = Mock(return_value=float(timestamp))
        self.model.time_func = mock_time
        mock_set_val = Mock(
            side_effect=dish_mode_quant.set_val)
        dish_mode_quant.set_val = mock_set_val
        calls = [call(dish_mode_enum_labels.index('CONFIG'), float(timestamp)),
                 call(dish_mode_enum_labels.index('OPERATE'), float(timestamp))]
        for cmd_name in ['ConfigureBand1', 'ConfigureBand2', 'ConfigureBand3',
                         'ConfigureBand4', 'ConfigureBand5']:
            self.model.sim_actions[cmd_name](data_input=timestamp)
            num_method_calls = mock_set_val.call_count
            self.assertEquals(num_method_calls, 2)
            self.assertEquals(calls, mock_set_val.mock_calls)
            mock_set_val.reset_mock()

    def test_low_power(self):
        power_state_quant = self.model.sim_quantities['powerState']
        power_state_enum_labels = power_state_quant.meta['enum_labels']

        # Write a value to the quantity to override the default one which is a boolean
        # True value. Pick any value except for 'LOW'.
        power_state_quant.last_val = power_state_enum_labels.index('OFF')

        dish_mode_quant = self.model.sim_quantities['dishMode']
        dish_mode_enum_labels = dish_mode_quant.meta['enum_labels']

        for allowed_mode in ['STOW', 'MAINTENANCE']:
            dish_mode_quant.last_val = dish_mode_enum_labels.index(allowed_mode)
            self.model.sim_actions['LowPower']()
            self.assertEqual(power_state_quant.last_val, power_state_enum_labels.index('LOW'))

        for not_allowed_mode in ['OFF', 'STARTUP', 'SHUTDOWN', 'STANDBY-LP',
                                 'STANDBY-FP', 'CONFIG', 'OPERATE']:
            dish_mode_quant.last_val = dish_mode_enum_labels.index(not_allowed_mode)
            self.assertRaises(DevFailed, self.model.sim_actions['LowPower'])

    def test_set_maintenance_mode(self):
        dish_mode_quant = self.model.sim_quantities['dishMode']
        dish_mode_enum_labels = dish_mode_quant.meta['enum_labels']

        # Write a value to the quantity to override the default one which is a boolean
        # True value. Pick any value except for 'MAINTENACE'.
        dish_mode_quant.last_val = dish_mode_enum_labels.index('STANDBY-LP')

        for allowed_mode in ['STANDBY-LP', 'STANDBY-FP']:
            dish_mode_quant.last_val = dish_mode_enum_labels.index(allowed_mode)
            self.model.sim_actions['SetMaintenanceMode']()
            self.assertEqual(dish_mode_quant.last_val, dish_mode_enum_labels.index('MAINTENANCE'))

        for not_allowed_mode in ['OFF', 'STARTUP', 'SHUTDOWN', 'STOW',
                                 'MAINTENANCE', 'CONFIG', 'OPERATE']:
            dish_mode_quant.last_val = dish_mode_enum_labels.index(not_allowed_mode)
            self.assertRaises(DevFailed, self.model.sim_actions['SetMaintenanceMode'])

    def test_set_operate_mode(self):
        dish_mode_quant = self.model.sim_quantities['dishMode']
        dish_mode_enum_labels = dish_mode_quant.meta['enum_labels']

        # Write a value to the quantity to override the default one which is a boolean
        # True value. Pick any value except for 'MAINTENACE'.
        dish_mode_quant.last_val = dish_mode_enum_labels.index('STANDBY-LP')

        for allowed_mode in ['STANDBY-FP']:
            dish_mode_quant.last_val = dish_mode_enum_labels.index(allowed_mode)
            self.model.sim_actions['SetOperateMode']()
            self.assertEqual(dish_mode_quant.last_val, dish_mode_enum_labels.index('OPERATE'))

        for not_allowed_mode in ['OFF', 'STARTUP', 'SHUTDOWN', 'STOW', 'STANDBY-LP',
                                 'MAINTENANCE', 'CONFIG', 'OPERATE']:
            dish_mode_quant.last_val = dish_mode_enum_labels.index(not_allowed_mode)
            self.assertRaises(DevFailed, self.model.sim_actions['SetOperateMode'])

    def test_set_operate_mode(self):
        dish_mode_quant = self.model.sim_quantities['dishMode']
        dish_mode_enum_labels = dish_mode_quant.meta['enum_labels']

        # Write a value to the quantity to override the default one which is a boolean
        # True value. Pick any value except for 'MAINTENACE'.
        dish_mode_quant.last_val = dish_mode_enum_labels.index('STANDBY-LP')

        for allowed_mode in ['STANDBY-FP']:
            dish_mode_quant.last_val = dish_mode_enum_labels.index(allowed_mode)
            self.model.sim_actions['SetOperateMode']()
            self.assertEqual(dish_mode_quant.last_val, dish_mode_enum_labels.index('OPERATE'))

        for not_allowed_mode in ['OFF', 'STARTUP', 'SHUTDOWN', 'STOW', 'STANDBY-LP',
                                 'MAINTENANCE', 'CONFIG', 'OPERATE']:
            dish_mode_quant.last_val = dish_mode_enum_labels.index(not_allowed_mode)
            self.assertRaises(DevFailed, self.model.sim_actions['SetOperateMode'])

    def test_set_stow_mode(self):
        dish_mode_quant = self.model.sim_quantities['dishMode']
        dish_mode_enum_labels = dish_mode_quant.meta['enum_labels']
        pointing_state_quant = self.model.sim_quantities['pointingState']
        pointing_state_enum_labels = pointing_state_quant.meta['enum_labels']

        self.model.sim_actions['SetStowMode']()
        self.assertEqual(dish_mode_quant.last_val, dish_mode_enum_labels.index('STOW'))
        self.assertEqual(pointing_state_quant.last_val,
                         pointing_state_enum_labels.index('STOW'))

        # Need to test that the the elevation position is changing. Can possibly do this
        # by testing the TANGO device.
