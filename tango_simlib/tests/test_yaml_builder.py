#########################################################################################
# Copyright 2020 SKA South Africa (http://ska.ac.za/)                                   #
#                                                                                       #
# BSD license - see LICENSE.txt for details                                             #
#########################################################################################
"""Tests for YAML builder"""
try:
    from unittest import mock
except ImportError:
    import mock
from argparse import Namespace
from pathlib import Path

import yaml
import tango

from tango_simlib.tango_yaml_tools.main import build_yaml

CONF_FILE_PATH = Path.joinpath(Path(__file__).parent, "config_files")


def validate_basic_structure(yaml_dict):
    """Do a basic check of the structure
    """
    assert len(yaml_dict) == 1
    assert "meta" in yaml_dict[0]
    assert "class" in yaml_dict[0]
    assert "properties" in yaml_dict[0]["meta"]
    assert "attributes" in yaml_dict[0]["meta"]


def test_file_builders_xmi():
    """test XMI parsing with some spot checks"""

    xmi_args = Namespace(
        xmi_file=Namespace(
            name=str(Path.joinpath(CONF_FILE_PATH, "DishElementMaster.xmi"))
        )
    )
    xmi_yaml = build_yaml(xmi_args)
    parsed_yaml = yaml.load(xmi_yaml, Loader=yaml.FullLoader)
    validate_basic_structure(parsed_yaml)

    assert parsed_yaml[0]["class"] == "DishElementMaster"

    attrs = [i["name"] for i in parsed_yaml[0]["meta"]["attributes"]]
    assert len(attrs) == 27
    assert "desiredPointing" in attrs
    assert "band4CapabilityState" in attrs

    # Order differs between Python 2 and 3
    for attr in parsed_yaml[0]["meta"]["attributes"]:
        if attr["name"] == "desiredPointing":
            assert attr["data_type"] == "DevDouble"
        if attr["name"] == "band4CapabilityState":
            assert attr["data_type"] == "DevEnum"

    comms = [i["name"] for i in parsed_yaml[0]["meta"]["commands"]]
    assert len(comms) == 22
    assert "Status" in comms
    assert "SetOperateMode" in comms
    for comm in parsed_yaml[0]["meta"]["commands"]:
        if comm["name"] == "Status":
            assert comm["dtype_out"] == "DevString"
            assert comm["dtype_in"] == "DevVoid"
        if comm["name"] == "SetOperateMode":
            assert comm["dtype_out"] == "DevVoid"
            assert comm["dtype_in"] == "DevVoid"

    assert {"name": "SkaLevel"} in parsed_yaml[0]["meta"]["properties"]


def test_file_builders_fandango():
    """test fandango parsing with some spot checks"""

    fgo_args = Namespace(
        fandango_file=Namespace(name=str(Path.joinpath(CONF_FILE_PATH, "database2.fgo")))
    )
    fgo_yaml = build_yaml(fgo_args)
    parsed_yaml = yaml.load(fgo_yaml, Loader=yaml.FullLoader)
    validate_basic_structure(parsed_yaml)

    assert parsed_yaml[0]["class"] == "DataBase"

    attrs = [i["name"] for i in parsed_yaml[0]["meta"]["attributes"]]
    assert len(attrs) == 9
    assert "Timing_info" in attrs
    assert "Timing_minimum" in attrs
    for attr in parsed_yaml[0]["meta"]["attributes"]:
        if attr["name"] == "Timing_info":
            assert attr["data_type"] == "DevString"
        if attr["name"] == "Timing_minimum":
            assert attr["data_type"] == "DevDouble"

    comms = [i["name"] for i in parsed_yaml[0]["meta"]["commands"]]
    assert len(comms) == 100
    assert "DbGetDataForServerCache" in comms
    assert "DbGetDeviceAttributeList" in comms
    for comm in parsed_yaml[0]["meta"]["commands"]:
        if comm["name"] == "DbGetDataForServerCache":
            assert comm["dtype_out"] == "DevVarStringArray"
            assert comm["dtype_in"] == "DevVarStringArray"
        if comm["name"] == "DbGetDeviceAttributeList":
            assert comm["dtype_out"] == "DevVarStringArray"
            assert comm["dtype_in"] == "DevVarStringArray"


def test_tango_device_builder():
    """Test a Tango device to YAML by mocking a running Tango device"""
    with mock.patch("tango_simlib.utilities.tango_device_parser.tango") as mocked_tango:
        mocked_device_proxy = mock.Mock()
        mocked_tango.DeviceProxy.return_value = mocked_device_proxy

        mocked_info = mock.Mock()
        mocked_info.dev_class = "DevClass"
        mocked_device_proxy.info.return_value = mocked_info

        mocked_command = mock.Mock()
        mocked_command.cmd_name = "CommandName"
        mocked_command.in_type = tango.CmdArgType.DevVoid
        mocked_command.out_type = tango.CmdArgType.DevVoid

        attr = tango.AttributeInfo()
        attr.name = "AttrName"
        attr.data_format = tango.AttrDataFormat.SCALAR

        mocked_device_proxy.get_command_config.return_value = [mocked_command]
        mocked_device_proxy.attribute_list_query.return_value = [attr]
        mocked_device_proxy.get_property_list.return_value = ["PropA", "PropB"]

        tango_args = Namespace(tango_device_name="a/b/c")
        tango_yaml = build_yaml(tango_args)
        parsed_yaml = yaml.load(tango_yaml, Loader=yaml.FullLoader)

        mocked_tango.DeviceProxy.assert_called_once_with("a/b/c")
        mocked_device_proxy.get_command_config.assert_called()
        mocked_device_proxy.attribute_list_query.assert_called()
        mocked_device_proxy.get_property_list.assert_called()
        assert parsed_yaml[0]["meta"]["attributes"] == [
            {"name": "AttrName", "data_type": "SCALAR"}
        ]
        assert parsed_yaml[0]["meta"]["commands"] == [
            {"dtype_out": "DevVoid", "name": "CommandName", "dtype_in": "DevVoid"}
        ]
        assert parsed_yaml[0]["meta"]["properties"] == [
            {"name": "PropA"},
            {"name": "PropB"},
        ]
