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
from tango_simlib.quantities import GaussianSlewLimited

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

    def action_add(self, model, tango_dev=None, data_input=None):
        """Add two or more numbers together and return their sum.
        """
        total = sum(data_input)
        return total

    def action_multiplystringby3(self, model, tango_dev=None, data_input=None):
        """Takes a string and multiplies it by a constant integer value of 3.
        """
        return 3 * data_input

    def action_stopquantitysimulation(self, model, tango_dev=None, data_input=None):
        """Totally sets the simulated quantities` values to a constant value of zero.
        """
        for quantity in data_input:
            try:
                simulated_quantity = model.sim_quantities[quantity]
            except KeyError:
                MODULE_LOGGER.debug("Quantity %s not in the model", quantity)
            else:
                if hasattr(simulated_quantity, 'max_bound'):
                    simulated_quantity.max_bound = 0.0
                else:
                    MODULE_LOGGER.debug("Quantity %s is not a GaussianSlewLimited"
                                        " instance.", simulated_quantity)
