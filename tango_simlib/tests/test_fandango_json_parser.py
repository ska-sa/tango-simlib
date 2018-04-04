"""This module tests the fandango_json_parser script.
"""
import unittest
import logging
import pkg_resources

import tango

from tango_simlib.utilities import fandango_json_parser

MODULE_LOGGER = logging.getLogger(__name__)


EXPECTED_DEVICE_PARAMETERS = [
    'commands', 'class_properties', 'name',
    'level', 'server', 'host', 'dev_class',
    'attributes', 'properties'
    ]

EXPECTED_CMD_PROPERTY_PARAMETERS = [
    'name', 'dtype_in',
    'doc_in', 'dtype_out',
    'doc_out'
    ]

INTERESTED_CMD_PROP = [
    EXPECTED_CMD_PROPERTY_PARAMETERS[1],
    EXPECTED_CMD_PROPERTY_PARAMETERS[3]
    ]

INTERESTED_ATTR_PROP = ['data_type', 'data_format']

EXPECTED_TANGO_TYPES = [tango._tango.CmdArgType, tango._tango.AttrDataFormat]

# The desired information for the attribute 'Status' when the database2
# json file is parsed by the FandangoExportDeviceParser.
EXPECTED_STATUS_ATTR_INFO = {
    'alarms': {
        'delta_t': 'Not specified',
        'delta_val': 'Not specified',
        'extensions': '[]',
        'max_alarm': 'Not specified',
        'max_warning': 'Not specified',
        'min_alarm': 'Not specified',
        'min_warning': 'Not specified'
        },
    'color': 'Lime',
    'data_format': tango._tango.AttrDataFormat.SCALAR,
    'data_type': tango._tango.CmdArgType.DevString,
    'database': 'monctl:10000',
    'description': '',
    'device': 'sys/database/2',
    'display_unit': 'No display unit',
    'events': {
        'arch_event': {
            'archive_abs_change': 'Not specified',
            'archive_period': 'Not specified',
            'archive_rel_change': 'Not specified',
            'extensions': '[]'
            },
        'ch_event': {
            'abs_change': 'Not specified',
            'extensions': '[]',
            'rel_change': 'Not specified'
            },
        'per_event': {
            'extensions': '[]',
            'period': '1000'
            }
        },
    'format': '%s',
    'label': 'Status',
    'max_alarm': 'Not specified',
    'min_alarm': 'Not specified',
    'model': 'monctl:10000/sys/database/2/Status',
    'name': 'Status',
    'polling': 0,
    'quality': 'ATTR_VALID',
    'standard_unit': 'No standard unit',
    'string': 'Device is OK',
    'time': 1521724934.799581,
    'unit': '',
    'value': 'Device is OK',
    'writable': 'READ'
    }


class GenericSetup(unittest.TestCase):
    """A class providing the setUp method definition for the other test classes.
    """
    longMessage = True

    def setUp(self):
        super(GenericSetup, self).setUp()
        self.fandango_json_file = pkg_resources.resource_filename(
            'tango_simlib.tests.config_files', 'database2.json')
        self.fandango_parser = fandango_json_parser.FandangoExportDeviceParser()
        self.fandango_parser.parse(self.fandango_json_file)


class TestFandangoJsonParser(GenericSetup):
    """A test class that tests that the fandango json parser works correctly.
    """
    def test_preprocess_command_types(self):
        """Testing that command property mapping was done well and command type
        of mapped properties is of tango type.
        """

        # testing that the command properties have been renamed to
        # match values in command signature
        for cmd_name in self.fandango_parser.get_device_command_metadata():
            self.assertEquals(
                EXPECTED_CMD_PROPERTY_PARAMETERS.sort(),
                self.fandango_parser.get_device_command_metadata()
                [cmd_name].keys().sort(),
                "The mapping of the command properties to the command"
                "signature wasn't successful for '%s' command" % (cmd_name)
                )
            # testing that data type of cmd property values is a tango type and
            # there is no occurence of 'Const' in the value of the cmd property
            for cmd_prop_value in [
                    self.fandango_parser.get_device_command_metadata()
                    [cmd_name][INTERESTED_CMD_PROP[0]],
                    self.fandango_parser.get_device_command_metadata()
                    [cmd_name][INTERESTED_CMD_PROP[1]]]:
                self.assertEquals(
                    str(cmd_prop_value).find('Const'), -1,
                    "The value (%s) of the cmd property, '%s', for the command, '%s',"
                    "has 'Const'" % (cmd_prop_value, INTERESTED_CMD_PROP[0], cmd_name)
                    )
                self.assertEquals(
                    EXPECTED_TANGO_TYPES[0], type(cmd_prop_value),
                    "The data type (%s) of the cmd property, '%s', of the command, '%s',"
                    "is not a tango type" % (cmd_prop_value, INTERESTED_CMD_PROP[0],
                                             cmd_name)
                    )

    def test_preprocess_attribute_types(self):
        """Testing values of attribute properties, 'data_type' and 'data_format',
        of all attributes are changed to tango types.
        """

        # testing that data type of specified attr property values is a tango type
        for attr_name in self.fandango_parser.get_device_attribute_metadata():
            self.assertEquals(
                EXPECTED_TANGO_TYPES[0],
                type(
                    self.fandango_parser.get_device_attribute_metadata()[attr_name]
                    [INTERESTED_ATTR_PROP[0]]
                    ),
                "The value of attr prop, '%s', of attr name, '%s', is not a tango type."
                % (INTERESTED_ATTR_PROP[0], attr_name)
                )
            self.assertEquals(
                EXPECTED_TANGO_TYPES[1],
                type(
                    self.fandango_parser.get_device_attribute_metadata()
                    [attr_name][INTERESTED_ATTR_PROP[1]]
                    ),
                "The value of attr prop, '%s', of attr name, '%s', is not a tango type."
                % (INTERESTED_ATTR_PROP[1], attr_name)
                )

    def test_parsed_attributes(self):
        """Testing that the attribute information parsed matches with the one captured
        in the fandango json file.
        """
        actual_parsed_attrs = self.fandango_parser.get_device_attribute_metadata()
        expected_attr_list = [
            'Status', 'Timing_maximum', 'Timing_average',
            'Timing_index', 'Timing_info', 'Timing_calls',
            'State', 'StoredProcedureRelease', 'Timing_minimum'
            ]
        actual_parsed_attr_list = actual_parsed_attrs.keys()
        self.assertGreater(
            len(actual_parsed_attr_list), 0,
            "There is no attribute information parsed"
            )
        self.assertEquals(
            expected_attr_list.sort(), actual_parsed_attr_list.sort(),
            "There are missing attributes"
            )

        # Using the 'Status' attribute expected results
        self.assertIn(
            'Status', actual_parsed_attrs.keys(),
            "The attribute temperature is not in the parsed attribute list"
            )
        actual_parsed_status_attr_info = actual_parsed_attrs['Status']
        # Compare the values of the attribute properties captured in the Jive
        # generated json file and the ones in the parsed attribute data structure.
        for prop in EXPECTED_STATUS_ATTR_INFO:
            self.assertEquals(
                actual_parsed_status_attr_info[prop], EXPECTED_STATUS_ATTR_INFO[prop],
                "The expected value for the parameter '%s' does not match with the actual"
                "value" % (prop))
