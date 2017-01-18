#!/usr/bin/env python
###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2013 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################


import sys
import logging
import threading

from PyTango.server import server_run

from mkat_tango.simlib.sim_test_interface import SimControl

def simulator_main(sim_class, sim_control_class=SimControl):
    """Main function for a simulator with class sim_class

    sim_class is a tango.server.Device subclass

    """
    run_ipython = '--ipython' in sys.argv
    if run_ipython:
        import IPython
        sys.argv.remove('--ipython')
        def start_ipython(sim_class):
            IPython.embed()
        t = threading.Thread(target=start_ipython, args=(sim_class,) )
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
