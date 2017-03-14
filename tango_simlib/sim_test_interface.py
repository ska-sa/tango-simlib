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
@author MeerKAT CAM team <cam@ska.ac.za>
"""
import weakref

from PyTango import UserDefaultAttrProp
from PyTango import DevState
from PyTango import Attr, AttrWriteType
from PyTango import DevDouble
from PyTango.server import Device, DeviceMeta
from PyTango.server import attribute, device_property

from tango_simlib import model


class TangoTestDeviceServerBase(Device):
    __metaclass__ = DeviceMeta

    instances = weakref.WeakValueDictionary()

    model_key = device_property(
        dtype=str, doc=
        "Simulator model key, usually the TANGO name of the simulated device.")

    def __init__(self, dev_class, name):
        super(TangoTestDeviceServerBase, self).__init__(dev_class, name)

        self.model = None
        self._attribute_name = ''
        self.model_quantity = None
        self._pause_active = False
        self.sim_device_attributes = None
        self.init_device()

    def init_device(self):
        super(TangoTestDeviceServerBase, self).init_device()
        name = self.get_name()
        self.instances[name] = self

        try:
            self.model = model.model_registry[self.model_key]
        except KeyError:
            raise RuntimeError('Could not find model with device name or key '
                               '{}. Set the "model_key" device property to the '
                               'correct value.'.format(self.model_key))
        self.sim_device_attributes = self.model.sim_quantities.keys()
        self.set_state(DevState.ON)


    def initialize_dynamic_attributes(self):
        '''The device method that sets up attributes during run time'''
        # Get attributes to control the device model quantities
        # from class variables of the quantities included in the device model.
        models = set([quant.__class__
                      for quant in self.model.sim_quantities.values()])
        control_attributes = []

        for cls in models:
            control_attributes += [attr for attr in cls.adjustable_attributes]

        # Add a list of float attributes from the list of Guassian variables
        for attribute_name in control_attributes:
            model.MODULE_LOGGER.info(
                "Added weather {} attribute control".format(attribute_name))
            attr_props = UserDefaultAttrProp()
            attr = Attr(attribute_name, DevDouble, AttrWriteType.READ_WRITE)
            attr.set_default_properties(attr_props)
            self.add_attribute(attr, self.read_attributes, self.write_attributes)

    # Static attributes of the device
    @attribute(dtype=bool)
    def pause_active(self):
        return self._pause_active

    @pause_active.write
    def pause_active(self, is_active):
        self._pause_active = is_active
        setattr(self.model, 'paused', is_active)

    def read_attributes(self, attr):
        '''Method reading an attribute value
        Parameters
        ==========
        attr : PyTango.DevAttr
            The attribute to read from.
        '''
        name = attr.get_name()
        self.info_stream("Reading attribute %s", name)
        attr.set_value(getattr(self.model_quantity, name))

    def write_attributes(self, attr):
        '''Method writing an attribute value
        Parameters
        ==========
        attr : PyTango.DevAttr
            The attribute to write to.
        '''
        name = attr.get_name()
        data = attr.get_write_value()
        self.info_stream("Writing attribute {} with value: {}".format(name, data))

        if name == 'last_val':
            self.model_quantity.set_val(data, self.model.time_func())
        else:
            setattr(self.model_quantity, name, data)
