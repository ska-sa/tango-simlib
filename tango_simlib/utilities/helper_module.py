######################################################################################### 
# Copyright 2017 SKA South Africa (http://ska.ac.za/)                                   #
#                                                                                       #
# BSD license - see LICENSE.txt for details                                             #
#########################################################################################
import os
import sys
import socket
import logging
import json

from tango import Database
from tango.server import command

MODULE_LOGGER = logging.getLogger(__name__)

DEFAULT_TANGO_DEVICE_COMMANDS = frozenset(['State', 'Status', 'Init'])
DEFAULT_TANGO_DEVICE_ATTRIBUTES = frozenset(['State', 'Status', 'AttributesNotAdded',
                                             'NumAttributesNotAdded'])
SIM_CONTROL_ADDITIONAL_IMPLEMENTED_ATTR = set([
    'Status',            # Tango library attribute
    'State',             # Tango library attribute
    'attribute_name',    # Attribute indentifier for attribute to be controlled
    'pause_active'       # Flag for pausing the model updates
    ])

# Mandatory parameters required to create a well configure Tango attribute.
DEFAULT_TANGO_ATTRIBUTE_PARAMETER_TEMPLATE = {
    'abs_change': '',
    'archive_abs_change': '',
    'archive_period': '',
    'archive_rel_change': '',
    'data_format': '',
    'format': '',
    'data_type': '',
    'delta_t': '',
    'delta_val': '',
    'description': '',
    'display_level': '',
    'enum_lables': [],
    'event_period': '',
    'label': '',
    'max_alarm': '',
    'max_warning': '',
    'max_dim_x': '',
    'max_dim_y': '',
    'max_value': '',
    'min_alarm': '',
    'min_value': '',
    'min_warning': '',
    'name': '',
    'period': '',
    'rel_change': '',
    'unit': '',
    'update_period': '',
    'writable': ''
}

TANGO_NOT_SPECIFIED_PROPS = ['Not specified', 'No display unit', 'No standard unit']

DEFAULT_CMD_PROPS = ('name', 'doc_in', 'dtype_in', 'doc_out', 'dtype_out')

def get_server_name():
    """Gets the TANGO server name from the command line arguments

    Returns
    -------
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
    executable_name = os.path.split(sys.argv[0])[-1].split('.')[0]
    server_name = executable_name + '/' + sys.argv[1]
    return server_name

def get_file_name():
    """Gets the db file name from the command line arguments

    Returns
    -------
    file_name : str
        file used as tango database
    """
    for val in sys.argv:
        if val.startswith('-file='):
            return val.split('=')[1]
    return None

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

def generate_cmd_handler(model, action_name, action_handler):
        def cmd_handler(tango_device, input_parameters=None):
            return action_handler(tango_dev=tango_device, data_input=input_parameters)

        cmd_handler.__name__ = action_name
        cmd_info_copy = model.sim_actions_meta[action_name].copy()
        # Delete all the keys that are not part of the Tango command parameters.
        cmd_info_copy.pop('name')
        for prop_key in model.sim_actions_meta[action_name]:
            if prop_key not in DEFAULT_CMD_PROPS:
                MODULE_LOGGER.warning(
                    "Warning! Property %s is not a tango command prop", prop_key)
                cmd_info_copy.pop(prop_key)
        """
        The command method signature:
        command(f=None, dtype_in=None, dformat_in=None, doc_in="",
                dtype_out=None, dformat_out=None, doc_out="", green_mode=None)
        """
        return command(f=cmd_handler, **cmd_info_copy)

# JSON `load` and `loads` equivalents, that force all strings to be returned
# as byte strings, rather than unicode.  This is critical for fields that will
# be used by TANGO, as it breaks with unicode strings.
# Solution from:  https://stackoverflow.com/a/33571117

def json_load_byteified(file_handle):
    """Similar to json.load(), but forces str instead of unicode strings."""
    return _byteify(
        json.load(file_handle, object_hook=_byteify),
        ignore_dicts=True
    )

def json_loads_byteified(json_text):
    """Similar to json.loads(), but forces str instead of unicode strings."""
    return _byteify(
        json.loads(json_text, object_hook=_byteify),
        ignore_dicts=True
    )

def _byteify(data, ignore_dicts=False):
    """If this is a unicode string, return its string representation."""
    if isinstance(data, unicode):
        return data.encode('utf-8')
    # if this is a list of values, return list of byteified values
    if isinstance(data, list):
        return [_byteify(item, ignore_dicts=True) for item in data]
    # if this is a dictionary, return dictionary of byteified keys and values
    # but only if we haven't already byteified it
    if isinstance(data, dict) and not ignore_dicts:
        return {
            _byteify(key, ignore_dicts=True): _byteify(value, ignore_dicts=True)
            for key, value in data.iteritems()
        }
    # if it's anything else, return it in its original form
    return data
