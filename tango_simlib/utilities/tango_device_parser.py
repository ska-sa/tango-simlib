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
            Tango device name in the domain/family/member format
        """
        assert "TANGO_HOST" in os.environ, "TANGO_HOST env variable is not set"
        self.device_proxy = tango.DeviceProxy(tango_device_name)
        self.device_class_name = self.device_proxy.info().dev_class

        for attribute in self.device_proxy.attribute_list_query():
            self.data_dict["meta"]["attributes"][attribute.name] = {
                "name": attribute.name,
                "data_type": attribute.data_format,
            }

        for command in self.device_proxy.get_command_config():
            self.data_dict["meta"]["commands"][command.cmd_name] = {
                "name": command.cmd_name,
                "dtype_in": command.in_type,
                "dtype_out": command.out_type,
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
                        'data_type': tango._tango.CmdArgType,
                        'name': '<attribute-name>',
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
                        'name': '<command-name>',
                        'dtype_out': tango._tango.CmdArgType
                        'dtype_in': tango._tango.CmdArgType
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
