"""Various tests for the validation logic"""
from __future__ import absolute_import, division, print_function

import yaml

from tango_simlib.utilities.validate_device import compare_data, MINIMAL_SPEC_FORMAT

YAML_A = """
class: DishMaster_A
meta:
  attributes:
  - data_format: SCALAR_A
    data_type: DevLong_A
    description: Current  logging level to Central logging target
    disp_level: OPERATOR
    display_unit: No display unit
    format: '%d'
    label: loggingLevelCentral
    max_alarm: Not specified
    max_dim_x: 1
    max_dim_y: 0
    max_value: Not specified
    min_alarm: Not specified
    min_value: Not specified
    name: loggingLevelCentral
    standard_unit: No standard unit
    unit: ''
    writable: READ_WRITE
    writable_attr_name: logginglevelcentral
  - data_format: SCALAR
    data_type: DevLong
    description: Current  logging level to Element logging target
    disp_level: OPERATOR
    display_unit: No display unit
    format: '%d'
    label: loggingLevelElement
    max_alarm: Not specified
    max_dim_x: 1
    max_dim_y: 0
    max_value: Not specified
    min_alarm: Not specified
    min_value: Not specified
    name: loggingLevelElement_A
    standard_unit: No standard unit
    unit: ''
    writable: READ_WRITE
    writable_attr_name: logginglevelelement
  - data_format: SCALAR
    data_type: DevLong
    description: Current  logging level to logging target
    disp_level: OPERATOR
    display_unit: No display unit
    format: '%d'
    label: loggingLevel
    max_alarm: Not specified
    max_dim_x: 1
    max_dim_y: 0
    max_value: Not specified
    min_alarm: Not specified
    min_value: Not specified
    name: OtherAttribute
    standard_unit: No standard unit
    unit: ''
    writable: READ_WRITE
    writable_attr_name: logginglevel
  commands:
  - disp_level: OPERATOR_A
    doc_in: ON/OFF_A
    doc_out: Uninitialised
    dtype_in: DevBoolean
    dtype_out: DevVoid
    name: Capture
  - disp_level: EXPERT
    doc_in_A: Uninitialised
    doc_out: Uninitialised
    dtype_in: DevVoid
    dtype_out: DevVoid
    name: ClearOldTasks
  - disp_level: EXPERT
    doc_in: Uninitialised
    doc_out: Uninitialised
    dtype_in: DevVoid
    dtype_out: DevVoid
    name: ClearTaskHistory_A
  - disp_level: EXPERT
    doc_in: Uninitialised
    doc_out: Uninitialised
    dtype_in: DevVoid
    dtype_out: DevVoid
    name: OtherCommand
  properties:
  - name: AdminModeDefault
  - name: AsynchCmdReplyNRetries
  - name: AsynchCmdReplyTimeout
  - name: CentralLoggerEnabledDefault
  - name: ConfigureTaskTimeout
  - name: ControlModeDefault_A
"""

YAML_B = """
class: DishMaster_B
meta:
  attributes:
  - data_format: SCALAR_B
    data_type: DevLong_B
    description: Current  logging level to Central logging target
    disp_level: OPERATOR
    display_unit: No display unit
    format: '%d'
    label: loggingLevelCentral
    max_alarm: Not specified
    max_dim_x: 1
    max_dim_y: 0
    max_value: Not specified
    min_alarm: Not specified
    min_value: Not specified
    name: loggingLevelCentral
    standard_unit: No standard unit
    unit: ''
    writable: READ_WRITE
    writable_attr_name: logginglevelcentral
  - data_format: SCALAR
    data_type: DevLong
    description: Current  logging level to Element logging target
    disp_level: OPERATOR
    display_unit: No display unit
    format: '%d'
    label: loggingLevelElement
    max_alarm: Not specified
    max_dim_x: 1
    max_dim_y: 0
    max_value: Not specified
    min_alarm: Not specified
    min_value: Not specified
    name: loggingLevelElement_B
    standard_unit: No standard unit
    unit: ''
    writable: READ_WRITE
    writable_attr_name: logginglevelelement
  - data_format: SCALAR
    data_type: DevLong
    description: Current  logging level to logging target
    disp_level: OPERATOR
    display_unit: No display unit
    format: '%d'
    label: loggingLevel
    max_alarm: Not specified
    max_dim_x: 1
    max_dim_y: 0
    max_value: Not specified
    min_alarm: Not specified
    min_value: Not specified
    name: OtherAttribute
    standard_unit: No standard unit
    unit: ''
    writable: READ_WRITE
    writable_attr_name: logginglevel
  commands:
  - disp_level: OPERATOR_B
    doc_in: ON/OFF_B
    doc_out: Uninitialised
    dtype_in: DevBoolean
    dtype_out: DevVoid
    name: Capture
  - disp_level: EXPERT
    doc_in: Uninitialised
    doc_out_B: Uninitialised
    dtype_in: DevVoid
    dtype_out: DevVoid
    name: ClearOldTasks
  - disp_level: EXPERT
    doc_in: Uninitialised
    doc_out: Uninitialised
    dtype_in: DevVoid
    dtype_out: DevVoid
    name: ClearTaskHistory_B
  - disp_level: EXPERT
    doc_in: Uninitialised
    doc_out: Uninitialised
    dtype_in: DevVoid
    dtype_out: DevVoid
    name: OtherCommand
  properties:
  - name: AdminModeDefault
  - name: AsynchCmdReplyNRetries
  - name: AsynchCmdReplyTimeout
  - name: CentralLoggerEnabledDefault
  - name: ConfigureTaskTimeout
  - name: ControlModeDefault_B
"""


def test_validate():
    """Test various combinations"""

    # If it's the same then no differences recorded
    assert not compare_data(YAML_A, YAML_A, 1)

    spec_yaml = YAML_A
    dev_yaml = YAML_B
    bi_directional_result = compare_data(spec_yaml, dev_yaml, 1)
    single_direction_result = compare_data(spec_yaml, dev_yaml, 0)
    class_result = (
        "Class differs, specified 'DishMaster_A', but device has 'DishMaster_B'"
    )
    assert class_result in bi_directional_result
    assert class_result in single_direction_result

    command_result = (
        "Command differs, [ClearTaskHistory_A] specified but missing in device"
    )
    assert command_result in bi_directional_result
    assert command_result in single_direction_result

    command_result = (
        "Command differs, [ClearTaskHistory_B] present in device but not specified"
    )
    assert command_result in bi_directional_result
    assert command_result not in single_direction_result

    command_result = (
        "Command [Capture] differs:\n\tdisp_level:"
        "\n\t\tspecification: OPERATOR_A\n\t\tdevice: OPERATOR_B"
    )
    assert command_result in bi_directional_result
    assert command_result in single_direction_result

    # Same in both
    assert "OtherCommand" not in bi_directional_result
    assert "OtherCommand" not in single_direction_result

    attr_result = (
        "Attribute differs, [loggingLevelElement_A] specified but missing in device"
    )
    assert attr_result in bi_directional_result
    assert attr_result in single_direction_result

    attr_result = (
        "Attribute differs, [loggingLevelElement_B] present"
        " in device but not specified"
    )
    assert attr_result in bi_directional_result
    assert attr_result not in single_direction_result

    # Same in both
    assert "OtherAttribute" not in bi_directional_result
    assert "OtherAttribute" not in single_direction_result

    prop_res = "Property [ControlModeDefault_A] differs, specified but missing in device"
    assert prop_res in bi_directional_result
    assert prop_res in single_direction_result

    prop_res = (
        "Property [ControlModeDefault_B] differs, present in device but not specified"
    )
    assert prop_res in bi_directional_result
    assert prop_res not in single_direction_result

    # Same in both
    assert "AdminModeDefault" not in bi_directional_result
    assert "AdminModeDefault" not in single_direction_result

    spec_yaml = YAML_B
    dev_yaml = YAML_A
    bi_directional_result = compare_data(spec_yaml, dev_yaml, 1)

    assert (
        "Class differs, specified 'DishMaster_B', but device has 'DishMaster_A'"
        in bi_directional_result
    )
    assert (
        "Command differs, [ClearTaskHistory_B] specified but missing in device"
        in bi_directional_result
    )
    assert (
        "Command differs, [ClearTaskHistory_A] present in device but not specified"
        in bi_directional_result
    )
    assert (
        "Command [Capture] differs:\n\tdisp_level:"
        "\n\t\tspecification: OPERATOR_B\n\t\tdevice: OPERATOR_A"
    ) in bi_directional_result

    # Same in both
    assert "OtherCommand" not in bi_directional_result

    assert (
        "Attribute differs, [loggingLevelElement_B] specified but missing in device"
    ) in bi_directional_result

    assert (
        (
            "Attribute differs, [loggingLevelElement_A] present"
            " in device but not specified"
        )
    ) in bi_directional_result

    assert "OtherAttribute" not in bi_directional_result

    assert (
        ("Property [ControlModeDefault_B] differs, specified but missing in device")
    ) in bi_directional_result

    assert (
        (
            "Property [ControlModeDefault_A] differs, present in device but "
            "not specified"
        )
    ) in bi_directional_result

    # Same in both
    assert "AdminModeDefault" not in bi_directional_result


def test_empty_validation():
    """Check that a empty spec is still works"""
    single_direction_result = compare_data(MINIMAL_SPEC_FORMAT, YAML_A, 0)
    assert not single_direction_result

    bi_direction_result = compare_data(MINIMAL_SPEC_FORMAT, YAML_A, 1)
    command_res = (
        "Command differs, [Capture,ClearOldTasks,ClearTaskHistory_A,OtherCommand]"
        " present in device but not specified"
    )
    assert command_res in bi_direction_result

    attr_res = (
        "Attribute differs, [OtherAttribute,loggingLevelCentral,loggingLevelElement_A]"
        " present in device but not specified"
    )
    assert attr_res in bi_direction_result

    prop_res = (
        "Property [AdminModeDefault,AsynchCmdReplyNRetries,AsynchCmdReplyTimeout,"
        "CentralLoggerEnabledDefault,ConfigureTaskTimeout,ControlModeDefault_A] differs,"
        " present in device but not specified"
    )
    assert prop_res in bi_direction_result


def test_invalid_spec():
    """Make sure that the minimal spec format is checked"""
    try:
        compare_data("class:", YAML_A, 0)
    except AssertionError as err:
        assert "Minimal structure not adhered to" in str(err)
    else:
        assert 0, "AssertionError not raised for invalid spec format"

    for key in ["attributes", "properties", "commands"]:
        try:
            minimal_format = yaml.load(MINIMAL_SPEC_FORMAT, Loader=yaml.FullLoader)
            minimal_format["meta"][key] = [{"A": "B"}]
            compare_data(yaml.dump(minimal_format), YAML_A, 0)
        except AssertionError as err:
            assert str(err) == "`name` field is required for all {}".format(key)
        else:
            assert 0, "AssertionError not raised for invalid spec format"
