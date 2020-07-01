#########################################################################################
# Copyright 2020 SKA South Africa (http://ska.ac.za/)                                   #
#                                                                                       #
# BSD license - see LICENSE.txt for details                                             #
#########################################################################################
"""Entrypoint for the script to parse a Tango file representation or a running device into
   YAML"""
from __future__ import absolute_import, division, print_function

import argparse

from tango_simlib.tango_yaml_tools.base import TangoToYAML
from tango_simlib.utilities.fandango_json_parser import FandangoExportDeviceParser as FP
from tango_simlib.utilities.sim_xmi_parser import XmiParser
from tango_simlib.utilities.tango_device_parser import TangoDeviceParser
from tango_simlib.utilities.validate_device import (
    validate_device_from_url,
    validate_device_from_path,
)


def _validate_device(args):
    """Validate the conformance of a Tango device against a YAML specification

    Parameters
    ----------
    args : argparse.Namespace
        The parsed arguments

    Returns
    -------
    str
        A string indicating whether there are differences or not
    """
    result = ""
    if args.url:
        result = validate_device_from_url(args.tango_device_name, args.url)
    else:
        result = validate_device_from_path(args.tango_device_name, args.path)

    if not result:
        source = args.path if args.path else args.url
        result = "No differences between device {} and specification {}".format(
            args.tango_device, source
        )
    return result


def _build_yaml(args):
    """Build the YAML depending on the file type or device name

    Parameters
    ----------
    args : argparse.Namespace
        The parsed arguments

    Returns
    -------
    str
        The YAML string if a valid option was chosen, otherwise an empty string
    """
    if "xmi_file" in args:
        return TangoToYAML(XmiParser).build_yaml_from_file(args.xmi_file.name)
    if "fandango_file" in args:
        return TangoToYAML(FP).build_yaml_from_file(args.fandango_file.name)
    if "tango_device_name" in args:
        return TangoToYAML(TangoDeviceParser).build_yaml_from_device(
            args.tango_device_name
        )
    return ""


def main():
    """Entrypoint for the script
    """
    parser = argparse.ArgumentParser(
        prog="tango_yaml",
        description=(
            "This program translates various file formats that "
            "describe Tango devices to YAML. Or validates the conformance of a device "
            "against a specification."
        ),
    )
    subparsers = parser.add_subparsers(help="sub command help")

    xmi_parser = subparsers.add_parser("xmi", help="Build YAML from a XMI file")
    xmi_parser.add_argument(
        "xmi_file", type=argparse.FileType("r"), help="Path to the XMI file"
    )

    fandango_parser = subparsers.add_parser(
        "fandango", help="Build YAML from a fandango file"
    )
    fandango_parser.add_argument(
        "fandango_file", type=argparse.FileType("r"), help="Path to the fandango file"
    )

    tango_device_parser = subparsers.add_parser(
        "tango_device", help="Build YAML from a running Tango device"
    )
    tango_device_parser.add_argument(
        "tango_device_name",
        type=str,
        help=(
            "Tango device name in the format domain/family/member. "
            "TANGO_HOST env variable has to be set"
        ),
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Check conformance of a Tango device against a specification in YAML format",
    )
    validate_parser.add_argument(
        "tango_device_name",
        type=str,
        help=(
            "Tango device name in the format domain/family/member. "
            "TANGO_HOST env variable has to be set"
        ),
    )
    source_group = validate_parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "-url", type=str, help="The URL to a YAML specification file",
    )
    source_group.add_argument(
        "-path", type=str, help="The file path to a YAML specification file",
    )

    args = parser.parse_args()

    result = ""
    if "url" in args:
        result = _validate_device(args)
    else:
        result = _build_yaml(args)
    if result:
        print(result)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
