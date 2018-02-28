###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2013 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################
"""This module performs the parsing of the Simulator Description Datafile,
containing the information needed to instantiate a useful device simulator.
@author MeerKAT CAM team <cam@ska.ac.za>
"""
import logging
import json
import pkg_resources

from PyTango._PyTango import CmdArgType, AttrDataFormat
from jsonschema import validate

from tango_simlib import helper_module
from base_parser import Parser

MODULE_LOGGER = logging.getLogger(__name__)
EXPECTED_SIMULATION_PARAMETERS = {
    'GaussianSlewLimited':
        ['min_bound', 'max_bound', 'max_slew_rate', 'mean', 'std_dev',
         'quantity_simulation_type', 'update_period'],
    'ConstantQuantity':
        ['quantity_simulation_type', 'initial_value']}


class SimddParser(Parser):
    """Parses the SimDD JSON file.

    Attributes
    ----------
    data_description_file_name: str

    device_class_name: str

    """
    def __init__(self):
        super(SimddParser, self).__init__() 
        self._device_override_class = {}

    def parse(self, simdd_json_file):
        '''Read simulator description data from json file.

        Stores all the simulator description data from the json file into appropriate
        attribute, command and device property data structures.

        Parameters
        ----------
        simdd_json_file: str
            Name of simulator descrition data file

        Notes
        =====
        - Data structures, are type dict with dictionary elements keyed with element name
        and values must be the corresponding data value.

        '''
        simdd_schema_file = pkg_resources.resource_filename(
                'tango_simlib', 'SIMDD.schema')
        with open(simdd_schema_file) as simdd_schema:
            schema_data = json.load(simdd_schema)
        self.data_description_file_name = simdd_json_file
        with open(simdd_json_file) as simdd_file:
            device_data = json.load(simdd_file)
        validate(device_data, schema_data)
        for data_component, elements in device_data.items():
            if data_component == 'class_name':
                self.device_class_name = str(elements)
            elif data_component == 'dynamicAttributes':
                attribute_info = self.get_device_data_components_dict(
                        elements, data_component)
                self._device_attributes.update(attribute_info)
            elif data_component == 'commands':
                command_info = self.get_device_data_components_dict(
                        elements, data_component)
                self._device_commands.update(command_info)
            elif data_component == 'deviceProperties':
                device_prop_info = self.get_device_data_components_dict(
                        elements, data_component)
                self._device_properties.update(device_prop_info)
            elif data_component == 'class_overrides':
                device_prop_info = self.get_device_data_components_dict(
                        elements, data_component)
                self._device_override_class.update(device_prop_info)

    def get_device_data_components_dict(self, elements, element_type):
        """Extract description data from the simdd json element

        Parameters
        ----------
        elements: list
            List of device data elements with items in unicode format
        e.g.
            [
                {
                    'basicAttributeData': {
                        'name': '<attribute-name>',
                        'unit': '',
                        'label': '',
                        'description': '',
                        'data_type': '<PyTango._PyTango.CmdArgType>',
                        'data_format': '<PyTango._PyTango.AttrDataFormat>',
                        'delta_t': '',
                        'delta_val': '',
                        'data_shape': {
                            'max_dim_x': '<int>',
                            'max_dim_y': '<int>'
                        },
                        'attributeErrorChecking': {
                            'min_value': '',
                            'max_value': '',
                            'min_alarm': '',
                            'max_alarm': ''
                        },
                        'attributeInterlocks': {
                            'writable': ''
                        },
                        'dataSimulationParameters': {
                            'quantity_simulation_type': 'GaussianSlewLimited',
                            'min_bound': '-10',
                    'max_bound': '50',
                    'mean': '25',
                    'max_slew_rate': '1',
                    'update_period': '1',
                    'std_dev': '5'
                },
                'attributeControlSystem': {
                    'display_level': 'OPERATOR',
                    'period': '1000',
                    'EventSettings': {
                        'eventArchiveCriteria': {
                            'archive_abs_change': '0.5',
                            'archive_period': '1000',
                            'archive_rel_change': '10'
                        },
                        'eventCrateria': {
                            'abs_change': '0.5',
                            'event_period': '1000',
                            'rel_change': '10'
                        }
                    }
                }
            }
        }]

        Returns
        -------
            device_dict: dict
                device data dictionary in the format of
                `self._device_attributes` or `self._device_commands`

        """
        device_dict = dict()
        params_template = helper_module.DEFAULT_TANGO_ATTRIBUTE_PARAMETER_TEMPLATE.copy()
        for element_data in elements:
            for element_info in element_data.values():
                name = element_info['name']
                element_params = self._get_reformatted_data(element_info, element_type)
                if 'Attributes' in element_type:
                    device_dict[str(name)] = dict(params_template.items() +
                                                  element_params.items())
                else:
                    device_dict[str(name)] = element_params
        return device_dict

    def _get_reformatted_data(self, sim_device_element_info, element_type):
        """Helper function for flattening the data dicts to be more readable.

        Parameters
        ----------
        sim_device_info: dict
            Data element Dict
        e.g.
            {
                'basicAttributeData': {
                    'name': '<attribute-name>',
                    'unit': '',
                    'label': '',
                    'description': '',
                    'data_type': '<tango._tango.CmdArgType>',
                    'data_format': '',
                    'delta_t': '',
                    'delta_val': '',
                    'data_shape': {
                        'max_dim_x': '<int>',
                        'max_dim_y': '<int>'
                    },
                    'attributeErrorChecking': {
                        'min_value': '',
                        'max_value': '',
                        'min_alarm': '',
                        'max_alarm': ''
                    },
                    'attributeInterlocks': {
                        'writable': ''
                    },
                    'dataSimulationParameters': {
                        'quantity_simulation_type': '<Quantity-subclass>',
                        'min_bound': '',
                        'max_bound': '',
                        'mean': '',
                        'max_slew_rate': '',
                        'update_period': ''
                    },
                    'attributeControlSystem': {
                        'display_level': '',
                        'period': '',
                        'EventSettings': {
                            'eventArchiveCriteria': {
                                'archive_abs_change': '',
                                'archive_period': '',
                                'archive_rel_change': ''
                            },
                           'eventCrateria': {
                                'abs_change': '',
                                'event_period': '',
                                'rel_change': ''
                            }
                        }
                    }
                }
            }

        Returns
        -------
        items : dict
            A more formatted and easy to read dictionary.

        e.g.
            {
                'abs_change': '',
                'archive_abs_change': '',
                'archive_period': '',
                'archive_rel_change': '',
                'data_format': '',
                'data_type': <tango._tango.CmdArgType>,
                'delta_t': '',
                'delta_val': '',
                'description': '',
                'display_level': '',
                'event_period': '',
                'label': '',
                'max_alarm': '',
                'max_bound': '',
                'max_dim_x': '<int>','
                'quantity_simulation_type': '<Quantity-subclass>',
                'max_dim_y': '<int>',
                'max_slew_rate': '',
                'max_value': '',
                'mean': '',
                'min_alarm': '',
                'min_bound': '',
                'min_value': '',
                'name': '<attribute-name>',
                'period': '',
                'rel_change': '',
                'unit': '',
                'update_period': '',
                'writable': ''
            }

        """
        def expand(value):
            """Method to expand values of a value if it is an instance of dict."""
            # Recursively call get_reformatted_data if value is still a dict
            return [(param_name, param_val)
                    for param_name, param_val in self._get_reformatted_data(
                    value, element_type).items()]

        formated_info = dict()
        for param_name, param_val in sim_device_element_info.items():
            if isinstance(param_val, dict):
                if 'dataSimulationParameters' in param_name:
                    try:
                        sim_type = param_val['quantity_simulation_type']
                    except ValueError:
                        raise ValueError("{} with name {} has no quantity "
                                         "simulation type specified".format(
                                             str(element_type),
                                             str(sim_device_element_info['name'])))
                    for sim_param in param_val:
                        try:
                            assert str(sim_param) in (
                                    EXPECTED_SIMULATION_PARAMETERS[sim_type])
                        except AssertionError:
                            raise ValueError("{} with name {} has "
                                             "unexpected simulation parameter {}"
                                             .format(
                                                 str(element_type),
                                                 str(sim_device_element_info['name']),
                                                 str(sim_param)))

                for item in expand(param_val):
                    property_key = str(item[0])
                    # Since the data type specified in the SIMDD is a string format
                    # e.g. String, it is require in Tango device as a CmdArgType
                    # i.e. PyTango._PyTango.CmdArgType.DevString
                    if property_key in ['dtype_in', 'dtype_out']:
                        # Here we extract the cmdArgType obect since
                        # for later when creating a Tango command,
                        # data type is required in this format.
                        val = getattr(CmdArgType, 'Dev%s' % str(item[1]))
                        formated_info[property_key] = val
                    elif property_key in ['dformat_in', 'dformat_out']:
                        val = getattr(AttrDataFormat, str(item[1]).upper())
                        formated_info[property_key] = val
                    else:
                        formated_info[property_key] = str(item[1])
            elif param_name in ['actions']:
                actions = []
                for item in param_val:
                    string_items = dict()
                    for key, value in item.iteritems():
                        string_items[str(key)] = str(value)
                    actions.append(string_items)
                formated_info['actions'] = actions
            else:
                # Since the data type specified in the SIMDD is a string format
                # e.g. Double, it is require in Tango device as a CmdArgType
                # i.e. PyTango._PyTango.CmdArgType.DevDouble
                if str(param_name) in ['data_type']:
                    # Here we extract the cmdArgType obect since
                    # for later when creating a Tango attibute,
                    # data type is required in this format.
                    val = getattr(CmdArgType, 'Dev%s' % str(param_val))
                elif str(param_name) in ['DefaultPropValue']:
                    # Default property value can be an string, number and array
                    # NB: It is also an optional parameter
                    val = param_val
                else:
                    val = str(param_val)
                formated_info[str(param_name)] = val
        return formated_info

    def get_device_attribute_metadata(self):
        """Returns a more formatted attribute data structure in a format of dict.

        e.g.
            {
                '<attribute-name>': {
                    'abs_change': '',
                    'archive_abs_change': '',
                    'archive_period': '',
                    'archive_rel_change': '',
                    'data_format': '',
                    'data_type': <tango._tango.CmdArgType>,
                    'delta_t': '',
                    'delta_val': '',
                    'description': '',
                    'display_level': '',
                    'event_period': '',
                    'label': '',
                    'max_alarm': '',
                    'max_bound': '',
                    'max_dim_x': '<int>',
                    'max_dim_y': '<int>',
                    'max_slew_rate': '',
                    'max_value': '',
                    'mean': '',
                    'min_alarm': '',
                    'min_bound': '',
                    'min_value': '',
                    'name': '<attribute-name>',
                    'quantity_simulation_type': '<Quantity-subclass',
                    'period': '',
                    'rel_change': '',
                    'unit': '',
                    'update_period': '',
                    'writable': ''},
            }
        """
        return self._device_attributes

    def get_device_command_metadata(self):
        """Returns a more formatted command data structure in a format of dict.

        e.g.
            {
                '<command-name>': {
                    'actions': [
                        {
                            'behaviour': '',
                            'source_variable': ''
                        }
                    ],
                    'description': '',
                    'dformat_in': '',
                    'dformat_out': '',
                    'doc_in': '',
                    'doc_out': '',
                    'dtype_in': <tango._tango.CmdArgType>,
                    'dtype_out': <tango._tango.CmdArgType>,
                    'name': '<command-name>',
                    'override_handler': '<boolean>'},
            }
        """
        return self._device_commands

    def get_device_properties_metadata(self, property_group):
        """Returns a more formatted device prop data structure in a format of dict.

        e.g.
            {
                '<property-name>': {
                    'DefaultPropValue': '',  # The key was changed from 'default_value'
                                             # so as to have the same data structures
                                             # across all the three parsers.
                    'name': '<property-name>',
                    'type': '<data-type'},
        }

        """
        return self._device_properties

    def get_device_cmd_override_metadata(self):
        """Returns more formatted device override info data structure in dict format.
        
        e.g.
            {
                'Sim_<class-name>_Override': {
                    'class_name': '<override-class-name>',
                    'module_directory': '<absolute-path>',
                    'module_name': '<module_name>',
                    'name': 'Sim_<class-name>_Override'
                }
            }
        """
        return self._device_override_class
