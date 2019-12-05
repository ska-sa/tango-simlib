# -*- coding: utf8 -*-

# BEGIN VERSION CHECK
# Get package version when locally imported from repo or via -e develop install
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
try:
    import katversion as _katversion
except ImportError:
    import time as _time
    __version__ = "0.0+unknown.{}".format(_time.strftime('%Y%m%d%H%M'))
else:
    __version__ = _katversion.get_version(__path__[0])
# END VERSION CHECK
