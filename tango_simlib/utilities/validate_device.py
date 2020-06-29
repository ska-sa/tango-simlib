#########################################################################################
# Copyright 2020 SKA South Africa (http://ska.ac.za/)                                   #
#                                                                                       #
# BSD license - see LICENSE.txt for details                                             #
#########################################################################################
"""This module validates the conformance of a Tango device against a specification"""
from pathlib import Path

import requests

import yaml

from tango_simlib.utilities.tango_device_parser import TangoDeviceParser
from tango_simlib.tango_yaml_tools.base import TangoToYAML


def validate_device_from_url(tango_device_name, url_to_yaml_file):
    """Retrieves the YAML from the URL and checks conformance against the Tango device.

    Parameters
    ----------
    url_to_yaml_file : str
        The URL to the specification file

    tango_device_name : str
        Tango device name in the domain/family/member format

    Returns
    -------
    str
        The validation result
    """
    response = requests.get(url_to_yaml_file, allow_redirects=True)
    response.raise_for_status()
    return validate_device(
        yaml.load(response.content), get_device_specification(tango_device_name)
    )


def validate_device_from_path(tango_device_name, path_to_yaml_file):
    """Retrieves the YAML from the file and checks conformance against the Tango device.

    Parameters
    ----------
    path_to_yaml_file : str
        The path to the specification file

    tango_device_name : str
        Tango device name in the domain/family/member format

    Returns
    -------
    str
        The validation result
    """
    file_path = Path(path_to_yaml_file)
    assert file_path.is_file(), "{} is not a file".format(file_path)
    file_data = ""
    with open(str(file_path), "r") as data_file:
        file_data = data_file.read()
    return validate_device(
        yaml.load(file_data), get_device_specification(tango_device_name)
    )


def get_device_specification(tango_device_name):
    """Translate a device to YAML specification

    Parameters
    ----------
    tango_device_name : str
        Tango device name in the domain/family/member format

    Returns
    -------
    str
        The device specification in YAML format
    """
    parser = TangoToYAML(TangoDeviceParser)
    return parser.build_yaml_from_device(tango_device_name)


def validate_device(specification_yaml, tango_device_yaml):
    """Check specification conformance against the Tango device.

    Parameters
    ----------
    specification_yaml : str
        The specification in YAML format

    tango_device_yaml : str
        The Tango device in YAML format

    Returns
    -------
    str
        The validation result
    """
    specification_data = yaml.load(specification_yaml, Loader=yaml.FullLoader)
    tango_device_data = yaml.load(tango_device_yaml, Loader=yaml.FullLoader)
    if isinstance(specification_data, list):
        specification_data = specification_data[0]
    if isinstance(tango_device_data, list):
        tango_device_data = tango_device_data[0]

    issues = []

    if tango_device_data["class"] != specification_data["class"]:
        issues.append(
            "\nClass discrepancy, specified '{}', but device has '{}'".format(
                specification_data["class"], tango_device_data["class"]
            )
        )

    if issues:
        issues.append("\n")
    # Commands
    issues.extend(
        check_data_differences(
            specification_data["meta"]["commands"],
            tango_device_data["meta"]["commands"],
            "Command",
        )
    )

    if issues:
        issues.append("\n")
    # Attributes
    issues.extend(
        check_data_differences(
            specification_data["meta"]["attributes"],
            tango_device_data["meta"]["attributes"],
            "Attribute",
        )
    )

    return "\n".join(issues)


def check_data_differences(spec_data, dev_data, type_str):
    """Compare Commands and Attributes in the YAML specification

    Parameters
    ----------
    spec_data : list
        List of dictionaries with specification data
        E.g [
                {'disp_level': 'OPERATOR',
                 'doc_in': 'ON/OFF',
                 'doc_out': 'Uninitialised',
                 'dtype_in': 'DevBoolean',
                 'dtype_out': 'DevVoid',
                 'name': 'Capture'},
                 ...
            ]

    dev_data : list
        List of dictionaries with specification data
        E.g [
                {'disp_level': 'OPERATOR',
                 'doc_in': 'ON/OFF',
                 'doc_out': 'Uninitialised',
                 'dtype_in': 'DevBoolean',
                 'dtype_out': 'DevVoid',
                 'name': 'Capture'},
                 ...
            ]

    type_str : str
        Either "Command" or "Attribute"

    Returns
    -------
    list
        A list of strings describing the issues, empty list for no issues
    """
    issues = []
    spec_data = sorted(spec_data, key=lambda i: i["name"])
    dev_data = sorted(dev_data, key=lambda i: i["name"])

    spec_data_names = {i["name"] for i in spec_data}
    dev_data_names = {i["name"] for i in dev_data}

    if spec_data_names != dev_data_names:
        diff = spec_data_names.difference(dev_data_names)
        issues.append(
            "{} discrepancy, [{}] specified but missing in device".format(
                type_str, ",".join(diff)
            )
        )

        diff = dev_data_names.difference(spec_data_names)
        issues.append(
            "{} discrepancy, [{}] present in device but not specified".format(
                type_str, ",".join(diff)
            )
        )

    mutual_command_names = spec_data_names.intersection(dev_data_names)
    mutual_spec_data = filter(lambda x: x["name"] in mutual_command_names, spec_data)
    mutual_dev_data = filter(lambda x: x["name"] in mutual_command_names, dev_data)

    for spec, dev in zip(mutual_spec_data, mutual_dev_data):
        if spec != dev:
            issues.append("{} details differ for {}:".format(type_str, spec["name"]))
            for key in spec.keys():
                if dev[key] != spec[key]:
                    issues.append(
                        "\t{}:\n\t\tspecification: {}, device: {}".format(
                            key, spec[key], dev[key]
                        )
                    )
    return issues
