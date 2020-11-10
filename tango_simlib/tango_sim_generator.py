#!/usr/bin/env python
#########################################################################################
# Copyright 2017 SKA South Africa (http://ska.ac.za/)                                   #
#                                                                                       #
# BSD license - see LICENSE.txt for details                                             #
#########################################################################################
"""
Simlib library generic simulator generator utility to be used to generate an actual
TANGO device that exhibits the behaviour defined in the data description file.
"""
from __future__ import absolute_import, division, print_function
from future import standard_library

standard_library.install_aliases()  # noqa: E402

import argparse
import logging
import os
import time
import weakref
from builtins import map, object, range
from functools import partial

import numpy as np

from tango import (
    Attr,
    AttrDataFormat,
    AttrQuality,
    AttrWriteType,
    CmdArgType,
    DevState,
    UserDefaultAttrProp,
)
from tango.server import Device, attribute, device_property
from tango_simlib.model import (
    INITIAL_CONSTANT_VALUE_TYPES,
    Model,
    PopulateModelActions,
    PopulateModelProperties,
    PopulateModelQuantities,
)
from future.utils import with_metaclass
from future.utils import itervalues
from tango_simlib.sim_test_interface import TangoTestDeviceServerBase
from tango_simlib.utilities import helper_module
from tango_simlib.utilities.fandango_json_parser import FandangoExportDeviceParser
from tango_simlib.utilities.sim_sdd_xml_parser import SDDParser
from tango_simlib.utilities.sim_xmi_parser import XmiParser
from tango_simlib.utilities.simdd_json_parser import SimddParser

MODULE_LOGGER = logging.getLogger(__name__)


class TangoDeviceServerBase(Device):
    instances = weakref.WeakValueDictionary()

    def init_device(self):
        super(TangoDeviceServerBase, self).init_device()
        name = self.get_name()
        self.model = None
        self.instances[name] = self
        self.set_state(DevState.ON)

    def always_executed_hook(self):
        self.model.update()

    def read_attributes(self, attr):
        """Method reading an attribute value.

        Parameters
        ----------
        attr : PyTango.DevAttr
            The attribute to read from.

        """
        if self.get_state() != DevState.OFF:
            name = attr.get_name()
            value, update_time = self.model.quantity_state[name]
            quality = AttrQuality.ATTR_VALID
            attr.set_value_date_quality(value, update_time, quality)

    def write_attributes(self, attr):
        """Method writing an attribute value.

        Parameters
        ----------
        attr : PyTango.DevAttr
            The attribute to write to.

        """
        if self.get_state() != DevState.OFF:
            name = attr.get_name()
            data = attr.get_write_value()
            MODULE_LOGGER.info("Writing value %s to attribute '%s'." % (data, name))
            self.model.sim_quantities[name].set_val(data, self.model.time_func())


def add_static_attribute(tango_device_class, attr_name, attr_meta):
    """Add any TANGO attribute of to the device server before start-up.

    Parameters
    ----------
    cls: class
        class object that the device server will inherit from
    attr_name: str
        Tango attribute name
    attr_meta: dict
        Meta data that enables the creation of a well configured attribute


    Note
    ====
    This is needed for DevEnum and spectrum type attributes

    """
    enum_labels = attr_meta.get("enum_labels", "")
    attr = attribute(
        label=attr_meta.get("label", attr_name),
        dtype=attr_meta["data_type"],
        enum_labels=enum_labels,
        doc=attr_meta.get("description", ""),
        dformat=attr_meta["data_format"],
        max_dim_x=attr_meta["max_dim_x"],
        max_dim_y=attr_meta["max_dim_y"],
        access=getattr(AttrWriteType, attr_meta["writable"]),
        polling_period=int(attr_meta.get("period", "-1")),
        min_value=attr_meta.get("min_value", ""),
        max_value=attr_meta.get("max_value", ""),
        min_alarm=attr_meta.get("min_alarm", ""),
        max_alarm=attr_meta.get("max_alarm", ""),
        min_warning=attr_meta.get("min_warning", ""),
        max_warning=attr_meta.get("max_warning", ""),
        delta_val=attr_meta.get("delta_val", ""),
        delta_t=attr_meta.get("delta_t", ""),
        abs_change=attr_meta.get("abs_change", ""),
        rel_change=attr_meta.get("rel_change", ""),
        event_period=attr_meta.get("event_period", ""),
        archive_abs_change=attr_meta.get("archive_abs_change", ""),
        archive_rel_change=attr_meta.get("archive_rel_change", ""),
        archive_period=attr_meta.get("archive_period", ""),
    )
    attr.__name__ = attr_name

    # Attribute read method
    def read_meth(tango_device_instance, attr):
        name = attr.get_name()
        value, update_time = tango_device_instance.model.quantity_state[name]
        quality = AttrQuality.ATTR_VALID
        # For attributes that have a SPECTRUM data format, there is no need to
        # type cast them to an integer data type. we need assign the list of values
        # to the attribute value parameter.
        if type(value) in (list, np.ndarray):
            attr.set_value_date_quality(value, update_time, quality)
        else:
            attr.set_value_date_quality(int(value), update_time, quality)

    # Attribute write method for writable attributes
    if str(attr_meta["writable"]) in ("READ_WRITE", "WRITE"):

        @attr.write
        def attr(tango_device_instance, new_val):
            # When selecting a model quantity we use the enum labels list indexing
            # to return the string value corresponding to the respective enum value
            # since an integer value is returned by device server when
            # attribute value is read
            MODULE_LOGGER.info(
                "Writing value {} to attribute '{}'.".format(new_val, attr_name)
            )
            _sim_quantities = tango_device_instance.model.sim_quantities
            tango_device_instance.model_quantity = _sim_quantities[attr_name]
            tango_device_instance.model_quantity.set_val(
                new_val, tango_device_instance.model.time_func()
            )

    read_meth.__name__ = "read_{}".format(attr_name)
    # Add the read method and the attribute to the class object
    setattr(tango_device_class, read_meth.__name__, read_meth)
    setattr(tango_device_class, attr.__name__, attr)
    MODULE_LOGGER.info("Adding static attribute {} to the device.".format(attr_name))


def _create_sim_test_interface_atttribute(models, class_instance):
    # Pick the first model instance in the dict.
    controllable_attribute_names = list(itervalues(models))[0].sim_quantities.keys()
    attr_control_meta = {}
    attr_control_meta["enum_labels"] = sorted(controllable_attribute_names)
    attr_control_meta["data_format"] = AttrDataFormat.SCALAR
    attr_control_meta["data_type"] = CmdArgType.DevEnum
    attr_control_meta["label"] = "Attribute name"
    attr_control_meta["description"] = "Attribute name to control"
    attr_control_meta["max_dim_x"] = 1
    attr_control_meta["max_dim_y"] = 0
    attr_control_meta["writable"] = "READ_WRITE"

    enum_labels = attr_control_meta.get("enum_labels", "")
    attr = attribute(
        label=attr_control_meta["label"],
        dtype=attr_control_meta["data_type"],
        enum_labels=enum_labels,
        doc=attr_control_meta["description"],
        dformat=attr_control_meta["data_format"],
        max_dim_x=attr_control_meta["max_dim_x"],
        max_dim_y=attr_control_meta["max_dim_y"],
        access=getattr(AttrWriteType, attr_control_meta["writable"]),
        fget=class_instance.read_fn,
        fset=class_instance.write_fn,
    )

    return attr


def get_tango_device_server(models, sim_data_files):
    """Declares a tango device class that inherits the Device class and then
    adds tango attributes (DevEnum and Spectrum type).

    Parameters
    ----------
    models: dict
        A dictionary of model.Model instances.
        e.g. {'model-name': model.Model}
    sim_data_files: list
        A list of direct paths to either xmi/xml/json data files.

    Returns
    -------
    TangoDeviceServer : PyTango.Device
        Tango device that has the commands dictionary populated.

    """
    # Declare a Tango Device class for specifically adding static
    # attributes prior running the device server and controller
    class TangoDeviceServerStaticAttrs(object):
        pass

    class TangoTestDeviceServerStaticAttrs(object):
        pass

    def read_fn(tango_device_instance):
        return tango_device_instance._attribute_name_index

    def write_fn(tango_device_instance, val):
        tango_device_instance._attribute_name_index = val
        tango_device_instance.model_quantity = tango_device_instance.model.sim_quantities[
            sorted(tango_device_instance.model.sim_quantities.keys())[val]
        ]

    # Sim test interface static attribute `attribute_name` info
    TangoTestDeviceServerStaticAttrs.read_fn = read_fn
    TangoTestDeviceServerStaticAttrs.write_fn = write_fn
    attr = _create_sim_test_interface_atttribute(models, TangoTestDeviceServerStaticAttrs)
    attr.setter(TangoTestDeviceServerStaticAttrs.write_fn)
    TangoTestDeviceServerStaticAttrs.attribute_name = attr
    # We use the `add_static_attribute` method to add DevEnum and Spectrum type
    # attributes statically to the tango device before start-up since the
    # cannot be well configured when added dynamically. This is suspected
    # to be a bug.
    # TODO(AR 02-03-2017): Ask the tango community on the upcoming Stack
    # Exchange community (AskTango) and also make follow ups on the next tango
    # releases.
    for quantity_name, quantity in list(itervalues(models))[0].sim_quantities.items():
        d_type = str(quantity.meta["data_type"])
        d_format = str(quantity.meta["data_format"])
        if d_type == "DevEnum" or d_format == "SPECTRUM":
            add_static_attribute(
                TangoDeviceServerStaticAttrs, quantity_name, quantity.meta
            )

    class TangoDeviceServer(TangoDeviceServerBase, TangoDeviceServerStaticAttrs):
        _models = models

        min_update_period = device_property(
            dtype=float,
            default_value=0.99,
            doc="Minimum time before model update method can be called again [seconds].",
        )

        def init_device(self):
            super(TangoDeviceServer, self).init_device()
            self.model = self._models[self.get_name()]
            self._not_added_attributes = []
            write_device_properties_to_db(self.get_name(), self.model)
            self.model.reset_model_state()
            self.model.min_update_period = self.min_update_period
            self.initialize_dynamic_commands()

        def initialize_dynamic_commands(self):
            for action_name, action_handler in self.model.sim_actions.items():
                cmd_handler = helper_module.generate_cmd_handler(
                    self.model, action_name, action_handler
                )
                setattr(TangoDeviceServer, action_name, cmd_handler)
                self.add_command(cmd_handler, device_level=True)

        def initialize_dynamic_attributes(self):
            model_sim_quants = self.model.sim_quantities
            attribute_list = set([attr for attr in model_sim_quants.keys()])
            for attribute_name in attribute_list:
                meta_data = model_sim_quants[attribute_name].meta
                # Dynamically add all attributes except those with DevEnum data type,
                # and SPECTRUM data format since they are added statically to the device
                # class prior to start-up. Also exclude attributes with a data format
                # 'IMAGE' as we currently do not handle them.
                if not self._is_attribute_addable_dynamically(meta_data):
                    continue
                # The return value of rwType is a string and it is required as a
                # PyTango data type when passed to the Attr function.
                # e.g. 'READ' -> tango._tango.AttrWriteType.READ
                rw_type = meta_data["writable"]
                rw_type = getattr(AttrWriteType, rw_type)
                attr = self._create_attribute(
                    attribute_name, meta_data["data_type"], rw_type
                )
                if attr is None:
                    continue

                self._configure_attribute_default_properties(attr, meta_data)
                self._add_dynamic_attribute(attr, rw_type)
                MODULE_LOGGER.debug("Added dynamic {} attribute".format(attribute_name))

        def _add_dynamic_attribute(self, attribute, read_write_type):
            if read_write_type in (AttrWriteType.READ, AttrWriteType.READ_WITH_WRITE):
                self.add_attribute(attribute, r_meth=self.read_attributes)
            elif read_write_type == AttrWriteType.WRITE:
                self.add_attribute(attribute, w_meth=self.write_attributes)
            elif read_write_type == AttrWriteType.READ_WRITE:
                self.add_attribute(
                    attribute, r_meth=self.read_attributes, w_meth=self.write_attributes
                )

        def _is_attribute_addable_dynamically(self, quantity_meta_data):
            attr_dtype = quantity_meta_data["data_type"]
            d_format = quantity_meta_data["data_format"]
            if str(attr_dtype) == "DevEnum" or str(d_format) == "SPECTRUM":
                return False
            elif str(d_format) == "IMAGE":
                self._not_added_attributes.append(quantity_meta_data["name"])
                return False

            return True

        def _create_attribute(self, attribute_name, attr_dtype, rw_type):
            attribute = None
            # Add a try/except clause when creating an instance of Attr class
            # as PyTango may raise an error when things go wrong.
            try:
                attribute = Attr(attribute_name, attr_dtype, rw_type)
            except Exception as e:
                self._not_added_attributes.append(attribute_name)
                MODULE_LOGGER.debug(
                    "Attribute %s could not be added dynamically"
                    " due to an error raised %s.",
                    attribute_name,
                    str(e),
                )

            return attribute

        def _configure_attribute_default_properties(self, attribute, quantity_meta_data):
            attribute_properties = UserDefaultAttrProp()
            for prop, prop_value in quantity_meta_data.items():
                # NB: Calling 'set_enum_labels' or setting the 'enum_labels' results
                # in a error, and we do not need to do anyway as DevEnum attributes are
                # handled by the `add_static_attribute` method.
                if prop == "enum_labels":
                    continue

                # UserDefaultAttrProp does not have the property 'event_period' but does
                # have a setter method for it.
                if prop == "event_period":
                    attribute_properties.set_event_period(prop_value)
                    continue

                if hasattr(attribute_properties, prop):
                    try:
                        setattr(attribute_properties, prop, prop_value)
                    except Exception as e:
                        attribute_name = quantity_meta_data["name"]
                        MODULE_LOGGER.error(
                            "The attribute '%s's property '%s' could not be set to "
                            "value '%s' due to an error raised %s.",
                            attribute_name,
                            prop,
                            prop_value,
                            str(e),
                        )
                else:
                    MODULE_LOGGER.debug(
                        "UserDefaultAttrProp has no attribute named '%s'", prop
                    )

            attribute.set_default_properties(attribute_properties)

        @attribute(
            dtype=(str,),
            doc="List of attributes that were not added to the "
            "device due to an error.",
            max_dim_x=10000,
        )
        def AttributesNotAdded(self):
            return self._not_added_attributes

        @attribute(
            dtype=int,
            doc="Number of attributes not added to the device due " "to an error.",
        )
        def NumAttributesNotAdded(self):
            return len(self._not_added_attributes)

    class SimControl(TangoTestDeviceServerBase, TangoTestDeviceServerStaticAttrs):
        instances = weakref.WeakValueDictionary()

        def init_device(self):
            super(SimControl, self).init_device()

            name = self.get_name()
            self.instances[name] = self

    klass_name = get_device_class(sim_data_files)
    TangoDeviceServer.TangoClassName = klass_name
    TangoDeviceServer.__name__ = klass_name
    SimControl.TangoClassName = "%sSimControl" % klass_name
    SimControl.__name__ = "%sSimControl" % klass_name
    return [TangoDeviceServer, SimControl]


def write_device_properties_to_db(device_name, model, db_instance=None):
    """Writes device properties, including optional default value, to tango DB.

    Parameters
    ----------
    device_name : str
        A TANGO device name
    model : model.Model instance
        Device model instance
    db_instance : tango._tango.Database instance
        Tango database instance
    """
    if not db_instance:
        db_instance = helper_module.get_database()

    for prop_name, prop_meta in model.sim_properties.items():
        db_instance.put_device_property(
            device_name, {prop_name: prop_meta["DefaultPropValue"]}
        )


def get_parser_instance(sim_datafile):
    """This method returns an appropriate parser instance to generate a Tango device.

    Parameters
    ----------
    sim_datafile : str
        A direct path to the xmi/xml/json/fgo file.

    Returns
    ------
    parser_instance: Parser instance
        The Parser object which reads an xmi/xml/json/fgo file and parses it into device
        attributes, commands, and properties.

    """
    extension = os.path.splitext(sim_datafile)[-1]
    extension = extension.lower()
    parser_instance = None
    if extension in [".xmi"]:
        parser_instance = XmiParser()
        parser_instance.parse(sim_datafile)
    elif extension in [".json"]:
        parser_instance = SimddParser()
        parser_instance.parse(sim_datafile)
    elif extension in [".xml"]:
        parser_instance = SDDParser()
        parser_instance.parse(sim_datafile)
    elif extension in [".fgo"]:
        parser_instance = FandangoExportDeviceParser()
        parser_instance.parse(sim_datafile)
    return parser_instance


def configure_device_model(sim_data_file=None, test_device_name=None, logger=None):
    models = configure_device_models(sim_data_file, test_device_name, logger)
    if len(models) == 1:
        return models
    else:
        raise RuntimeError(
            "Single model expected, but found {} devices"
            " registered under device server class {}. Rather use"
            " `configure_device_models`.".format(
                len(models), get_device_class(sim_data_file)
            )
        )


def configure_device_models(sim_data_file=None, test_device_name=None, logger=None):
    """
    In essence this function should get the data descriptor file, parse it,
    take the attribute and command information, populate the model(s) quantities and
    actions to be simulated and return that model.

    Parameters
    ----------
    sim_datafile : list
        A list of direct paths to either xmi/xml/json/fgo files.
    test_device_name : str
        A TANGO device name. This is used for running tests as we want the model
        instance and the device name to have the same name.

    Returns
    -------
    models : dict
        A dictionary of model.Model instances

    """
    data_file = sim_data_file
    klass_name = get_device_class(data_file)
    dev_names = None
    if test_device_name is None:
        server_name = helper_module.get_server_name()
        db_instance = helper_module.get_database()
        # db_datum is a PyTango.DbDatum structure with attribute name and value_string.
        # The name attribute represents the name of the device server and the
        # value_string attribute is a list of all the registered device instances in
        # that device server instance for the TANGO class 'TangoDeviceServer'.
        db_datum = db_instance.get_device_name(server_name, klass_name)
        # We assume that at least one device instance has been
        # registered for that class and device server.
        dev_names = getattr(db_datum, "value_string")
        if not dev_names:
            dev_name = "test/nodb/tangodeviceserver"
    else:
        dev_name = test_device_name

    # In case there are more than one data description files to be used to configure the
    # device.
    parsers = []
    for file_name in data_file:
        parsers.append(get_parser_instance(file_name))

    # In case there is more than one device instance per class.
    models = {}
    if dev_names:
        for dev_name in dev_names:
            models[dev_name] = Model(dev_name, logger=logger)
    else:
        models[dev_name] = Model(dev_name, logger=logger)

    # In case there is more than one parser instance for each file
    for model in models.values():
        command_info = {}
        properties_info = {}
        override_info = {}
        for parser in parsers:
            PopulateModelQuantities(parser, model.name, model)
            command_info.update(parser.get_device_command_metadata())
            properties_info.update(
                parser.get_device_properties_metadata("deviceProperties")
            )
            override_info.update(parser.get_device_cmd_override_metadata())
        PopulateModelActions(command_info, override_info, model.name, model)
        PopulateModelProperties(properties_info, model.name, model)
    return models


def generate_device_server(server_name, sim_data_files, directory=""):
    """Create a tango device server python file.

    Parameters
    ----------
    server_name: str
        Tango device server name
    sim_data_files: list
        A list of direct paths to either xmi/xml/json data files.

    """
    lines = [
        "#!/usr/bin/env python",
        "from tango.server import server_run",
        (
            "from tango_simlib.tango_sim_generator import ("
            "configure_device_models, get_tango_device_server)"
        ),
        "\n\n# File generated on {} by tango-simlib-generator".format(time.ctime()),
        "\n\ndef main():",
        "    sim_data_files = {}".format(sim_data_files),
        "    models = configure_device_models(sim_data_files)",
        "    TangoDeviceServers = get_tango_device_server(models, sim_data_files)",
        "    server_run(TangoDeviceServers)",
        '\nif __name__ == "__main__":',
        "    main()\n",
    ]
    with open(os.path.join(directory, "%s" % server_name), "w") as dserver:
        dserver.write("\n".join(lines))
    # Make the script executable
    os.chmod(os.path.join(directory, "%s" % server_name), 477)


def get_device_class(sim_data_files):
    """Get device class name from specified xmi/simdd description file.

    Parameters
    ----------
    sim_data_files: list
        A list of direct paths to either xmi/xml/json/fgo data files.

    Returns
    -------
    klass_name: str
        Tango device class name

    """
    if len(sim_data_files) < 1:
        raise Exception("No simulator data file specified.")

    parser_instance = None
    klass_name = ""
    precedence_map = {".xmi": 1, ".fgo": 2, ".json": 3}

    def get_precedence(file_name):
        extension = os.path.splitext(file_name)[-1]
        extension = extension.lower()
        return precedence_map.get(extension, 100)

    sorted_files = sorted(sim_data_files, key=get_precedence)
    parser_instance = get_parser_instance(sorted_files[0])

    # Since at the current moment the class name of the tango simulator to be
    # generated must be specified in the xmi data file, if no xmi if provided
    # the simulator will be given a default name.
    if parser_instance:
        klass_name = parser_instance.device_class_name
    else:
        klass_name = "TangoDeviceServer"

    return klass_name


def get_argparser():
    parser = argparse.ArgumentParser(
        description="Generate a tango data driven simulator, handling"
        " registration as needed. Supports multiple device per process."
    )
    required_argument = partial(parser.add_argument, required=True)
    required_argument(
        "--sim-data-file",
        action="append",
        help="Simulator description data files(s) " ".i.e. can specify multiple files",
    )
    required_argument("--directory", help="TANGO server executable path", default="")
    required_argument("--dserver-name", help="TANGO server executable command")
    return parser


def main():
    arg_parser = get_argparser()
    opts = arg_parser.parse_args()
    generate_device_server(
        opts.dserver_name, opts.sim_data_file, directory=opts.directory
    )


if __name__ == "__main__":
    main()
