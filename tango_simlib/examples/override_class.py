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
An example of the user-defined override class.
@author MeerKAT CAM team <cam@ska.ac.za>
"""

import logging
from PyTango import DevState

MODULE_LOGGER = logging.getLogger(__name__)

class OverrideWeather(object):
    """An example of the override class for the TANGO device class 'Weather'. It
    provides all the implementations of the command handler functions for the commands
    specified in the POGO generated XMI data description file.
    """
    def action_on(self, model, tango_dev=None, data_input=None):
        """Changes the State of the device to ON.
        """
        tango_dev.set_state(DevState.ON)

    def action_off(self, model, tango_dev=None, data_input=None):
        """Changes the State of the device to OFF.
        """
        tango_dev.set_state(DevState.OFF)

    def action_stoprainfall(self, model, tango_dev=None, data_input=None):
        """Totally sets the simulated quantity rainfall to a constant value of zero.
        """
        try:
            quant_rainfall = model.sim_quantities['rainfall']
        except KeyError:
            MODULE_LOGGER.debug("Quantity rainfall not in the model")
        else:
            quant_rainfall.max_bound = 0.0

# TODO(KM 15-12-2016) Will need to define action methods that take in inputs and returns
# some values that correspond to the dtype_out of the TANGO command.
