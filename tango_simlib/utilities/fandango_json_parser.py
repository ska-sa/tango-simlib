######################################################################################### 
# Author: cam@ska.ac.za                                                                 #
# Copyright 2018 SKA South Africa (http://ska.ac.za/)                                   #
#                                                                                       #
# BSD license - see LICENSE.txt for details                                             #
#########################################################################################
"""This module performs the parsing of the TANGO device data json file as produced by
the fandango library, containing the information needed to instantiate a useful device
simulator.
Instructions on how to create this json file can be found at the link below:
https://github.com/tango-controls/fandango/blob/master/doc/recipes/ExportDeviceData.rst
"""

import logging
import json

from tango import CmdArgType, AttrDataFormat

from tango_simlib.utilities.base_parser import Parser
from tango_simlib.utilities.helper_module import json_load_byteified

MODULE_LOGGER = logging.getLogger(__name__)

CMD_PROP_MAP = {
    'name': 'name',
    'in_type': 'dtype_in',
    'in_type_desc': 'doc_in',
    'out_type': 'dtype_out',
    'out_type_desc': 'doc_out'
}

class FandangoExportDeviceParser(Parser):

    def __init__(self):
	super(FandangoExportDeviceParser, self).__init__() 

        self._device_class_properties = {}

    def parse(self, json_file):
        self.data_description_file_name = json_file
        with open(json_file) as dev_data_file:
            device_data = json_load_byteified(dev_data_file)

        for data_component, elements in device_data.items():
            if data_component == 'attributes':
                self.preprocess_attribute_types(elements)
            elif data_component == 'commands':
                self.preprocess_command_types(elements)
            elif data_component == 'class_properties':
                self._device_class_properties.update(elements)
            elif data_component == 'properties':
                self._device_properties.update(elements)
            elif data_component == 'dev_class':
                self.device_class_name = elements     

    def preprocess_command_types(self, command_data):
        """Convert the command input and output data types from strings to the TANGO
        types and rename the command properties to match with the keyword arguments of
        the command signature.
        """
        for cmd_name, cmd_config in command_data.items():
            self._device_commands[cmd_name] = {}
            
            for cmd_prop, cmd_prop_value in cmd_config.items():
                try:
                    if cmd_prop in ['in_type', 'out_type']:
                        if cmd_prop_value.find('Const') != -1:
                            cmd_prop_value = cmd_prop_value.replace('Const', '')
                        cmd_prop_value = getattr(CmdArgType, cmd_prop_value)
                    self._device_commands[cmd_name].update(
                        {CMD_PROP_MAP[cmd_prop]: cmd_prop_value})
                except KeyError:
                    MODULE_LOGGER.info(
                        "The property '%s' cannot be translated to a corresponding "
                        "parameter in the TANGO library", cmd_prop)

    def preprocess_attribute_types(self, attribute_data):
        """Convert the attribute data types from strings to the TANGO types.
        """
        max_dim = {}
        for attr, attr_config in attribute_data.items():
            for attr_prop, attr_prop_value in attr_config.items():
                if attr_prop == 'data_type':
                    attr_config[attr_prop] = getattr(CmdArgType, attr_prop_value)
                elif attr_prop == 'data_format':
                    # checking if SPECTRUM format attr has max_dim_x key not registered
                    if (attr_prop_value == 'SPECTRUM' and 
                        'max_dim_x' not in attr_config.keys()):
                        max_dim[attr]= {'max_dim_x': len(attr_config['value']), 'max_dim_y': 0}
                    attr_config[attr_prop] = (
                        getattr(AttrDataFormat, attr_prop_value))

        for attr, max_config in max_dim.items():
            attribute_data[attr].update(max_config)

        self._device_attributes.update(attribute_data)           

    def get_device_attribute_metadata(self):
        """Returns the device's attributes' configuration.

        Returns
        -------
        self._device_attributes: dict
            The data structure format is a dict containing attribute info in a dict
            e.g.
                {
                'State': {
                    'alarms': {
                        'delta_t': 'Not specified',
                        'delta_val': 'Not specified',
                        'extensions': '[]',
                        'max_alarm': 'Not specified',
                        'max_warning': 'Not specified',
                        'min_alarm': 'Not specified',
                        'min_warning': 'Not specified'
                    },
                    'color': 'Lime',
                    'data_format': tango._tango.AttrDataFormat.SCALAR,
                    'data_type': tango._tango.CmdArgType.DevState,
                    'database': 'monctl:10000',
                    'description': '',
                    'device': 'tango/admin/monctl',
                    'display_unit': 'No display unit',
                    'events': {
                        'arch_event': {
                            'archive_abs_change': 'Not specified',
                            'archive_period': 'Not specified',
                            'archive_rel_change': 'Not specified',
                            'extensions': '[]'
                        },
                        'ch_event': {
                            'abs_change': 'Not specified',
                            'extensions': '[]',
                            'rel_change': 'Not specified'
                        },
                        'per_event': {
                            'extensions': '[]',
                            'period': '1000'
                        }
                    },
                    'format': 'Not specified',
                    'label': 'State',
                    'max_alarm': 'Not specified',
                    'min_alarm': 'Not specified',
                    'model': 'monctl:10000/tango/admin/monctl/State',
                    'name': 'State',
                    'polling': 1000,
                    'quality': PyTango.AttrQuality.ATTR_VALID,
                    'standard_unit': 'No standard unit',
                    'string': 'ON',
                    'time': 1519207194.715621,
                    'unit': '',
                    'value': 0,
                    'writable': 'READ'},
            }
        """
        return self._device_attributes

    def get_device_command_metadata(self):
        """Returns the device's commands' configuration.
        
        Returns
        -------
        self._device_attributes: dict
            The data structure format is a dict containing attribute info in a dict
            e.g.
            {
                'State': {
                    'doc_in': 'Uninitialised',
                    'doc_out': 'Device state',
                    'dtype_in': tango._tango.CmdArgType.DevVoid,
                    'dtype_out': tango._tango.CmdArgType.DevState,
                    'name': 'State'
                },
            }
        """
        return self._device_commands

    def get_device_properties_metadata(self, property_group):
        """Returns the device's class or device property configuration.
        
        Returns
        -------
        self._device_attributes: dict
            The data structure format is a dict containing class or device property
            info in a dict.
            e.g.
            {
                '<property_name>': <property_value>,
            }
        """
        return self._device_properties

    def get_device_cmd_override_metadata(self):
        return {}