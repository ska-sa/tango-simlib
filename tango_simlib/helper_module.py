import os
import sys

import PyTango


def get_server_name():
    """Gets the TANGO server name from the command line arguments

    Returns
    =======
    server_name : str
        tango device server name

    Note
    ====
    Extract the Tango server_name or equivalent executable
    (i.e.sim_xmi_parser.py -> sim_xmi_parser or
    /usr/local/bin/mkat-tango-katcpdevice2tango-DS ->
    mkat-tango-katcpdevice2tango-DS) from the command line
    arguments passed, where sys.argv[1] is the server instance.

    """
    executable_name = os.path.split(sys.argv[0].split('.')[0])[1]
    server_name = executable_name + '/' + sys.argv[1]
    return server_name

def register_device(name, device_class, server_name, instance):
    dev_info = PyTango.DbDevInfo()
    dev_info.name = name
    dev_info._class = device_class
    dev_info.server = "{}/{}".format(server_name, instance)
    print """Attempting to register TANGO device {!r}
        class: {!r}  server: {!r}.""".format(
        dev_info.name, dev_info._class, dev_info.server)
    db = PyTango.Database()
    db.add_device(dev_info)

def put_device_property(dev_name, property_name, property_value):
    db = PyTango.Database()
    print "Setting device {!r} property {!r}: {!r}".format(
          dev_name, property_name, property_value)
    db.put_device_property(dev_name, {property_name: property_value})
