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

from PyTango import (DevBoolean, DevString, DevEnum, AttrDataFormat,
                     CmdArgType, DevDouble, DevFloat, DevLong, DevVoid)

from tango_simlib import quantities
from tango_simlib import model

MODULE_LOGGER = logging.getLogger(__name__)

DEFAULT_TANGO_COMMANDS = frozenset(['State', 'Status', 'Init'])
CONSTANT_DATA_TYPES = frozenset([DevBoolean, DevEnum, DevString])
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

# In the case where an attribute with contant quantity simulation type is
# specified, this dict is used to convert the initial value if specified to
# the data-type corresponding to the attribute data-type.
INITIAL_CONTANT_VALUE = {
    DevString: str,
    DevDouble: float,
    DevBoolean: bool}

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
        self.data_description_file_name = ''
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
                "name": "sim_xmi_description_file",
                "DefaultPropValue": "<any object>"
            }
        }]
        """
        self.class_properties = []
        """Data structure format is a list containing class property info in a dict

        e.g.
        [{
            "classProperties": {
                "type": DevString,
                "mandatory": "true",
                "description": "Path to the pogo generate xmi file",
                "name": "sim_xmi_description_file",
                "DefaultPropValue": "<any object>"
            }
        }]
        """

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
        self.data_description_file_name = sim_xmi_file
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
                device_property_info = self.extract_property_description_data(
                    class_description_data, class_description_data.tag)
                self.device_properties.append(device_property_info)
            elif class_description_data.tag in ['classProperties']:
                class_property_info = self.extract_property_description_data(
                    class_description_data, class_description_data.tag)
                self.class_properties.append(class_property_info)

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

        try:
            attribute_data['eventCriteria'] = description_data.find(
                'eventCriteria').attrib
        except AttributeError:
            MODULE_LOGGER.info(
                "No periodic/change event(s) information was captured in the XMI file")

        try:
            attribute_data['eventArchiveCriteria'] = description_data.find(
                'evArchiveCriteria').attrib
        except AttributeError:
            MODULE_LOGGER.info(
                "No archive event(s) information was captured in the XMI file.")

        return attribute_data

    def extract_property_description_data(self, description_data, property_group):
        """Extract device/class property description data from the xmi tree element.

        Parameters
        ----------
        description_data: xml.etree.ElementTree.Element
            XMI tree element with device property data

            Expected element tag(s) are (i.e. description_data.tag)
            ['DefaultPropValue']

            description_data.attrib contains
            {
                'description': '',
                'name': 'katcp_address',
                'type': ''
            }

        property_group: str
            A string representing a group to which the property belongs to, either
            device properties or class properties.

        Returns
        -------
        device_property_data: dict
            Dictionary of all device property data required
            to create a tango device property

        """
        property_data = dict()
        property_data[property_group] = description_data.attrib
        property_data[property_group]['type'] = (
                self._get_arg_type(description_data))
        try:
            property_data[property_group]['DefaultPropValue'] = (
                description_data.find('DefaultPropValue').text)
        except KeyError:
            MODULE_LOGGER.info("%s has no default value(s) specified", property_group)
        except AttributeError:
            MODULE_LOGGER.info("The 'DefaultPropValue' element is not specified in the"
                               " description file for the %s tag", property_group)
        return property_data

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

        try:
            arg_type = getattr(PyTango, 'Dev' + arg_type)
        except AttributeError:
            MODULE_LOGGER.debug("PyTango has no attribute 'Dev{}".format(arg_type))
            raise AttributeError("PyTango has no attribute 'Dev{}.\n Try replacing"
                                 " '{}' with 'Var{}' in the configuration file"
                                 .format(*(3*(arg_type,))))

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
                    try:
                        attribute_meta[user_default_prop] = (
                            pogo_attribute_data[prop_group][pogo_prop])
                    except KeyError:
                        MODULE_LOGGER.debug("{} information is not captured in the XMI"
                                            " file".format(pogo_prop))
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

    def get_reformatted_properties_metadata(self, property_group):
        """Creates a dictionary of the device properties and their metadata.

        Parameter
        ---------
        property_group: str
            A string representing a group to which the property belongs to, either
            device properties or class properties (deviceProperties or classProperties).

        Returns
        -------
        device_properties: dict
            A dictionary of all the device properties together with their
            metadata specified in the POGO generated XMI file. The keys
            represent the name of the device property and the value is a
            dictionary of all the property's metadata.

            e.g. { 'device_property_name' : {device_property_metadata}

                 }
        property_group: str
            A string representing a group to which the property belongs to, either
            device properties or class properties.

        """
        properties = {}
        if property_group == 'deviceProperties':
            props = self.device_properties
        elif property_group == 'classProperties':
            props = self.class_properties
        else:
            raise Exception("Wrong argument provided")

        for properties_info in props:
            properties[properties_info[property_group]['name']] = (
                    properties_info[property_group])

        return properties

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
        attributes = self.parser_instance.get_reformatted_device_attr_metadata()

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
                model_attr_props.update(attr_props)

            if model_attr_props.has_key('quantity_simulation_type'):
                if model_attr_props['quantity_simulation_type'] == 'ConstantQuantity':
                    try:
                        initial_value = model_attr_props['initial_value']
                    except KeyError:
                        # `initial_value` is an optional parameter, thus if not
                        # specified in the SIMDD datafile, an initial value of
                        # default value of `True` is assigned to the attribute
                        # quantity initial value
                        initial_value = ""
                        MODULE_LOGGER.info(
                            "Parameter `initial_value` does not exist. Default "
                            "of True will be used")
                    init_val = initial_value if initial_value is not "" else True
                    start_val = INITIAL_CONTANT_VALUE[model_attr_props['data_type']](
                            init_val)
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
                self.sim_model.sim_quantities[attr_name] = quantities.ConstantQuantity(
                        start_time=start_time, meta=model_attr_props, start_value=True)

    def sim_attribute_quantities(self, min_bound, max_bound, max_slew_rate,
                                 mean, std_dev):
        """Simulate attribute quantities with a Guassian value distribution

        Parameters
        ==========
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
        ======
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
        instances = {}
        if override_info != {}:
            for klass_info in override_info.values():
                if klass_info['module_directory'] == 'None':
                    module = importlib.import_module(klass_info['module_name'])
                else:
                    module = imp.load_source(klass_info['module_name'].split('.')[-1],
                                             klass_info['module_directory'])
                klass = getattr(module, klass_info['class_name'])
                instance = klass()
                instances[klass_info['name']] = instance

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
            instance = None
            if cmd_name.startswith('test_'):
                for instance_ in instances:
                    if instance_.startswith('SimControl'):
                        instance = instances[instance_]
                self._check_override_action_presence(cmd_name, instance, 'test_action{}')
                handler = getattr(instance, 'test_action{}'.format(cmd_name.lower()),
                                  self.generate_action_handler(
                                      cmd_name, cmd_meta['dtype_out'], actions))
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
            self.sim_model.sim_actions_meta[cmd_name] = cmd_meta

    def _check_override_action_presence(self, cmd_name, instance, action_type):
        instance_attributes = dir(instance)
        instance_attributes_list = [attr.lower() for attr in instance_attributes]
        attr_occurences = instance_attributes_list.count(
            action_type.format(cmd_name.lower()))
        # Check if there is only one override class method defined for each command
        if attr_occurences > MAX_NUM_OF_CLASS_ATTR_OCCURENCE:
            raise Exception("The command '{}' has multiple override methods defined"
                            " in the override class".format(cmd_name))
        # Assuming that there is only one override method defined, now we check if
        # it is in the correct letter case.
        elif attr_occurences == MAX_NUM_OF_CLASS_ATTR_OCCURENCE:
            try:
                instance_attributes.index(action_type.format(cmd_name.lower()))
            except ValueError:
                raise Exception(
                    "Only lower-case override method names are supported")

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

        def action_handler(model, data_input=None, tango_dev=None):
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
            # TODO (KM 18-01-2016): Need to remove the tango_dev parameter from
            # action hanlder, currently used for testing functionality of the
            # override class actions.
            temp_variables = {}
            return_value = None
            for action in actions:
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

class SimModelException(Exception):
    def __init__(self, message):
        super(SimModelException, self).__init__(message)

