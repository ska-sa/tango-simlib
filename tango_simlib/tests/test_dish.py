import time
import unittest
import pkg_resources
import mock

from mock import Mock, call

from tango import DevFailed
from tango.test_context import DeviceTestContext

from katcp.testutils import start_thread_with_cleanup

from tango_simlib import tango_sim_generator, model
from tango_simlib.utilities.testutils import ClassCleanupUnittestMixin, cleanup_tempfile


DISH_ELEMENT_MASTER_COMMAND_LIST = frozenset([
    'Capture', 'ConfigureAttenuation', 'ConfigureBand1', 'ConfigureBand2',
    'ConfigureBand3', 'ConfigureBand4', 'ConfigureBand5', 'ConfigureNoiseDiode',
    'EnableEngInterface', 'LowPower', 'LongRun', 'FlushCmdQueue', 'Scan', 'Slew',
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
            pkg_resources.resource_filename(
                'tango_simlib.tests.config_files', 'DishElementMaster.xmi'))
        cls.data_descr_files.append(pkg_resources.resource_filename(
            'tango_simlib.tests.config_files', 'DishElementMaster_SIMDD.json'))
        cls.device_name = 'test/nodb/tangodeviceserver'
        cls.model = tango_sim_generator.configure_device_model(
            cls.data_descr_files, cls.device_name)

    def setUp(self):
        super(test_DishElementMaster, self).setUp()
        self.addCleanup(self._reset_model_defaults)

    def _reset_model_defaults(self):
        for quantity in self.model.sim_quantities.values():
            quantity.last_val = 0.0

    def test_attribute_list(self):
        """Test device attribute list.

        Check whether the attributes specified in the POGO generated xmi file
        are added to the model.
        """
        attributes = set(self.model.sim_quantities.keys())
        self.assertEqual(DISH_ELEMENT_MASTER_ATTRIBUTE_LIST, attributes,
                         "Actual tango device attribute list differs from expected "
                         "list! \n\n Missing attributes: \n {}".format(
                            DISH_ELEMENT_MASTER_ATTRIBUTE_LIST - attributes))

    def test_command_list(self):
        """Testing device command list.

        Check that the command list in the model matches with the one specified in the
        XMI/SIMDD data description file.
        """
        actual_device_commands = set(self.model.sim_actions.keys())
        self.assertEquals(actual_device_commands,
                          DISH_ELEMENT_MASTER_COMMAND_LIST,
                         "Actual model action's list differs from expected "
                         "list! \n\n Missing actions: \n {}".format(
                            DISH_ELEMENT_MASTER_COMMAND_LIST - actual_device_commands))

    def test_configure_band_x(self):
        timestamp1 = '2134231.30131'
        timestamp2 = '2242522.58271'
        dish_mode_quant = self.model.sim_quantities['dishMode']
        dish_mode_enum_labels = dish_mode_quant.meta['enum_labels']
        mock_time = Mock(return_value=float(timestamp2))
        self.model.time_func = mock_time
        mock_set_val = Mock(side_effect=dish_mode_quant.set_val)
        dish_mode_quant.set_val = mock_set_val

        for allowed_mode in ['OPERATE', 'STANDBY-FP']:
            dish_mode_quant.last_val = dish_mode_enum_labels.index(allowed_mode)
            calls = [call(dish_mode_enum_labels.index('CONFIG'), float(timestamp1)),
                     call(dish_mode_enum_labels.index(allowed_mode), float(timestamp2))]
            for cmd_name in ['ConfigureBand1', 'ConfigureBand2', 'ConfigureBand3',
                             'ConfigureBand4', 'ConfigureBand5']:
                self.model.sim_actions[cmd_name](data_input=timestamp1)
                num_method_calls = mock_set_val.call_count
                self.assertEquals(num_method_calls, 2)
                self.assertEquals(calls, mock_set_val.mock_calls)
                mock_set_val.reset_mock()

        for not_allowed_mode in ['OFF', 'STARTUP', 'SHUTDOWN', 'STANDBY-LP',
                                 'MAINTENANCE', 'STOW', 'CONFIG']:
            for cmd_name in ['ConfigureBand1', 'ConfigureBand2', 'ConfigureBand3',
                             'ConfigureBand4', 'ConfigureBand5']:
                dish_mode_quant.last_val = dish_mode_enum_labels.index(not_allowed_mode)
                self.assertRaises(DevFailed, self.model.sim_actions[cmd_name])

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
            self.assertEqual(power_state_quant.last_val,
                             power_state_enum_labels.index('LOW'))
            # Reset the powerState to any other value except for 'LOW'.
            power_state_quant.last_val = power_state_enum_labels.index('OFF')

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
            self.assertEqual(dish_mode_quant.last_val,
                             dish_mode_enum_labels.index('MAINTENANCE'))
            # Reset the dishMode an allowed value, not 'MAINTENANCE'.
            dish_mode_quant.last_val = dish_mode_enum_labels.index('STANDBY-LP')

        for not_allowed_mode in ['OFF', 'STARTUP', 'SHUTDOWN', 'STOW',
                                 'MAINTENANCE', 'CONFIG', 'OPERATE']:
            dish_mode_quant.last_val = dish_mode_enum_labels.index(not_allowed_mode)
            self.assertRaises(DevFailed, self.model.sim_actions['SetMaintenanceMode'])

    def test_set_operate_mode(self):
        dish_mode_quant = self.model.sim_quantities['dishMode']
        dish_mode_enum_labels = dish_mode_quant.meta['enum_labels']

        # Set the dishMode to 'STANDBY-FP', the only allowed mode for the
        # 'SetOperateMode' command execution.
        dish_mode_quant.last_val = dish_mode_enum_labels.index('STANDBY-FP')
        self.model.sim_actions['SetOperateMode']()
        self.assertEqual(dish_mode_quant.last_val,
                         dish_mode_enum_labels.index('OPERATE'))
        # Reset the dishMode to 'STANDBY-FP'.
        dish_mode_quant.last_val = dish_mode_enum_labels.index('STANDBY-FP')

        for not_allowed_mode in ['OFF', 'STARTUP', 'SHUTDOWN', 'STOW', 'STANDBY-LP',
                                 'MAINTENANCE', 'CONFIG', 'OPERATE']:
            dish_mode_quant.last_val = dish_mode_enum_labels.index(not_allowed_mode)
            self.assertRaises(DevFailed, self.model.sim_actions['SetOperateMode'])

    def test_set_standby_fp_mode(self):
        dish_mode_quant = self.model.sim_quantities['dishMode']
        dish_mode_enum_labels = dish_mode_quant.meta['enum_labels']

        # Write a value to the quantity to override the default one which is a boolean
        # True value. Pick any value except for 'STANDBY-FP'.
        dish_mode_quant.last_val = dish_mode_enum_labels.index('STANDBY-LP')

        for allowed_mode in ['STANDBY-LP', 'STOW', 'OPERATE', 'MAINTENANCE']:
            dish_mode_quant.last_val = dish_mode_enum_labels.index(allowed_mode)
            self.model.sim_actions['SetStandbyFPMode']()
            self.assertEqual(dish_mode_quant.last_val,
                             dish_mode_enum_labels.index('STANDBY-FP'))
            # Reset the dishMode to any other value except for 'STANDBY-FP'
            dish_mode_quant.last_val = dish_mode_enum_labels.index('STANDBY-LP')

        for not_allowed_mode in ['OFF', 'STARTUP', 'SHUTDOWN', 'STANDBY-FP',
                                 'CONFIG']:
            dish_mode_quant.last_val = dish_mode_enum_labels.index(not_allowed_mode)
            self.assertRaises(DevFailed, self.model.sim_actions['SetStandbyFPMode'])

    def test_set_standby_lp_mode(self):
        dish_mode_quant = self.model.sim_quantities['dishMode']
        dish_mode_enum_labels = dish_mode_quant.meta['enum_labels']

        # Write a value to the quantity to override the default one which is a boolean
        # True value. Pick any value except for 'MAINTENACE'.
        dish_mode_quant.last_val = dish_mode_enum_labels.index('STANDBY-LP')

        for allowed_mode in ['STANDBY-LP', 'STARTUP', 'SHUTDOWN', 'STANDBY-FP',
                             'MAINTENANCE', 'STOW', 'CONFIG', 'OPERATE', 'OFF']:
            dish_mode_quant.last_val = dish_mode_enum_labels.index(allowed_mode)
            self.model.sim_actions['SetStandbyLPMode']()
            self.assertEqual(dish_mode_quant.last_val,
                             dish_mode_enum_labels.index('STANDBY-LP'))
            # Reset the dishMode to any other value except for 'STANDBY-LP'
            dish_mode_quant.last_val = dish_mode_enum_labels.index('OPERATE')

    def test_set_stow_mode(self):
        dish_mode_quant = self.model.sim_quantities['dishMode']
        dish_mode_enum_labels = dish_mode_quant.meta['enum_labels']
        pointing_state_quant = self.model.sim_quantities['pointingState']
        pointing_state_enum_labels = pointing_state_quant.meta['enum_labels']

        self.model.sim_actions['SetStowMode']()
        self.assertEqual(dish_mode_quant.last_val,
                         dish_mode_enum_labels.index('STOW'))
        self.assertEqual(pointing_state_quant.last_val,
                         pointing_state_enum_labels.index('STOW'))

        self.assertEqual(self.model.sim_quantities['achievedElevation'].last_val, 0.0)
        self.assertEqual(self.model.sim_quantities['desiredElevation'].last_val, 90.0)

        self.model.last_update_time = 0.0
        # Fixed time updates for the model with the MAX_ELEV_DRIVE_RATE of 1.0.
        sim_time_update = [0.99, 10.99, 20.99, 30.99, 40.99,
                           50.99, 60.99, 70.99, 80.99, 90.99]
        with mock.patch.object(self.model, 'time_func') as mock_time:
            mock_time.side_effect = sim_time_update

            for update_x in sim_time_update:
                initial_actual_elevation = (
                    self.model.sim_quantities['achievedElevation'].last_val)
                self.model.update()
                self.assertGreater(
                    self.model.sim_quantities['achievedElevation'].last_val,
                    initial_actual_elevation)
                self.assertEqual(
                    self.model.sim_quantities['achievedAzimuth'].last_val, 0.0)
                self.assertEqual(
                    self.model.sim_quantities['achievedElevation'].last_update_time,
                    update_x)
                self.assertEqual(
                    self.model.sim_quantities['achievedAzimuth'].last_update_time,
                    update_x)

        self.assertEqual(self.model.sim_quantities['achievedElevation'].last_val,
                         self.model.sim_quantities['desiredElevation'].last_val)
        self.assertEqual(pointing_state_quant.last_val,
                         pointing_state_enum_labels.index('READY'))

    def test_slew(self):
        dish_mode_quant = self.model.sim_quantities['dishMode']
        dish_mode_enum_labels = dish_mode_quant.meta['enum_labels']
        pointing_state_quant = self.model.sim_quantities['pointingState']
        pointing_state_enum_labels = pointing_state_quant.meta['enum_labels']

        dish_mode_quant.last_val = dish_mode_enum_labels.index('OPERATE')
        self.assertNotEqual(pointing_state_quant.last_val,
                            pointing_state_enum_labels.index('SLEW'))
        dummy_timestamp = '31351.131'
        target_azim = 180.0
        target_elev = 90.0
        self.model.sim_actions['Slew'](data_input=
                                       [dummy_timestamp, target_azim, target_elev])
        self.assertEqual(self.model.sim_quantities['desiredAzimuth'].last_val, target_azim)
        self.assertEqual(self.model.sim_quantities['desiredElevation'].last_val, target_elev)
        self.assertEqual(self.model.sim_quantities['desiredPointing'].last_val,
                         [target_azim, target_elev])

        self.model.last_update_time = 0.0
        # Fixed time updates for the model with the MAX_ELEV_DRIVE_RATE of 1.0 and
        # MAX_AZIM_DRIVE_RATE of 2.0
        expected_azim_positions = [2.00, 22.00, 42.00, 62.00, 82.00,
                                   102.00, 122.00, 142.00, 162.00, 180.00]
        expected_elev_positions = [1.00, 11.00, 21.00, 31.00, 41.00,
                                   51.00, 61.00, 71.00, 81.00, 90.00]
        sim_time_update = [1.00, 11.00, 21.00, 31.0, 41.00,
                           51.00, 61.00, 71.00, 81.00, 91.00, 120.00]

        with mock.patch.object(self.model, 'time_func') as mock_time:
            mock_time.side_effect = sim_time_update

            for update_x, expected_azim_position, expected_elev_position in zip(
                    sim_time_update, expected_azim_positions, expected_elev_positions):
                initial_actual_azimuth = (
                    self.model.sim_quantities['achievedAzimuth'].last_val)
                initial_actual_elevation = (
                    self.model.sim_quantities['achievedElevation'].last_val)
                self.model.update()
                self.assertGreater(self.model.sim_quantities['achievedAzimuth'].last_val,
                                   initial_actual_azimuth)
                self.assertGreater(self.model.sim_quantities['achievedElevation'].last_val,
                                   initial_actual_elevation)
                self.assertEqual(self.model.sim_quantities['achievedAzimuth'].last_val,
                                 expected_azim_position)
                self.assertEqual(self.model.sim_quantities['achievedElevation'].last_val,
                                 expected_elev_position)
                self.assertEqual(
                    self.model.sim_quantities['achievedElevation'].last_update_time,
                    update_x)
                self.assertEqual(
                    self.model.sim_quantities['achievedAzimuth'].last_update_time,
                    update_x)
            # Update the model once more and ensure that azim/elev positions do not change.
            self.model.update()
            self.assertEqual(self.model.last_update_time, 120.00)
            self.assertEqual(
                self.model.sim_quantities['achievedAzimuth'].last_update_time,
                sim_time_update[-2])
            self.assertEqual(
                self.model.sim_quantities['achievedElevation'].last_update_time,
                sim_time_update[-2])
            self.assertEqual(self.model.sim_quantities['achievedAzimuth'].last_val,
                             self.model.sim_quantities['desiredAzimuth'].last_val)
            self.assertEqual(self.model.sim_quantities['achievedElevation'].last_val,
                             self.model.sim_quantities['desiredElevation'].last_val)
            self.assertEqual(pointing_state_quant.last_val,
                             pointing_state_enum_labels.index('READY'))

    def test_long_running(self):
        with mock.patch('time.sleep') as sleep_mock:
            # We use the value '4.5' as an arbitrary value here
            self.model.sim_actions['LongRun'](4.5)
            # We use value '5' as the time the long_running cmd is going sleep for.
            calls = [call(5)]
            num_method_calls = sleep_mock.call_count
            self.assertEquals(num_method_calls, 1, "The mocked method 'sleep' was called"
                              " more than once.")
            self.assertEquals(calls, sleep_mock.mock_calls, "The calls made to the"
                              " mocked method 'sleep' are not the same.")



class test_Device(ClassCleanupUnittestMixin, unittest.TestCase):

    longMessage = True

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.tango_db = cleanup_tempfile(cls, prefix='tango', suffix='.db')
        cls.data_descr_files = []
        cls.data_descr_files.append(
            pkg_resources.resource_filename(
                'tango_simlib.tests.config_files', 'DishElementMaster.xmi'))
        cls.data_descr_files.append(pkg_resources.resource_filename(
            'tango_simlib.tests.config_files', 'DishElementMaster_SIMDD.json'))
        cls.device_name = 'test/nodb/tangodeviceserver'
        model = tango_sim_generator.configure_device_model(cls.data_descr_files,
                                                           cls.device_name)
        cls.TangoDeviceServer = tango_sim_generator.get_tango_device_server(
                model, cls.data_descr_files)[0]
        cls.tango_context = DeviceTestContext(cls.TangoDeviceServer,
                                              device_name=cls.device_name,
                                              db=cls.tango_db)
        start_thread_with_cleanup(cls, cls.tango_context)

    def setUp(self):
        super(test_Device, self).setUp()
        self.device = self.tango_context.device

    def test_long_running(self):
        """Testing the device's long running command."""
        long_running_cmd_min_exec_time = 5
        expected_runtime = 5.00
        self.device.set_timeout_millis(5100)
        initial_time = time.time()
        # We use the value '4.5' as an arbitrary value here as the cmd is expecting
        # an input of type DevFloat.
        self.device.command_inout('LongRun', 4.5)
        final_time = time.time()
        actual_runtime = final_time - initial_time
        self.assertGreater(actual_runtime, long_running_cmd_min_exec_time,
                           "The long-running command 'LongRun' did not run for as long"
                           " as expected.")
        self.assertAlmostEqual(expected_runtime, actual_runtime, delta=0.01)
