#!/usr/bin/env python
from PyTango.server import server_run
from tango_simlib.tango_sim_generator import (configure_device_model, get_tango_device_server)


def main():
    sim_data_files = ['../tests/config_files/Weather.xmi', '../tests/config_files/Weather_SimDD_3.json']
    model = configure_device_model(sim_data_files)
    TangoDeviceServers = get_tango_device_server(model, sim_data_files)
    server_run(TangoDeviceServers)

if __name__ == "__main__":
    main()
