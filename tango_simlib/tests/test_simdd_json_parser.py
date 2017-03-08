import mock
import unittest
import logging

import PyTango
import pkg_resources

from devicetest import TangoTestContext

from katcore.testutils import cleanup_tempfile
from katcp.testutils import start_thread_with_cleanup
from tango_simlib import simdd_json_parser, helper_module
from tango_simlib import sim_xmi_parser, model
from tango_simlib import tango_sim_generator
from tango_simlib.examples import override_class
from tango_simlib.testutils import ClassCleanupUnittestMixin


MODULE_LOGGER = logging.getLogger(__name__)

TANGO_CMD_PARAMS_NAME_MAP = {
    'name': 'cmd_name',
    'doc_in': 'in_type_desc',
    'dtype_in': 'in_type',
    'doc_out': 'out_type_desc',
    'dtype_out': 'out_type'}

# Mandatory parameters required to create a well configure Tango command.
EXPECTED_MANDATORY_CMD_PARAMETERS = frozenset([
    'dformat_in', 'dformat_out', 'doc_in',
    'doc_out', 'dtype_in', 'dtype_out', 'name', ])

# Mandatory parameters required by each override_class.
EXPECTED_MANDATORY_OVERRIDE_CLASS_PARAMETERS = frozenset([
    'class_name', 'module_directory', 'module_name', 'name'])

# The desired information for the attribute temperature when the weather_SIMDD
# json file is parsed by the SimddParser.
EXPECTED_TEMPERATURE_ATTR_INFO = {
        'abs_change': '0.5',
        'archive_abs_change': '0.5',
        'archive_period': '1000',
        'archive_rel_change': '10',
        'data_format': 'Scalar',
        'data_type': PyTango._PyTango.CmdArgType.DevDouble,
        'format': '6.2f',
        'delta_t': '1000',
        'delta_val': '0.5',
        'description': 'Current actual temperature outside near the telescope.',
        'display_level': 'OPERATOR',
        'event_period': '1000',
        'label': 'Outside Temperature',
        'max_alarm': '50',
        'max_bound': '50',
        'max_dim_x': '1',
        'max_dim_y': '0',
        'max_slew_rate': '1',
        'max_value': '51',
        'mean': '25',
        'min_alarm': '-9',
        'min_bound': '-10',
        'min_value': '-10',
        'min_warning': '-8',
        'max_warning': '49',
        'name': 'temperature',
        'quantity_simulation_type': 'GaussianSlewLimited',
        'period': '1000',
        'rel_change': '10',
        'std_dev': '5',
        'unit': 'Degrees Centrigrade',
        'update_period': '1000',
        'writable': 'READ'
    }


class GenericSetup(unittest.TestCase):
    """A class providing the setUp method definition for the other test classes.
    """
    longMessage = True

    def setUp(self):
        super(GenericSetup, self).setUp()
        self.simdd_json_file = [pkg_resources.resource_filename(
            'tango_simlib.tests', 'weather_SIMDD.json')]
        self.simdd_parser = simdd_json_parser.SimddParser()
        self.simdd_parser.parse(self.simdd_json_file[0])

class test_SimddJsonParser(GenericSetup):
    """A test class that tests that the SimddJsonParser works correctly.
    """

    def test_parsed_attributes(self):
        """Testing that the attribute information parsed matches with the one captured
        in the SIMDD json file.
        """
        actual_parsed_attrs = self.simdd_parser.get_reformatted_device_attr_metadata()
        expected_attr_list = ['input_comms_ok', 'insolation', 'pressure', 'rainfall',
                              'relative_humidity', 'temperature', 'wind_direction',
                              'wind_speed']
        actual_parsed_attr_list = sorted(actual_parsed_attrs.keys())
        self.assertGreater(
            len(actual_parsed_attr_list), 0, "There is no attribute information parsed")
        self.assertEquals(set(expected_attr_list), set(actual_parsed_attr_list),
                          'There are missing attributes')

        # Test if all the parsed attributes have the mandatory properties
        for attr_name, attribute_metadata in actual_parsed_attrs.items():
            for param in helper_module.DEFAULT_TANGO_ATTRIBUTE_PARAMETER_TEMPLATE.keys():
                self.assertIn(
                    param, attribute_metadata.keys(),
                    "The parsed attribute '%s' does not have the mandotory parameter "
                    "'%s' " % (attr_name, param))

        # Using the made up temperature attribute expected results as we
        # haven't generated the full test data for the other attributes.
        self.assertIn('temperature', actual_parsed_attrs.keys(),
                      "The attribute pressure is not in the parsed attribute list")
        actual_parsed_temperature_attr_info = actual_parsed_attrs['temperature']

        # Compare the values of the attribute properties captured in the POGO
        # generated xmi file and the ones in the parsed attribute data structure.
        for prop in EXPECTED_TEMPERATURE_ATTR_INFO:
            self.assertEquals(actual_parsed_temperature_attr_info[prop],
                              EXPECTED_TEMPERATURE_ATTR_INFO[prop],
                              "The expected value for the parameter '%s' does "
                              "not match with the actual value" % (prop))

    def test_parsed_override_info(self):
        """Testing that the class override information parsed matches with the one
        captured in the SIMDD json file.
        """
        actual_override_info = self.simdd_parser.get_reformatted_override_metadata()
        for klass_info in actual_override_info.values():
            for param in EXPECTED_MANDATORY_OVERRIDE_CLASS_PARAMETERS:
                self.assertIn(param, klass_info.keys(), "Class override info missing"
                              " some important parameter.")

class test_PopulateModelQuantities(GenericSetup):

    def test_model_quantities(self):
        """Testing that the model quantities that are added to the model match with
        the attributes specified in the XMI file.
        """
        device_name = 'tango/device/instance'
        pmq = model.PopulateModelQuantities(self.simdd_parser, device_name)
        self.assertEqual(device_name, pmq.sim_model.name,
                         "The device name and the model name do not match.")
        expected_quantities_list = ['insolation', 'temperature',
                                    'pressure', 'input_comms_ok',
                                    'rainfall', 'relative_humidity',
                                    'wind_direction', 'wind_speed']
        actual_quantities_list = pmq.sim_model.sim_quantities.keys()
        self.assertEqual(set(expected_quantities_list), set(actual_quantities_list),
                         "The are quantities missing in the model")

    def test_model_quantities_metadata(self):
        """Testing that the metadata of the quantities matches with the metadata
        data of the parsed attribute data captured in the SDD xml file.
        """
        device_name = 'tango/device/instance'
        pmq = model.PopulateModelQuantities(self.simdd_parser, device_name)
        self.assertEqual(device_name, pmq.sim_model.name,
                         "The device name and the model name do not match.")
        attribute_metadata = self.simdd_parser.get_reformatted_device_attr_metadata()
        for sim_quantity_name, sim_quantity in (
                pmq.sim_model.sim_quantities.items()):
            sim_quantity_metadata = getattr(sim_quantity, 'meta')
            attr_meta = attribute_metadata[sim_quantity_name]
            for attr_param_name, attr_param_val in attr_meta.items():
                self.assertTrue(sim_quantity_metadata.has_key(attr_param_name),
                                "The param '%s' was not added to the model quantity"
                                " '%s'" % (attr_param_name, sim_quantity_name))
                self.assertEqual(
                    sim_quantity_metadata[attr_param_name], attr_param_val,
                    "The value of the param '%s' in the model quantity '%s' is "
                    "not the same with the one captured in the SDD xml file "
                    "for the monitoring point '%s'." % (
                        attr_param_name, sim_quantity_name, attr_param_name))


EXPECTED_ACTION_SET_TEMPERATURE_METADATA = {
    "name": "SetTemperature",
    "description": "Sets the temperature value",
    "dtype_in": "Double",
    "doc_in": "Value to set quantity",
    "dformat_in": "",
    "dtype_out": "String",
    "doc_out": "Command responds",
    "dformat_out": "",
    "actions": [
        {"behaviour": "input_transform",
         "destination_variable": "temporary_variable"},
        {"behaviour": "side_effect",
         "source_variable": "temporary_variable",
         "destination_quantity": "temperature"},
        {"behaviour": "output_return",
         "source_variable": "temporary_variable"}]
}


class test_PopulateModelActions(GenericSetup):

    def test_model_actions(self):
        """Testing that the model actions that are added to the model match with
        the commands specified in the XMI file.
        """
        device_name = 'tango/device/instance'
        pmq = model.PopulateModelQuantities(self.simdd_parser, device_name)
        sim_model = pmq.sim_model
        model.PopulateModelActions(self.simdd_parser, device_name, sim_model)

        actual_actions_list = sim_model.sim_actions.keys()
        expected_actions_list = ['On', 'Off', 'StopRainfall', 'SetTemperature', 'Add',
                                 'StopQuantitySimulation', 'MultiplyStringBy3']
        self.assertEqual(set(actual_actions_list), set(expected_actions_list),
                         "There are actions missing in the model")

    def test_model_actions_metadata(self):
        """Testing that the model action metadata has been added correctly to the model.
        """
        device_name = 'tango/device/instance'
        pmq = model.PopulateModelQuantities(self.simdd_parser, device_name)
        sim_model = pmq.sim_model
        cmd_info = self.simdd_parser.get_reformatted_cmd_metadata()
        model.PopulateModelActions(self.simdd_parser, device_name, sim_model)
        sim_model_actions_meta = sim_model.sim_actions_meta

        for cmd_name, cmd_metadata in cmd_info.items():
            model_act_meta = sim_model_actions_meta[cmd_name]
            for action_parameter in EXPECTED_MANDATORY_CMD_PARAMETERS:
                self.assertIn(action_parameter, model_act_meta,
                              "The parameter is not in the action's metadata")
            self.assertEqual(cmd_metadata, model_act_meta,
                             "The action's %s metadata was not processed correctly" %
                             cmd_name)

    def test_model_actions_overrides(self):
        """Testing that the On command defined in the SIMDD file is mapped to the
        correct user-defined action handler provided in the override class.
        """
        device_name = 'tango/device/instance'
        pmq = model.PopulateModelQuantities(self.simdd_parser, device_name)
        sim_model = pmq.sim_model
        model.PopulateModelActions(self.simdd_parser, device_name, sim_model)
        action_on = sim_model.sim_actions['On']
        self.assertEqual(action_on.func.im_class, override_class.OverrideWeather)

    def test_model_action_behaviour(self):
        device_name = 'tango/device/instance'
        pmq = model.PopulateModelQuantities(self.simdd_parser, device_name)
        sim_model = pmq.sim_model
        model.PopulateModelActions(self.simdd_parser, device_name, sim_model)
        action_set_temperature = sim_model.sim_actions['SetTemperature']
        data_in = 25.00
        self.assertEqual(action_set_temperature(data_in), data_in)


class test_SimddDeviceIntegration(ClassCleanupUnittestMixin, unittest.TestCase):

    longMessage = True

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.tango_db = cleanup_tempfile(cls, prefix='tango', suffix='.db')
        cls.data_descr_file = [pkg_resources.resource_filename('tango_simlib.tests',
                                                               'weather_SIMDD.json')]
        cls.device_name = 'test/nodb/tangodeviceserver'
        model = tango_sim_generator.configure_device_model(cls.data_descr_file,
                                                           cls.device_name)
        cls.TangoDeviceServer = tango_sim_generator.get_tango_device_server(
                    model, cls.data_descr_file)[0]
        cls.tango_context = TangoTestContext(cls.TangoDeviceServer,
                                             device_name=cls.device_name,
                                             db=cls.tango_db)
        start_thread_with_cleanup(cls, cls.tango_context)

    def setUp(self):
        super(test_SimddDeviceIntegration, self).setUp()
        self.device = self.tango_context.device
        self.instance = self.TangoDeviceServer.instances[self.device.name()]
        self.instance.model.paused = True
        self.device.Init()
        self.simdd_json_parser = simdd_json_parser.SimddParser()
        self.simdd_json_parser.parse(self.data_descr_file[0])

        default_metadata_values = {}
        for quantity in self.instance.model.sim_quantities.keys():
            if hasattr(self.instance.model.sim_quantities[quantity], 'max_bound'):
                default_metadata_values[quantity] = (
                    self.instance.model.sim_quantities[quantity].max_bound)

        self.addCleanup(self._restore_model, default_metadata_values)

    def _restore_model(self, default_metadata_values):
        for quantity in self.instance.model.sim_quantities.keys():
            if hasattr(self.instance.model.sim_quantities[quantity], 'max_bound'):
                self.instance.model.sim_quantities[quantity].max_bound = (
                    default_metadata_values[quantity])

    def test_attribute_list(self):
        """ Testing whether the attributes specified in the POGO generated xmi file
        are added to the TANGO device
        """
        attributes = set(self.device.get_attribute_list())
        expected_attributes = []
        default_attributes = {'State', 'Status'}
        expected_attributes = (
            self.simdd_json_parser.get_reformatted_device_attr_metadata().keys())

        self.assertEqual(set(expected_attributes), attributes - default_attributes,
                         "Actual tango device attribute list differs from expected "
                         "list!")

    def test_command_list(self):
        """Testing that the command list in the Tango device matches with the one
        specified in the SIMDD data description file.
        """
        actual_device_commands = set(self.device.get_command_list())
        expected_command_list = (
            self.simdd_json_parser.get_reformatted_cmd_metadata().keys())
        expected_command_list.extend(helper_module.DEFAULT_TANGO_DEVICE_COMMANDS)
        self.assertEquals(actual_device_commands, set(expected_command_list),
                          "The commands specified in the SIMDD file are not present in"
                          " the device")

    def test_command_properties(self):
        """Testing that the command parameter information matches with the information
        captured in the SIMDD data description file.
        """
        command_data = self.simdd_json_parser.get_reformatted_cmd_metadata()
        extra_command_parameters = ['dformat_in', 'dformat_out', 'description',
                                    'actions']
        for cmd_name, cmd_metadata in command_data.items():
            cmd_config_info = self.device.get_command_config(cmd_name)
            for cmd_prop, cmd_prop_value in cmd_metadata.items():
                # Exclude parameters that are not part of the TANGO command configuration
                # information.
                if cmd_prop in extra_command_parameters:
                    continue
                self.assertTrue(
                    hasattr(cmd_config_info, TANGO_CMD_PARAMS_NAME_MAP[cmd_prop]),
                    "The cmd parameter '%s' for the cmd '%s' was not translated" %
                    (cmd_prop, cmd_name))
                if cmd_prop_value == 'none' or cmd_prop_value == '':
                    cmd_prop_value = 'Uninitialised'
                self.assertEqual(
                    getattr(cmd_config_info, TANGO_CMD_PARAMS_NAME_MAP[cmd_prop]),
                    cmd_prop_value, "The cmd %s parameter '%s/%s' values do not match" %
                    (cmd_name, cmd_prop, TANGO_CMD_PARAMS_NAME_MAP[cmd_prop]))

    def test_On_command(self):
        """Testing that the On command changes the value of the State attribute of the
        Tango device to ON.
        """
        command_name = 'On'
        expected_result = None
        self.device.command_inout(command_name)
        self.assertEqual(self.device.command_inout(command_name),
                         expected_result)
        self.assertEqual(getattr(self.device.read_attribute('State'), 'value'),
                         PyTango.DevState.ON)

    def test_Add_command(self):
        """Testing that the Tango device command can take input of an array type and
        return a output value of type double.
        """
        command_name = 'Add'
        command_args = [12, 45, 53, 32, 2.1, 0.452]
        expected_return_value = 144.552
        actual_return_value = self.device.command_inout(command_name, command_args)
        self.assertEqual(expected_return_value, actual_return_value, "The actual return"
                         "value does not match with the expected return value.")

    def test_MultiplyStringBy3_command(self):
        """Testing that the Tango device command can take input of type string and
        return an output value of type string.
        """
        command_name = 'MultiplyStringBy3'
        command_args = 'LMC'
        expected_return_value = 'LMCLMCLMC'
        actual_return_value = self.device.command_inout(command_name, command_args)
        self.assertEqual(expected_return_value, actual_return_value, "The actual return"
                         "value does not match with the expected return value.")

    def test_Off_command(self):
        """Testing that the Off command changes the State attribute's value of the Tango
        device to OFF.
        """
        command_name = 'Off'
        expected_result = None
        self.assertEqual(self.device.command_inout(command_name),
                         expected_result)
        self.assertEqual(getattr(self.device.read_attribute('State'), 'value'),
                         PyTango.DevState.OFF)

    def test_set_temperature_command(self):
        """Testing that the SetTemperature command changes the temperature
        attribute's value of the Tango device to the specified input parameter.
        """
        command_name = 'SetTemperature'
        data_in = 25.0
        expected_result = data_in
        self.assertEqual(self.device.command_inout(command_name, data_in),
                         expected_result)
        self.instance.model.last_update_time = 0
        # The tango device temperature attribute value return a floating number
        # thus it is rounded to two decimal places before checking if it's the
        # same as the `data_in` value
        self.assertEqual(round(getattr(self.device.read_attribute('Temperature'),
                               'value'), 2), data_in)


MKAT_VDS_ATTRIBUTE_LIST = frozenset(['camera_power_on', 'flood_lights_on',
                                     'focus_position', 'pan_position', 'pdu_connected',
                                     'ptz_controller_connected', 'snmpd_trap_running',
                                     'tilt_position', 'zoom_position'])
MKAT_VDS_COMMAND_LIST = frozenset(['CameraPowerOn', 'FloodLightOn', 'Focus', 'Pan',
                                   'PresetClear', 'PresetGoto', 'PresetSet', 'Stop',
                                   'Tilt', 'Zoom'])

class test_XmiSimddDeviceIntegration(ClassCleanupUnittestMixin, unittest.TestCase):

    longMessage = True

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.tango_db = cleanup_tempfile(cls, prefix='tango', suffix='.db')
        cls.data_descr_files = []
        cls.data_descr_files.append(pkg_resources.resource_filename('tango_simlib.tests',
                                                                    'MkatVds.xmi'))
        cls.data_descr_files.append(pkg_resources.resource_filename(
            'tango_simlib.tests', 'MkatVds_SIMDD.json'))
        cls.device_name = 'test/nodb/tangodeviceserver'
        model = tango_sim_generator.configure_device_model(
            cls.data_descr_files, cls.device_name)
        cls.TangoDeviceServer = tango_sim_generator.get_tango_device_server(
            model, cls.data_descr_files)[0]
        cls.tango_context = TangoTestContext(cls.TangoDeviceServer,
                                             device_name=cls.device_name,
                                             db=cls.tango_db)
        start_thread_with_cleanup(cls, cls.tango_context)

    def setUp(self):
        super(test_XmiSimddDeviceIntegration, self).setUp()
        self.device = self.tango_context.device
        self.instance = self.TangoDeviceServer.instances[self.device.name()]

    def test_attribute_list(self):
        """Test device attribute list.

        Check whether the attributes specified in the POGO generated xmi file
        are added to the TANGO device

        """
        attributes = set(self.device.get_attribute_list())
        default_attributes = {'State', 'Status'}
        self.assertEqual(MKAT_VDS_ATTRIBUTE_LIST, attributes - default_attributes,
                         "Actual tango device attribute list differs from expected "
                         "list! \n\n Missing attributes: \n {}".format(
                            MKAT_VDS_ATTRIBUTE_LIST - attributes))

    def test_command_list(self):
        """Testing device command list.

        Check that the command list in the Tango device matches with the one
        specified in the SIMDD data description file.

        """
        actual_device_commands = set(self.device.get_command_list())
        self.assertEquals(actual_device_commands -
                          helper_module.DEFAULT_TANGO_DEVICE_COMMANDS,
                          MKAT_VDS_COMMAND_LIST,
                          "The commands specified in the SIMDD file are not present in"
                          " the device")


class test_SourceSimulatorInfo(unittest.TestCase):
    """This class is not testing the code, but only testing that the test XMI and SIMDD
    files are consistant with each other.
    """
    longMessage = True

    def setUp(self):
        super(test_SourceSimulatorInfo, self).setUp()
        self.sim_xmi_file = [pkg_resources.resource_filename(
            'tango_simlib.tests', 'MkatVds.xmi')]
        self.simdd_json_file = [pkg_resources.resource_filename(
            'tango_simlib.tests', 'MkatVds_SIMDD.json')]
        self.simdd_parser = simdd_json_parser.SimddParser()
        self.xmi_parser = sim_xmi_parser.XmiParser()
        self.xmi_parser.parse(self.sim_xmi_file[0])
        self.simdd_parser.parse(self.simdd_json_file[0])

    def test_source_data_attributes(self):
        """Testing attribute information from data files.

        Check if the attribute information in the SIMDD is consistant with the"
        information captured in the XMI file generated using POGO.

        """
        xmi_parser_attributes = (
            self.xmi_parser.get_reformatted_device_attr_metadata())
        simdd_parser_attributes = (
            self.simdd_parser.get_reformatted_device_attr_metadata())

        for attribute_name in MKAT_VDS_ATTRIBUTE_LIST:
            self.assertIn(attribute_name, xmi_parser_attributes,
                          "The attribute '{}' is missing from the file: '{}'.".
                          format(attribute_name, self.sim_xmi_file[0]))

        for attribute_name in simdd_parser_attributes:
            self.assertIn(attribute_name, xmi_parser_attributes,
                          "The attribute '{}' specified in the file: '{}' is not"
                          " captured in the main config file: '{}'.".
                          format(attribute_name, self.simdd_json_file[0],
                                 self.sim_xmi_file[0]))

    def test_source_data_commands(self):
        """Testing command information from data files.

        Check if the commands information in the SIMDD is consistant with the"
        information captured in the XMI file generated using POGO.

        """
        xmi_parser_commands = (
            self.xmi_parser.get_reformatted_cmd_metadata())
        simdd_parser_commands = (
            self.simdd_parser.get_reformatted_cmd_metadata())

        for command_name in MKAT_VDS_COMMAND_LIST:
            self.assertIn(command_name, xmi_parser_commands,
                          "The command '{}' is missing from the file: '{}'.".
                          format(command_name, self.sim_xmi_file[0]))

        for command_name in simdd_parser_commands:
            self.assertIn(command_name, xmi_parser_commands,
                          "The command '{}' specified in the file: '{}' is not captured"
                          "in the main config file: '{}'.".format(
                              command_name, self.simdd_json_file[0],
                              self.sim_xmi_file[0]))

    def test_source_data_device_properties(self):
        """Testing device properties information from data files.

        Check if the device properties information in the SIMDD is consistant with the
        information captured in the XMI file generated using POGO.

        """
        xmi_parser_properties = (
            self.xmi_parser.get_reformatted_properties_metadata('deviceProperties'))
        simdd_parser_properties = (
            self.simdd_parser.get_reformatted_properties_metadata('deviceProperties'))

        for property_name in simdd_parser_properties:
            self.assertIn(property_name, xmi_parser_properties,
                         "The property '{}' specified in the file: '{}' is not captured"
                         " in the main config file: '{}'.".format(
                         property_name, self.simdd_json_file[0], self.sim_xmi_file[0]))

    def test_source_data_class_properties(self):
        """Testing if the class properties information in the SIMDD is consistant with the"
        information captured in the XMI file generated using POGO.
        """
        xmi_parser_properties = (
            self.xmi_parser.get_reformatted_properties_metadata('classProperties'))
        simdd_parser_properties = (
            self.simdd_parser.get_reformatted_properties_metadata('classProperties'))

        for property_name in simdd_parser_properties:
            self.assertIn(property_name, xmi_parser_properties,
                         "The property '{}' specified in the file: '{}' is not captured"
                         " in the main config file: '{}'.".format(
                         property_name, self.simdd_json_file[0], self.sim_xmi_file[0]))


class test_XmiSimddSupplementaryDeviceIntegration(ClassCleanupUnittestMixin,
                                                  unittest.TestCase):
    """A test class that tests the use of both the xmi and simdd.

    This ensures that the specified parameters in the simdd override that of
    the xmi when a simulator is generated.

    """
    longMessage = True

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.tango_db = cleanup_tempfile(cls, prefix='tango', suffix='.db')
        cls.data_descr_files = []
        cls.data_descr_files.append(pkg_resources.resource_filename(
            'tango_simlib.tests', 'weather_sim.xmi'))
        cls.data_descr_files.append(pkg_resources.resource_filename(
            'tango_simlib.tests', 'weather_supplementary_SIMDD.json'))
        cls.device_name = 'test/nodb/tangodeviceserver'
        model = tango_sim_generator.configure_device_model(
            cls.data_descr_files, cls.device_name)
        cls.TangoDeviceServer = tango_sim_generator.get_tango_device_server(
            model, cls.data_descr_files)[0]
        cls.tango_context = TangoTestContext(cls.TangoDeviceServer,
                                             device_name=cls.device_name,
                                             db=cls.tango_db)
        start_thread_with_cleanup(cls, cls.tango_context)

    def setUp(self):
        super(test_XmiSimddSupplementaryDeviceIntegration, self).setUp()
        self.device = self.tango_context.device
        self.instance = self.TangoDeviceServer.instances[self.device.name()]

    def test_xmi_simdd_attribute_parameters_when_both_specified(self):
        """Testing attribute parameters when both xmi and simdd are specified.

        Check whether the attribute parameters specified in the xmi and
        simdd files are properly parsed to the device and also ensuring that
        those of the simdd override the ones in xmi in the configured model

        """
        attr_with_overrriden_info = 'temperature'
        simdd_specified_temperature_attr_params = {
                'description': 'Current actual '
                'temperature outside near the telescope.',
                'min_value': '-15', 'max_value': '55'}
        for data_file in self.data_descr_files:
            if '.xmi' in data_file.lower():
                xmi_parser = sim_xmi_parser.XmiParser()
                xmi_parser.parse(data_file)
        expected_device_attr_xmi_info = (
                xmi_parser.get_reformatted_device_attr_metadata())
        expected_device_temperature_attr_overridden_info = dict(
                expected_device_attr_xmi_info[attr_with_overrriden_info],
                **simdd_specified_temperature_attr_params)
        # Creating a copy of the attribute info as specified in the xmi and
        # overriding it with that specified in the simdd then create a
        # structure of what is expected as a result of the combination of the two.
        expected_device_attr_xmi_info_copy = expected_device_attr_xmi_info.copy()
        expected_device_attr_xmi_info_copy[attr_with_overrriden_info] = (
                expected_device_temperature_attr_overridden_info)
        expected_device_attr_xmi_overridden = (
                expected_device_attr_xmi_info_copy)
        sim_quantities = self.instance.model.sim_quantities
        for expected_quantity in expected_device_attr_xmi_info.keys():
            self.assertIn(expected_quantity, sim_quantities,
                          "The attribute {} is not in the parsed "
                          "attribute list".format(expected_quantity))
            actual_device_attr_info = sim_quantities[expected_quantity].meta
            for prop in expected_device_attr_xmi_info[expected_quantity]:
                if prop not in simdd_specified_temperature_attr_params.keys():
                    self.assertEquals(
                            expected_device_attr_xmi_info[expected_quantity][prop],
                            actual_device_attr_info[prop],
                            "The {} quantity expected value for the parameter "
                            "'{}' does not match with the actual value in the "
                            "device model".format(expected_quantity, prop))
                self.assertEquals(
                        expected_device_attr_xmi_overridden[expected_quantity][prop],
                        actual_device_attr_info[prop],
                        "The {} quantity expected value for the overridden "
                        "parameter '{}' does not match with the actual value "
                        "in the device model".format(expected_quantity, prop))

    def test_xmi_simdd_command_parameters_when_both_specified(self):
        """Testing command parameters when both xmi and simdd are specified.

        Check whether the command parameters specified in the xmi and
        simdd files are properly parsed to the device and also ensuring that
        those of the simdd override the ones in xmi in the configured model

        """
        cmd_with_overrriden_info = 'On'
        simdd_specified_on_cmd_params = {'doc_in': 'No input parameter required',
                                         'doc_out': 'Command responds only'}
        for data_file in self.data_descr_files:
            if '.xmi' in data_file.lower():
                xmi_parser = sim_xmi_parser.XmiParser()
                xmi_parser.parse(data_file)
        expected_device_cmd_xmi_info = (
                xmi_parser.get_reformatted_cmd_metadata())
        expected_device_on_cmd_overridden_info = dict(
                expected_device_cmd_xmi_info[cmd_with_overrriden_info],
                **simdd_specified_on_cmd_params)
        # Creating a copy of the command info as specified in the xmi and
        # overriding it with that specified in the simdd then create a
        # structure of what is expected as a result of the combination of the two.
        expected_device_cmd_xmi_info_copy = expected_device_cmd_xmi_info.copy()
        expected_device_cmd_xmi_info_copy[cmd_with_overrriden_info] = (
                expected_device_on_cmd_overridden_info)
        expected_device_cmd_xmi_overridden = (
                expected_device_cmd_xmi_info_copy)
        sim_actions = self.instance.model.sim_actions_meta
        for expected_action in expected_device_cmd_xmi_info.keys():
            if expected_action not in helper_module.DEFAULT_TANGO_DEVICE_COMMANDS:
                self.assertIn(expected_action, sim_actions.keys(),
                              "The command {} is not in the parsed "
                              "command list".format(expected_action))
                actual_device_attr_info = sim_actions[expected_action]
                for prop in expected_device_cmd_xmi_info[expected_action]:
                    if prop not in simdd_specified_on_cmd_params.keys():
                        self.assertEquals(
                                expected_device_cmd_xmi_info[expected_action][prop],
                                actual_device_attr_info[prop],
                                "The {} action expected value for the parameter "
                                "'{}' does not match with the actual value in the "
                                "device model".format(expected_action, prop))
                    self.assertEquals(
                            expected_device_cmd_xmi_overridden[expected_action][prop],
                            actual_device_attr_info[prop],
                            "The {} action expected value for the overridden "
                            "parameter '{}' does not match with the actual value "
                            "in the device model".format(expected_action, prop))
