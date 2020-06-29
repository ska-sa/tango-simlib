"""Various tests for the validation logic"""
from __future__ import absolute_import, division, print_function

from tango_simlib.utilities.validate_device import validate_device

YAML_A = """
{
  "class": "DishMaster_A",
  "meta":
    {
      "attributes":
        [
          {
            "data_format": "SCALAR_A",
            "data_type": "DevLong_A",
            "description": "Current  logging level to Central logging target for this device",
            "disp_level": "OPERATOR",
            "display_unit": "No display unit",
            "format": "%d",
            "label": "loggingLevelCentral",
            "max_alarm": "Not specified",
            "max_dim_x": 1,
            "max_dim_y": 0,
            "max_value": "Not specified",
            "min_alarm": "Not specified",
            "min_value": "Not specified",
            "name": "loggingLevelCentral",
            "standard_unit": "No standard unit",
            "unit": "",
            "writable": "READ_WRITE",
            "writable_attr_name": "logginglevelcentral",
          },
          {
            "data_format": "SCALAR",
            "data_type": "DevLong",
            "description": "Current  logging level to Element logging target for this device",
            "disp_level": "OPERATOR",
            "display_unit": "No display unit",
            "format": "%d",
            "label": "loggingLevelElement",
            "max_alarm": "Not specified",
            "max_dim_x": 1,
            "max_dim_y": 0,
            "max_value": "Not specified",
            "min_alarm": "Not specified",
            "min_value": "Not specified",
            "name": "loggingLevelElement_A",
            "standard_unit": "No standard unit",
            "unit": "",
            "writable": "READ_WRITE",
            "writable_attr_name": "logginglevelelement",
          },
        ],
      "commands":
        [
          {
            "disp_level": "OPERATOR_A",
            "doc_in": "ON/OFF_A",
            "doc_out": "Uninitialised",
            "dtype_in": "DevBoolean",
            "dtype_out": "DevVoid",
            "name": "Capture",
          },
          {
            "disp_level": "EXPERT",
            "doc_in": "Uninitialised",
            "doc_out": "Uninitialised",
            "dtype_in": "DevVoid",
            "dtype_out": "DevVoid",
            "name": "ClearOldTasks",
          },
          {
            "disp_level": "EXPERT",
            "doc_in": "Uninitialised",
            "doc_out": "Uninitialised",
            "dtype_in": "DevVoid",
            "dtype_out": "DevVoid",
            "name": "ClearTaskHistory_A",
          },
        ],
      "properties":
        [
          { "name": "AdminModeDefault" },
          { "name": "AsynchCmdReplyNRetries" },
          { "name": "AsynchCmdReplyTimeout" },
          { "name": "CentralLoggerEnabledDefault" },
          { "name": "ConfigureTaskTimeout" },
          { "name": "ControlModeDefault_A" },
        ],
    },
}
"""

YAML_B = """
{
  "class": "DishMaster_B",
  "meta":
    {
      "attributes":
        [
          {
            "data_format": "SCALAR_B",
            "data_type": "DevLong_B",
            "description": "Current  logging level to Central logging target for this device",
            "disp_level": "OPERATOR",
            "display_unit": "No display unit",
            "format": "%d",
            "label": "loggingLevelCentral",
            "max_alarm": "Not specified",
            "max_dim_x": 1,
            "max_dim_y": 0,
            "max_value": "Not specified",
            "min_alarm": "Not specified",
            "min_value": "Not specified",
            "name": "loggingLevelCentral",
            "standard_unit": "No standard unit",
            "unit": "",
            "writable": "READ_WRITE",
            "writable_attr_name": "logginglevelcentral",
          },
          {
            "data_format": "SCALAR",
            "data_type": "DevLong",
            "description": "Current  logging level to Element logging target for this device",
            "disp_level": "OPERATOR",
            "display_unit": "No display unit",
            "format": "%d",
            "label": "loggingLevelElement",
            "max_alarm": "Not specified",
            "max_dim_x": 1,
            "max_dim_y": 0,
            "max_value": "Not specified",
            "min_alarm": "Not specified",
            "min_value": "Not specified",
            "name": "loggingLevelElement_B",
            "standard_unit": "No standard unit",
            "unit": "",
            "writable": "READ_WRITE",
            "writable_attr_name": "logginglevelelement",
          },
        ],
      "commands":
        [
          {
            "disp_level": "OPERATOR_B",
            "doc_in": "ON/OFF_B",
            "doc_out": "Uninitialised",
            "dtype_in": "DevBoolean",
            "dtype_out": "DevVoid",
            "name": "Capture",
          },
          {
            "disp_level": "EXPERT",
            "doc_in": "Uninitialised",
            "doc_out": "Uninitialised",
            "dtype_in": "DevVoid",
            "dtype_out": "DevVoid",
            "name": "ClearOldTasks",
          },
          {
            "disp_level": "EXPERT",
            "doc_in": "Uninitialised",
            "doc_out": "Uninitialised",
            "dtype_in": "DevVoid",
            "dtype_out": "DevVoid",
            "name": "ClearTaskHistory_B",
          },
        ],
      "properties":
        [
          { "name": "AdminModeDefault" },
          { "name": "AsynchCmdReplyNRetries" },
          { "name": "AsynchCmdReplyTimeout" },
          { "name": "CentralLoggerEnabledDefault" },
          { "name": "ConfigureTaskTimeout" },
          { "name": "ControlModeDefault_B" },
        ],
    },
}
"""


def test_validate():
    """Test various combinations"""

    # If it's the same then no differences recorded
    assert not validate_device(YAML_A, YAML_A)

    spec_yaml = YAML_A
    dev_yaml = YAML_B
    result = validate_device(spec_yaml, dev_yaml)
    assert (
        "Class discrepancy, specified 'DishMaster_A', but device has 'DishMaster_B'"
        in result
    )
    assert (
        "Command discrepancy, {'ClearTaskHistory_A'} specified but missing in device"
        in result
    )
    assert (
        "Command discrepancy, {'ClearTaskHistory_B'} present in device but not specified"
        in result
    )
    assert (
        "Command details differ for Capture:\n\tdisp_level:"
        "\n\t\tspecification: OPERATOR_A, device: OPERATOR_B"
    ) in result

    assert (
        "Attribute discrepancy, {'loggingLevelElement_A'} specified but missing in device"
    ) in result

    assert (
        ("Attribute discrepancy, {'loggingLevelElement_B'} present"
         " in device but not specified")
    ) in result


    spec_yaml = YAML_B
    dev_yaml = YAML_A
    result = validate_device(spec_yaml, dev_yaml)
    assert (
        "Class discrepancy, specified 'DishMaster_B', but device has 'DishMaster_A'"
        in result
    )
    assert (
        "Command discrepancy, {'ClearTaskHistory_B'} specified but missing in device"
        in result
    )
    assert (
        "Command discrepancy, {'ClearTaskHistory_A'} present in device but not specified"
        in result
    )
    assert (
        "Command details differ for Capture:\n\tdisp_level:"
        "\n\t\tspecification: OPERATOR_B, device: OPERATOR_A"
    ) in result

    assert (
        "Attribute discrepancy, {'loggingLevelElement_B'} specified but missing in device"
    ) in result

    assert (
        ("Attribute discrepancy, {'loggingLevelElement_A'} present"
         " in device but not specified")
    ) in result

    print(result)
