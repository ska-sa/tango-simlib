#!/usr/bin/env python

from __future__ import absolute_import, division, print_function
from future import standard_library

standard_library.install_aliases()  # noqa: E402

import logging

from PyTango.server import server_run
from tango_simlib.tango_sim_generator import (
    configure_device_models,
    get_tango_device_server,
)


MODULE_LOGGER = logging.getLogger(__name__)


def main():
    sim_data_files = [
        "../tests/config_files/MkatVds.xmi",
        "../tests/config_files/MkatVds_SimDD.json",
    ]
    model = configure_device_models(sim_data_files, logger=MODULE_LOGGER)
    TangoDeviceServers = get_tango_device_server(model, sim_data_files)
    server_run(TangoDeviceServers)


if __name__ == "__main__":
    main()
