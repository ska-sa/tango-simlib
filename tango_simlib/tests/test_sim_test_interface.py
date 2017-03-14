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

class FixtureModel(model.Model):

    def setup_sim_quantities(self):
        start_time = self.start_time
        GaussianSlewLimited = partial(
            quantities.GaussianSlewLimited, start_time=start_time)
        ConstantQuantity = partial(
            quantities.ConstantQuantity, start_time=start_time)

        self.sim_quantities['relative_humidity'] = GaussianSlewLimited(
            mean=65.0, std_dev=10.0, max_slew_rate=10.0,
            min_bound=0.0, max_bound=150.0, meta=dict(
                label="Air humidity",
                data_type=float,
                data_format=AttrDataFormat.SCALAR,
                description="Relative humidity in central telescope area.",
                max_warning=98, max_alarm=99,
                max_value=100, min_value=0,
                unit="percent",
                period=1000))
        self.sim_quantities['wind_speed'] = GaussianSlewLimited(
            mean=1.0, std_dev=20.0, max_slew_rate=3.0,
            min_bound=0.0, max_bound=100.0, meta=dict(
                label="Wind speed",
                data_type=float,
                data_format=AttrDataFormat.SCALAR,
                description="Wind speed in central telescope area.",
                max_warning=15, max_alarm=25,
                max_value=30, min_value=0,
                unit="m/s",
                period=1000))
        self.sim_quantities['wind_direction'] = GaussianSlewLimited(
            mean=0.0, std_dev=150.0, max_slew_rate=60.0,
            min_bound=0.0, max_bound=359.9999, meta=dict(
                label="Wind direction",
                data_type=float,
                data_format=AttrDataFormat.SCALAR,
                description="Wind direction in central telescope area.",
                max_value=360, min_value=0,
                unit="Degrees",
                period=1000))
        self.sim_quantities['input_comms_ok'] = ConstantQuantity(
            start_value=True, meta=dict(
                label="Input communication OK",
                data_type=bool,
                data_format=AttrDataFormat.SCALAR,
                description="Communications with all weather sensors are nominal.",
                period=1000))
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
    device = None
    properties = dict(model_key='the_test_model')

    @classmethod
    def setUpClass(cls):
        cls.test_model = FixtureModel('the_test_model')
        # The get_tango_device_server function requires  data file which it uses to
        # extract the device class name. However for this test we don't need  it,
        # hence the use of the dummy sim data file.
        cls.device_klass = tango_sim_generator.get_tango_device_server(
            cls.test_model, ['dummy_sim_data_file.txt'])[-1]
        cls.device = cls.device_klass
        super(test_SimControl, cls).setUpClass()

    def setUp(self):
        super(test_SimControl, self).setUp()
        self.addCleanup(self.test_model.reset_model)
        self.control_attributes = control_attributes(self.test_model)
        self.attr_name_enum_labels = self.device.attribute_query(
                                          'attribute_name').enum_labels
        self.device_instance = self.device_klass.instances[
                self.device.name()]

        self.mock_time = Mock()
        self.mock_time.return_value = time.time()
        self.device_instance.model.time_func = self.mock_time

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
            # sets the sensor name for which to evaluate the quantities to be controlled
            self.device.attribute_name = list(self.attr_name_enum_labels).index(quantity)
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
        control_attr_dict['desired_last_update_time'] = (
            self.device_instance.model.time_func())
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
        desired_attribute_name = 'relative_humidity'
        self.device.attribute_name = list(self.attr_name_enum_labels).index(
                                                desired_attribute_name)
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
        desired_attribute_name = 'wind_speed'
        self.device.attribute_name = list(self.attr_name_enum_labels).index(
                                        desired_attribute_name)
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
        self.sim_control_device.write_attribute(
                'attribute_name', self.attr_name_enum_labels.index('rainfall'))
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

    def test_model_update_paused_via_attrs(self):
        """Testing that the model's quantities values get updated when the model is in a
        paused state.
        """
        # Sim control device attributes under test
        simctrl_attr1_name = 'pause_active'
        simctrl_attr2_name = 'attribute_name'

        # Get the sim device attributes under test
        sim_attr1_name = 'temperature'
        sim_attr2_name = 'input_comms_ok'

        # Testing a ConstantQuantity type attribute
        # Check if the model is in an unpaused state
        self.assertEqual(
            self.sim_control_device.read_attribute(simctrl_attr1_name).value,
            False, 'The model is in a paused state.')
        # Get the input_comms_ok default value and ensure it is True
        sim_attr2_val = getattr(self.sim_device.read_attribute(sim_attr2_name), 'value')
        self.assertEqual(sim_attr2_val, False, "The attribute {}'s value is not the"
                         " expected value 'False'".format(sim_attr2_name))
        # Set the model to a paused state
        self.sim_control_device.write_attribute(simctrl_attr1_name, True)
        self.assertEqual(
            self.sim_control_device.read_attribute(simctrl_attr1_name).value,
            True, 'The model is not in a paused state.')
        # Select attribute to control e.g. input_comms_ok
        self.sim_control_device.write_attribute(
            simctrl_attr2_name, self.attr_name_enum_labels.index(sim_attr2_name))
        # Write a new value to the quantity/attribute
        self.sim_control_device.write_attribute('last_val', True)
        # Check if the changes appear in the sim device attributes
        self.assertEqual(
            self.sim_device.read_attribute(sim_attr2_name).value, True,
            "The model was not updated")

        # Unpause the model
        self.sim_control_device.write_attribute(simctrl_attr1_name, False)

        # Testing a GaussianSlewLimited type quantity
        # Check if the model is in an unpaused state
        self.assertEqual(
            self.sim_control_device.read_attribute(simctrl_attr1_name).value,
            False, 'The model is in a paused state.')
        # Select the attribute to control
        self.sim_control_device.write_attribute(
            simctrl_attr2_name, self.attr_name_enum_labels.index(sim_attr1_name))
        # Pause the model
        self.sim_control_device.write_attribute(simctrl_attr1_name, True)
        # Read the attribute's value
        sim_attr1_val = self.sim_device.read_attribute(sim_attr1_name).value
        # Write a new value to the quantity/attribute (choose a very big number which
        # is outside the default simulation value range).
        sim_attr1_new_val = 200000
        # First check that the current attribute value is not equal to the proposed
        # new value
        self.assertNotEqual(sim_attr1_val, sim_attr1_new_val,
                            "The proposed new value is the same as the current value.")
        self.sim_control_device.write_attribute('last_val', sim_attr1_new_val)
        # Check if the changes appear in the sim device attribute under test
        self.assertEqual(
            self.sim_device.read_attribute(sim_attr1_name).value,
            sim_attr1_new_val, 'The model was not updated')

