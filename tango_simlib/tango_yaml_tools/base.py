#########################################################################################
# Copyright 2020 SKA South Africa (http://ska.ac.za/)                                   #
#                                                                                       #
# BSD license - see LICENSE.txt for details                                             #
#########################################################################################
"""Module that contains the TangoToYAML class that parses a Tango device specification
   file (xmi, fgo) or a running Tango device into YAML"""
from pathlib import Path

import yaml


class TangoToYAML:
    """Class that translates a Tango specification file or a running Tango device to
       YAML."""

    def __init__(self, parser_class):
        """Initialise TangoToYAML with a parser class

        Parameters
        ----------
        parser_class : Python class definition
            A Python class that implements methods,
                - `parse`
                - `get_device_command_metadata`
                - `get_device_attribute_metadata`
                - `get_device_properties_metadata`
            and has the attribute `device_class_name`
        """
        self.parser = parser_class()

    def _build_yaml(self):
        """Build YAML from the parser
        """
        data_dict = [
            {
                "class": self.parser.device_class_name,
                "meta": {"commands": [], "attributes": [], "properties": []},
            }
        ]

        for command in self.parser.get_device_command_metadata().values():
            data_dict[0]["meta"]["commands"].append(
                {
                    "name": command["name"],
                    "dtype_in": command["dtype_in"].name,
                    "dtype_out": command["dtype_out"].name,
                }
            )
        for attr in self.parser.get_device_attribute_metadata().values():
            data_dict[0]["meta"]["attributes"].append(
                {"name": attr["name"],
                 "data_type": attr["data_type"].name}
            )
        for prop in self.parser.get_device_properties_metadata(
                "deviceProperties"
        ).values():
            data_dict[0]["meta"]["properties"].append({"name": prop["name"]})
        return yaml.dump(data_dict)

    def build_yaml_from_file(self, file_loc):
        """Builds YAML from a Tango specification file

        Parameters
        ----------
        file_loc : str
            The path to the specification file

        Returns
        -------
        str
            A YAML representation of the specification file
        """
        file_path = Path(file_loc)
        assert file_path.is_file(), "{} is not a file".format(file_loc)
        self.parser.parse(file_loc)
        return self._build_yaml()

    def build_yaml_from_device(self, device_name):
        """Interrogates a running Tango device and builds the YAML from its attributes,
           properties and commands.

        Parameters
        ----------
        device_name : str
            Tango device name in the domain/family/member format
        """
        self.parser.parse(device_name)
        return self._build_yaml()
