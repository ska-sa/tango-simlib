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

import os
import weakref
import logging
import argparse
import time

from functools import partial

from tango import (Attr, AttrDataFormat, AttrQuality, AttrWriteType, CmdArgType,
                   Database, DevState, UserDefaultAttrProp)
from tango.server import attribute, Device, DeviceMeta, command

from tango_simlib.model import (Model, PopulateModelActions, PopulateModelProperties,
                                PopulateModelQuantities)
from tango_simlib.utilities import helper_module
from tango_simlib.utilities.sim_xmi_parser import XmiParser
from tango_simlib.utilities.simdd_json_parser import SimddParser
from tango_simlib.utilities.sim_sdd_xml_parser import SDDParser
from tango_simlib.utilities.fandango_json_parser import FandangoExportDeviceParser
from tango_simlib.sim_test_interface import TangoTestDeviceServerBase


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
        """Method reading an attribute value

        Parameters
        ----------
        attr : PyTango.DevAttr
            The attribute to read from.

        """
        if self.get_state() != DevState.OFF:
            name = attr.get_name()
            value, update_time = self.model.quantity_state[name]
            quality = AttrQuality.ATTR_VALID
            self.info_stream("Reading attribute %s", name)
            attr.set_value_date_quality(value, update_time, quality)


def get_tango_device_server(model, sim_data_files):
    """Declares a tango device class that inherits the Device class and then
    adds tango attributes (DevEnum and Spectrum type).

    Parameters
    ----------
    model: model.Model instance
        Device model instance
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
            sorted(tango_device_instance.model.sim_quantities.keys())[val]]
    
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
        This is needed for DevEnum and spectrum type attribues

        """
        attr = attribute(label=attr_meta['label'], dtype=attr_meta['data_type'],
                         enum_labels=attr_meta['enum_labels']
                         if 'enum_labels' in attr_meta else '',
                         doc=attr_meta['description'],
                         dformat=attr_meta['data_format'],
                         max_dim_x=attr_meta['max_dim_x'],
                         max_dim_y=attr_meta['max_dim_y'],
                         access=getattr(AttrWriteType, attr_meta['writable']))
        attr.__name__ = attr_name
        # Attribute read method
        def read_meth(tango_device_instance, attr):
            name = attr.get_name()
            value, update_time = tango_device_instance.model.quantity_state[name]
            quality = AttrQuality.ATTR_VALID
            tango_device_instance.info_stream("Reading attribute %s", name)
            # For attributes that have a SPECTRUM data format, there is no need to
            # type cast them to an integer data type. we need assign the list of values
            # to the attribute value parameter.
            if type(value) == list:
                attr.set_value_date_quality(value, update_time, quality)
            else:
                attr.set_value_date_quality(int(value), update_time, quality)
        # Attribute write method for writable attributes
        if str(attr_meta['writable']) == 'READ_WRITE':
            @attr.write
            def attr(tango_device_instance, new_val):
                # When selecting a model quantity we use the enum labels list indexing
                # to return the string value corresponding to the respective enum value
                # since an integer value is returned by device server when
                # attribute value is read
                tango_device_instance.model_quantity = (
                        tango_device_instance.model.sim_quantities[attr_name])
                tango_device_instance.model_quantity.set_val(
                        new_val, tango_device_instance.model.time_func())
        read_meth.__name__ = 'read_{}'.format(attr_name)
        # Add the read method and the attribute to the class object
        setattr(tango_device_class, read_meth.__name__, read_meth)
        setattr(tango_device_class, attr.__name__, attr)
        MODULE_LOGGER.info("Adding static attribute {} to the device.".format(attr_name))

    # Sim test interface static attribute `attribute_name` info
    controllable_attribute_names = model.sim_quantities.keys()
    attr_control_meta = dict()
    attr_control_meta['enum_labels'] = sorted(controllable_attribute_names)
    attr_control_meta['data_format'] = AttrDataFormat.SCALAR
    attr_control_meta['data_type'] = CmdArgType.DevEnum
    attr_control_meta['label'] = 'Attribute name'
    attr_control_meta['description'] = 'Attribute name to control'
    attr_control_meta['max_dim_x'] = 1
    attr_control_meta['max_dim_y'] = 0
    attr_control_meta['writable'] = 'READ_WRITE'

    TangoTestDeviceServerStaticAttrs.read_fn = read_fn
    TangoTestDeviceServerStaticAttrs.write_fn = write_fn
    attr = attribute(
        label=attr_control_meta['label'], dtype=attr_control_meta['data_type'],
        enum_labels=attr_control_meta['enum_labels']
        if 'enum_labels' in attr_control_meta else '',
        doc=attr_control_meta['description'],
        dformat=attr_control_meta['data_format'],
        max_dim_x=attr_control_meta['max_dim_x'],
        max_dim_y=attr_control_meta['max_dim_y'],
        access=getattr(AttrWriteType, attr_control_meta['writable']),
        fget=TangoTestDeviceServerStaticAttrs.read_fn,
        fset=TangoTestDeviceServerStaticAttrs.write_fn)
    TangoTestDeviceServerStaticAttrs.attribute_name = attr
    # We use the `add_static_attribute` method to add DevEnum and Spectrum type
    # attributes statically to the tango device before start-up since the
    # cannot be well configured when added dynamically. This is suspected
    # to be a bug.
    # TODO(AR 02-03-2017): Ask the tango community on the upcoming Stack
    # Exchange community (AskTango) and also make follow ups on the next tango
    # releases.
    for quantity_name, quantity in model.sim_quantities.items():
        d_type = quantity.meta['data_type']
        d_type = str(quantity.meta['data_type'])
        d_format = str(quantity.meta['data_format'])
        if d_type == 'DevEnum' or d_format == 'SPECTRUM':
            add_static_attribute(TangoDeviceServerStaticAttrs, quantity_name,
                                 quantity.meta)


    class TangoDeviceServer(TangoDeviceServerBase, TangoDeviceServerStaticAttrs):
        __metaclass__ = DeviceMeta

        def init_device(self):
            super(TangoDeviceServer, self).init_device()
            self.model = model
            self._not_added_attributes = []
            write_device_properties_to_db(self.get_name(), self.model)
            self._reset_to_default_state()
            self.initialize_dynamic_commands()

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

        def initialize_dynamic_commands(self):
            for action_name, action_handler in self.model.sim_actions.items():
                cmd_handler = helper_module.generate_cmd_handler(
                    self.model, action_name, action_handler)
                setattr(TangoDeviceServer, action_name, cmd_handler)
                self.add_command(cmd_handler, device_level=True)

        def initialize_dynamic_attributes(self):
            model_sim_quants = self.model.sim_quantities
            attribute_list = set([attr for attr in model_sim_quants.keys()])
            for attribute_name in attribute_list:
                meta_data = model_sim_quants[attribute_name].meta
                attr_dtype = meta_data['data_type']
                d_format = meta_data['data_format']
                # Dynamically add all attributes except those with DevEnum data type,
                # and SPECTRUM data format since they are added statically to the device
                # class prior to start-up. Also exclude attributes with a data format
                # 'IMAGE' as we currently do not handle them.
                if str(attr_dtype) == 'DevEnum':
                    continue
                elif str(d_format) == 'SPECTRUM':
                    continue
                elif str(d_format) == 'IMAGE':
                    self._not_added_attributes.append(attribute_name)
                    continue
                else:
                    # The return value of rwType is a string and it is required as a
                    # PyTango data type when passed to the Attr function.
                    # e.g. 'READ' -> tango._tango.AttrWriteType.READ
                    rw_type = meta_data['writable']
                    rw_type = getattr(AttrWriteType, rw_type)
                    # Add a try/except clause when creating an instance of Attr class
                    # as PyTango may raise an error when things go wrong.
                    try:
                        attr = Attr(attribute_name, attr_dtype, rw_type)
                    except Exception as e:
                        self._not_added_attributes.append(attribute_name)
                        MODULE_LOGGER.info("Attribute %s could not be added dynamically"
                                           " due to an error raised %s.", attribute_name,
                                           str(e))
                        continue
                    attr_props = UserDefaultAttrProp()
                    for prop in meta_data.keys():
                        attr_prop_setter = getattr(attr_props, 'set_' + prop, None)
                        if attr_prop_setter:
                            attr_prop_setter(str(meta_data[prop]))
                        else:
                            MODULE_LOGGER.info(
                                "No setter function for " + prop + " property")
                    attr.set_default_properties(attr_props)
                    self.add_attribute(attr, self.read_attributes)
                    MODULE_LOGGER.info("Added dynamic {} attribute"
                                       .format(attribute_name))

        @attribute(dtype=(str,), doc="List of attributes that were not added to the "
                   "device due to an error.",
                   max_dim_x=10000)
        def AttributesNotAdded(self):
            return self._not_added_attributes

        @attribute(dtype=int, doc="Number of attributes not added to the device due "
                   "to an error.")
        def NumAttributesNotAdded(self):
            return len(self._not_added_attributes)

    class SimControl(TangoTestDeviceServerBase, TangoTestDeviceServerStaticAttrs):
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

def write_device_properties_to_db(device_name, model, db_instance=None):
    """Writes device properties, including optional default value, to tango DB

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
        db_instance = Database()
    for prop_name, prop_meta in model.sim_properties.items():
        db_instance.put_device_property(
            device_name, {prop_name: prop_meta['DefaultPropValue']})

def get_parser_instance(sim_datafile):
    """This method returns an appropriate parser instance to generate a Tango device

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

def configure_device_model(sim_data_file=None, test_device_name=None):
    """In essence this function should get the data descriptor file, parse it,
    take the attribute and command information, populate the model quantities and
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
    model : model.Model instance

    """
    data_file = sim_data_file
    klass_name = get_device_class(data_file)

    if test_device_name is None:
        server_name = helper_module.get_server_name()
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
    for file_name in data_file:
        parsers.append(get_parser_instance(file_name))

    # In case there is more than one parser instance for each file
    model = Model(dev_name)
    attribute_info = {}
    command_info = {}
    properties_info = {}
    override_info = {}
    for parser in parsers:
        attribute_info.update(parser.get_device_attribute_metadata())
        command_info.update(parser.get_device_command_metadata())
        properties_info.update(parser.get_device_properties_metadata('deviceProperties'))
        override_info.update(parser.get_device_cmd_override_metadata())
    PopulateModelQuantities(attribute_info, dev_name, model)
    PopulateModelActions(command_info, override_info, dev_name, model)
    PopulateModelProperties(properties_info, dev_name, model)
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
             'from tango.server import server_run',
             ('from tango_simlib.tango_sim_generator import ('
              'configure_device_model, get_tango_device_server)'),
             '\n\n# File generated on {} by tango-simlib-generator'.format(time.ctime()),
             '\n\ndef main():',
             '    sim_data_files = %s' % sim_data_files,
             '    model = configure_device_model(sim_data_files)',
             '    TangoDeviceServers = get_tango_device_server(model, sim_data_files)',
             '    server_run(TangoDeviceServers)',
             '\nif __name__ == "__main__":',
             '    main()\n']
    with open(os.path.join(directory, "%s" % server_name), 'w') as dserver:
        dserver.write('\n'.join(lines))
    # Make the script executable
    os.chmod(os.path.join(directory, "%s" % server_name), 477)

def get_device_class(sim_data_files):
    """Get device class name from specified xmi/simdd description file

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
        raise Exception('No simulator data file specified.')

    parser_instance = None
    klass_name = ''
    precedence_map = {'.xmi': 1, '.fgo': 2, '.json': 3}

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
    required_argument('--directory', help='TANGO server executable path', default='')
    required_argument('--dserver-name', help='TANGO server executable command')
    return parser

def main():
    arg_parser = get_argparser()
    opts = arg_parser.parse_args()
    generate_device_server(opts.dserver_name, opts.sim_data_file, directory=opts.directory)

if __name__ == "__main__":
    main()