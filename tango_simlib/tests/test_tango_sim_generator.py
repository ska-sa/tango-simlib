import time
import logging
import unittest
import shutil
import tempfile
import subprocess

import pkg_resources
import devicetest

from tango_simlib.testutils import ClassCleanupUnittestMixin
from tango_simlib import tango_sim_generator, sim_xmi_parser, helper_module

from tango_simlib.tests import test_sim_test_interface

MODULE_LOGGER = logging.getLogger(__name__)


class test_TangoSimGenDeviceIntegration(ClassCleanupUnittestMixin, unittest.TestCase):

    longMessage = True

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.port = helper_module.get_port()
        cls.host = helper_module.get_host_address()
        cls.data_descr_file = [pkg_resources.resource_filename(
            'tango_simlib.tests', 'Weather.xmi')]
        cls.temp_dir = tempfile.mkdtemp()
        cls.sim_device_class = tango_sim_generator.get_device_class(cls.data_descr_file)
        device_name = 'test/nodb/tangodeviceserver'
        server_name = 'weather_ds'
        server_instance = 'test'
        database_filename = '%s/%s_tango.db' % (cls.temp_dir, server_name)
        sim_test_device_prop = dict(model_key=device_name)
        patcher = devicetest.patch.Patcher()
        device_proxy = patcher.ActualDeviceProxy
        tango_sim_generator.generate_device_server(
                server_name, cls.data_descr_file, cls.temp_dir)
        helper_module.append_device_to_db_file(
                server_name, server_instance, device_name,
                database_filename, cls.sim_device_class)
        cls.db_instance = helper_module.append_device_to_db_file(
                            server_name, server_instance, '%scontrol' % device_name,
                            database_filename, '%sSimControl' % cls.sim_device_class,
                            sim_test_device_prop)
        cls.sub_proc = subprocess.Popen(["python", "{}/{}".format(
                                            cls.temp_dir, server_name),
                                        server_instance, "-file={}".format(
                                            database_filename),
                                        "-ORBendPoint", "giop:tcp::{}".format(
                                            cls.port)])
        # Note that tango demands that connection to the server must
        # be delayed by atleast 1000 ms of device server start up.
        time.sleep(1)
        cls.sim_device = device_proxy(
                '%s:%s/test/nodb/tangodeviceserver#dbase=no' % (
                    cls.host, cls.port))
        cls.sim_control_device = device_proxy(
                '%s:%s/test/nodb/tangodeviceservercontrol#dbase=no' % (
                    cls.host, cls.port))
        cls.addCleanupClass(cls.sub_proc.kill)
        cls.addCleanupClass(shutil.rmtree, cls.temp_dir)

    def setUp(self):
        super(test_TangoSimGenDeviceIntegration, self).setUp()
        self.xmi_parser = sim_xmi_parser.XmiParser()
        self.xmi_parser.parse(self.data_descr_file[0])
        self.expected_model = tango_sim_generator.configure_device_model(
                self.data_descr_file, self.sim_device.name())
        self.attr_name_enum_labels = sorted(
                self.sim_control_device.attribute_query(
                     'attribute_name').enum_labels)

    def test_device_attribute_list(self):
        """ Testing whether the attributes specified in the POGO generated xmi file
        are added to the TANGO device
        """
        attributes = set(self.sim_device.get_attribute_list())
        expected_attributes = []
        default_attributes = helper_module.DEFAULT_TANGO_DEVICE_ATTRIBUTES
        for attribute_data in self.xmi_parser.device_attributes:
            expected_attributes.append(attribute_data['dynamicAttributes']['name'])
        self.assertEqual(set(expected_attributes), attributes - default_attributes,
                         "Actual tango device attribute list differs from expected "
                         "list!")

    def test_device_command_list(self):
        """Testing whether commands are defined on the device as expected
        """
        actual_device_commands = set(self.sim_device.get_command_list()) - {'Init'}
        expected_command_list = set(self.xmi_parser.get_reformatted_cmd_metadata().keys())
        self.assertEquals(actual_device_commands, expected_command_list,
                          "The commands specified in the xmi file are not present in"
                          " the device")

    def test_write_device_properties_to_db(self):
        """Testing whether the device properties in the model are added to
        the tangoDB
        """
        tango_sim_generator.write_device_properties_to_db(
                self.sim_device.name(), self.expected_model, self.db_instance)
        expected_property_list = set(self.expected_model.sim_properties.keys())
        expected_properties = len(expected_property_list)
        db_info = self.db_instance.get_info()
        db_info_list = db_info.split('\n')
        device_prop_str = 'Device properties defined'
        device_control_props = 1  # One property already in data base file. line 45
        device_properties_defined = 0
        for item in db_info_list:
            if device_prop_str in item:
                device_properties_defined = item.split('=')[-1]
        self.assertEquals(expected_properties,
                          # device_properties_defined include all props in  db file)
                          # There are two devices in database file with sim
                          # control device having one (1) model_key props
                          int(device_properties_defined) - device_control_props,
                          "The device properties specified in the config file"
                          " are not same number as in the database")

    def test_sim_control_attribute_list(self):
        """Testing whether the attributes quantities in the model are added to
        the TANGO sim device controller
        """
        implemented_attr = helper_module.SIM_CONTROL_ADDITIONAL_IMPLEMENTED_ATTR
        control_attributes = test_sim_test_interface.control_attributes(
                self.expected_model)
        attributes = set(self.sim_control_device.get_attribute_list())
        self.assertEqual(
            attributes - implemented_attr,
            set(control_attributes))

    def test_sim_control_device_attribute_change(self):
        """Setting the desired attribute value for the device's attribute from
        the simulator controller device
        """
        desired_attribute_name = 'temperature'
        input_value = 100.0
        self.sim_control_device.attribute_name = self.attr_name_enum_labels.index(
                                                    desired_attribute_name)
        self.sim_control_device.pause_active = True
        setattr(self.sim_control_device, 'last_val', input_value)
        self.assertEqual(self.sim_device.temperature, input_value)
