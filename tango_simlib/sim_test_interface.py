from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


#########################################################################################
# Copyright 2017 SKA South Africa (http://ska.ac.za/)                                   #
#                                                                                       #
# BSD license - see LICENSE.txt for details                                             #
#########################################################################################
from future import standard_library

standard_library.install_aliases()

import weakref

from tango import Attr, AttrWriteType, DevDouble, DevState, UserDefaultAttrProp
from tango.server import Device, DeviceMeta, attribute, device_property
from tango_simlib import model
from tango_simlib.utilities.helper_module import generate_cmd_handler
from future.utils import with_metaclass


class TangoTestDeviceServerBase(with_metaclass(DeviceMeta, Device)):
    instances = weakref.WeakValueDictionary()

    model_key = device_property(
        dtype=str,
        doc="Simulator model key, usually the TANGO name of the simulated device.",
    )

    def __init__(self, dev_class, name):
        super(TangoTestDeviceServerBase, self).__init__(dev_class, name)

        self.model = None
        self._attribute_name = ""
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
            raise RuntimeError(
                "Could not find model with device name or key "
                '{}. Set the "model_key" device property to the '
                "correct value.".format(self.model_key)
            )
        self.sim_device_attributes = list(self.model.sim_quantities.keys())
        self.set_state(DevState.ON)
        self.initialize_dynamic_commands()

    def initialize_dynamic_commands(self):
        for action_name, action_handler in list(self.model.test_sim_actions.items()):
            cmd_handler = generate_cmd_handler(self.model, action_name, action_handler)
            # You might need to turn cmd_handler into an unbound method before you add
            # it to the class
            setattr(TangoTestDeviceServerBase, action_name, cmd_handler)
            self.add_command(cmd_handler, device_level=True)

    def initialize_dynamic_attributes(self):
        """The device method that sets up attributes during run time."""
        # Get attributes to control the device model quantities
        # from class variables of the quantities included in the device model.
        models = set(
            [quant.__class__ for quant in list(self.model.sim_quantities.values())]
        )
        control_attributes = []

        for cls in models:
            control_attributes += [attr for attr in cls.adjustable_attributes]

        # Add a list of float attributes from the list of Gaussian variables
        for attribute_name in control_attributes:
            model.MODULE_LOGGER.info(
                "Added weather {} attribute control".format(attribute_name)
            )
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
        setattr(self.model, "paused", is_active)

    def read_attributes(self, attr):
        """Method reading an attribute value.

        Parameters
        ----------
        attr : PyTango.DevAttr
            The attribute to read from.

        """
        name = attr.get_name()
        attr.set_value(getattr(self.model_quantity, name))

    def write_attributes(self, attr):
        """Method writing an attribute value.

        Parameters
        ----------
        attr : PyTango.DevAttr
            The attribute to write to.

        """
        name = attr.get_name()
        data = attr.get_write_value()
        self.info_stream("Writing attribute {} with value: {}".format(name, data))

        if name == "last_val":
            self.model_quantity.set_val(data, self.model.time_func())
        else:
            setattr(self.model_quantity, name, data)
