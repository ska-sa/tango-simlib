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


def validate_device_from_url(tango_device_name, url_to_yaml_file, bidirectional):
    """Retrieves the YAML from the URL and checks conformance against the Tango device.

    Parameters
    ----------
    url_to_yaml_file : str
        The URL to the specification file

    tango_device_name : str
        Tango device name in the domain/family/member format or the
        FQDN tango://<TANGO_HOST>:<TANGO_PORT>/domain/family/member

    bidirectional: bool
        Whether to include details on the device that is not in the specification

    Returns
    -------
    str
        The validation result
    """
    response = requests.get(url_to_yaml_file, allow_redirects=True)
    response.raise_for_status()
    return compare_data(
        response.text, get_device_specification(tango_device_name), bidirectional
    )


def validate_device_from_path(tango_device_name, path_to_yaml_file, bidirectional):
    """Retrieves the YAML from the file and checks conformance against the Tango device.

    Parameters
    ----------
    path_to_yaml_file : str
        The path to the specification file

    tango_device_name : str
        Tango device name in the domain/family/member format or the
        FQDN tango://<TANGO_HOST>:<TANGO_PORT>/domain/family/member

    bidirectional: bool
        Whether to include details on the device that is not in the specification

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
    return compare_data(
        file_data, get_device_specification(tango_device_name), bidirectional
    )


def get_device_specification(tango_device_name):
    """Translate a device to YAML specification

    Parameters
    ----------
    tango_device_name : str
        Tango device name in the domain/family/member format or the
        FQDN tango://<TANGO_HOST>:<TANGO_PORT>/domain/family/member

    Returns
    -------
    str
        The device specification in YAML format
    """
    parser = TangoToYAML(TangoDeviceParser)
    return parser.build_yaml_from_device(tango_device_name)


def compare_data(specification_yaml, tango_device_yaml, bidirectional):
    """Compare 2 sets of YAML built from the specification and from the device

    Parameters
    ----------
    specification_yaml : str
        The specification in YAML format

    tango_device_yaml : str
        The Tango device in YAML format

    bidirectional: bool
        Whether to include details on the device that is not in the specification

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

    # Class
    if tango_device_data["class"] != specification_data["class"]:
        issues.append(
            "\nClass differs, specified '{}', but device has '{}'".format(
                specification_data["class"], tango_device_data["class"]
            )
        )

    # Commands
    issues.extend(
        check_list_dict_differences(
            specification_data["meta"]["commands"],
            tango_device_data["meta"]["commands"],
            "Command",
            bidirectional,
        )
    )

    # Attributes
    issues.extend(
        check_list_dict_differences(
            specification_data["meta"]["attributes"],
            tango_device_data["meta"]["attributes"],
            "Attribute",
            bidirectional,
        )
    )

    # Properties
    issues.extend(
        check_property_differences(
            specification_data["meta"]["properties"],
            tango_device_data["meta"]["properties"],
            bidirectional,
        )
    )

    return "\n".join(issues)


def check_list_dict_differences(spec_data, dev_data, type_str, bidirectional):
    """Compare Commands and Attributes in the parsed YAML

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
        List of dictionaries with device data
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

    bidirectional: bool
        Whether to include details on the device that is not in the specification

    Returns
    -------
    list
        A list of strings describing the issues, empty list for no issues
    """
    issues = []
    spec_data = sorted(spec_data, key=lambda i: i["name"])
    dev_data = sorted(dev_data, key=lambda i: i["name"])

    # Check that the command/attribute names match
    spec_data_names = {i["name"] for i in spec_data}
    dev_data_names = {i["name"] for i in dev_data}
    if spec_data_names != dev_data_names:
        diff = spec_data_names.difference(dev_data_names)
        issues.append(
            "{} differs, [{}] specified but missing in device".format(
                type_str, ",".join(diff)
            )
        )

        if bidirectional:
            diff = dev_data_names.difference(spec_data_names)
            issues.append(
                "{} differs, [{}] present in device but not specified".format(
                    type_str, ",".join(diff)
                )
            )

    # Check that the commands/attributes (by name) that are in both the spec and device
    # are the same
    mutual_names = spec_data_names.intersection(dev_data_names)
    mutual_spec_data = filter(lambda x: x["name"] in mutual_names, spec_data)
    mutual_dev_data = filter(lambda x: x["name"] in mutual_names, dev_data)
    for spec, dev in zip(mutual_spec_data, mutual_dev_data):
        issues.extend(check_single_dict_differences(spec, dev, type_str, bidirectional))

    return issues


def check_single_dict_differences(spec, dev, type_str, bidirectional):
    """Compare a single attribute/property

    Parameters
    ----------
    spec : dict
        A single Attribute/Command dictionary form the specficication
        E.g {'disp_level': 'OPERATOR',
             'doc_in': 'ON/OFF',
             'doc_out': 'Uninitialised',
             'dtype_in': 'DevBoolean',
             'dtype_out': 'DevVoid',
             'name': 'Capture'}

    dev : dict
        A single Attribute/Command dictionary form the device
        E.g {'disp_level': 'OPERATOR',
             'doc_in': 'ON/OFF',
             'doc_out': 'Uninitialised',
             'dtype_in': 'DevBoolean',
             'dtype_out': 'DevVoid',
             'name': 'Capture'}

    type_str : str
        Either "Command" or "Attribute"

    bidirectional: bool
        Whether to include details on the device that is not in the specification

    Returns
    -------
    list
        A list of strings describing the issues, empty list for no issues
    """
    assert spec["name"] == dev["name"]
    issues = []

    if spec != dev:
        spec_keys = set(spec.keys())
        dev_keys = set(dev.keys())

        keys_not_in_spec = spec_keys.difference(dev_keys)
        keys_not_in_dev = dev_keys.difference(spec_keys)
        mutual_keys = spec_keys.intersection(dev_keys)

        if keys_not_in_spec:
            issues.append(
                "{} [{}] differs, specification has keys [{}] but it's "
                "not in device".format(type_str, spec["name"], ",".join(keys_not_in_spec))
            )

        if keys_not_in_dev and bidirectional:
            issues.append(
                "{} [{}] differs, device has keys [{}] but it's "
                "not in the specification".format(
                    type_str, spec["name"], ",".join(keys_not_in_dev)
                )
            )

        for key in mutual_keys:
            if dev[key] != spec[key]:
                issues.append("{} [{}] differs:".format(type_str, spec["name"]))
                issues.append(
                    "\t{}:\n\t\tspecification: {}\n\t\tdevice: {}".format(
                        key, spec[key], dev[key]
                    )
                )

    return issues


def check_property_differences(spec_properties, dev_properties, bidirectional):
    """Compare properties in the parsed YAML

    Parameters
    ----------
    spec_data : list
        List of dictionaries with specification data properties
        E.g [{'name': 'AdminModeDefault'},
             {'name': 'AsynchCmdReplyNRetries'},
             {'name': 'AsynchCmdReplyTimeout'},
             {'name': 'CentralLoggerEnabledDefault'},
             {'name': 'ConfigureTaskTimeout'},
             {'name': 'ControlModeDefault_B'}]

    dev_data : list
        List of dictionaries with device data properties
        E.g [{'name': 'AdminModeDefault'},
             {'name': 'AsynchCmdReplyNRetries'},
             {'name': 'AsynchCmdReplyTimeout'},
             {'name': 'CentralLoggerEnabledDefault'},
             {'name': 'ConfigureTaskTimeout'},
             {'name': 'ControlModeDefault_B'}]

    bidirectional: bool
        Whether to include details on the device that is not in the specification

    Returns
    -------
    list
        A list of strings describing the issues, empty list for no issues
    """
    issues = []

    spec_props = {i["name"] for i in spec_properties}
    dev_props = {i["name"] for i in dev_properties}

    if spec_props != dev_props:
        diff = spec_props.difference(dev_props)
        issues.append(
            "Property [{}] differs, specified but missing in device".format(
                ",".join(diff)
            )
        )

        if bidirectional:
            diff = dev_props.difference(spec_props)
            issues.append(
                "Property [{}] differs, present in device but not specified".format(
                    ",".join(diff)
                )
            )

    return issues
