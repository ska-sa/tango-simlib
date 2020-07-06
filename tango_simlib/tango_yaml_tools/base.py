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
            command_data = {
                "name": command["name"],
                "dtype_in": command["dtype_in"].name,
                "dtype_out": command["dtype_out"].name,
            }
            for key in ["doc_out", "doc_in", "inherited", "disp_level"]:
                if key in command:
                    command_data[key] = command[key]
            data_dict[0]["meta"]["commands"].append(command_data)

        for attr in self.parser.get_device_attribute_metadata().values():
            attr_data = {"name": attr["name"]}
            if "data_type" in attr:
                attr_data["data_type"] = attr["data_type"].name
            if "data_format" in attr:
                attr_data["data_format"] = attr["data_format"].name
            if "disp_level" in attr:
                attr_data["disp_level"] = attr["disp_level"].name
            # pylint insists on this spacing
            for key in [
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
                if key in attr:
                    attr_data[key] = attr[key]
            data_dict[0]["meta"]["attributes"].append(attr_data)

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
            Tango device name in the domain/family/member format or the
            FQDN tango://<TANGO_HOST>:<TANGO_PORT>/domain/family/member
        """
        self.parser.parse(device_name)
        return self._build_yaml()
