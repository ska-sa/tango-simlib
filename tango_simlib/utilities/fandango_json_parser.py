#########################################################################################
# Author: cam@ska.ac.za                                                                 #
# Copyright 2018 SKA South Africa (http://ska.ac.za/)                                   #
#                                                                                       #
# BSD license - see LICENSE.txt for details                                             #
#########################################################################################
"""
This module performs the parsing of the TANGO device data json file as produced by
the fandango library, containing the information needed to instantiate a useful device
simulator.

Instructions on how to create this json file can be found at the link below:
https://github.com/tango-controls/fandango/blob/master/doc/recipes/ExportDeviceData.rst
"""
from __future__ import absolute_import, division, print_function
from future import standard_library

standard_library.install_aliases()  # noqa: E402

import json
import logging

from tango import AttrDataFormat, CmdArgType
from tango_simlib.utilities.base_parser import Parser
from tango_simlib.utilities.helper_module import json_load_byteified

MODULE_LOGGER = logging.getLogger(__name__)

CMD_PROP_MAP = {
    "name": "name",
    "in_type": "dtype_in",
    "in_type_desc": "doc_in",
    "out_type": "dtype_out",
    "out_type_desc": "doc_out",
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
            if data_component == "attributes":
                self.preprocess_attribute_types(elements)
                self._flatten_device_attribute_dictionary()
                self._remove_unused_device_attributes_keys()
            elif data_component == "commands":
                self.preprocess_command_types(elements)
            elif data_component == "class_properties":
                self._device_class_properties.update(elements)
            elif data_component == "properties":
                self.update_property_data(elements)
            elif data_component == "dev_class":
                self.device_class_name = elements

    def _flatten_device_attribute_dictionary(self):
        for attribute_name, attribute_config in self._device_attributes.items():
            _events_properties = attribute_config["events"]
            events_properties = self._extract_attribute_events_properties(
                _events_properties
            )
            attribute_config.update(events_properties)

            alarms_properties = attribute_config["alarms"]
            attribute_config.update(alarms_properties)

    def _remove_unused_device_attributes_keys(self):
        keys_to_pop = [
            "alarms",
            "color",
            "database",
            "device",
            "dim_x",
            "dim_y",
            "events",
            "extensions",
            "format",
            "model",
            "string",
            "time",
        ]
        for attribute_name, attribute_config in self._device_attributes.items():
            # pop out keys not required to configure an attribute
            for key in keys_to_pop:
                attribute_config.pop(key)

    def preprocess_command_types(self, command_data):
        """
        Convert the command input and output data types from strings to the TANGO
        types and rename the command properties to match with the keyword arguments of
        the command signature.
        """
        for cmd_name, cmd_config in command_data.items():
            self._device_commands[cmd_name] = {}

            for cmd_prop, cmd_prop_value in cmd_config.items():
                try:
                    if cmd_prop in ["in_type", "out_type"]:
                        if cmd_prop_value.find("Const") != -1:
                            cmd_prop_value = cmd_prop_value.replace("Const", "")
                        cmd_prop_value = getattr(CmdArgType, cmd_prop_value)
                    self._device_commands[cmd_name].update(
                        {CMD_PROP_MAP[cmd_prop]: cmd_prop_value}
                    )
                except KeyError:
                    MODULE_LOGGER.info(
                        "The property '%s' cannot be translated to a corresponding "
                        "parameter in the TANGO library",
                        cmd_prop,
                    )

    def preprocess_attribute_types(self, attribute_data):
        """Convert the attribute data types from strings to the TANGO types."""

        for attr, attr_config in attribute_data.items():
            # assign 'READ_WRITE' to all attributes with 'WT_UNKNOWN'
            attr_access = ["READ", "WRITE", "READ_WRITE", "READ_WITH_WRITE"]
            if attr_config["writable"] not in attr_access:
                attr_config["writable"] = "READ_WRITE"
            for attr_prop, attr_prop_value in attr_config.items():
                if attr_prop == "data_type":
                    attr_config[attr_prop] = getattr(CmdArgType, attr_prop_value)
                elif attr_prop == "data_format":
                    attr_config[attr_prop] = getattr(AttrDataFormat, attr_prop_value)

        self._device_attributes.update(attribute_data)

    def _extract_attribute_events_properties(self, attribute_events_configuration):
        """Flattens the events' properties dictionary.

        Parameters
        ----------
        attribute_events_configuration: dict
        e.g.
            {
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
           }

        Returns
        -------
        events_properties: dict
        e.g.
            {
                'abs_change': 'Not specified',
                'archive_abs_change': 'Not specified',
                'archive_period': 'Not specified',
                'archive_rel_change': 'Not specified',
                'event_period': '1000'
                'extensions': '[]'
                'rel_change': 'Not specified'
            }

        """
        events_properties = {}

        for event_props in attribute_events_configuration.values():
            events_properties.update(event_props)

        # Rename key 'period' to 'event_period'.
        events_properties["event_period"] = events_properties["period"]
        events_properties.pop("period")

        return events_properties

    def update_property_data(self, property_data):
        """
        Update key values to a dict with keys 'DefaultPropValue','name' and 'type'.

        Parameters
        ----------
        property_data: dict
        e.g.
            {
                '<property-name>': '<list-of-strings>',
                '<property-name>': '<list-of-strings>'
            }

        property_data is reformatted to the format below
            {
                '<property-name>': {
                    'DefaultPropValue': '<list-of-strings>',
                    'name': '<property-name>',
                    'type': '<data-type>'},
                '<property-name>': {
                    'DefaultPropValue': '<list-of-strings>',
                    'name': '<property-name>',
                    'type': '<data-type>'}
            }

        """
        prop_data = [
            (
                prop,
                dict(
                    [
                        ("DefaultPropValue", prop_val),
                        ("name", prop),
                        ("type", "VarStringArray"),
                    ]
                ),
            )
            for prop, prop_val in property_data.items()
        ]

        property_data = dict(prop_data)

        self._device_properties.update(property_data)

    def get_device_attribute_metadata(self):
        """Returns the device's attributes configuration.

        Returns
        -------
        self._device_attributes: dict
            The data structure format is a dict containing attribute info in a dict
            e.g.
                {
                'State': {
                    'abs_change': 'Not specified',
                    'archive_abs_change': 'Not specified',
                    'archive_period': 'Not specified',
                    'archive_rel_change': 'Not specified',
                    'data_format': tango._tango.AttrDataFormat.SCALAR,
                    'data_type': tango._tango.CmdArgType.DevState,
                    'description': '',
                    'display_unit': 'No display unit',
                    'delta_t': 'Not specified',
                    'delta_val': 'Not specified',
                    'enum_labels': [],
                    'event_period': '1000',
                    'format': 'Not specified',
                    'label': 'State',
                    'max_alarm': 'Not specified',
                    'max_dim_x': 1,
                    'max_dim_y': 0,
                    'max_value': 'Not specified',
                    'max_warning': 'Not specified',
                    'min_alarm': 'Not specified',
                    'min_value': 'Not specified',
                    'min_warning': 'Not specified',
                    'name': 'State',
                    'polling': 1000,
                    'quality': PyTango.AttrQuality.ATTR_VALID,
                    'rel_change': 'Not specified',
                    'standard_unit': 'No standard unit',
                    'unit': '',
                    'value': 0,
                    'writable': 'READ'},
            }
        """
        return self._device_attributes

    def get_device_command_metadata(self):
        """Returns the device's commands configuration.

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
                '<property-name>': {
                    'DefaultPropValue': '<list-of-strings>',
                    'name': '<property-name>',
                    'type': '<data-type>'}
            }
        """
        return self._device_properties

    def get_device_cmd_override_metadata(self):
        return {}
