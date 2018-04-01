import mock
import unittest
import logging
import pkg_resources

import tango

from tango_simlib.utilities import fandango_json_parser, helper_module

MODULE_LOGGER = logging.getLogger(__name__)


EXPECTED_DEVICE_PARAMETERS = frozenset(['attributes', 'commands',
                                        'class_properties', 'properties',
                                        'dev_class'])


# Mandatory parameters required to create a well configure Tango command.
EXPECTED_CMD_PROPERTY_PARAMETERS = frozenset(['dtype_in', 'dtype_out'])

# The desired information for the attribute Status when the database2
# json file is parsed by the FandangoExportDeviceParser.
EXPECTED_STATUS_ATTR_INFO = {
        'alarms': {'delta_t': 'Not specified',
                    'delta_val': 'Not specified',
                    'extensions': '[]',
                    'max_alarm': 'Not specified',
                    'max_warning': 'Not specified',
                    'min_alarm': 'Not specified',
                    'min_warning': 'Not specified'},
        'color': 'Lime',
        'data_format': 'SCALAR',
        'data_type': 'DevString',
        'database': 'monctl:10000',
        'description': '',
        'device': 'sys/database/2',
        'display_unit': 'No display unit',
        'events': {'arch_event': {'archive_abs_change': 'Not specified',
                                    'archive_period': 'Not specified',
                                    'archive_rel_change': 'Not specified',
                                    'extensions': '[]'},
                    'ch_event': {'abs_change': 'Not specified',
                                  'extensions': '[]',
                                  'rel_change': 'Not specified'},
                    'per_event': {'extensions': '[]', 'period': '1000'}},
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
        'writable': 'READ'}


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

class test_fandangoJsonParser(GenericSetup):
    """A test class that tests that the SimddJsonParser works correctly.
    """

    def test_parsed_attributes(self):
        """Testing that the attribute information parsed matches with the one captured
        in the fandango json file.
        """
        actual_parsed_attrs = self.fandango_parser.get_device_attribute_metadata()
        
        expected_attr_list = ['Status', 'Timing_maximum', 'Timing_average', 
                              'Timing_index','Timing_info', 'Timing_calls',
                              'State', 'StoredProcedureRelease', 'Timing_minimum']
        actual_parsed_attr_list = sorted(actual_parsed_attrs.keys())
        self.assertGreater(len(actual_parsed_attr_list), 0, 
                           "There is no attribute information parsed")
        self.assertEquals(expected_attr_list, actual_parsed_attr_list,
                          'There are missing attributes')

#
#        # Using the made up temperature attribute expected results as we
#        # haven't generated the full test data for the other attributes.
#        self.assertIn('temperature', actual_parsed_attrs.keys(),
#                      "The attribute temperature is not in the parsed attribute list")
#        actual_parsed_temperature_attr_info = actual_parsed_attrs['temperature']
#
#        # Compare the values of the attribute properties captured in the POGO
#        # generated xmi file and the ones in the parsed attribute data structure.
#        for prop in EXPECTED_TEMPERATURE_ATTR_INFO:
#            self.assertEquals(actual_parsed_temperature_attr_info[prop],
#                              EXPECTED_TEMPERATURE_ATTR_INFO[prop],
#                              "The expected value for the parameter '%s' does "
#                              "not match with the actual value" % (prop))
#
#    def test_parsed_override_info(self):
#        """Testing that the class override information parsed matches with the one
#        captured in the SIMDD json file.
#        """
#        actual_override_info = self.simdd_parser.get_device_cmd_override_metadata()
#        for klass_info in actual_override_info.values():
#            for param in EXPECTED_MANDATORY_OVERRIDE_CLASS_PARAMETERS:
#                self.assertIn(param, klass_info.keys(), "Class override info missing"
#                              " some important parameter.")
        
    def test_preprocess_command_types(self):
        """Testing that command property mapping was done well and command type
        of mapped properties is of type tango
        """
        for i in self.fandango_parser.get_device_command_metadata():
            self.assertIn(EXPECTED_CMD_PROPERTY_PARAMETERS,i.keys(),"The mapping
                          "of the command properties to the command signature
                          wasn't successful")