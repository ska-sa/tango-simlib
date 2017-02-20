import os
import time
import unittest
import subprocess

import pkg_resources
import devicetest

from functools import partial

from devicetest import DeviceTestCase

from tango_simlib import sim_test_interface, model, quantities
from tango_simlib import tango_sim_generator, helper_module
from tango_simlib.testutils import ClassCleanupUnittestMixin, cleanup_tempdir

from PyTango import DevState

class FixtureModel(model.Model):

    def setup_sim_quantities(self):
        start_time = self.start_time
        GaussianSlewLimited = partial(
            quantities.GaussianSlewLimited, start_time=start_time)
        ConstantQuantity = partial(
            quantities.ConstantQuantity, start_time=start_time)

        self.sim_quantities['relative-humidity'] = GaussianSlewLimited(
            mean=65, std_dev=10, max_slew_rate=10,
            min_bound=0, max_bound=150)
        self.sim_quantities['wind-speed'] = GaussianSlewLimited(
            mean=1, std_dev=20, max_slew_rate=3,
            min_bound=0, max_bound=100)
        self.sim_quantities['wind-direction'] = GaussianSlewLimited(
            mean=0, std_dev=150, max_slew_rate=60,
            min_bound=0, max_bound=359.9999)
        self.sim_quantities['input-comms-ok'] = ConstantQuantity(start_value=True)
        super(FixtureModel, self).setup_sim_quantities()

    def reset_model(self):
        self.setup_sim_quantities()

def control_attributes(test_model):
    """Function collects all the available models and gets all the
    adjustable_attributes which will be control attributes on the
    simulator test interface device.
    Returns
    =======
    control_attributes : list
        A list of all the adjustable attributes
    """
    control_attributes = []
    models = set([quant.__class__
            for quant in test_model.sim_quantities.values()])
    for cls in models:
        control_attributes += [attr for attr in cls.adjustable_attributes
                if attr not in control_attributes]
    return control_attributes

class test_SimControl(DeviceTestCase):
    device = sim_test_interface.TangoTestDeviceServerBase
    properties = dict(model_key='the_test_model')

    @classmethod
    def setUpClass(cls):
        cls.test_model = FixtureModel('the_test_model')
        super(test_SimControl, cls).setUpClass()

    def setUp(self):
        super(test_SimControl, self).setUp()
        self.addCleanup(self.test_model.reset_model)
        self.control_attributes = control_attributes(self.test_model)
        self.device_instance = sim_test_interface.TangoTestDeviceServerBase.instances[
                self.device.name()]
        def cleanup_refs(): del self.device_instance
        self.addCleanup(cleanup_refs)

    def test_attribute_list(self):
        sim_control_static_attributes = (
            helper_module.SIM_CONTROL_ADDITIONAL_IMPLEMENTED_ATTR)
        attributes = set(self.device.get_attribute_list())
        self.assertEqual(attributes - sim_control_static_attributes,
                        set(self.control_attributes))

    def test_model_defaults(self):
        device_model = self.device_instance.model
        # test that the model instance of the sim control is the same one as Fixture
        self.assertIs(device_model, self.test_model)
        expected_model = FixtureModel(
                'random_test_name',
                time_func=lambda: self.test_model.start_time)
        self._compare_models(device_model, expected_model)

    def _compare_models(self, device_model, expected_model):
        """Function compares two models for equality using assertEqual

        Parameters
        ==========
        device_model : device instance model
        expected_model : default instance test model
        """
        # test that expected values from the instantiated model match that of sim control
        for quantity in expected_model.sim_quantities.keys():
            self.device.attribute_name = quantity  # sets the sensor name for which
            # to evaluate the quantities to be controlled
            desired_quantity = expected_model.sim_quantities[quantity]
            for attr in desired_quantity.adjustable_attributes:
                attribute_value = getattr(self.device, attr)
                model_attr_value = getattr(desired_quantity, attr)
                self.assertEqual(attribute_value, model_attr_value)

    def generate_test_attribute_values(self):
        """Generate adjustable attribute test values for GaussianSlewLimited quantities

        Returns
        =======
        control_attr_dict : dict
            A dictionary of all GaussianSlewLimited quantity adjustable control
            attributes.  Values are guaranteed to be different to the values in
            FixtureModel.

        """
        control_attr_dict = {}
        control_attr_dict['desired_mean'] = 600
        control_attr_dict['desired_min_bound'] = 50
        control_attr_dict['desired_max_bound'] = 1000
        control_attr_dict['desired_std_dev'] = 200
        control_attr_dict['desired_max_slew_rate'] = 200
        control_attr_dict['desired_last_val'] = 62
        control_attr_dict['desired_last_update_time'] = time.time()
        return control_attr_dict

    def _quants_before_dict(self, test_model):
        """Function generate a dictionary of all the expected
        quantity values of the initial test model.
        Returns
        =======
        quants_before : dict
            A dictionary of all expected model quantity values
        """
        quants_before = {}
        # expected values of the model quantities before the attributes change
        for quant_name, quant in test_model.sim_quantities.items():
            quants_before[quant_name] = {attr: getattr(quant, attr)
                    for attr in quant.adjustable_attributes}
        return quants_before

    def test_model_attribute_change(self):
        # setting the desired attribute values for the device's attributes
        # that can be controlled and checking if new values are actually
        # different to from the defualt.
        expected_model = FixtureModel('random_test1_name',
                time_func=lambda: self.test_model.start_time)
        quants_before = self._quants_before_dict(expected_model)
        desired_attribute_name = 'relative-humidity'
        self.device.attribute_name = desired_attribute_name
        for attr in self.control_attributes:
            new_val = self.generate_test_attribute_values()[
                    'desired_' + attr]
            setattr(self.device, attr, new_val)
            setattr(expected_model.sim_quantities[desired_attribute_name], attr, new_val)
            self.assertNotEqual(getattr(self.device, attr),
                    quants_before[desired_attribute_name][attr])
        # Compare the modified quantities and check if the other
        # quantities have not changed
        self._compare_models(self.test_model, expected_model)

        # Changing the second quantity to see modification and making sure
        # the other quantities are not modified
        self.test_model.reset_model()
        expected_model = FixtureModel('random_test2_name',
                time_func=lambda: self.test_model.start_time)
        quants_before = self._quants_before_dict(self.test_model)
        desired_attribute_name = 'wind-speed'
        self.device.attribute_name = desired_attribute_name
        for attr in self.control_attributes:
            new_val = self.generate_test_attribute_values()[
                    'desired_' + attr]
            setattr(self.device, attr, new_val)
            setattr(expected_model.sim_quantities[desired_attribute_name], attr, new_val)
            # Sanity check that we have indeed changed the value.
            self.assertNotEqual(getattr(self.device, attr),
                    quants_before[desired_attribute_name][attr])
        # Compare the modified quantities and check that no other quantities
        # have changed.
        self._compare_models(self.test_model, expected_model)


EXPECTED_COMMAND_LIST = frozenset(['StopRainfall', 'StopQuantitySimulation',
                                   'SetAttributeMaxValue', 'SimulateFaultDeviceState',
                                   'StimulateAttributeConfigurationError',
                                   'SetOffWindStorm', 'StopWindStorm', 'SetOffRainStorm',
                                   'StopRainStorm'])


class test_TangoSimGenDeviceIntegration(ClassCleanupUnittestMixin, unittest.TestCase):

    longMessage = True

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.port = helper_module.get_port()
        cls.host = helper_module.get_host_address()
        cls.data_descr_files = []
        cls.data_descr_files.append(pkg_resources.resource_filename(
            'tango_simlib.tests', 'weather_sim.xmi'))
        cls.data_descr_files.append(pkg_resources.resource_filename(
            'tango_simlib.tests', 'weather_SIMDD_3.json'))
        cls.temp_dir = cleanup_tempdir(cls)
        cls.sim_device_class = tango_sim_generator.get_device_class(cls.data_descr_files)
        device_name = 'test/nodb/tangodeviceserver'
        server_name = 'weather_ds'
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

    def test_sim_control_command_list(self):
        device_commands = self.sim_control_device.get_command_list()
        self.assertEqual(
            EXPECTED_COMMAND_LIST,
            set(device_commands) - helper_module.DEFAULT_TANGO_DEVICE_COMMANDS)
        self.assertEqual(
            set(self.sim_device.get_command_list()) & EXPECTED_COMMAND_LIST,
            set(), "The device has commands meant for the test sim control device.")

    def test_StopRainfall_command(self):
        command_name = 'StopRainfall'
        expected_rainfall_value = 0.0
        self.sim_control_device.command_inout(command_name)
        # TODO (KM 17-02-2018) Follow up on this issue:
        # https://skaafrica.atlassian.net/browse/LMC-64 for testing two dependent TANGO
        # device servers.
        # The model needs 'dt' to be greater than the min_update_period for it to update
        # the model.quantity_state dictionary. If it was posssible to get hold of the
        # model instance, we would manipulate the value of the last_update_time of the
        # model to ensure that the model.quantity_state dictionary is updated before
        # reading the attribute value. So instead we use the sleep method to allow for
        # 'dt' to be large enough.
        time.sleep(1)
        self.assertEqual(expected_rainfall_value,
                         getattr(self.sim_device.read_attribute('rainfall'), 'value'),
                         "The rainfall value is not zero.")

    def test_StopQuantitySimulation_command(self):
        """Testing that the Tango device weather simulation of quantities can be halted.
        """
        command_name = 'StopQuantitySimulation'
        expected_result = {'temperature': 0.0,
                           'insolation': 0.0}
        device_attributes = self.sim_device.get_attribute_list()
        for quantity_name in expected_result.keys():
            self.assertIn(quantity_name, device_attributes)

        self.sim_control_device.command_inout(command_name, expected_result.keys())
        # The model needs 'dt' to be greater than the min_update_period for it to update
        # the model.quantity_state dictionary. If it was posssible to get hold of the
        # model instance, we would manipulate the value of the last_update_time of the
        # model to ensure that the model.quantity_state dictionary is updated before
        # reading the attribute value. So instead we use the sleep method to allow for
        # 'dt' to be large enough.
        time.sleep(1)
        for quantity_name, quantity_value in expected_result.items():
            self.assertEqual(quantity_value,
                             getattr(self.sim_device.read_attribute(quantity_name),
                                     'value'),
                             "The {} quantity value in the model does not match with the"
                             " value read from the device attribute.".format(
                                 quantity_name))

    def test_SetOffRainStorm(self):
        command_name = 'SetOffRainStorm'
        max_rainfall_value = 3.45
        test_max_slew_rate = 1000
        self.assertIn('rainfall', self.sim_device.get_attribute_list())
        self.sim_control_device.write_attribute('attribute_name', 'rainfall')
        self.sim_control_device.write_attribute('max_slew_rate', test_max_slew_rate)
        self.sim_control_device.command_inout(command_name)
        # The model needs 'dt' to be greater than the min_update_period for it to update
        # the model.quantity_state dictionary. If it was posssible to get hold of the
        # model instance, we would manipulate the value of the last_update_time of the
        # model to ensure that the model.quantity_state dictionary is updated before
        # reading the attribute value. So instead we use the sleep method to allow for
        # 'dt' to be large enough.
        time.sleep(1)
        self.assertGreater(getattr(self.sim_device.read_attribute('rainfall'), 'value'),
                           max_rainfall_value,
                           "Rain levels not above the expected value for a rainstorm")
        self.assertEqual(self.sim_device.State(), DevState.ALARM,
                         "The rainfall levels are higher than the maximun allowed value"
                         " but the device is not in ALARM state.")
