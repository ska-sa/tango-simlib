#!/usr/bin/env python
###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2018 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################
"""This module performs the parsing of the TANGO device data json file ,
containing the information needed to instantiate a useful device simulator.
@author MeerKAT CAM team <cam@ska.ac.za>
"""

import logging
import json

from PyTango._PyTango import CmdArgType, AttrDataFormat

MODULE_LOGGER = logging.getLogger(__name__)

CMD_PROP_MAP = {
    'name': 'name',
    'in_type': 'dtype_in',
    'in_type_desc': 'doc_in',
    'out_type': 'dtype_out',
    'out_type_desc': 'doc_out'
}

class DeviceDataParser(object):

    def __init__(self):
        """Parser class handling a TANGO device data file in json format.

        Creating an instance of this class requires calling :meth:`parse` method
        afterwards to extract all the provided TANGO attributes, commands,
        device property and device override class information from the specified
        file. The formated data is a dict structure and can be obtained using
        :meth:`get_reformatted_device_attr_metadata`,
        :meth:`get_reformatted_cmd_metadata`,
        :meth:`get_reformatted_properties_metadata` and
        :meth:`get_reformatted_override_metadata`.
        """

        # Simulator decription datafile in json format
        self.data_description_file_name = ''
        self.device_class_name = ''
        self._device_attributes = {}
        """The data structure format is a dict containing attribute info in a dict
            {
                u'<attribute_name>': {
                    u'alarms': {
                        u'delta_t': u'Not specified',
                        u'delta_val': u'Not specified',
                        u'extensions': u'[]',
                        u'max_alarm': u'Not specified',
                        u'max_warning': u'Not specified',
                        u'min_alarm': u'Not specified',
                        u'min_warning': u'Not specified'
                    },
                    u'color': u'Lime',
                    u'data_format': <tango._tango.AttrDataFormat>,
                    u'data_type': <tango._tango.CmdArgType>,
                    u'database': u'monctl:10000',
                    u'description': u'',
                    u'device': u'tango/admin/monctl',
                    u'display_unit': u'No display unit',
                    u'events': {
                        u'arch_event': {
                            u'archive_abs_change': u'Not specified',
                            u'archive_period': u'Not specified',
                            u'archive_rel_change': u'Not specified',
                            u'extensions': u'[]'
                        },
                        u'ch_event': {
                            u'abs_change': u'Not specified',
                            u'extensions': u'[]',
                            u'rel_change': u'Not specified'
                        },
                        u'per_event': {
                            u'extensions': u'[]',
                            u'period': u'1000'
                        }
                    },
                    u'format': u'Not specified',
                    u'label': u'State',
                    u'max_alarm': u'Not specified',
                    u'min_alarm': u'Not specified',
                    u'model': u'monctl:10000/tango/admin/monctl/State',
                    u'name': u'State',
                    u'polling': 1000,
                    u'quality': u'ATTR_VALID',
                    u'standard_unit': u'No standard unit',
                    u'string': u'ON',
                    u'time': 1519128820.715947,
                    u'unit': u'',
                    u'value': 0,
                    u'writable': u'READ'},
            }
        """
        self._device_commands = {}
        """The data structure format is a dict containing command info in a dict
            {
                u'<command_name>': {
                    'doc_in': u'<description>',
                    'doc_out': u'<description>,
                    'dtype_in': <tango._tango.CmdArgType>,
                    'dtype_out': <tango._tango.CmdArgType>,
                    'name': u'<command_name>'
                },
            }
        """
        self._device_properties = {}
        """The data structure format is a list containing device property info in a dict
            {
                '<property_name>': <property_value>,
            }
        """
        self._device_class_properties = {}
        """The data structure format is a list containing device property info in a dict
            {
                '<property_name>': <property_value>,
            }
        """


    def parse(self, json_file):

        with open(json_file) as dev_data_file:
            device_data = json.load(dev_data_file)

        for data_component, elements in device_data.items():
            if data_component == 'attributes':
                self.preprocess_attr_types(elements)
            elif data_component == 'commands':
                self.update_command_dict(elements)
            elif data_component == 'class_properties':
                self._device_class_properties.update(elements)
            elif data_component == 'properties':
                self._device_properties.update(elements)
            elif data_component == 'dev_class':
                self.device_class_name = elements     

    def update_command_dict(self, command_data):
        for cmd_name, cmd_config in command_data.items():
            self._device_commands[cmd_name] = {}
            
            for cmd_prop, cmd_prop_value in cmd_config.items():
                try:
                    if cmd_prop in ['in_type', 'out_type']:
                        if cmd_prop_value.find('Const') != -1:
                            cmd_prop_value = cmd_prop_value.replace('Const', '')
                        cmd_prop_value = getattr(CmdArgType, str(cmd_prop_value))
                    self._device_commands[cmd_name].update(
                        {CMD_PROP_MAP[cmd_prop]: cmd_prop_value})
                except KeyError:
                    MODULE_LOGGER.info(
                        "The property '%s' cannot be translated to a corresponding "
                        "parameter in the TANGO library", cmd_prop)

    def preprocess_attr_types(self, attribute_data):
        """Convert the attribute data types from strings to the TANGO types.
        """
        for attr_config in attribute_data.values():
            for attr_prop, attr_prop_value in attr_config.items():
                if attr_prop == 'data_type':
                    attr_config[attr_prop] = getattr(CmdArgType, str(attr_prop_value))
                elif attr_prop == 'data_format':
                    attr_config[attr_prop] = (
                        getattr(AttrDataFormat, str(attr_prop_value)))

        self._device_attributes.update(attribute_data)           

    def get_reformatted_device_attr_metadata(self):
        return self._device_attributes

    def get_reformatted_cmd_metadata(self):
        return self._device_commands

    def get_reformatted_properties_metadata(self, deviceProps):
        return self._device_properties

    def get_reformatted_override_metadata(self):
        return {}
