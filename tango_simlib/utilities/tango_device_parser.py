#########################################################################################
# Copyright 2020 SKA South Africa (http://ska.ac.za/)                                   #
#                                                                                       #
# BSD license - see LICENSE.txt for details                                             #
#########################################################################################
# pylint: disable=W0221
"""This module performs the parsing of a running Tango device.
"""
from __future__ import absolute_import, division, print_function
import os

import tango

from tango_simlib.utilities.base_parser import Parser


class TangoDeviceParser(Parser):
    """Parses a running TANGO device to YAML.
    """

    def __init__(self):
        super(TangoDeviceParser, self).__init__()
        self.device_proxy = None
        self.data_dict = {
            "class": None,
            "meta": {"commands": {}, "attributes": {}, "properties": {}},
        }

    def parse(self, tango_device_name):
        """Interrogate a running Tango device and extract information from it.

        Parameters
        ----------
        tango_device_name: str
            Tango device name in the domain/family/member format or the
            FQDN tango://<TANGO_HOST>:<TANGO_PORT>/domain/family/member
        """
        self.device_proxy = tango.DeviceProxy(tango_device_name)
        self.device_class_name = self.device_proxy.info().dev_class

        for attribute in self.device_proxy.attribute_list_query_ex():
            attr_data = {
                "name": attribute.name,
                "data_type": tango.CmdArgType.values[attribute.data_type],
                "data_format": attribute.data_format,
                "description": attribute.description,
                "disp_level": attribute.disp_level,
                "display_unit": attribute.display_unit,
                "enum_labels": list(attribute.enum_labels),
                "format": attribute.format,
                "label": attribute.label,
                "max_alarm": attribute.max_alarm,
                "max_dim_x": attribute.max_dim_x,
                "max_dim_y": attribute.max_dim_y,
                "max_value": attribute.max_value,
                "min_alarm": attribute.min_alarm,
                "min_value": attribute.min_value,
                "standard_unit": attribute.standard_unit,
                "unit": attribute.unit,
                "writable": str(attribute.writable),
                "writable_attr_name": attribute.writable_attr_name,
            }
            self.data_dict["meta"]["attributes"][attribute.name] = attr_data

        for command in self.device_proxy.get_command_config():
            self.data_dict["meta"]["commands"][command.cmd_name] = {
                "name": command.cmd_name,
                "dtype_in": command.in_type,
                "dtype_out": command.out_type,
                "doc_out": command.out_type_desc,
                "doc_in": command.in_type_desc,
                "disp_level": command.disp_level.name,
            }

        for prop in self.device_proxy.get_property_list("*"):
            self.data_dict["meta"]["properties"][prop] = {"name": prop}

    def get_device_attribute_metadata(self):
        """Returns the attributes.

        Returns
        -------
        dict
            E.g.
                {
                    '<attribute-name>': {
                        "data_format": "SPECTRUM",
                        "data_type": "DevString",
                        "description": "",
                        "display_unit": "No display unit",
                        "enum_labels": []
                        "format": "%s",
                        "label": "Timing_info",
                        "max_alarm": "Not specified",
                        "max_dim_x": 64,
                        "max_dim_y": 0,
                        "max_value": "Not specified",
                        "min_alarm": "Not specified",
                        "min_value": "Not specified",
                        "name": "<attribute-name>",
                        "standard_unit": "No standard unit",
                        "unit": "",
                        "writable": "READ",
                    }
                ...
                }
        """
        assert self.device_proxy, "`parse` needs to be called first"
        return self.data_dict["meta"]["attributes"]

    def get_device_command_metadata(self):
        """Returns the commands.

        Returns
        -------
        dict
            E.g.
                {
                    '<command-name>': {
                        "doc_out": "out_type_desc",
                        "disp_level": "OPERATOR",
                        "name": "<command-name>",
                        "doc_in": "in_type_desc",
                        "dtype_out": "DevVoid",
                        "dtype_in": "DevVoid",
                    }
                ...
                }
        """
        assert self.device_proxy, "`parse` needs to be called first"
        return self.data_dict["meta"]["commands"]

    def get_device_properties_metadata(self, _):
        """Get the device properties

        Returns
        -------
        dict
            E.g.
                {
                    '<property-name>': {
                        'name': '<property-name>'
                    }
                ...
                }
        """
        assert self.device_proxy, "`parse` needs to be called first"
        return self.data_dict["meta"]["properties"]

    def get_device_cmd_override_metadata(self):
        """This method is not implemented"""
        raise NotImplementedError("get_device_cmd_override_metadata not implemented")

    def get_parsed_data(self):
        """Returns all the parsed data

        Returns
        -------
        dict
        """
        return self.data_dict
