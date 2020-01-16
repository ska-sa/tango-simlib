#########################################################################################
# Author: cam@ska.ac.za                                                                 #
# Copyright 2018 SKA South Africa (http://ska.ac.za/)                                   #
#                                                                                       #
# BSD license - see LICENSE.txt for details                                             #
#########################################################################################
from __future__ import absolute_import, division, print_function
from future import standard_library

standard_library.install_aliases()  # noqa: E402

import logging
import unittest

import pkg_resources

import tango

from katcp.testutils import start_thread_with_cleanup
from tango.test_context import DeviceTestContext
from tango_simlib import model, tango_sim_generator
from tango_simlib.utilities import helper_module, sim_xmi_parser
from tango_simlib.utilities.testutils import ClassCleanupUnittestMixin, cleanup_tempfile

LOGGER = logging.getLogger(__name__)

TANGO_CMD_PARAMS_NAME_MAP = {
    "name": "cmd_name",
    "doc_in": "in_type_desc",
    "dtype_in": "in_type",
    "doc_out": "out_type_desc",
    "dtype_out": "out_type",
    "inherited": "inherited",
}

# These expected values are not yet complete, see comment in sim_xmi_parser.py
# about currently unhandled attribute and command parameters.
# Must be updated when they are implemented.
# ['enum_labels', 'disp_level']

default_pogo_commands = ["State", "Status"]  # TODO(KM 31-10-2016): Might need to move
# this list to the testutils module as it
# seems to be used in many tests.

expected_mandatory_attr_parameters = frozenset(
    [
        "max_dim_x",
        "max_dim_y",
        "data_format",
        "period",
        "data_type",
        "writable",
        "name",
        "description",
        "delta_val",
        "max_alarm",
        "max_value",
        "min_value",
        "standard_unit",
        "min_alarm",
        "max_warning",
        "unit",
        "display_unit",
        "format",
        "delta_t",
        "label",
        "min_warning",
        "inherited",
    ]
)

expected_mandatory_cmd_parameters = frozenset(
    ["name", "doc_in", "dtype_in", "doc_out", "dtype_out", "inherited"]
)

expected_mandatory_device_property_parameters = frozenset(
    ["type", "mandatory", "description", "name", "inherited"]
)

expected_mandatory_default_cmds_info = [
    {
        "name": "State",
        "arginDescription": "none",
        "arginType": tango._tango.CmdArgType.DevVoid,
        "argoutDescription": "Device state",
        "argoutType": tango.utils.DevState,
        "description": "This command gets the device state (stored in its "
        "device_state data member) and returns it to the caller.",
        "displayLevel": "OPERATOR",
        "polledPeriod": "0",
        "execMethod": "dev_state",
        "inherited": "true",
    },
    {
        "arginDescription": "none",
        "arginType": tango._tango.CmdArgType.DevVoid,
        "argoutDescription": "Device status",
        "argoutType": tango._tango.CmdArgType.DevString,
        "description": "This command gets the device status"
        "(stored in its device_status data member) and returns it to the caller.",
        "displayLevel": "OPERATOR",
        "execMethod": "dev_status",
        "name": "Status",
        "polledPeriod": "0",
        "inherited": "true",
    },
]

# The desired information for the atttribute pressure when the Weather.xmi file is
# parsed by the XmiParser.
expected_pressure_attr_info = {
    "name": "pressure",
    "data_type": tango.CmdArgType.DevDouble,
    "period": "1000",
    "writable": "READ",
    # The description in the XMI file has unicode quote characters around the word
    # 'quoted', each must be replaced by a question mark
    "description": "Barometric pressure in central telescope area (unicode: ?quoted?).",
    "label": "Barometric pressure",
    "unit": "mbar",
    "standard_unit": "",
    "display_unit": "",
    "format": "",
    "max_value": "1100",
    "min_value": "500",
    "max_alarm": "1000",
    "min_alarm": "",
    "max_warning": "900",
    "min_warning": "",
    "delta_t": "",
    "delta_val": "",
    "data_format": tango.AttrDataFormat.SCALAR,
    "max_dim_y": 0,
    "max_dim_x": 1,
    "abs_change": "0.5",
    "rel_change": "10",
    "event_period": "1000",
    "archive_abs_change": "0.5",
    "archive_period": "1000",
    "archive_rel_change": "10",
    "inherited": "false",
}


# The desired information for the DevEnum data type adminMode atttribute when
# DishElementMaster file is parsed by the XmiParser.
expected_admin_mode_devenum_attr_info = {
    "abs_change": "1",
    "archive_abs_change": "1",
    "archive_period": "",
    "archive_rel_change": "",
    "data_type": tango.CmdArgType.DevEnum,
    "delta_t": "",
    "delta_val": "",
    "description": (
        "Report the current admin mode of the DSH Element. "
        "Factory defaut is MAINTENANCE."
    ),
    "data_format": tango.AttrDataFormat.SCALAR,
    "display_unit": "",
    "enum_labels": ["ONLINE", "OFFLINE", "MAINTENANCE", "NOT-FITTED", "RESERVE"],
    "event_period": "",
    "format": "%s",
    "label": "Admin Mode",
    "max_alarm": "",
    "max_dim_x": 1,
    "max_dim_y": 0,
    "max_value": "",
    "max_warning": "",
    "min_alarm": "",
    "min_value": "",
    "min_warning": "",
    "name": "adminMode",
    "period": "0",
    "rel_change": "",
    "standard_unit": "",
    "unit": "",
    "writable": tango.AttrWriteType.READ_WRITE,
    "inherited": "false",
}


expected_achieved_pointing_spectrum_attr_info = {
    "abs_change": "",
    "data_format": tango._tango.AttrDataFormat.SPECTRUM,
    "data_type": tango._tango.CmdArgType.DevFloat,
    "delta_t": "",
    "delta_val": "",
    "description": (
        "The achieved pointing of the DSH Element. "
        "[timestamp] Milliseconds since UNIX epoch, "
        "UTC ms [Azimuth] degree [Elevation] degree"
    ),
    "display_unit": "",
    "event_period": "1000",
    "format": "%6.2f",
    "label": "Achieved pointing",
    "max_alarm": "",
    "max_dim_x": 3,
    "max_dim_y": 0,
    "max_value": "",
    "max_warning": "",
    "min_alarm": "",
    "min_value": "",
    "min_warning": "",
    "name": "achievedPointing",
    "period": "0",
    "rel_change": "",
    "standard_unit": "",
    "unit": "[ms, degree, degree]",
    "writable": tango.AttrWriteType.READ_WRITE,
    "inherited": "false",
}

# The desired information for the 'On' command when the Weather.xmi file is parsed
expected_on_cmd_info = {
    "name": "On",
    "doc_in": "No input parameter",
    "dtype_in": tango.CmdArgType.DevVoid,
    "doc_out": "Command responds",
    "dtype_out": tango.CmdArgType.DevVoid,
    "inherited": "false",
}

# The expected information that would be obtained for the device property when the
# Weather.xmi file is parsed by the XmiParser.
expected_sim_xmi_file_device_property_info = {
    "name": "sim_xmi_description_file",
    "mandatory": "true",
    "description": "Path to the pogo generated xmi file",
    "type": tango.CmdArgType.DevString,
    "inherited": "false",
}

EXPECTED_QUANTITIES_LIST = frozenset(
    [
        "insolation",
        "temperature",
        "pressure",
        "rainfall",
        "relative-humidity",
        "wind-direction",
        "integer2",
        "input-comms-ok",
        "wind-speed",
        "image1",
        "integer1",
    ]
)


class test_SimXmiDeviceIntegration(ClassCleanupUnittestMixin, unittest.TestCase):

    longMessage = True

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.tango_db = cleanup_tempfile(cls, prefix="tango", suffix=".db")
        cls.xmi_file = [
            pkg_resources.resource_filename(
                "tango_simlib.tests.config_files", "Weather.xmi"
            )
        ]
        cls.device_name = "test/nodb/tangodeviceserver"
        model = tango_sim_generator.configure_device_models(cls.xmi_file, cls.device_name)
        cls.TangoDeviceServer = tango_sim_generator.get_tango_device_server(
            model, cls.xmi_file
        )[0]
        cls.tango_context = DeviceTestContext(
            cls.TangoDeviceServer, device_name=cls.device_name, db=cls.tango_db
        )
        start_thread_with_cleanup(cls, cls.tango_context)

    def setUp(self):
        super(test_SimXmiDeviceIntegration, self).setUp()
        self.device = self.tango_context.device
        self.instance = self.TangoDeviceServer.instances[self.device.name()]
        self.xmi_parser = sim_xmi_parser.XmiParser()
        self.xmi_parser.parse(self.xmi_file[0])

    def test_attribute_list(self):
        """ Test whether the attributes specified in the POGO generated xmi file
        are added to the TANGO device
        """
        # First testing that the attribute with data format "IMAGE" is not in the device.
        attribute_name = "image1"
        device_attributes = set(self.device.get_attribute_list())
        self.assertNotIn(
            attribute_name,
            device_attributes,
            "The attribute {} has been added to the device.".format(attribute_name),
        )
        not_added_attr = self.device.read_attribute("AttributesNotAdded")
        not_added_attr_names = not_added_attr.value
        self.assertIn(
            attribute_name,
            not_added_attr_names,
            "The attribute {} was not added to the list of attributes that"
            " could not be added to the device.".format(attribute_name),
        )

        attributes = set(self.device.get_attribute_list())
        expected_attributes = []
        default_attributes = helper_module.DEFAULT_TANGO_DEVICE_ATTRIBUTES
        for attribute_data in self.xmi_parser._device_attributes:
            expected_attributes.append(attribute_data["dynamicAttributes"]["name"])
        self.assertEqual(
            set(expected_attributes) - set(not_added_attr_names),
            attributes - default_attributes,
            "Actual tango device attribute list differs from expected " "list!",
        )

    def test_attribute_properties(self):
        attribute_list = self.device.get_attribute_list()
        attribute_data = self.xmi_parser.get_device_attribute_metadata()
        not_added_attr = self.device.read_attribute("AttributesNotAdded")
        not_added_attr_names = not_added_attr.value

        for attr_name, attr_metadata in attribute_data.items():
            if attr_name in not_added_attr_names:
                continue
            self.assertIn(
                attr_name,
                attribute_list,
                "Device does not have the attribute %s" % (attr_name),
            )
            attr_query_data = self.device.attribute_query(attr_name)

            for attr_parameter in attr_metadata:
                # The 'inherited' parameter is not part of the TANGO device attribute
                # properties.
                if attr_parameter == "inherited":
                    continue
                expected_attr_value = attr_metadata[attr_parameter]
                attr_prop_value = getattr(attr_query_data, attr_parameter, None)
                # Here the writable property is checked for, since Pogo
                # expresses in as a string (e.g. 'READ') where tango device return a
                # tango object `tango._tango.AttrWriteType.READ` and taking
                # its string returns 'READ' which corresponds to the Pogo one.
                if attr_parameter in ["writable"]:
                    attr_prop_value = str(attr_prop_value)
                    if attr_prop_value == "WT_UNKNOWN":  # Attributes with a 'READ_WRITE'
                        # writable type are always set
                        # to 'WT_UNKOWN', but the
                        # `writable_attr_name` property
                        # is set to the name of the
                        # attribute.
                        attr_prop_value = "READ_WRITE"

                if attr_prop_value is None:
                    # In the case where no attr_query data is not found it is
                    # further checked in the mentioned attribute object
                    # i.e. alarms and events
                    # (check `self._test_tango_property_object`)
                    attr_prop_value = self._get_attribute_property_object_value(
                        attr_query_data, attr_parameter
                    )

                # Here the data_type property is checked for, since Pogo
                # expresses in as a PyTango object (e.g.`PyTango.DevDouble`)
                # where tango device return a corresponding int value (e.g. 5)
                # and taking int of `PyTango.DevDouble` returns 5.
                if attr_parameter in ["data_type"]:
                    expected_attr_value = int(expected_attr_value)

                # For some reason tango device attribute properties not
                # stated are assigned a string 'Not Specified' or even 'No
                # writable Specified'
                if "No" in str(attr_prop_value):
                    attr_prop_value = ""

                # Pogo doesn't seem to populate the value for the format parameter
                # as expected i.e. format = '', and tango  device return (e.g. %6.2f for
                # floating points). TANGO library assigns a default value according to
                # the attributes data type.
                # '%6.2f' is the default for attributes that have a data type of
                # DevDouble and DevFloat, and for DevInt its '%d', and for DevString
                # and DevEnum it uses '%s'.
                if attr_parameter in ["format"]:
                    attr_prop_value = ""

                self.assertEqual(
                    expected_attr_value,
                    attr_prop_value,
                    "Non matching %s property for %s attribute"
                    % (attr_parameter, attr_name),
                )

    def _get_attribute_property_object_value(self, attr_query_data, user_default_prop):
        """Extract the tango attribute property value from alarms an events objects

        Parameters
        ----------
        attr_query_data : PyTango.AttributeInfoEx
            data structure containing string arguments of attribute properties
        user_default_prop : str
            user default property as per items in `POGO_USER_DEFAULT_ATTR_PROP_MAP`

        Returns
        -------
        attr_prop_value : str
            tango attribute property value

        Note
        ----
         `self.device.attribute_query(attr_name)` is
         a structure (inheriting from :class:`AttributeInfo`) containing
         available information for an attribute with the following members:
         - alarms : object containing alarm information (see AttributeAlarmInfo).
         - events : object containing event information (see AttributeEventInfo).
         Thus a sequence with desired attribute objects is defined and besides
         this object is the normal attribute properties, refere to
         POGO_USER_DEFAULT_ATTR_PROP_MAP keys dynamicAttributes and properties

        """
        tango_property_members = ["alarms", "arch_event", "ch_event", "per_event"]
        for member in tango_property_members:
            if member in ["alarms"]:
                attr_prop_value = getattr(attr_query_data.alarms, user_default_prop, None)
            else:
                attr_prop_value = getattr(attr_query_data.events, member, None)
                # The per_event obect has attribute period
                # which is defferent from the object in the
                # POGO_USER_DEFAULT_ATTR_PROP_MAP (event_period)
                # used for # setting the value
                if "period" in user_default_prop:
                    attr_prop_value = getattr(attr_prop_value, "period", None)
                else:
                    attr_prop_value = getattr(attr_prop_value, user_default_prop, None)
            if attr_prop_value:
                return attr_prop_value

    def test_command_list(self):
        """Test tango command list."""

        actual_device_commands = set(self.device.get_command_list()) - {"Init"}
        expected_command_list = set(self.xmi_parser.get_device_command_metadata().keys())
        self.assertEquals(
            actual_device_commands,
            expected_command_list,
            "The commands specified in the xmi file are not present in" " the device",
        )

    def test_command_properties(self):
        command_data = self.xmi_parser.get_device_command_metadata()

        for cmd_name, cmd_metadata in command_data.items():
            cmd_config_info = self.device.get_command_config(cmd_name)
            for cmd_prop, cmd_prop_value in cmd_metadata.items():
                # The 'inherited' parameter is not part of the TANGO device command
                # properties.
                if cmd_prop == "inherited":
                    continue
                self.assertTrue(
                    hasattr(cmd_config_info, TANGO_CMD_PARAMS_NAME_MAP[cmd_prop]),
                    "The cmd parameter '%s' for the cmd '%s' was not translated"
                    % (cmd_prop, cmd_name),
                )
                if cmd_prop_value == "none" or cmd_prop_value == "":
                    cmd_prop_value = "Uninitialised"
                self.assertEqual(
                    getattr(cmd_config_info, TANGO_CMD_PARAMS_NAME_MAP[cmd_prop]),
                    cmd_prop_value,
                    "The cmd parameter '%s/%s' values do not match"
                    % (cmd_prop, TANGO_CMD_PARAMS_NAME_MAP[cmd_prop]),
                )


class GenericSetup(unittest.TestCase):
    longMessage = True

    def setUp(self):
        super(GenericSetup, self).setUp()
        self.xmi_file = [
            pkg_resources.resource_filename(
                "tango_simlib.tests.config_files", "Weather.xmi"
            )
        ]
        self.xmi_parser = sim_xmi_parser.XmiParser()
        self.xmi_parser.parse(self.xmi_file[0])


class test_XmiParser(GenericSetup):
    def test_parsed_attributes(self):
        """Test attribute information parsed matches with the one captured in the
        XMI file.
        """
        actual_parsed_attrs = self.xmi_parser.get_device_attribute_metadata()
        actual_parsed_attr_list = actual_parsed_attrs.keys()
        self.assertGreater(
            len(actual_parsed_attr_list), 0, "There is no attribute information parsed"
        )
        self.assertEquals(
            set(EXPECTED_QUANTITIES_LIST),
            set(actual_parsed_attr_list),
            "There are missing attributes",
        )

        # Test if all the parsed attributes have the mandatory properties
        for attribute_metadata in actual_parsed_attrs.values():
            for param in expected_mandatory_attr_parameters:
                self.assertIn(
                    param,
                    attribute_metadata.keys(),
                    "The parsed attribute '%s' does not the mandotory parameter"
                    " '%s' " % (attribute_metadata["name"], param),
                )

        # Using the made up pressure attribute expected results as we haven't generated
        # the full test data for the other attributes.
        self.assertIn(
            "pressure",
            actual_parsed_attrs.keys(),
            "The attribute pressure is not in the parsed attribute list",
        )
        actual_parsed_pressure_attr_info = actual_parsed_attrs["pressure"]

        # Compare the values of the attribute properties captured in the POGO generated
        # xmi file and the ones in the parsed attribute data structure.
        for prop in expected_pressure_attr_info:
            self.assertEquals(
                actual_parsed_pressure_attr_info[prop],
                expected_pressure_attr_info[prop],
                "The expected value for the parameter '%s' does not match"
                " with the actual value" % (prop),
            )

    def test_parsed_commands(self):
        """Test the parsed device commands.

        Check that the command information in the xmi parser object matches
        with the one captured in the XMI file generated using POGO.

        """
        actual_parsed_cmds = self.xmi_parser.get_device_command_metadata()
        expected_cmd_list = ["On", "Off", "Add", "cmd1"] + default_pogo_commands
        actual_parsed_cmd_list = actual_parsed_cmds.keys()
        self.assertGreater(
            len(actual_parsed_cmd_list),
            len(default_pogo_commands),
            "There are missing commands in the parsed list",
        )
        self.assertEquals(
            set(expected_cmd_list),
            set(actual_parsed_cmd_list),
            "There are some missing commands",
        )

        # Test if all the parsed commands have the mandatory properties
        for command_metadata in actual_parsed_cmds.values():
            for param in expected_mandatory_cmd_parameters:
                self.assertIn(
                    param,
                    command_metadata.keys(),
                    "The parsed command '%s' does not the mandatory parameter"
                    " '%s' " % (command_metadata["name"], param),
                )

        # Test the 'On' command using the made up expected results as we haven't
        # generated the full test data for the other commands.
        self.assertIn(
            "On",
            actual_parsed_cmds.keys(),
            "The 'On' command is not in the parsed command list",
        )
        actual_on_cmd_info = actual_parsed_cmds["On"]
        for prop in expected_on_cmd_info:
            self.assertEqual(
                expected_on_cmd_info[prop],
                actual_on_cmd_info[prop],
                "The expected value for the command paramater '%s'"
                " does not match with the actual value" % (prop),
            )

    def test_parsed_device_properties(self):
        """Test that the device property information captured in the XMI file
        generating using POGO is parsed correctly with no data loss.
        """
        actual_parsed_dev_properties = self.xmi_parser.get_device_properties_metadata(
            "deviceProperties"
        )
        expected_device_properties_list = ["sim_xmi_description_file"]
        actual_parsed_dev_props_list = actual_parsed_dev_properties.keys()
        self.assertEqual(
            set(expected_device_properties_list),
            set(actual_parsed_dev_props_list),
            "The device property list do not match",
        )

        # Test if all the parsed device properties have the mandatoy parameters
        for dev_prop_metadata in actual_parsed_dev_properties.values():
            for param in expected_mandatory_device_property_parameters:
                self.assertIn(
                    param,
                    dev_prop_metadata.keys(),
                    "The parsed device property '%s' does not have the"
                    " mandatory parameter '%s' " % (dev_prop_metadata["name"], param),
                )

        # Test the 'sim_xmi_description_file' device property as it is the only device
        # property we have for our device
        self.assertIn(
            "sim_xmi_description_file",
            actual_parsed_dev_properties.keys(),
            "The 'sim_xmi_description_file' device property is not in the"
            "parsed device properties' list",
        )
        actual_dev_prop_info = actual_parsed_dev_properties["sim_xmi_description_file"]
        for prop in expected_sim_xmi_file_device_property_info:
            self.assertEqual(
                expected_sim_xmi_file_device_property_info[prop],
                actual_dev_prop_info[prop],
                "The expected value for the device property parameter '%s'"
                " does not match with the actual value" % (prop),
            )


class test_PopModelQuantities(GenericSetup):
    def test_model_quantites_populator(self):
        """Test if quantities are populated to the model.

        Check that the model quantities that are added to the model match with
        the attributes specified in the XMI file.

        """
        device_name = "tango/device/instance"
        # Ensure that the SimModelException is raised when an instance of
        # PopulateModelQuantities is created with any object other than a Model
        # class instance.
        with self.assertRaises(model.SimModelException):
            model.PopulateModelQuantities(
                self.xmi_parser, device_name, sim_model="some_model"
            )
        pmq = model.PopulateModelQuantities(self.xmi_parser, device_name)

        self.assertEqual(
            device_name,
            pmq.sim_model.name,
            "The device name and the model name do not match.",
        )
        actual_quantities_list = pmq.sim_model.sim_quantities.keys()
        self.assertEqual(
            set(EXPECTED_QUANTITIES_LIST),
            set(actual_quantities_list),
            "The are quantities missing in the model",
        )


class test_PopModelActions(GenericSetup):
    def test_model_actions_populator(self):
        """Test if actions are populated to the model.
        """
        device_name = "tango/device/instance"
        cmd_info = self.xmi_parser.get_device_command_metadata()
        override_info = self.xmi_parser.get_device_cmd_override_metadata()

        sim_model = model.PopulateModelActions(
            cmd_info, override_info, device_name
        ).sim_model
        self.assertEqual(
            len(sim_model.sim_quantities), 0, "The model has some unexpected quantities"
        )

        for cmd_name in cmd_info.keys():
            # Exclude the State and Status command (cmd_handlers for them are created
            # automatically by TANGO
            if cmd_name not in ["State", "Status"]:
                self.assertTrue(
                    cmd_name in sim_model.sim_actions,
                    "The an action handler for the cmd '%s' was not created" % (cmd_name),
                )


class test_XmiStaticAttributes(ClassCleanupUnittestMixin, unittest.TestCase):
    """Test the use of XMI to generate a TANGO simulator.

    This class specifically ensures that the devEnum attribute type and
    spectrum data format attributes added statically prior to device start-up
    are well configured using the specified parameters in the POGO XMI.

    """

    longMessage = True

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.tango_db = cleanup_tempfile(cls, prefix="tango", suffix=".db")
        cls.xmi_file = [
            pkg_resources.resource_filename(
                "tango_simlib.tests.config_files", "devenum_test_case.xmi"
            )
        ]
        cls.device_name = "test/nodb/tangodeviceserver"
        model = tango_sim_generator.configure_device_models(cls.xmi_file, cls.device_name)
        cls.TangoDeviceServer = tango_sim_generator.get_tango_device_server(
            model, cls.xmi_file
        )[0]
        cls.tango_context = DeviceTestContext(
            cls.TangoDeviceServer, device_name=cls.device_name, db=cls.tango_db
        )
        start_thread_with_cleanup(cls, cls.tango_context)

    def setUp(self):
        super(test_XmiStaticAttributes, self).setUp()
        self.device = self.tango_context.device
        self.instance = self.TangoDeviceServer.instances[self.device.name()]
        self.xmi_parser = sim_xmi_parser.XmiParser()
        self.xmi_parser.parse(self.xmi_file[0])

    def test_attribute_list(self):
        """Test device attribute list.

        Check whether the attributes specified in the POGO generated xmi file
        are added to the TANGO device

        """
        attributes = set(self.device.get_attribute_list())
        expected_attributes = []
        for attribute_data in self.xmi_parser._device_attributes:
            expected_attributes.append(attribute_data["dynamicAttributes"]["name"])
        self.assertEqual(
            set(expected_attributes),
            attributes - helper_module.DEFAULT_TANGO_DEVICE_ATTRIBUTES,
            "Actual tango device attribute list differs from " "expected list!",
        )

    def test_enum_attribute_properties(self):
        """Test whether the DevEnum attributes are well configured.

        Checks whether the DevEnum data type attribute properties specified
        in the POGO generated XMI file are added to the TANGO device

        """
        attr_name = "adminMode"
        attributes = set(self.device.get_attribute_list())
        self.assertIn(
            attr_name,
            attributes,
            "The attribute {} is not in the device attribute list".format(attr_name),
        )
        attr_config = self.device.get_attribute_config(attr_name)
        for attr_prop, attr_prop_val in expected_admin_mode_devenum_attr_info.items():
            device_attr_prop_val = getattr(attr_config, attr_prop, None)
            if device_attr_prop_val:
                # Tango device return attribute properties with Not pecified
                # or No `property name` value if no info is provided
                if str(device_attr_prop_val) in helper_module.TANGO_NOT_SPECIFIED_PROPS:
                    device_attr_prop_val = ""
                # In the case of enum labels we assert the set of the lists
                if type(attr_prop_val) == list:
                    self.assertEqual(
                        set(device_attr_prop_val),
                        set(attr_prop_val),
                        "The expected value for the device property "
                        "parameter '%s' does not match with the "
                        "actual value" % (attr_prop),
                    )
                else:
                    self.assertEqual(
                        device_attr_prop_val,
                        attr_prop_val,
                        "The expected value for the device property "
                        "parameter '%s' does not match with the "
                        "actual value" % (attr_prop),
                    )

    def test_spectrum_attribute_properties(self):
        """Test whether the Spectrum attributes are well configred.

        Checks whether the Spectrum data format attribute properties specified
        in the POGO generated XMI file are added to the TANGO device

        """
        attr_name = "achievedPointing"
        attributes = set(self.device.get_attribute_list())
        self.assertIn(
            attr_name,
            attributes,
            "The attribute {} is not in the device attribute list".format(attr_name),
        )
        attr_config = self.device.get_attribute_config(attr_name)
        for (
            attr_prop,
            attr_prop_val,
        ) in expected_achieved_pointing_spectrum_attr_info.items():
            device_attr_prop_val = getattr(attr_config, attr_prop, None)
            if device_attr_prop_val:
                # Tango device return attribute properties with 'Not specified'
                # or No `property name` value if no info is provided
                if str(device_attr_prop_val) in helper_module.TANGO_NOT_SPECIFIED_PROPS:
                    device_attr_prop_val = ""
                self.assertEqual(
                    device_attr_prop_val,
                    attr_prop_val,
                    "The expected value for the device property "
                    "parameter '%s' does not match with the "
                    "actual value" % (attr_prop),
                )

    def test_writable_spectrum_attribute(self):
        """Test that the Spectrum writable attribute can be set correctly."""
        _timestamp = 0.0
        az = 0.0
        el = 0.0
        az_speed = 0.0
        el_speed = 0.0
        az_accl = 0.0
        el_accl = 0.0
        self.assertListEqual(
            self.device.desiredPointing.tolist(),
            [_timestamp, az, el, az_speed, el_speed, az_accl, el_accl],
        )

        # Change the values of the timestamp,  az and el
        _timestamp = 124324
        az = 45.0
        el = 104.0
        # Write to the attribute desiredPointing
        self.device.desiredPointing = [
            _timestamp,
            az,
            el,
            az_speed,
            el_speed,
            az_accl,
            el_accl,
        ]

        self.assertListEqual(
            self.device.desiredPointing.tolist(),
            [_timestamp, az, el, az_speed, el_speed, az_accl, el_accl],
        )
