import os
import sys
import errno
import shutil
import tempfile

from PyTango import Database

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

def generate_db_file(server, instance, device, directory='',
                     tangoclass=None, properties={}):
    """Generate a database file corresponding to the given arguments."""
    if not tangoclass:
        tangoclass = server
    # Open the file
    db_file = os.path.join(directory, '%s_tango.db' % server)
    with open(db_file, 'a') as f:
        f.write("/".join((server, instance, "DEVICE", tangoclass)))
        f.write(': "' + device + '"\n')
    # Create database
    db = Database(db_file)
    # Patched the property dict to avoid a PyTango bug
    patched = dict((key, value if value != '' else ' ')
                   for key, value in properties.items())
    # Write properties
    db.put_device_property(device, patched)
    return db
