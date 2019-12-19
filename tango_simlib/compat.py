# katcp.py
# -*- coding: utf8 -*-
# vim:fileencoding=utf8 ai ts=4 sts=4 et sw=4
# Copyright 2019 National Research Foundation (South African Radio Astronomy Observatory)
# BSD license - see LICENSE for details

"""Utilities for dealing with Python 2 and 3 compatibility."""

from __future__ import absolute_import, division, print_function
from future import standard_library
standard_library.install_aliases()  # noqa: E402

import builtins
import future

if future.utils.PY2:

    def ensure_native_str(value):
        """Coerce unicode string or bytes to native string type (UTF-8 encoding)."""
        if isinstance(value, str):
            return value
        elif isinstance(value, unicode): # noqa
            return value.encode("ascii", "replace")
        else:
            raise TypeError("Invalid type for string conversion: {}".format(type(value)))


else:

    def ensure_native_str(value):
        """Coerce unicode string or bytes to native string type (UTF-8 encoding)."""
        if isinstance(value, str):
            return value
        elif isinstance(value, bytes):
            return value.decode("ascii", "replace")
        else:
            raise TypeError("Invalid type for string conversion: {}".format(type(value)))