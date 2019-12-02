from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
#########################################################################################
# Copyright 2017 SKA South Africa (http://ska.ac.za/)                                   #
#                                                                                       #
# BSD license - see LICENSE.txt for details                                             #
#########################################################################################
import logging
import time
import weakref
import sys
import importlib

from functools import partial
from tango_simlib import quantities
from tango import CmdArgType

MODULE_LOGGER = logging.getLogger(__name__)

model_registry = weakref.WeakValueDictionary()

DEFAULT_TANGO_COMMANDS = frozenset(['State', 'Status', 'Init'])
MAX_NUM_OF_CLASS_ATTR_OCCURENCE = 1
ARBITRARY_DATA_TYPE_RETURN_VALUES = {
    CmdArgType.DevString: 'Ok!',
    CmdArgType.DevBoolean: True,
    CmdArgType.DevDouble: 4.05,
    CmdArgType.DevFloat: 8.1,
    CmdArgType.DevLong: 3,
    CmdArgType.DevVoid: None}

# In the case where an attribute with contant quantity simulation type is
# specified, this dict is used to convert the initial value if specified to
# the data-type corresponding to the attribute data-type.
INITIAL_CONSTANT_VALUE_TYPES = {
    CmdArgType.DevString: (str, ""),
    CmdArgType.DevFloat: (float, 0.0),
    CmdArgType.DevDouble: (float, 0.0),
    CmdArgType.DevBoolean: (bool, False),
    CmdArgType.DevEnum: (int, 0),
    CmdArgType.DevUChar: (int, 0),
    CmdArgType.DevShort: (int, 0),
    CmdArgType.DevUShort: (int, 0),
    CmdArgType.DevLong: (int, 0),
    CmdArgType.DevULong: (int, 0),
    CmdArgType.DevLong64: (int, 0),
    CmdArgType.DevULong64: (int, 0),
    CmdArgType.DevVoid: (None, None),
    CmdArgType.DevState: (int, 0),
    CmdArgType.DevEncoded: (bytearray, 0)
}


class Model(object):
    """Tango Device main model with quantities and actions

    Parameters
    ----------
    name : str
        Model name identifier
    start_time : float
        Time at instantiation of the model
    min_update_period : float
        Minimun update period of the quantites in the model
    time_func : time function
        Function that return current time i.e. time.time

    """

    def __init__(self, name, start_time=None, min_update_period=0.99,
                 time_func=time.time):
        self.name = name
        model_registry[self.name] = self
        self.min_update_period = min_update_period
        self.time_func = time_func
        self.start_time = start_time or time_func()
        self.last_update_time = self.start_time
        self.sim_quantities = {}
        self.sim_actions = {}
        self.sim_properties = {}
        self.test_sim_actions = {}
        self.sim_actions_meta = {}
        self._sim_state = {}
        self.setup_sim_quantities()
        self.override_pre_updates = []
        self.override_post_updates = []
        self.paused = False  # Flag to pause updates
        # Making a public reference to _sim_state. Allows us to hook read-only views
        # or updates or whatever the future requires of this humble public attribute.
        self.quantity_state = self._sim_state

    def setup_sim_quantities(self):
        """Set up self.sim_quantities with simulated quantities

        Subclasses should implement this method. Should place simulated quantities in
        self.sim_quantities dict. Keyed by name of quantity, value must be instances
        satisfying the :class:`quantites.Quantity` interface.

        Notes
        =====
        - Must use self.start_time to set initial time values.
        - Must call super method after setting up `sim_quantities`

        """
        self._sim_state.update(
            {var: (quant.last_val, quant.last_update_time)
             for var, quant in self.sim_quantities.items()})

    def update(self):
        sim_time = self.time_func()
        dt = sim_time - self.last_update_time
        if dt < self.min_update_period or self.paused:
            # Updating the sim_state in case the test interface or external command
            # updated the quantities.
            for var, quant in self.sim_quantities.items():
                self._sim_state[var] = (quant.last_val, quant.last_update_time)
            MODULE_LOGGER.debug(
                "Sim {} skipping update at {}, dt {} < {} and pause {}"
                .format(self.name, sim_time, dt, self.min_update_period, self.paused))
            return

        for override_update in self.override_pre_updates:
            override_update(self, sim_time, dt)

        MODULE_LOGGER.info("Stepping at {}, dt: {}".format(sim_time, dt))
        self.last_update_time = sim_time
        try:
            for var, quant in self.sim_quantities.items():
                self._sim_state[var] = (quant.next_val(sim_time), sim_time)
        except Exception:
            MODULE_LOGGER.exception('Exception in update loop')

        for override_update in self.override_post_updates:
            override_update(self, sim_time, dt)

    def set_sim_action(self, name, handler):
        """Add an action handler function

        Parameters
        ----------
        name : str
            Name of the action
        handler : callable(model_instance, action_args)
            Callable that handles action (name). Is called with the model instance as
            the first parameter.

        """
        self.sim_actions[name] = partial(handler, self)

    def set_test_sim_action(self, name, handler):
        """Add an action handler function

        Parameters
        ----------
        name : str
            Name of the action
        handler : callable(model_instance, action_args)
            Callable that handles action (name). Is called with the model instance as
            the first parameter.

        """
        self.test_sim_actions[name] = partial(handler, self)

    def set_sim_property(self, device_prop):
        self.sim_properties.update(device_prop)


class PopulateModelQuantities(object):
    """Used to populate/update model quantities

    Populates the model quantities using the data from the TANGO device information
    captured in the json file / POGO generated xmi / FANDANGO generated fgo file.

    Attributes
    ----------
    parser_instance : Parser instance
        The Parser object which reads an xmi/xml/json file and parses it into device
        attributes, commands, and properties.
    sim_model :  Model instance
        An instance of the Model class which is used for simulation of simple attributes.

    """
    def __init__(self, parser_instance, tango_device_name, sim_model=None):
        self.parser_instance = parser_instance
        if sim_model:
            if isinstance(sim_model, Model):
                self.sim_model = sim_model
            else:
                raise SimModelException("The sim_model object passed is not an instance"
                                        " of the class mkat_tango.simlib.model.Model")

        else:
            self.sim_model = Model(tango_device_name)
        self.setup_sim_quantities()

    def setup_sim_quantities(self):
        """Set up self.sim_quantities from Model with simulated quantities

        Places simulated quantities in sim_quantities dict. Keyed by name of
        quantity, value must be instances satifying the
        :class:`quantities.Quantity` interface

        Notes
        =====
        - Must use self.start_time to set initial time values.
        - Must call super method after setting up `sim_quantities`

        """
        start_time = self.sim_model.start_time
        attributes = self.parser_instance.get_device_attribute_metadata()

        for attr_name, attr_props in attributes.items():
            # When using more than one config file, the attribute meta data can be
            # overwritten, so we need to update it instead of reassigning a different
            # object.
            try:
                model_attr_props = self.sim_model.sim_quantities[attr_name].meta
            except KeyError:
                MODULE_LOGGER.info(
                    "Initializing '{}' quantity meta information using config file:"
                    " '{}'.".format(attr_name,
                                    self.parser_instance.data_description_file_name))
                model_attr_props = attr_props
            else:
                # Before the model attribute props dict is updated, the
                # parameter keys with no values specified from the attribute
                # props template are removed.
                # i.e. All optional parameters not provided in the SimDD
                attr_props = dict((param_key, param_val)
                                  for param_key, param_val in attr_props.iteritems()
                                  if param_val)
                model_attr_props = dict(model_attr_props.items() + attr_props.items())

            if 'quantity_simulation_type' in model_attr_props:
                if model_attr_props['quantity_simulation_type'] == 'ConstantQuantity':
                    try:
                        initial_value = model_attr_props['initial_value']
                    except KeyError:
                        # `initial_value` is an optional parameter, thus if not
                        # specified in the SimDD datafile, an initial value of
                        # default value of is assigned to the attribute
                        # quantity initial value
                        initial_value = None
                        MODULE_LOGGER.info(
                            "Parameter `initial_value` does not exist for"
                            "attribute {}. Default will be used".format(
                                model_attr_props['name']))
                    attr_data_type = model_attr_props['data_type']
                    val_type, val = INITIAL_CONSTANT_VALUE_TYPES[attr_data_type]
                    init_val = (initial_value if initial_value not in [None, ""]
                                else val)
                    if val_type is None:
                        start_val = None
                    else:
                        start_val = val_type(init_val)
                    quantity_factory = (
                            quantities.registry[attr_props['quantity_simulation_type']])
                    self.sim_model.sim_quantities[attr_name] = quantity_factory(
                            start_time=start_time, meta=model_attr_props,
                            start_value=start_val)
                else:
                    try:
                        sim_attr_quantities = self.sim_attribute_quantities(
                            float(model_attr_props['min_bound']),
                            float(model_attr_props['max_bound']),
                            float(model_attr_props['max_slew_rate']),
                            float(model_attr_props['mean']),
                            float(model_attr_props['std_dev']))
                    except KeyError:
                        raise ValueError(
                            "Attribute with name '{}' specified in the configuration"
                            " file [{}] has no mininum or maximum values set".format(
                                attr_name,
                                self.parser_instance.data_description_file_name))
                    quantity_factory = (
                            quantities.registry[attr_props['quantity_simulation_type']])
                    self.sim_model.sim_quantities[attr_name] = quantity_factory(
                            start_time=start_time, meta=model_attr_props,
                            **sim_attr_quantities)
            else:
                key_vals = model_attr_props.keys()
                attr_data_type = model_attr_props['data_type']
                # the xmi, json and fgo files have data_format attributes indicating
                # SPECTRUM, SCALAR OR IMAGE data formats. The xml file does not have this
                # key in its attribute list. It has a key labelled possiblevalues which
                # is a list. Hence, SPECTRUM is no data_format is found.
                try:
                    attr_data_format = str(model_attr_props['data_format'])
                except KeyError:
                    attr_data_format = 'SPECTRUM'
                expected_key_vals = ['max_dim_x', 'max_dim_y', 'maxX', 'maxY']
                # the xmi, json and fgo files have either (max_dim_x, max_dim_y) or
                # (maxX, maxY) keys. If none of these keys are found in them or in the
                # xml file, we use default values of 1 for x and 2 for y - same applies
                # for files where the keys have empty values.
                if any(key_val in expected_key_vals for key_val in key_vals):
                    try:
                        max_dim_x = model_attr_props['max_dim_x']
                        max_dim_y = model_attr_props['max_dim_y']
                    except KeyError:
                        max_dim_x = model_attr_props.get('maxX', 1)
                        max_dim_y = model_attr_props.get('maxY', 2)
                    # just in case the keys exist but have no values
                    if not max_dim_x:
                        max_dim_x = 1
                    if not max_dim_y:
                        max_dim_y = 2

                val_type, val = INITIAL_CONSTANT_VALUE_TYPES[attr_data_type]
                expected_key_vals = ['value', 'possiblevalues']
                if any(key_val in expected_key_vals for key_val in key_vals):
                    try:
                        default_val = model_attr_props['value']
                    except KeyError:
                        default_val = model_attr_props['possiblevalues']
                    if attr_data_format == 'SCALAR':
                        default_val = val_type(default_val)
                    elif attr_data_format == 'SPECTRUM':
                        default_val = map(val_type, default_val)
                    else:
                        default_val = [[val_type(curr_val) for curr_val in sublist]
                                       for sublist in default_val]
                else:
                    if attr_data_format == 'SCALAR':
                        default_val = val
                    elif attr_data_format == 'SPECTRUM':
                        default_val = [val] * max_dim_x
                    else:
                        default_val = [[val] * max_dim_x for i in range(max_dim_y)]
                self.sim_model.sim_quantities[attr_name] = quantities.ConstantQuantity(
                        start_time=start_time, meta=model_attr_props,
                        start_value=default_val)

        self.sim_model.setup_sim_quantities()

    def sim_attribute_quantities(self, min_bound, max_bound, max_slew_rate,
                                 mean, std_dev):
        """Simulate attribute quantities with a Guassian value distribution

        Parameters
        ----------
        min_value : float
            minimum attribute value to be simulated
        max_value : float
            maximum attribute value to be simulated
        max_slew_rate : float
            maximum changing rate of the simulated quantities between min
            and max values
        mean : float
            average value of the simulated quantity
        std_dev : float
            starndard deviation value of the simulated quantity

        Returns
        -------
        sim_attribute_quantities : dict
            Dict of Gaussian simulated quantities

        """
        sim_attribute_quantities = dict()
        sim_attribute_quantities['max_slew_rate'] = max_slew_rate
        sim_attribute_quantities['min_bound'] = min_bound
        sim_attribute_quantities['max_bound'] = max_bound
        sim_attribute_quantities['mean'] = mean
        sim_attribute_quantities['std_dev'] = std_dev
        return sim_attribute_quantities


class PopulateModelActions(object):
    """Used to populate/update model actions

    Populates the model actions using the data from the TANGO device information
    captured in the json file / POGO generated xmi / FANDANGO generated fgo file.

    Attributes
    ----------
    cmd_info : dict
        A dictionary of all the device commands together with their
        metadata specified in the xmi, json or fgo file(s).

    override_info : dict
        A dictionary of device override info in specified the xmi, json or fgo file(s).

    sim_model :  Model instance
        An instance of the Model class which is used for simulation of simple attributes
        and/or commands.

    """
    def __init__(self, cmd_info, override_info, tango_device_name, model_instance=None):
        self.cmd_info = cmd_info
        self.override_info = override_info
        if model_instance is None:
            self.sim_model = Model(tango_device_name)
        else:
            self.sim_model = model_instance
        self.add_actions()

    def add_actions(self):
        instances = {}
        if self.override_info != {}:
            instances = self._get_class_instances(self.override_info)

        # Need to override the model's update method if the override class provides one.
        instance = []
        for instance_ in instances:
            if instance_.startswith('Sim'):
                instance.append(instances[instance_])

        for inst in instance:
            try:
                pre_update_overwrite = getattr(inst, 'pre_update')
            except AttributeError:
                MODULE_LOGGER.info("No pre-update method defined in the '{}'"
                                   " override class.".format(type(inst).__name__))
            else:
                self.sim_model.override_pre_updates.append(pre_update_overwrite)
            try:
                post_update_overwrite = getattr(inst, 'post_update')
            except AttributeError:
                MODULE_LOGGER.info("No post-update method defined in the '{}'"
                                   " override class.".format(type(inst).__name__))
            else:
                self.sim_model.override_post_updates.append(post_update_overwrite)

        for cmd_name, cmd_meta in self.cmd_info.items():
            # Exclude the TANGO default commands as they have their own built in handlers
            # provided.
            if cmd_name in DEFAULT_TANGO_COMMANDS:
                continue
            # Every command is to be declared to have one or more  action behaviour.
            # Example of a list of actions handle at this moment is as follows
            # [{'behaviour': 'input_transform',
            # 'destination_variable': 'temporary_variable'},
            # {'behaviour': 'side_effect',
            # 'destination_quantity': 'temperature',
            # 'source_variable': 'temporary_variable'},
            # {'behaviour': 'output_return',
            # 'source_variable': 'temporary_variable'}]
            actions = cmd_meta.get('actions', [])
            instance = None
            if cmd_name.startswith('test_'):
                cmd_name = cmd_name.split('test_')[1]
                for instance_ in instances:
                    if instance_.startswith('SimControl'):
                        instance = instances[instance_]
                self._check_override_action_presence(cmd_name, instance,
                                                     'test_action_{}')
                handler = getattr(
                    instance, 'test_action_{}'.format(cmd_name.lower()),
                    self.generate_action_handler(cmd_name, cmd_meta['dtype_out'],
                                                 actions))
                self.sim_model.set_test_sim_action(cmd_name, handler)
            else:
                for instance_ in instances:
                    if instance_.startswith('Sim'):
                        instance = instances[instance_]
                self._check_override_action_presence(cmd_name, instance, 'action_{}')
                handler = getattr(instance, 'action_{}'.format(cmd_name.lower()),
                                  self.generate_action_handler(
                                       cmd_name, cmd_meta['dtype_out'], actions))

                self.sim_model.set_sim_action(cmd_name, handler)
            # Might store the action's metadata in the sim_actions dictionary
            # instead of creating a separate dict.
            try:
                self.sim_model.sim_actions_meta[cmd_name.split('test_')[1]] = cmd_meta
            except IndexError:
                self.sim_model.sim_actions_meta[cmd_name] = cmd_meta

    def _get_class_instances(self, override_class_info):
        instances = {}
        for klass_info in override_class_info.values():
            if klass_info['module_directory'] == 'None':
                module = importlib.import_module(klass_info['module_name'])
            else:
                sys.path.append(klass_info['module_directory'])
                module = importlib.import_module(klass_info['module_name'])
                sys.path.remove(klass_info['module_directory'])
            klass = getattr(module, klass_info['class_name'])
            instance = klass()
            instances[klass_info['name']] = instance

        return instances

    def _check_override_action_presence(self, cmd_name, instance, action_type):
        instance_attributes = dir(instance)
        instance_attributes_list = [attr.lower() for attr in instance_attributes]
        attr_occurences = instance_attributes_list.count(
            action_type.format(cmd_name.lower()))
        # Check if there is only one override class method defined for each command
        if attr_occurences > MAX_NUM_OF_CLASS_ATTR_OCCURENCE:
            raise Exception("The command '{}' has multiple override methods defined"
                            " in the override class".format(cmd_name))
        # Assuming that there is only one override method defined, now we check if it
        # is in the correct letter case.
        elif attr_occurences == MAX_NUM_OF_CLASS_ATTR_OCCURENCE:
            try:
                instance_attributes.index(action_type.format(cmd_name.lower()))
            except ValueError:
                raise Exception("Only lower-case overide method names are supported.")

    def generate_action_handler(self, action_name, action_output_type, actions=None):
        """Generates and returns an action handler to manage tango commands

        Parameters
        ----------
        action_name : str
            Name of action handler to generate
        action_output_type : PyTango._PyTango.CmdArgType
            Tango command argument type
        actions : list
            List of actions that the handler will provide

        Returns
        -------
        action_handler : function
            action handler, taking command input argument in case of tango
            commands with input arguments.

        """
        if actions is None:
            actions = []

        def action_handler(model, data_input=None, tango_dev=None):
            """Action handler taking command input arguments

            Parameters
            ----------
            model : model.Model
                Model instance
            data_in : float, string, int, etc.
                Input arguments of tango command

            Returns
            -------
            return_value : float, string, int, etc.
                Output value of an executed tango command

            """
            # TODO (KM 18-01-2016): Need to remove the tango_dev parameter from
            # action hanlder, currently used for testing functionality of the
            # override class actions.
            temp_variables = {}
            return_value = None
            for action in actions:
                if action['behaviour'] == 'long_running':
                    time.sleep(float(action['execution_time_secs']))
                if action['behaviour'] == 'input_transform':
                    temp_variables[action['destination_variable']] = data_input
                if action['behaviour'] == 'side_effect':
                    quantity = action['destination_quantity']
                    temp_variables[action['source_variable']] = data_input
                    model_quantity = model.sim_quantities[quantity]
                    model_quantity.set_val(data_input, model.time_func())

                if action['behaviour'] == 'output_return':
                    if 'source_variable' in action and 'source_quantity' in action:
                        raise ValueError(
                            "{}: Either 'source_variable' or 'source_quantity'"
                            " for 'output_return' action, not both"
                            .format(action_name))
                    elif 'source_variable' in action:
                        source_variable = action['source_variable']
                        try:
                            return_value = temp_variables[source_variable]
                        except KeyError:
                            raise ValueError(
                                "{}: Source variable {} not defined"
                                .format(action_name, source_variable))
                    elif 'source_quantity' in action:
                        quantity = action['source_quantity']
                        try:
                            model_quantity = model.sim_quantities[quantity]
                        except KeyError:
                            raise ValueError(
                                "{}: Source quantity {} not defined"
                                .format(action_name, quantity))
                        return_value = model_quantity.last_val
                    else:
                        raise ValueError(
                            "{}: Need to specify one of 'source_variable' "
                            "or 'source_quantity' for 'output_return' action"
                            .format(action_name))
                else:
                    # Return a default value if output_return is not specified.
                    return_value = ARBITRARY_DATA_TYPE_RETURN_VALUES[action_output_type]
            return return_value

        action_handler.__name__ = action_name
        return action_handler


class PopulateModelProperties(object):
    """Used to populate/update model properties

    Populates the model properties using the data from the TANGO device information
    captured in the json file / POGO generated xmi / FANDANGO generated fgo file.

    Attributes
    ----------
    properties_info : dict
        A dictionary of device property configuration specified in the xmi, json
        or fgo file(s).
    sim_model :  Model instance
        An instance of the Model class which is used for simulation of simple attributes.

    """
    def __init__(self, properties_info, tango_device_name, sim_model=None):
        self.properties_info = properties_info
        if sim_model:
            if isinstance(sim_model, Model):
                self.sim_model = sim_model
            else:
                raise SimModelException("The sim_model object passed is not an instance"
                                        " of the class mkat_tango.simlib.model.Model")
        else:
            self.sim_model = Model(tango_device_name)
        self.setup_sim_properties()

    def setup_sim_properties(self):
        """Set up self.sim_properties from Model with simulated quantities

        Places simulated properties in sim_quantities dict. Keyed by name of
        property, value must be a string, number or array and it is optional.

        """
        self.sim_model.set_sim_property(self.properties_info)

class SimModelException(Exception):
    def __init__(self, message):
        super(SimModelException, self).__init__(message)
