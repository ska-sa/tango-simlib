import os
import time
import logging
import unittest
import shutil
import tempfile
import subprocess

import PyTango
import pkg_resources

from tango_simlib.testutils import ClassCleanupUnittestMixin
from tango_simlib import tango_sim_generator, sim_xmi_parser, helper_module


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


class test_TangoSimGenDeviceIntegration(ClassCleanupUnittestMixin, unittest.TestCase):

    longMessage = True

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.data_descr_file = [pkg_resources.resource_filename('tango_simlib.tests',
                                                               'weather_sim.xmi')]
        cls.temp_dir = tempfile.mkdtemp()
        device_name = 'test/nodb/tangodeviceserver'
        server_name = 'weather_ds'
        server_instance = 'test'
        tango_class = tango_sim_generator.get_device_class(cls.data_descr_file)
        sim_device_prop = dict(sim_data_description_file=cls.data_descr_file[0])
        sim_test_device_prop = dict(model_key=device_name)
        tango_sim_generator.generate_device_server(
                server_name, cls.data_descr_file, cls.temp_dir)
        helper_module.generate_db_file(server_name, server_instance,
                                       device_name, cls.temp_dir,
                                       tango_class, sim_device_prop)
        helper_module.generate_db_file(server_name, server_instance,
                                       '%s1' % device_name, cls.temp_dir,
                                       '%sSimControl' % tango_class,
                                       sim_test_device_prop)
        # To ensure that the tango device server process will be the only
        # runnning process on port 12345, all process are killed on this port 
        subprocess.call('fuser -k 12345/tcp', shell=True)
        cls.sub_proc = subprocess.Popen('python %s/weather_ds.py test '
                                        '-file=%s/weather_ds_tango.db '
                                        '-ORBendPoint giop:tcp::12345' % (
                                           cls.temp_dir, cls.temp_dir),
                                        shell=True)
        # Note that the connection request must be delayed by atleast 1000 ms
        # of device server start up
        time.sleep(1)
        cls.sim_device = PyTango.DeviceProxy('localhost:12345/test/nodb/'
                                             'tangodeviceserver#dbase=no')
        cls.sim_test_device = PyTango.DeviceProxy('localhost:12345/test/nodb/'
                                                  'tangodeviceserver1#dbase=no')
        #shutil.rmtree(cls.tempfile)

    def setUp(self):
        super(test_TangoSimGenDeviceIntegration, self).setUp()
        # Reconnection to the device require atleast 1000 ms delay
        self.xmi_parser = sim_xmi_parser.XmiParser()
        self.xmi_parser.parse(self.data_descr_file[0])

    @classmethod
    def tearDownClass(cls):
        subprocess.call('fuser -k 12345/tcp', shell=True)
        shutil.rmtree(cls.temp_dir)

    def test_attribute_list(self):
        """ Testing whether the attributes specified in the POGO generated xmi file
        are added to the TANGO device
        """
        attributes = set(self.sim_device.get_attribute_list())
        expected_attributes = []
        default_attributes = {'State', 'Status'}
        for attribute_data in self.xmi_parser.device_attributes:
            expected_attributes.append(attribute_data['dynamicAttributes']['name'])
        self.assertEqual(set(expected_attributes), attributes - default_attributes,
                         "Actual tango device attribute list differs from expected "
                         "list!")

    def test_attribute_properties(self):
        attribute_list = self.sim_device.get_attribute_list()
        attribute_data = self.xmi_parser.get_reformatted_device_attr_metadata()

        for attr_name, attr_metadata in attribute_data.items():
            self.assertIn(attr_name, attribute_list,
                          "Device does not have the attribute %s" % (attr_name))
            attr_query_data = self.sim_device.attribute_query(attr_name)

            for attr_parameter in attr_metadata:
                expected_attr_value = attr_metadata[attr_parameter]
                attr_prop_value = getattr(attr_query_data, attr_parameter, None)
                # Here the writable property is checked for, since Pogo
                # expresses in as a string (e.g. 'READ') where tango device return a
                # Pytango object `PyTango.AttrWriteType.READ` and taking
                # its string returns 'READ' which corresponds to the Pogo one.
                if attr_parameter in ['writable']:
                    attr_prop_value = str(attr_prop_value)

                if attr_prop_value is None:
                    # In the case where no attr_query data is not found it is
                    # further checked in the mentioned attribute object
                    # i.e. alarms and events
                    # (check `self._test_tango_property_object`)
                    attr_prop_value = self._get_attribute_property_object_value(
                            attr_query_data, attr_parameter)

                # Here the data_type property is checked for, since Pogo
                # expresses in as a PyTango object (e.g.`PyTango.DevDouble`)
                # where tango device return a corresponding int value (e.g. 5)
                # and taking int of `PyTango.DevDouble` returns 5.
                if attr_parameter in ['data_type']:
                    expected_attr_value = int(expected_attr_value)

                # For some reason tango device attribute properties not
                # stated are assigned a string 'Not Specified' or even 'No
                # writable Specified'
                if 'No' in str(attr_prop_value):
                    attr_prop_value = ''

                # Pogo doesn't seem to populate the value for the format parameter
                # as expected i.e. format = '', and tango  device return (e.g. %6.2f for
                # floating points). TANGO library assigns a default value according to
                # the attributes data type.
                # '%6.2f' is the default for attributes that have a data type of
                # DevDouble and DevFloat, and for DevInt its '%d', and for DevString
                # and DevEnum it uses '%s'.
                if attr_parameter in ['format']:
                    attr_prop_value = ''

                self.assertEqual(expected_attr_value, attr_prop_value,
                                 "Non matching %s property for %s attribute" %
                                 (attr_parameter, attr_name))

    def _get_attribute_property_object_value(self, attr_query_data, user_default_prop):
        """Extracting the tango attribute property value from alarms an events objects

        Parameters
        ----------
        attr_query_data : PyTango.AttributeInfoEx
            data structure containing string arguments of attribute properties
        user_default_prop : str
            user default property as per items in `POGO_USER_DEFAULT_ATTR_PROP_MAP`

        Returns
        -------
        attr_prop_value : str
            tango attribute property value

        Note
        ----
         `self.sim_device.attribute_query(attr_name)` is
         a structure (inheriting from :class:`AttributeInfo`) containing
         available information for an attribute with the following members:
         - alarms : object containing alarm information (see AttributeAlarmInfo).
         - events : object containing event information (see AttributeEventInfo).
         Thus a sequence with desired attribute objects is defined and besides
         this object is the normal attribute properties, refere to
         POGO_USER_DEFAULT_ATTR_PROP_MAP keys dynamicAttributes and properties

        """
        tango_property_members = ['alarms', 'arch_event', 'ch_event', 'per_event']
        for member in tango_property_members:
            if member in ['alarms']:
                attr_prop_value = getattr(attr_query_data.alarms,
                                          user_default_prop, None)
            else:
                attr_prop_value = getattr(attr_query_data.events,
                                          member, None)
                # The per_event obect has attribute period
                # which is defferent from the object in the
                # POGO_USER_DEFAULT_ATTR_PROP_MAP (event_period)
                # used for # setting the value
                if 'period' in user_default_prop:
                    attr_prop_value = getattr(attr_prop_value,
                                              'period', None)
                else:
                    attr_prop_value = getattr(attr_prop_value,
                                              user_default_prop, None)
            if attr_prop_value:
                return attr_prop_value

    def test_command_list(self):
        """
        """
        actual_device_commands = set(self.sim_device.get_command_list()) - {'Init'}
        expected_command_list = set(self.xmi_parser.get_reformatted_cmd_metadata().keys())
        self.assertEquals(actual_device_commands, expected_command_list,
                          "The commands specified in the xmi file are not present in"
                          " the device")

    def test_command_properties(self):
        command_data = self.xmi_parser.get_reformatted_cmd_metadata()

        for cmd_name, cmd_metadata in command_data.items():
            cmd_config_info = self.sim_device.get_command_config(cmd_name)
            for cmd_prop, cmd_prop_value in cmd_metadata.items():
                self.assertTrue(
                    hasattr(cmd_config_info, TANGO_CMD_PARAMS_NAME_MAP[cmd_prop]),
                    "The cmd parameter '%s' for the cmd '%s' was not translated" %
                    (cmd_prop, cmd_name))
                if cmd_prop_value == 'none' or cmd_prop_value == '':
                    cmd_prop_value = 'Uninitialised'
                self.assertEqual(
                    getattr(cmd_config_info, TANGO_CMD_PARAMS_NAME_MAP[cmd_prop]),
                    cmd_prop_value, "The cmd parameter '%s/%s' values do not match" %
                    (cmd_prop, TANGO_CMD_PARAMS_NAME_MAP[cmd_prop]))
