#!/usr/bin/env python
#########################################################################################
# Copyright 2017 SKA South Africa (http://ska.ac.za/)                                   #
#                                                                                       #
# BSD license - see LICENSE.txt for details                                             #
#########################################################################################
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import sys
import logging
import threading

from tango.server import server_run

from tango_simlib.sim_test_interface import TangoTestDeviceServerBase


def simulator_main(sim_class, sim_control_class=TangoTestDeviceServerBase):
    """Main function for a simulator with class sim_class.

    sim_class is a tango.server.Device subclass.
    """
    run_ipython = '--ipython' in sys.argv
    if run_ipython:
        import IPython
        sys.argv.remove('--ipython')
        def start_ipython(sim_class):
            IPython.embed()
        t = threading.Thread(target=start_ipython, args=(sim_class,))
        t.setDaemon(True)
        t.start()

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(module)s - '
        '%(pathname)s : %(lineno)d - %(message)s',
        level=logging.INFO)

    classes = [sim_class]
    if sim_control_class:
        classes.append(sim_control_class)
    server_run(classes)
