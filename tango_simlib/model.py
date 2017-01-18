#!/usr/bin/env python
###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2013 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################


import logging
import time
import numpy
import weakref
from functools import partial

MODULE_LOGGER = logging.getLogger(__name__)

model_registry = weakref.WeakValueDictionary()

class Model(object):

    def __init__(self, name, start_time=None, min_update_period=0.99,
                 time_func=time.time):
        self.name = name
        model_registry[self.name] = self
        self.min_update_period = min_update_period
        self.time_func = time_func
        self.start_time = start_time or time_func()
        self.last_update_time = self.start_time
        self.sim_quantities = {}
        self.sim_actions = {}
        self.sim_actions_meta = {}
        self._sim_state = {}
        self.setup_sim_quantities()
        self.paused = False  # Flag to pause updates
        # Making a public reference to _sim_state. Allows us to hook read-only views
        # or updates or whatever the future requires of this humble public attribute.
        self.quantity_state = self._sim_state

    def setup_sim_quantities(self):
        """Set up self.sim_quantities with simulated quantities

        Subclasses should implement this method. Should place simulated quantities in
        self.sim_quantities dict. Keyed by name of quantity, value must be instances
        satisfying the :class:`quantites.Quantity` interface.

        Notes
        =====

        - Must use self.start_time to set initial time values.
        - Must call super method after setting up `sim_quantities`

        """
        self._sim_state.update(
            {var: (quant.last_val, quant.last_update_time)
             for var, quant in self.sim_quantities.items()})

    def update(self):
        sim_time = self.time_func()
        dt = sim_time - self.last_update_time
        if dt < self.min_update_period or self.paused:
            MODULE_LOGGER.debug(
                "Sim {} skipping update at {}, dt {} < {} and pause {}"
                .format(self.name, sim_time, dt, self.min_update_period, self.paused))
            return

        MODULE_LOGGER.info("Stepping at {}, dt: {}".format(sim_time, dt))
        self.last_update_time = sim_time
        try:
            for var, quant in self.sim_quantities.items():
                self._sim_state[var] = (quant.next_val(sim_time), sim_time)
        except Exception:
            MODULE_LOGGER.exception('Exception in update loop')

    def set_sim_action(self, name, handler):
        """Add an action handler function
        Parameters
        ----------
        name : str
            Name of the action
        handler : callable(model_instance, action_args)
            Callable that handles action (name). Is called with the
            model instance as the first parameter.
        """
        # Perhaps you need to check that the names are valid, or you need to escape
        # stuff to underscores or something, since we need to generate python function
        # names.
        self.sim_actions[name] = partial(handler, self)
