#!/usr/bin/env python
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

MODULE_LOGGER = logging.getLogger(__name__)
EXPECTED_SIMULATION_PARAMETERS = {
    'GaussianSlewLimited':
        ['min_bound', 'max_bound', 'max_slew_rate', 'mean', 'std_dev',
         'quantity_simulation_type', 'update_period'],
    'ConstantQuantity':
        ['quantity_simulation_type', 'initial_value']}


class SimddParser(object):

    def __init__(self):
        """Parser class handling a simulator description datafile in json format.

        Creating an instance of this class requires calling :meth:`parse` method
        afterwards to extract all the provided tango attributes, commands,
        device property and device override class information from the specified
        file. The formated data is a dict structure and can be obtained using
        :meth:`get_reformatted_device_attr_metadata`,
        :meth:`get_reformatted_cmd_metadata`,
        :meth:`get_reformatted_properties_metadata` and
        :meth:`get_reformatted_override_metadata`.

        """
        # Simulator decription datafile in json format
        self.data_description_file_name = ''
        self.device_class_name = ''
        self._device_attributes = {}
        """The Data structure format is a dict containing attribute info in a dict

        e.g.
        {'temperature': {
            'abs_change': '0.5',
            'archive_abs_change': '0.5',
            'archive_period': '1000',
            'archive_rel_change': '10',
            'data_format': '',
            'data_type': PyTango._PyTango.CmdArgType.DevDouble,
            'delta_t': '1000',
            'delta_val': '0.5',
            'description': 'Current temperature outside near the telescope.',
            'display_level': 'OPERATOR',
            'event_period': '1000',
            'label': 'Outside Temperature',
            'max_alarm': '50',
            'max_bound': '50',
            'max_dim_x': '1',
            'max_dim_y': '0',
            'max_slew_rate': '1',
            'max_value': '51',
            'mean': '25',
            'min_alarm': '-9',
            'min_bound': '-10',
            'min_value': '-10',
            'name': 'temperature',
            'quantity_simulation_type': 'GaussianSlewLimited',
            'period': '1000',
            'rel_change': '10',
            'unit': 'Degrees Centrigrade',
            'update_period': '1',
            'writable': 'READ'},
        }

        """
        self._device_commands = {}
        """
        The Data structure format is a dict containing command info in a dict

        e.g.
        {'On': {
        'actions': [{'behaviour': 'output_return',
                     'source_variable': 'temporary_variable'}],
        'description': 'Turns On Device',
        'dformat_in': '',
        'dformat_out': '',
        'doc_in': 'No input parameter',
        'doc_out': 'Command responds',
        'dtype_in': PyTango._PyTango.CmdArgType.DevVoid,
        'dtype_out': PyTango._PyTango.CmdArgType.DevString,
        'name': 'On',
        'override_handler': 'False'},
        }
        """
        self._device_properties = {}
        """
        Data structure format is a list containing device property info in a dict

        e.g.
        {'sim_data_description_file': {
            'DefaultPropValue': '',          # The key was changed from 'default_value'
                                             # so as to have the same data structures
                                             # across all the three parsers.
            'name': 'sim_data_description_file',
            'type': 'string'},
        }

        """
        self._device_override_class = {}

    def parse(self, simdd_json_file):
        """
        Read simulator description data from json file into `self._device_properties`

        Stores all the simulator description data from the json file into
        appropriate attribute, command and device property data structures.
        Loops through the json object elements and updates description
        information of dynamic/attributes into `self._device_attributes`,
        commands into `self._device_commands`, and device_properties into
        `self._device_properties`.

        Parameters
        ----------
        simdd_json_file: str
            Name of simulator descrition data file

        Notes
        -----
        - Data structures, are type dict with dictionary elements keyed with
          element name and values must be the corresponding data value.

        """
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
        """
        Extract description data from the simdd json element

        Parameters
        ----------

        elements: list
            List of device data elements with items in unicode format
        e.g.
        [{
            "basicAttributeData": {
                "name": "temperature",
                "unit": "Degrees Centrigrade",
                "label": "Outside Temperature",
                "description": "Current temperature outside near the telescope.",
                "data_type": "Double",
                "data_format": "",
                "delta_t": "1000",
                "delta_val": "0.5",
                "data_shape": {
                    "max_dim_x": "1",
                    "max_dim_y": "0"
                },
                "attributeErrorChecking": {
                    "min_value": "-10",
                    "max_value": "51",
                    "min_alarm": "-9",
                    "max_alarm": "50"
                },
                "attributeInterlocks": {
                    "writable": "READ"
                },
                "dataSimulationParameters": {
                    "quantity_simulation_type": "GaussianSlewLimited",
                    "min_bound": "-10",
                    "max_bound": "50",
                    "mean": "25",
                    "max_slew_rate": "1",
                    "update_period": "1",
                    "std_dev": "5"
                },
                "attributeControlSystem": {
                    "display_level": "OPERATOR",
                    "period": "1000",
                    "EventSettings": {
                        "eventArchiveCriteria": {
                            "archive_abs_change": "0.5",
                            "archive_period": "1000",
                            "archive_rel_change": "10"
                        },
                        "eventCrateria": {
                            "abs_change": "0.5",
                            "event_period": "1000",
                            "rel_change": "10"
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
                element_params = self.get_reformated_data(element_info, element_type)
                if 'Attributes' in element_type:
                    device_dict[str(name)] = dict(params_template.items() +
                                                  element_params.items())
                else:
                    device_dict[str(name)] = element_params
        return device_dict

    def get_reformated_data(self, sim_device_element_info, element_type):
        """Helper function for flattening the data dicts to be more readable

        Parameters
        ----------
        sim_device_info: dict
            Data element Dict
        e.g.
        {"basicAttributeData": {
                "name": "temperature",
                "unit": "Degrees Centrigrade",
                "label": "Outside Temperature",
                "description": "Current temperature outside near the telescope.",
                "data_type": "Double",
                "data_format": "",
                "delta_t": "1000",
                "delta_val": "0.5",
                "data_shape": {
                    "max_dim_x": "1",
                    "max_dim_y": "0"
                },
                "attributeErrorChecking": {
                    "min_value": "-10",
                    "max_value": "51",
                    "min_alarm": "-9",
                    "max_alarm": "50"
                },
                "attributeInterlocks": {
                    "writable": "READ"
                },
                "dataSimulationParameters": {
                    'quantity_simulation_type': 'GaussianSlewLimited',
                    "min_bound": "-10",
                    "max_bound": "50",
                    "mean": "25",
                    "max_slew_rate": "1",
                    "update_period": "1"
                },
                "attributeControlSystem": {
                    "display_level": "OPERATOR",
                    "period": "1000",
                    "EventSettings": {
                        "eventArchiveCriteria": {
                            "archive_abs_change": "0.5",
                            "archive_period": "1000",
                            "archive_rel_change": "10"
                        },
                        "eventCrateria": {
                            "abs_change": "0.5",
                            "event_period": "1000",
                            "rel_change": "10"
                        }
                    }
                }
            }
        }

        Return
        ------
        items : dict
            A more formatted and easy to read dictionary
        e.g.

        {
            'abs_change': '0.5',
            'archive_abs_change': '0.5',
            'archive_period': '1000',
            'archive_rel_change': '10',
            'data_format': '',
            'data_type': PyTango._PyTango.CmdArgType.DevDouble,
            'delta_t': '1000',
            'delta_val': '0.5',
            'description': 'Current temperature outside near the telescope.',
            'display_level': 'OPERATOR',
            'event_period': '1000',
            'label': 'Outside Temperature',
            'max_alarm': '50',
            'max_bound': '50',
            'max_dim_x': '1',
            'quantity_simulation_type': 'GaussianSlewLimited',
            'max_dim_y': '0',
            'max_slew_rate': '1',
            'max_value': '51',
            'mean': '25',
            'min_alarm': '-9',
            'min_bound': '-10',
            'min_value': '-10',
            'name': 'temperature',
            'period': '1000',
            'rel_change': '10',
            'unit': 'Degrees Centrigrade',
            'update_period': '1',
            'writable': 'READ'
        }
        """
        def expand(value):
            """Method to expand values of a value if it is an instance of dict"""
            # Recursively call get_reformated_data if value is still a dict
            return [(param_name, param_val)
                    for param_name, param_val in self.get_reformated_data(
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
                        val = getattr(CmdArgType, "Dev%s" % str(item[1]))
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
                    val = getattr(CmdArgType, "Dev%s" % str(param_val))
                else:
                    val = str(param_val)
                formated_info[str(param_name)] = val
        return formated_info

    def get_reformatted_device_attr_metadata(self):
        """Returns a more formatted attribute data structure in a format of dict"""
        return self._device_attributes

    def get_reformatted_cmd_metadata(self):
        """Returns a more formatted command data structure in a format of dict"""
        return self._device_commands

    def get_reformatted_properties_metadata(self, property_group):
        """Returns a more formatted device prop data structure in a format of dict"""
        return self._device_properties

    def get_reformatted_override_metadata(self):
        """Returns a more formatted device override info data structure in a format of a
        dict.
        """
        return self._device_override_class

