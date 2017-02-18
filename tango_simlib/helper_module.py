import os
import sys
import socket

from PyTango import Database


DEFAULT_TANGO_DEVICE_COMMANDS = frozenset(['State', 'Status', 'Init'])
DEFAULT_TANGO_DEVICE_ATTRIBUTES = frozenset(['State', 'Status'])
SIM_CONTROL_ADDITIONAL_IMPLEMENTED_ATTR = set([
    'Status',   # Tango library attribute
    'State',    # Tango library attribute
    'attribute_name',    # Attribute indentifier for attribute to be controlled
    'pause_active',    # Flag for pausing the model updates
    'control_attribute_list_names',  # List of attributes to control
    ])


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

def append_device_to_db_file(server, instance, device, db_file_name,
                             tangoclass=None, properties={}):
    """Generate a database file corresponding to the given arguments."""
    if not tangoclass:
        tangoclass = server
    # Open the file
    with open(db_file_name, 'a') as f:
        f.write("/".join((server, instance, "DEVICE", tangoclass)))
        f.write(': "' + device + '"\n')
    # Create database
    db = Database(db_file_name)
    # Patched the property dict to avoid a PyTango bug
    patched = dict((key, value if value != '' else ' ')
                   for key, value in properties.items())
    # Write properties
    db.put_device_property(device, patched)
    return db

def get_port():
    sock = socket.socket()
    sock.bind(('', 0))
    res = sock.getsockname()[1]
    del sock
    return res

def get_host_address():
    host_name = socket.gethostname()
    return host_name
