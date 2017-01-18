import mock
import unittest
import logging

import PyTango
import pkg_resources

from devicetest import TangoTestContext

from katcore.testutils import cleanup_tempfile
from katcp.testutils import start_thread_with_cleanup
from mkat_tango.simlib import simdd_json_parser
from mkat_tango.simlib import sim_xmi_parser
from mkat_tango.simlib import tango_sim_generator
from mkat_tango.simlib.examples import override_class
from mkat_tango.testutils import ClassCleanupUnittestMixin


MODULE_LOGGER = logging.getLogger(__name__)

DEFAULT_TANGO_COMMANDS = ['State', 'Status', 'Init']

TANGO_CMD_PARAMS_NAME_MAP = {
    'name': 'cmd_name',
    'doc_in': 'in_type_desc',
    'dtype_in': 'in_type',
    'doc_out': 'out_type_desc',
    'dtype_out': 'out_type'}

# Mandatory parameters required to create a well configure Tango attribute.
EXPECTED_MANDATORY_ATTR_PARAMETERS = frozenset([
    "max_dim_x", "max_dim_y", "data_format", "period",
    "data_type", "writable", "name", "description", "delta_val",
    "max_alarm", "max_value", "min_value", "max_warning", "min_warning",
    "min_alarm", "unit", "delta_t", "label", "format"])

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
        'description': 'Current temperature outside near the telescope.',
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
        "min_warning": "-8",
        "max_warning": "49",
        'name': 'temperature',
        'period': '1000',
        'rel_change': '10',
        'unit': 'Degrees Centrigrade',
        'update_period': '1',
        'writable': 'READ'
    }

# The desired information for the On command when the weather_SIMDD
# json file is parsed by the SimddParser.
EXPECTED_ON_CMD_INFO = {
        'description': 'Turns On Device',
        'dformat_in': 'Scalar',
        'dformat_out': 'Scalar',
        'doc_in': 'No input parameter',
        'doc_out': 'Command responds',
        'dtype_in': 'Void',
        'dtype_out': 'String',
        'name': 'On',
        'actions': []
    }


class GenericSetup(unittest.TestCase):
    """A class providing the setUp method definition for the other test classes.
    """
    longMessage = True

    def setUp(self):
        super(GenericSetup, self).setUp()
        self.simdd_json_file = [pkg_resources.resource_filename(
            'mkat_tango.simlib.tests', 'weather_SIMDD.json')]
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
            for param in EXPECTED_MANDATORY_ATTR_PARAMETERS:
                self.assertIn(
                    param, attribute_metadata.keys(),
                    "The parsed attribute '%s' does not the mandotory parameter "
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
        pmq = sim_xmi_parser.PopulateModelQuantities(self.simdd_parser, device_name)

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
        pmq = sim_xmi_parser.PopulateModelQuantities(self.simdd_parser, device_name)
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
        pmq = sim_xmi_parser.PopulateModelQuantities(self.simdd_parser, device_name)
        model = pmq.sim_model
        sim_xmi_parser.PopulateModelActions(self.simdd_parser, device_name, model)

        actual_actions_list = model.sim_actions.keys()
        expected_actions_list = ['On', 'Off', 'StopRainfall', 'SetTemperature']
        self.assertEqual(set(actual_actions_list), set(expected_actions_list),
                         "There are actions missing in the model")

    def test_model_actions_metadata(self):
        """Testing that the model action metadata has been added correctly to the model.
        """
        device_name = 'tango/device/instance'
        pmq = sim_xmi_parser.PopulateModelQuantities(self.simdd_parser, device_name)
        model = pmq.sim_model
        cmd_info = self.simdd_parser.get_reformatted_cmd_metadata()
        sim_xmi_parser.PopulateModelActions(self.simdd_parser, device_name, model)
        sim_model_actions_meta = model.sim_actions_meta

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
        pmq = sim_xmi_parser.PopulateModelQuantities(self.simdd_parser, device_name)
        model = pmq.sim_model
        sim_xmi_parser.PopulateModelActions(self.simdd_parser, device_name, model)
        action_on = model.sim_actions['On']
        self.assertEqual(action_on.func.im_class, override_class.OverrideWeather)


class test_SimddDeviceIntegration(ClassCleanupUnittestMixin, unittest.TestCase):

    longMessage = True

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.tango_db = cleanup_tempfile(cls, prefix='tango', suffix='.db')
        cls.data_descr_file = [pkg_resources.resource_filename('mkat_tango.simlib.tests',
                                                               'weather_SIMDD.json')]
        # Since the sim_xmi_parser gets the simdd file from the device properties
        # in the tango database, here the method is mocked to return the simdd
        # file that found using the pkg_resources since it is included in the
        # test module
        with mock.patch(tango_sim_generator.__name__ + '.get_data_description_file_name'
                        ) as mock_get_description_file_name:
            mock_get_description_file_name.return_value = cls.data_descr_file[0]
            cls.properties = dict(sim_data_description_file=cls.data_descr_file[0])
            cls.device_name = 'test/nodb/tangodeviceserver'
            model = tango_sim_generator.configure_device_model(cls.data_descr_file,
                                                               cls.device_name)
            cls.TangoDeviceServer = tango_sim_generator.get_tango_device_server(model)
            cls.tango_context = TangoTestContext(cls.TangoDeviceServer,
                                                 device_name=cls.device_name,
                                                 db=cls.tango_db,
                                                 properties=cls.properties)
            start_thread_with_cleanup(cls, cls.tango_context)

    def setUp(self):
        super(test_SimddDeviceIntegration, self).setUp()
        self.device = self.tango_context.device
        self.instance = self.TangoDeviceServer.instances[self.device.name()]
        self.simdd_json_parser = simdd_json_parser.SimddParser()
        self.simdd_json_parser.parse(self.data_descr_file[0])

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
        expected_command_list.extend(DEFAULT_TANGO_COMMANDS)
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

    def test_StopRainfall_command(self):
        """Testing that the Tango device weather simulator 'detects' no rainfall when
        the StopRainfall command is executed.
        """
        command_name = 'StopRainfall'
        expected_result = 0.0
        self.device.command_inout(command_name)
        # The model needs 'dt' to be greater than the min_update_period for it to update
        # the model.quantity_state dictionary, so by manipulating the value of the last
        # update time of the model it will  ensure that the model.quantity_state
        # dictionary will be updated before reading the attribute value.
        self.instance.model.last_update_time = 0
        self.assertEqual(expected_result,
                         getattr(self.device.read_attribute('Rainfall'), 'value'),
                         "The value override action didn't execute successfully")

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


    def test_model_action_behaviour(self):
        device_name = 'tango/device/instance'
        pmq = sim_xmi_parser.PopulateModelQuantities(self.simdd_json_parser, device_name)
        model = pmq.sim_model
        sim_xmi_parser.PopulateModelActions(self.simdd_json_parser, device_name, model)
        action_set_temperature = model.sim_actions['SetTemperature']
        data_in = 25.0
        self.assertEqual(action_set_temperature(data_in), data_in)
