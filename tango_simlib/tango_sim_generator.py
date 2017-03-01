#!/usr/bin/env python
###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2013 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################
"""
Simlib library generic simulator generator utility to be used to generate an actual
TANGO device that exhibits the behaviour defined in the data description file.
@author MeerKAT CAM team <cam@ska.ac.za>
"""

import os
import weakref
import logging
import argparse

from PyTango import Attr, AttrWriteType, UserDefaultAttrProp, AttrQuality, Database
from PyTango import DevState, DevEnum
from PyTango.server import Device, DeviceMeta, device_property, command, attribute

from enum import Enum
from functools import partial

from tango_simlib.model import Model
from tango_simlib.sim_xmi_parser import XmiParser
from tango_simlib.simdd_json_parser import SimddParser
from tango_simlib.sim_sdd_xml_parser import SDDParser
from tango_simlib.sim_test_interface import TangoTestDeviceServerBase
from tango_simlib.model import PopulateModelQuantities, PopulateModelActions
from tango_simlib import helper_module

MODULE_LOGGER = logging.getLogger(__name__)

POGO_USER_DEFAULT_CMD_PROP_MAP = {
        'name': 'name',
        'arginDescription': 'doc_in',
        'arginType': 'dtype_in',
        'argoutDescription': 'doc_out',
        'argoutType': 'dtype_out'}


class TangoDeviceServerBase(Device):
    instances = weakref.WeakValueDictionary()

    sim_xmi_description_file = device_property(
            dtype=str, doc='Complete path name of the POGO xmi file to be parsed')

    def init_device(self):
        super(TangoDeviceServerBase, self).init_device()
        name = self.get_name()
        self.model = None
        self.instances[name] = self
        self.set_state(DevState.ON)

    def always_executed_hook(self):
        self.model.update()

    def read_attributes(self, attr):
        """Method reading an attribute value

        Parameters
        ==========

        attr : PyTango.DevAttr
            The attribute to read from.

        """
        if self.get_state() != DevState.OFF:
            name = attr.get_name()
            value, update_time = self.model.quantity_state[name]
            quality = AttrQuality.ATTR_VALID
            self.info_stream("Reading attribute %s", name)
            attr.set_value_date_quality(value, update_time, quality)

def get_data_description_file_name():
    """Gets the xmi/xml/json description file name from the tango-db device properties

    Returns
    =======
    sim_data_description_file_list : list
        Tango device server description file(s) (POGO xmi or SDD xml or SIMDD json)
        e.g. ['home/user/weather.xmi']

    """

    # TODO (NM 2016-11-04) At the moment this is hardcoded to assume only the
    # first class and first device configures the XMI file. But more
    # fundamentally, this is a chicken and egg problem. TANGO usually assumes
    # that a device server knows what TANGO classes it supports even before any
    # device have been registered to the device server, allowing e.g. the Jive
    # server wizard to work. Now we are forcing the user to register a device
    # first to specify the XMI file. Passing the XMI file on the command line is
    # problematic since we still want to use the TANGO main function.
    #
    # Potential solutions
    #
    # 1) Generate a script that hardcodes the name of the XMI file for each
    #    dynamic device (perhaps a good simple solution, also gives you unique
    #    device server names)
    #
    # 2) Use an OS environment variable (probably too magic)
    #
    # 3) Perhaps define a "DynamicControl" class that is always exposed by the
    #    dynamic simulator. A property can then be defined on a DynamicControl
    #    instance, that is used to find the XMI file. Once the device is
    #    restarted, the classes defined in the XMI file can be exposed.

    #This function should perhaps take the device name

    server_name = helper_module.get_server_name()
    db_instance = Database()
    server_class = db_instance.get_server_class_list(server_name).value_string[0]
    device_name = db_instance.get_device_name(server_name, server_class).value_string[0]
    sim_data_description_file_list = db_instance.get_device_property(device_name,
        'sim_data_description_file')['sim_data_description_file']
    return sim_data_description_file_list


def get_tango_device_server(model, sim_data_files):
    """Declares a tango device class that inherits the Device class and then
    adds tango commands.

    Parameters
    ----------
    model: model.Model instance
        Device model instance
    sim_data_files: list
        A list of direct paths to either xmi/xml/json data files.

    Returns
    -------
    TangoDeviceServer : PyTango.Device
        Tango device that has the results of the translated KATCP server

    """
    # Declare a Tango Device class for specifically adding commands prior
    # running the device server
    class TangoDeviceServerCommands(object):
        pass

    class TangoTestDeviceServerCommands(object):
        pass

    # Declare a Tango Device class for specifically adding enum
    # attributes prior running the device server and controller
    class TangoDeviceServerEnumAttrs(object):
        pass

    class TangoTestDeviceServerEnumAttrs(object):
        pass

    def generate_cmd_handler(action_name, action_handler):
        def cmd_handler(tango_device, input_parameters=None):
            return action_handler(tango_dev=tango_device, data_input=input_parameters)

        cmd_handler.__name__ = action_name
        cmd_info_copy = model.sim_actions_meta[action_name].copy()
        # Delete all the keys that are not part of the Tango command parameters.
        cmd_info_copy.pop('name')
        tango_cmd_prop = POGO_USER_DEFAULT_CMD_PROP_MAP.values()
        for prop_key in model.sim_actions_meta[action_name]:
            if prop_key not in tango_cmd_prop:
                MODULE_LOGGER.info(
                    "Warning! Property %s is not a tango command prop", prop_key)
                cmd_info_copy.pop(prop_key)
        """
        The command method signature:
        command(f=None, dtype_in=None, dformat_in=None, doc_in="",
                dtype_out=None, dformat_out=None, doc_out="", green_mode=None)
        """
        return command(f=cmd_handler, **cmd_info_copy)

    def add_enum_attribute(cls, attr_name, attr_meta):
        """Add an attribute of tango type DevEnum to the device server.

        Parameters
        ----------
        cls: class
            class object that the device server will inherit from
        attr_name: str
            Tango enum attribute name
        attr_meta: dict
            Meta data that enables the creation of a well configured enum
            attribute

        """
        attr = attribute(label=attr_meta['label'], dtype=attr_meta['data_type'],
                         enum_labels=attr_meta['enum_labels'],
                         doc=attr_meta['description'],
                         access=getattr(AttrWriteType, attr_meta['writable']))
        attr.__name__ = attr_name
        # Attribute read method
        def read_meth(cls):
            return cls.some_variable_val
        # Attribute write method for writable attributes
        if str(attr_meta['writable']) == 'READ_WRITE':
            @attr.write
            def attr(cls, new_val):
                cls.some_variable_val = new_val
        read_meth.__name__ = 'read_{}'.format(attr_name)
        # Add the read method and the attribute to the class object
        setattr(cls, read_meth.__name__, read_meth)
        setattr(cls, attr.__name__, attr)

    for quantity_name, quantity in model.sim_quantities.items():
        d_type = quantity.meta['data_type']
        if d_type == DevEnum:
            add_enum_attribute(TangoDeviceServerEnumAttrs, quantity_name, quantity.meta)

    for action_name, action_handler in model.sim_actions.items():
        cmd_handler = generate_cmd_handler(action_name, action_handler)
        # You might need to turn cmd_handler into an unbound method before you add
        # it to the class
        setattr(TangoDeviceServerCommands, action_name, cmd_handler)

    for action_name, action_handler in model.test_sim_actions.items():
        cmd_handler = generate_cmd_handler(action_name, action_handler)
        # You might need to turn cmd_handler into an unbound method before you add
        # it to the class
        setattr(TangoTestDeviceServerCommands, action_name, cmd_handler)

    class TangoDeviceServer(TangoDeviceServerBase, TangoDeviceServerCommands,
                            TangoDeviceServerEnumAttrs):
        __metaclass__ = DeviceMeta

        def init_device(self):
            super(TangoDeviceServer, self).init_device()
            self.model = model
            self._reset_to_default_state()

        def _reset_to_default_state(self):
            """Reset the model's quantities' adjustable attributes to their default
            values.
            """
            simulated_quantities = self.model.sim_quantities.values()
            for simulated_quantity in simulated_quantities:
                sim_quantity_meta_info = simulated_quantity.meta
                adjustable_attrs = simulated_quantity.adjustable_attributes

                for attr in adjustable_attrs:
                    try:
                        adjustable_val = float(sim_quantity_meta_info[attr])
                    except KeyError:
                        adjustable_val = 0.0
                    setattr(simulated_quantity, attr, adjustable_val)

        def initialize_dynamic_attributes(self):
            model_sim_quants = self.model.sim_quantities
            attribute_list = set([attr for attr in model_sim_quants.keys()])
            for attribute_name in attribute_list:
                MODULE_LOGGER.info("Added dynamic {} attribute"
                                   .format(attribute_name))
                meta_data = model_sim_quants[attribute_name].meta
                attr_dtype = meta_data['data_type']
                # Dynamically add all attributes except those with DevEnum data type
                # since they are added to the device class prior to start-up.
                if str(attr_dtype) != 'DevEnum':
                    # The return value of rwType is a string and it is required as a
                    # PyTango data type when passed to the Attr function.
                    # e.g. 'READ' -> PyTango.AttrWriteType.READ
                    rw_type = meta_data['writable']
                    rw_type = getattr(AttrWriteType, rw_type)
                    attr = Attr(attribute_name, attr_dtype, rw_type)
                    attr_props = UserDefaultAttrProp()
                    for prop in meta_data.keys():
                        attr_prop_setter = getattr(attr_props, 'set_' + prop, None)
                        if attr_prop_setter:
                            attr_prop_setter(str(meta_data[prop]))
                        else:
                            MODULE_LOGGER.info("No setter function for " + prop + " property")
                    attr.set_default_properties(attr_props)
                    self.add_attribute(attr, self.read_attributes)

    class SimControl(TangoTestDeviceServerBase, TangoTestDeviceServerCommands,
                     TangoTestDeviceServerEnumAttrs):
        __metaclass__ = DeviceMeta

        instances = weakref.WeakValueDictionary()

        def init_device(self):
            super(SimControl, self).init_device()

            name = self.get_name()
            self.instances[name] = self

    klass_name = get_device_class(sim_data_files)
    TangoDeviceServer.TangoClassName = klass_name
    TangoDeviceServer.__name__ = klass_name
    SimControl.TangoClassName = '%sSimControl' % klass_name
    SimControl.__name__ = '%sSimControl' % klass_name
    return [TangoDeviceServer, SimControl]


def get_parser_instance(sim_datafile):
    """This method returns an appropriate parser instance to generate a Tango device

    Parameters
    ----------
    sim_datafile : str
        A direct path to the xmi/xml/json file.

    return
    ------
    parser_instance: Parser instance
        The Parser object which reads an xmi/xml/json file and parses it into device
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
    return parser_instance

def configure_device_model(sim_data_file=None, test_device_name=None):
    """In essence this function should get the xmi file, parse it,
    take the attribute and command information, populate the model quantities and
    actions to be simulated and return that model.

    Parameters
    ----------
    sim_datafile : list
        A list of direct paths to either xmi/xml/json files.
    test_device_name : str
        A TANGO device name. This is used for running tests as we want the model
        instance and the device name to have the same name.

    Returns
    -------
    model : model.Model instance
    """
    if sim_data_file is None:
        data_file = get_data_description_file_name()
    else:
        data_file = sim_data_file

    server_name = helper_module.get_server_name()
    klass_name = get_device_class(data_file)

    if test_device_name is None:
        db_instance = Database()
        # db_datum is a PyTango.DbDatum structure with attribute name and value_string.
        # The name attribute represents the name of the device server and the
        # value_string attribute is a list of all the registered device instances in
        # that device server instance for the TANGO class 'TangoDeviceServer'.
        db_datum = db_instance.get_device_name(server_name, klass_name)
        # We assume that at least one device instance has been
        # registered for that class and device server.
        dev_names = getattr(db_datum, 'value_string')
        if dev_names:
            dev_name = dev_names[0]
        else:
            # In case a device name is not provided during testing a
            # default name is assigned since it cannot be found in database.
            dev_name = 'test/nodb/tangodeviceserver'
    else:
        dev_name = test_device_name

    # In case there are more than one data description files to be used to configure the
    # device.
    parsers = []
    for file_descriptor in data_file:
        parsers.append(get_parser_instance(file_descriptor))

    # In case there is more than one parser instance for each file
    model = Model(dev_name)
    for parser in parsers:
        model_quantity_populator = PopulateModelQuantities(parser, dev_name, model)
        sim_model = model_quantity_populator.sim_model
        PopulateModelActions(parser, dev_name, sim_model)
    return model

def generate_device_server(server_name, sim_data_files, directory=''):
    """Create a tango device server python file

    Parameters
    ---------
    server_name: str
        Tango device server name
    sim_data_files: list
        A list of direct paths to either xmi/xml/json data files.

    """
    lines = ['#!/usr/bin/env python',
             'from PyTango.server import server_run',
             ('from tango_simlib.tango_sim_generator import ('
              'configure_device_model, get_tango_device_server)'),
             '\n\ndef main():',
             '    sim_data_files = %s' % sim_data_files,
             '    model = configure_device_model(sim_data_files)',
             '    TangoDeviceServers = get_tango_device_server(model, sim_data_files)',
             '    server_run(TangoDeviceServers)',
             '\nif __name__ == "__main__":',
             '    main()']
    with open(os.path.join(directory, "%s.py" % server_name), 'w') as dserver:
        dserver.write('\n'.join(lines))

def get_device_class(sim_data_files):
    """Get device class name from specified xmi/simdd description file

    Parameters
    ----------
    sim_data_files: list
        A list of direct paths to either xmi/xml/json data files.

    Return
    ------
    klass_name: str
        Tango device class name
    """
    if len(sim_data_files) < 1:
        raise Exception('No simulator data file specified.')

    parser_instance = None
    klass_name = ''
    for data_file in sim_data_files:
        extension = os.path.splitext(data_file)[-1]
        extension = extension.lower()
        if extension in [".xmi"]:
            parser_instance = get_parser_instance(data_file)
        elif extension in [".json"] and len(sim_data_files) < 2:
            parser_instance = get_parser_instance(data_file)

    # Since at the current moment the class name of the tango simulator to be
    # generated must be specified in the xmi data file, if no xmi if provided
    # the simulator will be given a default name.
    if parser_instance:
        klass_name = parser_instance.device_class_name
    else:
        klass_name = 'TangoDeviceServer'

    return klass_name

def get_argparser():
    parser = argparse.ArgumentParser(
            description="Generate a tango data driven simulator, handling"
            "registration as needed. Supports multiple device per process.")
    required_argument = partial(parser.add_argument, required=True)
    required_argument('--sim-data-file', action='append',
                      help='Simulator description data files(s) '
                      '.i.e. can specify multiple files')
    required_argument('--dserver-name', help='TANGO server executable command')
    return parser

def main():
    arg_parser = get_argparser()
    opts = arg_parser.parse_args()
    generate_device_server(opts.dserver_name, opts.sim_data_file)

if __name__ == "__main__":
    main()
