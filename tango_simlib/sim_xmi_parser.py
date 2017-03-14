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

import xml.etree.ElementTree as ET
import PyTango

from PyTango import (DevBoolean, DevString, DevEnum, AttrDataFormat,
                     CmdArgType)

MODULE_LOGGER = logging.getLogger(__name__)
CONSTANT_DATA_TYPES = frozenset([DevBoolean, DevEnum, DevString])
POGO_PYTANGO_ATTR_FORMAT_TYPES_MAP = {
    'Image': AttrDataFormat.IMAGE,
    'Scalar': AttrDataFormat.SCALAR,
    'Spectrum': AttrDataFormat.SPECTRUM}

# TODO(KM 31-10-2016): Need to add xmi attributes' properties that are currently
# not being handled by the parser e.g. [displayLevel, enumLabels] etc.
POGO_USER_DEFAULT_ATTR_PROP_MAP = {
    'dynamicAttributes': {
        'name': 'name',
        'dataType': 'data_type',
        'rwType': 'writable',
        'polledPeriod': 'period',
        'attType': 'data_format',
        'enum_labels': 'enum_labels',
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
        if str(attribute_data['dynamicAttributes']['dataType']) == 'DevEnum':
            enum_labels = []
            for child in description_data.getchildren():
                if child.tag == 'enumLabels':
                    enum_labels.append(child.text)
            attribute_data['dynamicAttributes']['enum_labels'] = sorted(enum_labels)

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
            # The DevVarTypeArray data type specified in pogo writes
            # TypeArray in xmi file instead
            if arg_type in ['FloatArray', 'DoubleArray', 'StringArray']:
                arg_type = getattr(PyTango, 'DevVar' + arg_type)
            else:
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
                'data_format: PyTango._PyTango.AttrDataFormat.SCALAR,
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
                'writable': 'READ',
                'enum_labels': []}, # If attribute data type is DevEnum
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
