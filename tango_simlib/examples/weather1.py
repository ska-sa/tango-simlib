#!/usr/bin/env python

from __future__ import absolute_import, division, print_function
from future import standard_library

standard_library.install_aliases()  # noqa: E402

from PyTango.server import server_run
from tango_simlib.tango_sim_generator import (
    configure_device_models,
    get_tango_device_server,
)


def main():
    sim_data_files = ["../tests/config_files/Weather.xmi"]
    model = configure_device_models(sim_data_files)
    TangoDeviceServers = get_tango_device_server(model, sim_data_files)
    server_run(TangoDeviceServers)


if __name__ == "__main__":
    main()
