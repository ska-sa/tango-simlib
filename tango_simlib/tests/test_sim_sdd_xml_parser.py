import logging
import unittest
import pkg_resources

from PyTango import DevDouble

from mkat_tango.simlib import sim_sdd_xml_parser
from mkat_tango.simlib import sim_xmi_parser

LOGGER = logging.getLogger(__name__)

expected_mandatory_monitoring_point_parameters = frozenset([
    "name", "id", "description", "data_type",
    "size", "writable", "samplingfrequency",
    "logginglevel"])

expected_mandatory_cmd_parameters = frozenset([
    "cmd_id", "cmd_name", "cmd_description", "cmd_type",
    "time_out", "max_retry", "time_for_exec", "available_modes",
    "cmd_params", "response_list"])


# The desired information for the monitoring point pressure when the WeatherSimulator_CN
# xml file is parsed by the SDDParser.
expected_pressure_mnt_pt_info = {
    'name': 'Pressure',
    'data_type': DevDouble,
    'description': None,
    'max_value': '1100',
    'min_value': '500',
    'size': '0',
    'writable': None,
    'possiblevalues': [],
    'samplingfrequency': {
        'DefaultValue': None,
        'MaxValue': None
    },
    'logginglevel': None
}
# The desired information for the 'On' command when the WeatherSimulator_CN xml file is
# parsed
expected_on_cmd_info = {
        'cmd_name': 'ON',
        'cmd_description': None,
        'cmd_id': None,
        'cmd_type': None,
        'time_out': None,
        'max_retry': None,
        'available_modes': {},
        'cmd_params': None,
        'response_list': {
            'msg': {
                'ParameterName': 'msg',
                'ParameterID': None,
                'ParameterValue': None
            },
            'gsm': {
                'ParamaterName': 'gsm',
                'ParameterID': None,
                'ParameterValue': None
            }
        }
}

class GenericSetup(unittest.TestCase):
    longMessage = True

    def setUp(self):
        super(GenericSetup, self).setUp()
        self.xml_file = [pkg_resources.resource_filename('mkat_tango.simlib.tests',
                                                         'WeatherSimulator_CN.xml')]
        self.xml_parser = sim_sdd_xml_parser.SDDParser()
        self.xml_parser.parse(self.xml_file[0])

class test_Sdd_Xml_Parser(GenericSetup):

    def test_parsed_monitoring_points(self):
        """Testing that the monitoring points' information parsed matches with the one
        captured in the XML file.
        """
        actual_parsed_mnt_pts = self.xml_parser.get_reformatted_device_attr_metadata()
        expected_monitoring_points_list = ['Insolation', 'Temperature', 'Pressure',
                                           'Rainfall', 'Relative_Humidity',
                                           'Wind_Direction', 'Wind_Speed']
        actual_parsed_monitoring_points_list = actual_parsed_mnt_pts.keys()
        self.assertGreater(len(actual_parsed_monitoring_points_list), 0,
                           "There is no monitoring points information parsed")
        self.assertEquals(set(expected_monitoring_points_list),
                          set(actual_parsed_monitoring_points_list),
                          'There are missing monitoring points')

        # Test if all the parsed monitoring points have the mandatory properties
        for mnt_pt_name, mnt_pt_metadata in actual_parsed_mnt_pts.items():
            for param_name in expected_mandatory_monitoring_point_parameters:
                self.assertIn(param_name, mnt_pt_metadata.keys(),
                              "The parsed monitoring point '%s' does not the mandatory"
                              " parameter '%s' " % (mnt_pt_name, param_name))

        # Using the made up pressure monitoring point's expected results as we haven't
        # generated the full test data for the other attributes.
        self.assertIn('Pressure', actual_parsed_mnt_pts.keys(),
                      "The attribute pressure is not in the parsed attribute list")
        actual_parsed_pressure_mnt_pt_info = actual_parsed_mnt_pts['Pressure']

        # Compare the values of the monitoring point's properties captured in the DSL
        # generated xml file and the ones in the parsed monitoring point's data
        # structure.
        for prop in expected_pressure_mnt_pt_info:
            self.assertEquals(actual_parsed_pressure_mnt_pt_info[prop],
                              expected_pressure_mnt_pt_info[prop],
                              "The expected value for the parameter '%s' does not match"
                              " with the actual value" % (prop))


class test_PopModelQuantities(GenericSetup):

    def test_model_quantities(self):
        """Testing that the model quantities that are added to the model match with
        the attributes specified in the XMI file.
        """
        device_name = 'tango/device/instance'
        pmq = sim_xmi_parser.PopulateModelQuantities(self.xml_parser, device_name)

        self.assertEqual(device_name, pmq.sim_model.name,
                         "The device name and the model name do not match.")
        expected_quantities_list = ['Insolation', 'Temperature', 'Pressure', 'Rainfall',
                                    'Relative_Humidity', 'Wind_Direction',
                                    'Wind_Speed']
        actual_quantities_list = pmq.sim_model.sim_quantities.keys()
        self.assertEqual(set(expected_quantities_list), set(actual_quantities_list),
                         "The are quantities missing in the model")


    def test_model_quantities_metadata(self):
        """Testing that the metadata of the quantities matches with the metadata data of
        the parsed monitoring points captured in the SDD xml file.
        """
        device_name = 'tango/device/instance'
        pmq = sim_xmi_parser.PopulateModelQuantities(self.xml_parser, device_name)
        self.assertEqual(device_name, pmq.sim_model.name,
                         "The device name and the model name do not match.")
        mnt_pt_metadata = self.xml_parser.get_reformatted_device_attr_metadata()
        for sim_quantity_name, sim_quantity in (
                pmq.sim_model.sim_quantities.items()):
            sim_quantity_metadata = getattr(sim_quantity, 'meta')
            mpt_meta = mnt_pt_metadata[sim_quantity_name]
            for mnt_pt_param_name, mnt_pt_param_val in mpt_meta.items():
                self.assertTrue(sim_quantity_metadata.has_key(mnt_pt_param_name),
                                "The param '%s' was not added to the model quantity"
                                " '%s'" % (mnt_pt_param_name, sim_quantity_name))
                self.assertEqual(sim_quantity_metadata[mnt_pt_param_name],
                                 mnt_pt_param_val, "The value of the param '%s' in the"
                                 " model quantity '%s' is not the same with the one"
                                 " captured in the SDD xml file for the monitoring"
                                 " point '%s'." % (mnt_pt_param_name, sim_quantity_name,
                                                  mnt_pt_param_name))
