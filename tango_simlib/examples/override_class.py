#!/usr/bin/env python
###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2013 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################
"""
An example of the user-defined override class.
@author MeerKAT CAM team <cam@ska.ac.za>
"""

import logging

from PyTango import DevState

MODULE_LOGGER = logging.getLogger(__name__)

class OverrideWeather(object):
    """An example of the override class for the TANGO device class 'Weather'. It
    provides all the implementations of the command handler functions for the commands
    specified in the POGO generated XMI data description file.
    """
    def action_on(self, model, tango_dev=None, data_input=None):
        """Changes the State of the device to ON.
        """
        tango_dev.set_state(DevState.ON)

    def action_off(self, model, tango_dev=None, data_input=None):
        """Changes the State of the device to OFF.
        """
        tango_dev.set_state(DevState.OFF)

    def action_stoprainfall(self, model, tango_dev=None, data_input=None):
        """Totally sets the simulated quantity rainfall to a constant value of zero.
        """
        try:
            quant_rainfall = model.sim_quantities['rainfall']
        except KeyError:
            MODULE_LOGGER.debug("Quantity rainfall not in the model")
        else:
            quant_rainfall.max_bound = 0.0

    def action_add(self, model, tango_dev=None, data_input=None):
        """Add two or more numbers together and return their sum.
        """
        total = sum(data_input)
        return total

    def action_multiplystringby3(self, model, tango_dev=None, data_input=None):
        """Takes a string and multiplies it by a constant integer value of 3.
        """
        return 3 * data_input

    def action_stopquantitysimulation(self, model, tango_dev=None, data_input=None):
        """Totally sets the simulated quantities` values to a constant value of zero.
        """
        for quantity in data_input:
            try:
                simulated_quantity = model.sim_quantities[quantity]
            except KeyError:
                MODULE_LOGGER.debug("Quantity %s not in the model", quantity)
            else:
                if hasattr(simulated_quantity, 'max_bound'):
                    simulated_quantity.max_bound = 0.0
                else:
                    MODULE_LOGGER.debug("Quantity %s is not a GaussianSlewLimited"
                                        " instance.", simulated_quantity)


class OverrideVds(object):
    """An example of the override class for the TANGO device class 'MKATVDS'. It
    provides all the implementations of the command handler functions for the commands
    specified in the POGO generated XMI data description file.
    """
    def action_pan(self, model, tango_dev=None, data_input=None):
        """Drive camera to a pan direction(left or right) or pan to specified position.

        Parameters:
        -----------
        data_input[0] : str
            pan direction e.g. 'left', 'right', 'to'.
        data_input[1] : str
            pan position, a stringified numeral
        """
        pan_direction = data_input[0]
        try:
            quant_pan_position = model.sim_quantities['pan_position']
            if pan_direction in ['left', 'right', 'to']:
                if pan_direction == 'to':
                    try:
                        pan_position = int(data_input[1])
                    except IndexError:
                        MODULE_LOGGER("Optional argument not provided")
                        pan_position = 0
                    except ValueError:
                        MODULE_LOGGER("Optional argument provided cannot be converted"
                                      " to a number.")
                        pans_position = 0
                elif pan_direction == 'left':
                    pan_position = int(quant_pan_position.meta['min_value'])
                elif pan_direction == 'right':
                    pan_position = int(quant_pan_position.meta['max_value'])
            else:
                raise Exception("Invalid focus direction argument provided")
        except KeyError:
            raise Exception("Focus position quantity not found in the model")
        else:
            quant_pan_position.set_val(pan_position, model.time_func())

    def action_camerapoweron(self, model, tango_dev=None, data_input=None):
        """Switch camera electronics on or off

        Parameters:
        -----------
        data_input[0] : str
            'on' or 'off' value
        """
        camera_power_status = {'on': True, 'off': False}
        try:
            quant_camera_power = model.sim_quantities['camera_power_on']
        except KeyError:
            MODULE_LOGGER.debug("'camera_power_on' model quantity not found")
        else:
            try:
                quant_camera_power.set_val(camera_power_status[data_input.lower()],
                                           model.time_func())
            except KeyError:
                raise Exception("Invalid argument ({}) provided. Please provide a string"
                                " of either 'on' or 'off' value.".format(data_input))

    def action_floodlighton(self, model, tango_dev=None, data_input=None):
        """Set floodlight to a on or off.

        Parameters:
        -----------
        data_input[0] : str
            'on' or 'off' value
        """
        flood_lights_status = {'on': True, 'off': False}
        try:
            quant_flood_lights = model.sim_quantities['flood_lights_on']
        except KeyError:
            MODULE_LOGGER.debug("'flood_lights_on' model quantity not found")
        else:
            try:
                quant_flood_lights.set_val(flood_lights_status[data_input.lower()],
                                           model.time_func())
            except KeyError:
                raise Exception("Invalid argument ({}) provided. Please provide a string"
                                " of either 'on' or 'off'.".format(data_input))

    def action_focus(self, model, tango_dev=None, data_input=None):
        """Focuses camera to a specified direction or specified position.

        Parameters:
        -----------
        data_input[0] : str
            focus direction e.g. 'far', 'near', 'to'.
        data_input[1] : str
            focus position, a stringified numeral
        """
        focus_direction = data_input[0]
        try:
            quant_focus_position = model.sim_quantities['focus_position']
            if focus_direction in ['far', 'near', 'to']:
                if focus_direction == 'to':
                    try:
                        focus_position = int(data_input[1])
                    except IndexError:
                        MODULE_LOGGER("Optional argument not provided")
                        focus_position = 0
                    except ValueError:
                        MODULE_LOGGER("Optional argument provided cannot be converted"
                                      " to a number.")
                        focus_position = 0
                elif focus_direction == 'far':
                    focus_position = int(quant_focus_position.meta['max_value'])
                elif focus_direction == 'near':
                    focus_position = int(quant_focus_position.meta['min_value'])
            else:
                raise Exception("Invalid focus direction argument provided")
        except KeyError:
            raise Exception("Focus position quantity not found in the model")
        else:
            quant_focus_position.set_val(focus_position, model.time_func())

    def action_presetclear(self, model, tango_dev=None, data_input=None):
        """Clear the specified preset.

        Parameters:
        -----------
        data_input[0] : str
            receptor name (from m000 to m063)
        """
        preset_id = self._format_receptor_name(data_input)
        if hasattr(model, 'presets_dict'):
            try:
                if preset_id in model.presets_dict:
                    del model.presets_dict[preset_id]
                else:
                    MODULE_LOGGER.info("Preset id has no presets to clear")
            except AttributeError:
                MODULE_LOGGER.info("No presets to clear")

        else:
            raise Exception("No preset were setup previously")

    def action_presetgoto(self, model, tango_dev=None, data_input=None):
        """Go to preset stored position(pan, tilt, zoom).

        Parameters:
        -----------
        data_input[0] : str
            receptor name (from m000 to m063)
        """
        preset_id = self._format_receptor_name(data_input)
        if hasattr(model, 'presets_dict'):
            try:
                if preset_id in model.presets_dict:
                    for position_id in range(len(model.presets_dict[preset_id])):
                        model_quant = model.sim_quantities[
                            '%s_position' % model.position_lst[position_id]]
                        model_quant.set_val(model.presets_dict[preset_id][position_id],
                                            model.time_func())
                else:
                    MODULE_LOGGER.debug("No previous presets were setup")
            except AttributeError:
                MODULE_LOGGER.debug("Preset not set")
        else:
            raise Exception("No previous presets were setup")

    def action_presetset(self, model, tango_dev=None, data_input=None):
        """Set the position which the camera is at currently as preset position.

        Parameters:
        -----------
        data_input[0] : str
            receptor name (from m000 to m063)
        """
        model.presets_dict = {}
        model.preset_position_values_dict = {'pan': 0, 'tilt': 0, 'zoom': 0}
        model.position_lst = ['pan', 'tilt', 'zoom']

        quantity_value_list = []
        tmp_presets_dict = {}
        preset_id = self._format_receptor_name(data_input)
        try:
            for position in model.position_lst:
                quant_position = model.sim_quantities['%s_position' % position]
                quant_position_value = quant_position.last_val
                quantity_value_list.append(quant_position_value)
            tmp_presets_dict[preset_id] = quantity_value_list
            model.presets_dict.update(tmp_presets_dict)
        except KeyError:
            MODULE_LOGGER.debug("Preset not set for %s", preset_id)

    def action_stop(self, model, tango_dev=None, data_input=None):
        """Stop camera.
        """
        pass

    def action_tilt(self, model, tango_dev=None, data_input=None):
        """Drive camera to a tilt direction or specified position.

        Parameters:
        -----------
        data_input[0] : str
            tilt_direction e.g. 'up', 'down', 'to'.
        data_input[1] : str
            tilt_position, a stringified numeral
        """
        tilt_direction = data_input[0]
        try:
            quant_tilt_position = model.sim_quantities['tilt_position']
            if tilt_direction in ['down', 'to', 'up']:
                if tilt_direction == 'to':
                    try:
                        tilt_position = int(data_input[1])
                    except IndexError:
                        MODULE_LOGGER("Optional argument not provided")
                        tilt_position = 0
                    except ValueError:
                        MODULE_LOGGER("Optional argument provided cannot be converted"
                                      " to a number.")
                        tilt_position = 0
                elif tilt_direction == 'down':
                    tilt_position = int(quant_tilt_position.meta['min_value'])
                elif tilt_direction == 'up':
                    tilt_position = int(quant_tilt_position.meta['max_value'])
            else:
                raise Exception("Invalid tilt direction argument provided")
        except KeyError:
            raise Exception("Tilt position quantity not found in the model")
        else:
            quant_tilt_position.set_val(tilt_position, model.time_func())

    def action_zoom(self, model, tango_dev=None, data_input=None):
        """Zoom camera to a specified direction or specified position.

        Parameters:
        -----------
        data_input[0] : str
            zoom_direction e.g. 'tele', 'wide', 'to'.
        data_input[1] : str
            zoom_position, a stringified numeral
        """
        zoom_direction = data_input[0]
        try:
            quant_zoom_position = model.sim_quantities['zoom_position']
            if zoom_direction in ['tele', 'to', 'wide']:
                if zoom_direction == 'to':
                    try:
                        zoom_position = int(data_input[1])
                    except IndexError:
                        MODULE_LOGGER("Optional argument not provided")
                        zoom_position = 0
                    except ValueError:
                        MODULE_LOGGER("Optional argument provided cannot be converted"
                                      " to a number.")
                        zoom_position = 0
                elif zoom_direction == 'wide':
                    zoom_position = int(quant_zoom_position.meta['min_value'])
                elif zoom_direction == 'tele':
                    zoom_position = int(quant_zoom_position.meta['max_value'])
            else:
                raise Exception("Invalid zoom direction argument provided")
        except KeyError:
            raise Exception("Zoom position quantity not found in the model")
        else:
            quant_zoom_position.set_val(zoom_position, model.time_func())

    def action_trapupdate(self, model, tango_dev=None, data_input=None):
        """Update trap. this request is called by a script.

        Parameters:
        -----------
        data_input : str
            Trap update from a script (8, 'on')
        """
        pass

    def _format_receptor_name(self, receptor_name):
        """Format the receptor name by removing the first character(m).
        Parameters:
        -----------
        receptor_name : str
            receptor name e.g m001.
        """
        if receptor_name.startswith("m"):
            receptor_number = int(receptor_name.replace("m", ""))
        else:
            receptor_number = int(receptor_name)
        return receptor_number

