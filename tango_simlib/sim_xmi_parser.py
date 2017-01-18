#!/usr/bin/env python
###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2013 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################
"""
Simlib library generic simulator generator utility to be used to generate an actual
TANGO device that exhibits the behaviour defined in the data description file.
@author MeerKAT CAM team <cam@ska.ac.za>
"""

import logging
import importlib
import imp

import xml.etree.ElementTree as ET
import PyTango

from functools import partial
from PyTango import (DevBoolean, DevString, DevEnum, AttrDataFormat,
                     CmdArgType, DevDouble, DevFloat, DevLong, DevVoid)

from mkat_tango.simlib import quantities
from mkat_tango.simlib import model

MODULE_LOGGER = logging.getLogger(__name__)

DEFAULT_TANGO_COMMANDS = ['State', 'Status', 'Init']
CONSTANT_DATA_TYPES = [DevBoolean, DevEnum, DevString]
MAX_NUM_OF_CLASS_ATTR_OCCURENCE = 1
POGO_PYTANGO_ATTR_FORMAT_TYPES_MAP = {
        'Image': AttrDataFormat.IMAGE,
        'Scalar': AttrDataFormat.SCALAR,
        'Spectrum': AttrDataFormat.SPECTRUM}

ARBITRARY_DATA_TYPE_RETURN_VALUES = {
    DevString: 'Ok!',
    DevBoolean: True,
    DevDouble: 4.05,
    DevFloat: 8.1,
    DevLong: 3,
    DevVoid: None}

# TODO(KM 31-10-2016): Need to add xmi attributes' properties that are currently
# not being handled by the parser e.g. [displayLevel, enumLabels] etc.
POGO_USER_DEFAULT_ATTR_PROP_MAP = {
        'dynamicAttributes': {
            'name': 'name',
            'dataType': 'data_type',
            'rwType': 'writable',
            'polledPeriod': 'period',
            'attType': 'data_format',
            'maxX': 'max_dim_x',
            'maxY': 'max_dim_y'},
        'eventArchiveCriteria': {
            'absChange': 'archive_abs_change',
            'period': 'archive_period',
            'relChange': 'archive_rel_change'},
        'eventCriteria': {
            'absChange': 'abs_change',
            'period': 'event_period',
            'relChange': 'rel_change'},
        'properties': {
            'maxAlarm': 'max_alarm',
            'maxValue': 'max_value',
            'maxWarning': 'max_warning',
            'minAlarm': 'min_alarm',
            'deltaTime': 'delta_t',
            'minValue': 'min_value',
            'deltaValue': 'delta_val',
            'minWarning': 'min_warning',
            'description': 'description',
            'displayUnit': 'display_unit',
            'standardUnit': 'standard_unit',
            'format': 'format',
            'label': 'label',
            'unit': 'unit'}
        }

POGO_USER_DEFAULT_CMD_PROP_MAP = {
        'name': 'name',
        'arginDescription': 'doc_in',
        'arginType': 'dtype_in',
        'argoutDescription': 'doc_out',
        'argoutType': 'dtype_out'}

class XmiParser(object):

    def __init__(self):
        """Parser class handling a simulator description datafile in xmi format.

        Creating an instance of this class requires calling :meth:`parse`
        afterwards to extract all the provided tango attributes, commands,
        device property and device override class information from the specified
        file.  The formated data is a dict structure and can be obtained using
        :meth:`get_reformatted_device_attr_metadata`,
        :meth:`get_reformatted_cmd_metadata`,
        :meth:`get_reformatted_properties_metadata` and
        :meth:`get_reformatted_override_metadata`

        """
        self.device_class_name = ''
        self.device_attributes = []
        """The Data structure format is a list containing attribute info in a dict

        e.g.
        [{
            "attribute": {
                "displayLevel": "OPERATOR",
                "maxX": "",
                "maxY": "",
                "attType": "Scalar",
                "polledPeriod": "1000",
                "dataType": DevDouble,
                "isDynamic": "true",
                "rwType": "READ",
                "allocReadMember": "true",
                "name": "temperature"
            },
            "eventCriteria": {
                "relChange": "10",
                "absChange": "0.5",
                "period": "1000"
            },
            "evArchiveCriteria": {
                "relChange": "10",
                "absChange": "0.5",
                "period": "1000"
            },
            "properties": {
                "description": "Current temperature outside near the telescope.",
                "deltaValue": "",
                "maxAlarm": "50",
                "maxValue": "51",
                "minValue": "-10",
                "standardUnit": "",
                "minAlarm": "-9",
                "maxWarning": "45",
                "unit": "Degrees Centrigrade",
                "displayUnit": "",
                "format": "",
                "deltaTime": "",
                "label": "Outside Temperature",
                "minWarning": "-5"
           }
        }]

        """
        self.device_commands = []
        """The Data structure format is a list containing command info in a dict

        e.g.
        [{
             "name": "On",
             "arginDescription": "",
             "arginType": tango._tango.CmdArgType.DevVoid,
             "argoutDescription": "ok | Device ON",
             "argoutType": tango._tango.CmdArgType.DevString,
             "description": "Turn On Device"
        }]
        """
        self.device_properties = []
        """Data structure format is a list containing device property info in a dict

        e.g.
        [{
            "deviceProperties": {
                "type": DevString,
                "mandatory": "true",
                "description": "Path to the pogo generate xmi file",
                "name": "sim_xmi_description_file"
            }
        }]
        """
        # TODO(KM 31-10-2016): Need to also parse the class properties.

    def parse(self, sim_xmi_file):
        """
        Read simulator description data from xmi file into `self.device_properties`

        Stores all the simulator description data from the xmi tree into
        appropriate attribute, command and device property data structures.
        Loops through the xmi tree class elements and appends description
        information of dynamic/attributes into `self.device_attributes`,
        commands into `self.device_commands`, and device_properties into
        `self.device_properties`.

        Parameters
        ----------
        sim_xmi_file: str
            Name of simulator descrition data file

        Notes
        =====
        - Data structures, are type list with dictionary elements keyed with
          description data and values must be the corresponding data value.

        """
        tree = ET.parse(sim_xmi_file)
        root = tree.getroot()
        device_class = root.find('classes')
        self.device_class_name = device_class.attrib['name']
        for class_description_data in device_class:
            if class_description_data.tag in ['commands']:
                command_info = (
                    self.extract_command_description_data(class_description_data))
                self.device_commands.append(command_info)
            elif class_description_data.tag in ['dynamicAttributes', 'attributes']:
                attribute_info = self.extract_attributes_description_data(
                                            class_description_data)
                self.device_attributes.append(attribute_info)
            elif class_description_data.tag in ['deviceProperties']:
                device_property_info = self.extract_device_property_description_data(
                                                       class_description_data)
                self.device_properties.append(device_property_info)

    def extract_command_description_data(self, description_data):
        """Extract command description data from the xmi tree element.

        Parameters
        ----------
        description_data: xml.etree.ElementTree.Element
            XMI tree element with command data, where
            expected element tag(s) are (i.e. description_data.tag)
            ['argin', 'argout'] and
            description_data.attrib contains
            {
                "description": "Turn On Device",
                "displayLevel": "OPERATOR",
                "isDynamic": "false",
                "execMethod": "on",
                "polledPeriod": "0",
                "name": "On"
            }

        Returns
        -------
        command_data: dict
            Dictionary of all the command data required to create a tango command

        """
        command_data = description_data.attrib
        input_parameter = description_data.find('argin')
        command_data['arginDescription'] = input_parameter.attrib['description']
        command_data['arginType'] = self._get_arg_type(input_parameter)
        output_parameter = description_data.find('argout')
        command_data['argoutDescription'] = output_parameter.attrib['description']
        command_data['argoutType'] = self._get_arg_type(output_parameter)
        return command_data

    def extract_attributes_description_data(self, description_data):
        """Extract attribute description data from the xmi tree element.

        Parameters
        ----------
        description_data: xml.etree.ElementTree.Element
            XMI tree element with attribute data

            Expected element tag(s) are (i.e. description_data.tag)
            'dynamicAttributes'

            description_data.find('properties').attrib contains
            {
                "description": "",
                "deltaValue": "",
                "maxAlarm": "",
                "maxValue": "",
                "minValue": "",
                "standardUnit": "",
                "minAlarm": "",
                "maxWarning": "",
                "unit": "",
                "displayUnit": "",
                "format": "",
                "deltaTime": "",
                "label": "",
                "minWarning": ""
            }

            and

            description_data.attrib contains
            {
                "maxX": "",
                "maxY": "",
                "attType": "Scalar",
                "polledPeriod": "0",
                "displayLevel": "OPERATOR",
                "isDynamic": "false",
                "rwType": "WRITE",
                "allocReadMember": "false",
                "name": "Constant"
            }



            description_data.find('eventCriteria').attrib contains
            {
                "relChange": "10",
                "absChange": "0.5",
                "period": "1000"
            }

            description_data.find('evArchiveCriteria').attrib contains
            {
                "relChange": "10",
                "absChange": "0.5",
                "period": "1000"
            }

        Returns
        -------
        attribute_data: dict
            Dictionary of all attribute data required to create a tango attribute

        """
        attribute_data = dict()
        attribute_data['dynamicAttributes'] = description_data.attrib

        attType = attribute_data['dynamicAttributes']['attType']
        if attType in POGO_PYTANGO_ATTR_FORMAT_TYPES_MAP.keys():
            attribute_data['dynamicAttributes']['attType'] = (
                    POGO_PYTANGO_ATTR_FORMAT_TYPES_MAP[attType])

        attribute_data['dynamicAttributes']['maxX'] = (1
                if attribute_data['dynamicAttributes']['maxX'] == ''
                else int(attribute_data['dynamicAttributes']['maxX']))
        attribute_data['dynamicAttributes']['maxY'] = (0
                if attribute_data['dynamicAttributes']['maxY'] == ''
                else int(attribute_data['dynamicAttributes']['maxY']))

        attribute_data['dynamicAttributes']['dataType'] = (
            self._get_arg_type(description_data))
        attribute_data['properties'] = description_data.find('properties').attrib
        # TODO(KM 31-10-2016): Events information is not mandatory for attributes, need
        # to handle this properly as it raises an AttributeError error when trying to
        # parse an xmi file with an attribute with not event information specified.
        attribute_data['eventCriteria'] = description_data.find(
                'eventCriteria').attrib
        attribute_data['eventArchiveCriteria'] = description_data.find(
                'evArchiveCriteria').attrib
        return attribute_data

    def extract_device_property_description_data(self, description_data):
        """Extract device property description data from the xmi tree element.

        Parameters
        ----------
        description_data: xml.etree.ElementTree.Element
            XMI tree element with device property data

            Expected element tag(s) are (i.e. description_data.tag)
            ['DefaultPropValue']

            description_data.attrib contains
            {
                'description': '',
                'name': 'katcp_address'
            }

        Returns
        -------
        device_property_data: dict
            Dictionary of all device property data required
            to create a tango device property

        """
        device_property_data = dict()
        device_property_data['deviceProperties'] = description_data.attrib
        device_property_data['deviceProperties']['type'] = (
                self._get_arg_type(description_data))
        if description_data.find('defaultPropValue'):
            device_property_data['deviceProperties']['defaultPropValue'] = (
                 description_data.find('defaultPropValue').text)
        return device_property_data

    def _get_arg_type(self, description_data):
        """Extract argument data type from the xmi tree element.

        Parameters
        ----------
        description_data: xml.etree.ElementTree.Element
            XMI tree element with device_property or attribute or command data

            Expected element tag(s) are (i.e. description_data.tag)
            ['dataType'] for attributes and dynamicAttributes
            ['type'] for commands and deviceProperties

        Returns
        -------
        arg_type: tango._tango.CmdArgType
            Tango argument type

        """
        if description_data.tag in ['attributes', 'dynamicAttributes']:
            pogo_type = description_data.find('dataType').attrib.values()[0]
        else:
            pogo_type = description_data.find('type').attrib.values()[0]
        # pogo_type has format -> pogoDsl:DoubleType
        # Pytango type must be of the form DevDouble
        arg_type = pogo_type.split(':')[1].replace('Type', '')
        # pogo_type for status turns out to be 'pogoDsl:ConstStringType
        # For now it will be treated as normal DevString type
        if arg_type.find('Const') != -1:
            arg_type = arg_type.replace('Const', '')
        # The out_type of the device State command is PyTango._PyTango.CmdArgType.DevState
        # instead of the default PyTango.utils.DevState
        if arg_type == 'State':
            return CmdArgType.DevState
        arg_type = getattr(PyTango, 'Dev' + arg_type)
        return arg_type


    def get_reformatted_device_attr_metadata(self):
        """Converts the device_attributes data structure into a dictionary
        to make searching easier.

        Returns
        -------
        attributes: dict
            A dictionary of all the device attributes together with their
            metadata specified in the POGO generated XMI file. The key
            represents the name of the attribute and the value is a dictionary
            of all the attribute's metadata.

            e.g.
            {'input_comms_ok': {
                'abs_change': '',
                'archive_abs_change': '',
                'archive_period': '1000',
                'archive_rel_change': '',
                'data_type': PyTango._PyTango.CmdArgType.DevBoolean,
                'delta_t': '',
                'delta_val': '',
                'description': 'Communications with all weather sensors are nominal.',
                'display_unit': '',
                'event_period': '1000',
                'format': '',
                'label': 'Input communication OK',
                'max_alarm': '',
                'max_value': '',
                'max_warning': '',
                'min_alarm': '',
                'min_value': '',
                'min_warning': '',
                'name': 'input_comms_ok',
                'period': '1000',
                'rel_change': '',
                'standard_unit': '',
                'unit': '',
                'writable': 'READ'},
            }

        """
        attributes = {}

        for pogo_attribute_data in self.device_attributes:
            attribute_meta = {}
            for (prop_group, default_attr_props) in (
                    POGO_USER_DEFAULT_ATTR_PROP_MAP.items()):
                for pogo_prop, user_default_prop in default_attr_props.items():
                    attribute_meta[user_default_prop] = (
                            pogo_attribute_data[prop_group][pogo_prop])
            attributes[attribute_meta['name']] = attribute_meta
        return attributes

    def get_reformatted_cmd_metadata(self):
        """Converts the device_commands data structure into a dictionary that
        makes searching easier.

        Returns
        -------
        commands : dict
            A dictionary of all the device commands together with their
            metadata specified in the POGO generated XMI file. The key
            represents the name of the command and the value is a dictionary
            of all the attribute's metadata.

            e.g. { 'cmd_name': {cmd_properties}

                 }
        """
        temp_commands = {}
        for cmd_info in self.device_commands:
            temp_commands[cmd_info['name']] = cmd_info

        commands = {}
        # Need to convert the POGO parameter names to the TANGO names
        for cmd_name, cmd_metadata in temp_commands.items():
            commands_metadata = {}
            for cmd_prop_name, cmd_prop_value in cmd_metadata.items():
                try:
                    commands_metadata.update(
                        {POGO_USER_DEFAULT_CMD_PROP_MAP[cmd_prop_name]: cmd_prop_value})
                except KeyError:
                    MODULE_LOGGER.info(
                        "The property '%s' cannot be translated to a "
                        "corresponding parameter in the TANGO library",
                        cmd_prop_name)
            commands[cmd_name] = commands_metadata
        return commands

    def get_reformatted_properties_metadata(self):
        """Creates a dictionary of the device properties and their metadata.

        Returns
        -------
        device_properties: dict
            A dictionary of all the device properties together with their
            metadata specified in the POGO generated XMI file. The keys
            represent the name of the device property and the value is a
            dictionary of all the property's metadata.

            e.g. { 'device_property_name' : {device_property_metadata}

                 }

        """
        device_properties = {}
        for properties_info in self.device_properties:
            device_properties[properties_info['deviceProperties']['name']] = (
                    properties_info['deviceProperties'])

        return device_properties

    def get_reformatted_override_metadata(self):
        # TODO(KM 15-12-2016) The PopulateModelQuantities and PopulateModelActions
        # classes assume that the parsers we have developed have the same interface
        # so this method does nothing but return an empty dictionary. Might provide
        # an implementation when the XMI file has such parameter information (provided
        # in the SIMDD file).
        return {}

class PopulateModelQuantities(object):
    """Used to populate/update model quantities.

    Populates the model quantities using the data from the TANGO device information
    captured in the POGO generated xmi file.

    Attributes
    ----------
    parser_instance: Parser instance
        The Parser object which reads an xmi/xml/json file and parses it into device
        attributes, commands, and properties.
    sim_model:  Model instance
        An instance of the Model class which is used for simulation of simple attributes.
    """
    def __init__(self, parser_instance, tango_device_name, sim_model=None):
        self.parser_instance = parser_instance
        if sim_model:
            if isinstance(sim_model, model.Model):
                self.sim_model = sim_model
            else:
                raise SimModelException("The sim_model object passed is not an "
                    "instance of the class mkat_tango.simlib.model.Model")

        else:
            self.sim_model = model.Model(tango_device_name)
        self.setup_sim_quantities()

    def setup_sim_quantities(self):
        """Set up self.sim_quantities from Model with simulated quantities.

        Places simulated quantities in sim_quantities dict. Keyed by name of
        quantity, value must be instances satifying the
        :class:`quantities.Quantity` interface

        Notes
        =====
        - Must use self.start_time to set initial time values.
        - Must call super method after setting up `sim_quantities`

        """
        start_time = self.sim_model.start_time
        GaussianSlewLimited = partial(
            quantities.GaussianSlewLimited, start_time=start_time)
        ConstantQuantity = partial(
            quantities.ConstantQuantity, start_time=start_time)
        attributes = self.parser_instance.get_reformatted_device_attr_metadata()

        for attr_name, attr_props in attributes.items():
            if attr_props['data_type'] in CONSTANT_DATA_TYPES:
                self.sim_model.sim_quantities[attr_name] = ConstantQuantity(
                    meta=attr_props, start_value=True)
            else:
                try:
                    sim_attr_quantities = self.sim_attribute_quantities(
                            float(attr_props['min_value']),
                            float(attr_props['max_value']))
                except ValueError:
                    raise NotImplementedError(
                            'Attribute min or max not specified')
                self.sim_model.sim_quantities[
                        attr_props['name']] = GaussianSlewLimited(
                                meta=attr_props, **sim_attr_quantities)

    def sim_attribute_quantities(self, min_value, max_value, slew_rate=None):
        """Simulate attribute quantities with a Guassian value distribution

        Parameters
        ==========
        min_value : float
            minimum attribute value to be simulated
        max_value : float
            maximum attribute value to be simulated
        slew_rate : float
            maximum changing rate of the simulated quantities between min
            and max values

        Returns
        ======
        sim_attribute_quantities : dict
            Dict of Gaussian simulated quantities

        Notes
        =====
        - Statistical simulation parameters (mean, std dev, slew rate) are
          derived from the min/max values of the attribute.

        """
        sim_attribute_quantities = dict()
        if slew_rate:
            max_slew_rate = slew_rate
        else:
            # A hard coded value is computed as follows
            max_slew_rate = (max_value + abs(min_value))/10.0
        sim_attribute_quantities['max_slew_rate'] = max_slew_rate
        sim_attribute_quantities['min_bound'] = min_value
        sim_attribute_quantities['max_bound'] = max_value
        # TODO (AR) 2016-10-14: In the future we might define a way to specify
        # simulation defaults or simulation bounds different from the XMI bounds
        sim_attribute_quantities['mean'] = (max_value - min_value)/2
        sim_attribute_quantities['std_dev'] = max_slew_rate/2
        return sim_attribute_quantities


class PopulateModelActions(object):
    """Used to populate/update model actions.

    Populates the model actions using the data from the TANGO device information
    captured in the POGO generated xmi file.

    Attributes
    ----------
    command_info: dict
        A dictionary of all the device commands together with their
        metadata specified in the POGO generated XMI file. The key
        represents the name of the command and the value is a dictionary
        of all the attribute's metadata.

    sim_model:  Model instance
        An instance of the Model class which is used for simulation of simple attributes
        and/or commands.
    """
    def __init__(self, parser_instance, tango_device_name, model_instance=None):
        self.parser_instance = parser_instance
        if model_instance is None:
            self.sim_model = model.Model(tango_device_name)
        else:
            self.sim_model = model_instance
        self.add_actions()

    def add_actions(self):
        command_info = self.parser_instance.get_reformatted_cmd_metadata()
        override_info = self.parser_instance.get_reformatted_override_metadata()
        if override_info != {}:
            for klass_info in override_info.values():
                if klass_info['module_directory'] == 'None':
                    module = importlib.import_module(klass_info['module_name'])
                else:
                    module = imp.load_source(klass_info['module_name'].split('.')[-1],
                                             klass_info['module_directory'])
                klass = getattr(module, klass_info['class_name'])
                instance = klass()
        else:
            instance = None

        for cmd_name, cmd_meta in command_info.items():
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
            instance_attributes = dir(instance)
            instance_attributes_list = [attr.lower() for attr in instance_attributes]
            attr_occurences = instance_attributes_list.count(
                'action_{}'.format(cmd_name.lower()))
            # Check if there is only one override class method defined for each command
            if attr_occurences > MAX_NUM_OF_CLASS_ATTR_OCCURENCE:
                raise Exception("The command '{}' has multiple override methods defined"
                                " in the override class".format(cmd_name))
            # Assuming that there is only one override method defined, now we check if
            # it is in the correct letter case.
            elif attr_occurences == MAX_NUM_OF_CLASS_ATTR_OCCURENCE:
                try:
                    instance_attributes.index('action_{}'.format(cmd_name.lower()))
                except ValueError:
                    raise Exception(
                        "Only lower-case override method names are supported")

            handler = getattr(instance, 'action_{}'.format(cmd_name.lower()),
                              self.generate_action_handler(
                              cmd_name, cmd_meta['dtype_out'], actions))

            self.sim_model.set_sim_action(cmd_name, handler)
            # Might store the action's metadata in the sim_actions dictionary
            # instead of creating a separate dict.
            self.sim_model.sim_actions_meta[cmd_name] = cmd_meta

    def generate_action_handler(self, action_name, action_output_type, actions=None):
        """Generates and returns an action handler to manage tango commands

        Parameters
        ----------
        action_name: str
            Name of action handler to generate
        action_output_type: PyTango._PyTango.CmdArgType
            Tango command argument type
        actions: list
            List of actions that the handler will provide

        Returns
        -------
        action_handler: function
            action handler, taking command input argument in case of tango
            commands with input arguments.
        """
        if actions is None:
            actions = []

        def action_handler(model, data_in=None):
            """Action handler taking command input arguments

            Parameters
            ----------
            model: model.Model
                Model instance
            data_in: float, string, int, etc.
                Input arguments of tango command

            Returns
            -------
            return_value: float, string, int, etc.
                Output value of an executed tango command
            """
            # args contains the model instance and tango device instance
            # whereby the third item is a value in the case of commands with
            # input parameters.
            temp_variables = {}
            for action in actions:
                if action['behaviour'] == 'input_transform':
                    temp_variables[action['destination_variable']] = data_in
                if action['behaviour'] == 'side_effect':
                    quantity = action['destination_quantity']
                    temp_variables[action['source_variable']] = data_in
                    model_quantity = model.sim_quantities[quantity]
                    model_quantity.set_val(data_in, model.time_func())
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

class SimModelException(Exception):
    def __init__(self, message):
        super(SimModelException, self).__init__(message)

