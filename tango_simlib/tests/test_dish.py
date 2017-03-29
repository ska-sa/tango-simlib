import os
import time
import unittest
import subprocess
import pkg_resources
import devicetest

from functools import partial
from devicetest import DeviceTestCase
from mock import Mock

from tango_simlib import model, quantities
from tango_simlib import tango_sim_generator, helper_module
from tango_simlib.testutils import ClassCleanupUnittestMixin, cleanup_tempdir

from PyTango import DevState, AttrDataFormat


class test_TangoSimGenDeviceIntegration(ClassCleanupUnittestMixin, unittest.TestCase):

    longMessage = True

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.port = helper_module.get_port()
        cls.host = helper_module.get_host_address()
        cls.data_descr_files = []
        cls.data_descr_files.append(pkg_resources.resource_filename(
            'tango_simlib.tests', 'DishElementMaster.xmi'))
        cls.data_descr_files.append(pkg_resources.resource_filename(
            'tango_simlib.tests', 'DishElementMaster_SIMDD.json'))
        cls.temp_dir = cleanup_tempdir(cls)
        cls.sim_device_class = tango_sim_generator.get_device_class(cls.data_descr_files)
        device_name = 'test/nodb/tangodeviceserver'
        server_name = 'dish_ds'
        server_instance = 'test'
        database_filename = os.path.join('{}', '{}_tango.db').format(
            cls.temp_dir, server_name)
        sim_device_prop = dict(sim_data_description_file=cls.data_descr_files[0])
        sim_test_device_prop = dict(model_key=device_name)
        # Cannot create an instance of the DeviceProxy inside the test because the
        # devicetest module patches it as a side effect at import time. It does
        # save the original DeviceProxy class in the Patcher singleton, so get it
        # from there
        patcher = devicetest.patch.Patcher()
        device_proxy = patcher.ActualDeviceProxy
        tango_sim_generator.generate_device_server(
                server_name, cls.data_descr_files, cls.temp_dir)
        helper_module.append_device_to_db_file(
                server_name, server_instance, device_name,
                database_filename, cls.sim_device_class, sim_device_prop)
        helper_module.append_device_to_db_file(
                server_name, server_instance, '%scontrol' % device_name,
                database_filename, '%sSimControl' % cls.sim_device_class,
                sim_test_device_prop)
        cls.sub_proc = subprocess.Popen(["python", "{}/{}.py".format(
                                            cls.temp_dir, server_name),
                                        server_instance, "-file={}".format(
                                            database_filename),
                                        "-ORBendPoint", "giop:tcp::{}".format(
                                            cls.port)])
        cls.addCleanupClass(cls.sub_proc.kill)
        # Note that tango demands that connection to the server must
        # be delayed by atleast 1000 ms of device server start up.
        time.sleep(1)
        cls.sim_device = device_proxy(
                '%s:%s/test/nodb/tangodeviceserver#dbase=no' % (
                    cls.host, cls.port))
        cls.sim_control_device = device_proxy(
                '%s:%s/test/nodb/tangodeviceservercontrol#dbase=no' % (
                    cls.host, cls.port))

    def setUp(self):
        super(test_TangoSimGenDeviceIntegration, self).setUp()
        self.attr_name_enum_labels = list(self.sim_control_device.attribute_query(
                                          'attribute_name').enum_labels)

    def test_sim_control_command_list(self):
        device_commands = self.sim_control_device.get_command_list()
        self.assertEqual(
            EXPECTED_COMMAND_LIST,
            set(device_commands) - helper_module.DEFAULT_TANGO_DEVICE_COMMANDS)
        self.assertEqual(
            set(self.sim_device.get_command_list()) & EXPECTED_COMMAND_LIST,
            set(), "The device has commands meant for the test sim control device.")
