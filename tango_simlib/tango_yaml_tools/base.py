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

        command_values = self.parser.get_device_command_metadata().values()
        command_values = sorted(command_values, key=lambda x: x["name"])
        for command in command_values:
            command_keys = sorted(command.keys())
            command_keys.insert(0, command_keys.pop(command_keys.index("name")))
            command_data = {}
            for key in command_keys:
                if key in ["dtype_in", "dtype_out"]:
                    command_data[key] = command[key].name
                else:
                    command_data[key] = command[key]
            data_dict[0]["meta"]["commands"].append(command_data)

        attr_values = self.parser.get_device_attribute_metadata().values()
        attr_values = sorted(attr_values, key=lambda x: x["name"])
        for attr in attr_values:
            attr_keys = sorted(attr.keys())
            attr_keys.insert(0, attr_keys.pop(attr_keys.index("name")))
            attr_data = {}
            for key in attr_keys:
                if key in ["data_format", "data_type", "disp_level"]:
                    attr_data[key] = attr[key].name
                elif key in [
                        "name",
                        "delta_val",
                        "period",
                        "display_unit",
                        "standard_unit",
                        "unit",
                        "max_dim_y",
                        "max_dim_x",
                        "label",
                        "max_value",
                        "min_alarm",
                        "max_warning",
                        "description",
                        "format",
                        "delta_t",
                        "max_alarm",
                        "min_value",
                        "inherited",
                        "min_warning",
                        "writable",
                        "writable_attr_name",
                ]:
                    attr_data[key] = attr[key]
            data_dict[0]["meta"]["attributes"].append(attr_data)

        prop_values = self.parser.get_device_properties_metadata(
            "deviceProperties"
        ).values()
        prop_values = sorted(prop_values, key=lambda x: x["name"])
        for prop in prop_values:
            data_dict[0]["meta"]["properties"].append({"name": prop["name"]})
        return yaml.dump(data_dict, sort_keys=False)

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
            Tango device name in the domain/family/member format or the
            FQDN tango://<TANGO_HOST>:<TANGO_PORT>/domain/family/member
        """
        self.parser.parse(device_name)
        return self._build_yaml()
