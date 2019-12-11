#########################################################################################
# Copyright 2017 SKA South Africa (http://ska.ac.za/)                                   #
#                                                                                       #
# BSD license - see LICENSE.txt for details                                             #
#########################################################################################
from __future__ import absolute_import, division, print_function
from future import standard_library
standard_library.install_aliases()  # noqa: E402

import abc
import logging
import time

from random import gauss

from builtins import object
from future.utils import with_metaclass
from past.builtins import cmp

MODULE_LOGGER = logging.getLogger(__name__)

inf = float("inf")
ninf = float("-inf")
registry = {}


def register_quantity_class(cls):
    assert cls.__name__ not in registry
    registry[cls.__name__] = cls
    Quantity.register(cls)


class Quantity(with_metaclass(abc.ABCMeta, object)):
    """Attributes that should be adjustable via a simulation control interface.

    Parameters
    ----------
    start_time : float
        The initial time when a quantity is updated.
    start_value : float
        The initial value of a quantity.
    meta : dict
        This data structure must contain all the attribute description data
        of all quantities that represent tango device simulator attributes.
        List of all available tango attribute description data:
        abs_change, archive_abs_change, archive_period, archive_rel_change,
        label, max_alarm, max_value, max_warning, min_alarm, min_value,
        delta_t, delta_val, description, display_unit, format,
        min_warning, period, rel_change
        e.g. meta=dict(label="Outside Temperature", dtype=float)
        TODO (AR) 2016-07-27 : Ideally these properties should not be TANGO
        specific as is at the moment.

    Notes
    =====
    Subclasses should add all the attributes to this set that users should be
    able to adjust via a user interface at simulation runtime, also initialise
    the `last_val` attribute with the initial quantity value.

    """

    adjustable_attributes = frozenset(["last_val", "last_update_time"])

    def __init__(self, start_value=None, start_time=None, meta=None):
        """Subclasses must call this super __init__()"""
        self.last_update_time = start_time or time.time()
        self.meta = meta

        if start_value is not None:
            self.last_val = start_value

    @abc.abstractmethod
    def next_val(self, t):
        """Return the next simulated value for simulation time at t seconds.

        Must update attributes `last_val` with the new value and `last_update_time` with
        the simulation time

        Parameters
        ----------
        t : float
            Time to update quantity

        """
        pass

    def set_val(self, val, t):
        """Set a value to the quantity.

        Parameters
        ----------
        t : float
            Time to update quantity
        val : int/float/string
            Value to update quantity

        """
        self.last_update_time = t
        self.last_val = val

    def default_val(self, t):
        """Set a default value of 0 to the quantity.

        Parameters
        ----------
        t : float
            Time to update quantity

        """
        self.last_val = 0
        self.last_update_time = t


class GaussianSlewLimited(Quantity):
    """A Gaussian random variable a slew-rate limit and clipping.

    Parameters
    ----------
    mean : float
        Gaussian mean value
    std_dev : float
        Gaussian standard deviation
    max_slew_rate : float
        Maximum quantity slew rate in amount per second. Random values will be clipped to
        satisfy this condition.
    min_bound : float
        Minimum quantity value, random values will be clipped if needed.
    max_bound : float
        Maximum quantity value, random values will be clipped if needed.

    """

    adjustable_attributes = Quantity.adjustable_attributes | frozenset(
        ["mean", "std_dev", "max_slew_rate", "min_bound", "max_bound"]
    )

    def __init__(
        self,
        mean,
        std_dev,
        max_slew_rate=inf,
        meta=None,
        min_bound=ninf,
        max_bound=inf,
        start_value=None,
        start_time=None,
    ):
        start_value = start_value if start_value is not None else mean
        super(GaussianSlewLimited, self).__init__(
            start_value=start_value, start_time=start_time, meta=meta
        )
        self.mean = mean
        self.std_dev = std_dev
        assert max_slew_rate > 0
        self.max_slew_rate = max_slew_rate
        self.min_bound = min_bound
        self.max_bound = max_bound
        self.last_val = mean

    def next_val(self, t):
        """Returns the next value of the simulation.

        Parameters
        ----------
        t : float
            Time to update quantity

        """
        dt = t - self.last_update_time
        max_slew = self.max_slew_rate * dt
        new_val = gauss(self.mean, self.std_dev)
        delta = new_val - self.last_val
        val = self.last_val + cmp(delta, 0) * min(abs(delta), max_slew)
        val = min(val, self.max_bound)
        val = max(val, self.min_bound)
        self.last_val = val
        self.last_update_time = t
        return val


register_quantity_class(GaussianSlewLimited)


class ConstantQuantity(Quantity):
    """A quantity that does not change unless explicitly set."""

    def next_val(self, t):
        """Returns the last value as the next simulated value.

        Parameters
        ----------
        t : float
            Time to update quantity

        """
        return self.last_val

    def default_val(self, t):
        """Set a default value of `True` to the quantity.

        Parameters
        ----------
        t : float
            Time to update quantity

        """
        self.last_val = True
        self.last_update_time = t


register_quantity_class(ConstantQuantity)
