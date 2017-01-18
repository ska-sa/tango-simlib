#!/usr/bin/env python
###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2013 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################


import time
import weakref
import logging
import PyTango
import numpy

from PyTango import UserDefaultAttrProp
from PyTango import AttrQuality, DevState
from PyTango import Attr, AttrWriteType, WAttribute
from PyTango import DevString, DevDouble, DevBoolean
from PyTango.server import Device, DeviceMeta
from PyTango.server import attribute, command, device_property

from mkat_tango.simlib import model

class SimControl(Device):
    __metaclass__ = DeviceMeta

    instances = weakref.WeakValueDictionary()

    def init_device(self):
        super(SimControl, self).init_device()

        name = self.get_name()
        self.instances[name] = self
        # Get the device instance model to be controlled
        try:
            self.model = model.model_registry[self.model_key]
        except KeyError:
            raise RuntimeError('Could not find model with device name or key '
                               '{}. Set the "model_key" device property to the '
                               'correct value.'.format(self.model_key))
        # Get a list of attributes a device contains from the model
        self.device_sensors = self.model.sim_quantities.keys()
        self.set_state(DevState.ON)
        self.model_quantities = None
        self._sensor_name = ''
        self._pause_active = False

    model_key = device_property(
        dtype=str, doc=
        'Simulator model key, usually the TANGO name of the simulated device.')

    # Static attributes of the device

    @attribute(dtype=str)
    def sensor_name(self):
        return self._sensor_name

    @sensor_name.write
    def sensor_name(self, name):
        if name in self.device_sensors:
            self._sensor_name = name
            self.model_quantities = self.model.sim_quantities[self._sensor_name]
        else:
            raise NameError('Name does not exist in the sensor list {}'.
                            format(self.device_sensors))

    @attribute(dtype=str, dformat=PyTango.AttrDataFormat.SPECTRUM, max_dim_x=9999)
    def control_sensor_list_names(self):
        return self.device_sensors

    @attribute(dtype=bool)
    def pause_active(self):
        return self._pause_active

    @pause_active.write
    def pause_active(self, isActive):
        self._pause_active = isActive
        setattr(self.model, 'paused', isActive)

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

    def read_attributes(self, attr):
        '''Method reading an attribute value
        Parameters
        ==========
        attr : PyTango.DevAttr
            The attribute to read from.
        '''
        name = attr.get_name()
        self.info_stream("Reading attribute %s", name)
        attr.set_value(getattr(self.model_quantities, name))

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
        attr.set_value(data)
        setattr(self.model_quantities, name, data)
        if name == 'last_val' and self._pause_active:
            self.model.quantity_state[self._sensor_name] = data, time.time()
        else:
            setattr(self.model_quantities, name, data)

