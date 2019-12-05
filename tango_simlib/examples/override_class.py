#########################################################################################
# Copyright 2017 SKA South Africa (http://ska.ac.za/)                                   #
#                                                                                       #
# BSD license - see LICENSE.txt for details                                             #
#########################################################################################
"""
An example of the user-defined override class.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


from past.builtins import cmp
from future import standard_library
standard_library.install_aliases()


from builtins import object
import logging

from PyTango import DevState, Except, ErrSeverity

MODULE_LOGGER = logging.getLogger(__name__)


class WeatherSimError(Exception):
    """Raised when a Weather simulator action could not be executed.
    """


class VdsSimError(Exception):
    """Raised when a Video Display System simulator action could not be executed.
    """


class DishSimError(Exception):
    """Raised when a Dish simulator action could not be executed.
    """


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

    def action_add(self, model, tango_dev=None, data_input=None):
        """Add two or more numbers together and return their sum.
        """
        total = sum(data_input)
        return total

    def action_multiplystringby3(self, model, tango_dev=None, data_input=None):
        """Takes a string and multiplies it by a constant integer value of 3.
        """
        return 3 * data_input


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
            Optional argument, pan position; a stringified integer numeral.
        """
        try:
            quant_pan_position = model.sim_quantities["pan_position"]
        except KeyError:
            raise VdsSimError("pan_position quantity not found in the VDS model.")

        valid_pan_directions = ("left", "right", "to")
        pan_direction = data_input[0]
        if pan_direction not in valid_pan_directions:
            raise VdsSimError(
                "Invalid pan direction value ({}) provided. Valid "
                " pan directions are ({}).".format(pan_direction, valid_pan_directions)
            )

        if pan_direction == "to":
            try:
                pan_position = float(data_input[1])
            except IndexError:
                MODULE_LOGGER.debug("Optional argument 'pan_position' not provided.")
                pan_position = 0
            except ValueError:
                raise VdsSimError(
                    "Optional argument provided ({}) cannot be converted to a float".format(
                        data_input[1]
                    )
                )
        elif pan_direction == "left":
            pan_position = float(quant_pan_position.meta["min_value"])
        elif pan_direction == "right":
            pan_position = float(quant_pan_position.meta["max_value"])

        quant_pan_position.set_val(pan_position, model.time_func())

    def action_camerapoweron(self, model, tango_dev=None, data_input=None):
        """Switch camera electronics on or off.

        Parameters:
        -----------
        data_input[0] : str
            'on' or 'off' value.
        """
        camera_power_state = {"on": True, "off": False}
        try:
            quant_camera_power_on = model.sim_quantities["camera_power_on"]
        except KeyError:
            raise VdsSimError("'camera_power_on' quantity not found in the VDS model.")

        try:
            camera_power_state_value = camera_power_state[data_input.lower()]
        except KeyError:
            raise VdsSimError(
                "Invalid argument ({}) provided. Please provide a string of either"
                " {} value.".format(data_input, list(camera_power_state.keys()))
            )

        quant_camera_power_on.set_val(camera_power_state_value, model.time_func())

        if camera_power_state[data_input.lower()]:
            for quantity in list(model.sim_quantities.values()):
                quantity.default_val(model.time_func())
            tango_dev.set_state(DevState.ON)
        else:
            for quantity in list(model.sim_quantities.values()):
                quantity.set_val(None, model.time_func())
            tango_dev.set_state(DevState.OFF)

    def action_floodlighton(self, model, tango_dev=None, data_input=None):
        """Set floodlight to a on or off.

        Parameters:
        -----------
        data_input[0] : str
            'on' or 'off' value.
        """
        flood_lights_state = {"on": True, "off": False}
        try:
            quant_flood_lights_on = model.sim_quantities["flood_lights_on"]
        except KeyError:
            raise VdsSimError("'flood_lights_on' quantity not found in the VDS model.")

        try:
            flood_lights_state_value = flood_lights_state[data_input.lower()]
        except KeyError:
            raise VdsSimError(
                "Invalid argument ({}) provided. Please provide a string of either"
                " {} value.".format(data_input, list(flood_lights_state.keys()))
            )

        quant_flood_lights_on.set_val(flood_lights_state_value, model.time_func())

    def action_focus(self, model, tango_dev=None, data_input=None):
        """Focuses camera to a specified direction or specified position.

        Parameters:
        -----------
        data_input[0] : str
            focus direction e.g. 'far', 'near', 'to'.
        data_input[1] : str
            Optional argument, focus position; a stringified integer numeral.
        """
        try:
            quant_focus_position = model.sim_quantities["focus_position"]
        except KeyError:
            raise VdsSimError("focus_position quantity not found in the VDS model.")

        valid_focus_directions = ("far", "near", "to")
        focus_direction = data_input[0]
        if focus_direction not in valid_focus_directions:
            raise VdsSimError(
                "Invalid focus direction value ({}) provided. Valid focus"
                " directions are {}.".format(focus_direction, valid_focus_directions)
            )

        if focus_direction == "to":
            try:
                focus_position = float(data_input[1])
            except IndexError:
                MODULE_LOGGER.debug("Optional argument 'focus_position' not provided.")
                focus_position = 0
            except ValueError:
                raise VdsSimError(
                    "Optional argument provided ({}) cannot be converted to a float".format(
                        data_input[1]
                    )
                )
        elif focus_direction == "near":
            focus_position = float(quant_focus_position.meta["min_value"])
        elif focus_direction == "far":
            focus_position = float(quant_focus_position.meta["max_value"])

        quant_focus_position.set_val(focus_position, model.time_func())

    def action_presetclear(self, model, tango_dev=None, data_input=None):
        """Clear the specified preset.

        Parameters:
        -----------
        data_input[0] : str
            receptor name (from m000 to m063).
        """
        preset_id = self._format_receptor_name(data_input)
        try:
            del model.presets[preset_id]
        except KeyError:
            raise VdsSimError(
                "Receptor {} has no preset position values to clear.".format(data_input)
            )
        except AttributeError:
            raise VdsSimError(
                "No preset position values for receptor {}.".format(data_input)
            )

    def action_presetgoto(self, model, tango_dev=None, data_input=None):
        """Go to preset stored position(pan, tilt, zoom).

        Parameters:
        -----------
        data_input[0] : str
            receptor name (from m000 to m063).
        """
        preset_id = self._format_receptor_name(data_input)
        try:
            presets = model.presets[preset_id]
        except KeyError:
            raise VdsSimError(
                "There are no preset position values for receptor {}.".format(data_input)
            )
        except AttributeError:
            raise VdsSimError(
                "No preset position values set up previously for receptor {}.".format(
                    data_input
                )
            )

        for position in list(presets.keys()):
            try:
                model_quant = model.sim_quantities["%s_position" % position]
            except KeyError:
                MODULE_LOGGER.debug(
                    "%s_position quantity is not found in the VDS model.", position
                )
            else:
                model_quant.set_val(presets[position], model.time_func())

    def action_presetset(self, model, tango_dev=None, data_input=None):
        """Set the position which the camera is at currently as preset position.

        Parameters:
        -----------
        data_input[0] : str
            receptor name (from m000 to m063).
        """
        camera_positions = ("focus", "pan", "tilt", "zoom")
        model.presets = {}
        tmp_presets = {}
        preset_id = self._format_receptor_name(data_input)
        for position in camera_positions:
            try:
                quant_position = model.sim_quantities["%s_position" % position]
            except KeyError:
                MODULE_LOGGER.debug(
                    "%s_position quantity is not found in the VDS model.", position
                )
            else:
                quant_position_value = quant_position.last_val
                tmp_presets[position] = quant_position_value
        tmp_presets[preset_id] = tmp_presets
        model.presets.update(tmp_presets)

    def action_stop(self, model, tango_dev=None, data_input=None):
        """Stop camera."""
        pass

    def action_tilt(self, model, tango_dev=None, data_input=None):
        """Drive camera to a tilt direction or specified position.

        Parameters:
        -----------
        data_input[0] : str
            tilt_direction e.g. 'up', 'down', 'to'.
        data_input[1] : str
            Optional argument, tilt_position; a stringified integer numeral.
        """
        try:
            quant_tilt_position = model.sim_quantities["tilt_position"]
        except KeyError:
            raise VdsSimError("tilt_position quantity not found in the VDS model.")

        valid_tilt_directions = ("down", "to", "up")
        tilt_direction = data_input[0]
        if tilt_direction not in valid_tilt_directions:
            raise VdsSimError(
                "Invalid tilt direction value ({}) provided. Valid tilt directions are"
                " {}.".format(tilt_direction, valid_tilt_directions)
            )

        if tilt_direction == "to":
            try:
                tilt_position = float(data_input[1])
            except IndexError:
                MODULE_LOGGER.debug("Optional argument 'tilt_position' not provided")
                tilt_position = 0.0
            except ValueError:
                raise VdsSimError(
                    "Optional argument provided cannot be converted to a float.".format(
                        data_input[1]
                    )
                )
        elif tilt_direction == "down":
            tilt_position = float(quant_tilt_position.meta["min_value"])
        elif tilt_direction == "up":
            tilt_position = float(quant_tilt_position.meta["max_value"])

        quant_tilt_position.set_val(tilt_position, model.time_func())

    def action_zoom(self, model, tango_dev=None, data_input=None):
        """Zoom camera to a specified direction or specified position.

        Parameters:
        -----------
        data_input[0] : str
            zoom_direction e.g. 'tele', 'wide', 'to'.
        data_input[1] : str
            Optional argument, zoom_position; a stringified numeral.
        """
        try:
            quant_zoom_position = model.sim_quantities["zoom_position"]
        except KeyError:
            raise VdsSimError("zoom_position quantity not found in the VDS model.")

        valid_zoom_directions = ("tele", "to", "wide")
        zoom_direction = data_input[0]
        if zoom_direction not in valid_zoom_directions:
            raise VdsSimError(
                "Invalid zoom direction value ({}) provided. Valid"
                " zoom directions are {}.".format(zoom_direction, valid_zoom_directions)
            )

        if zoom_direction == "to":
            try:
                zoom_position = float(data_input[1])
            except IndexError:
                MODULE_LOGGER.debug("Optional argument 'zoom_position' not provided.")
                zoom_position = 0.0
            except ValueError:
                raise VdsSimError(
                    "Optional argument provided cannot be converted to a float.".format(
                        data_input[1]
                    )
                )
        elif zoom_direction == "wide":
            zoom_position = float(quant_zoom_position.meta["min_value"])
        elif zoom_direction == "tele":
            zoom_position = float(quant_zoom_position.meta["max_value"])

        quant_zoom_position.set_val(zoom_position, model.time_func())

    def action_trapupdate(self, model, tango_dev=None, data_input=None):
        """Update trap. this request is called by a script.

        Parameters:
        -----------
        data_input : str
            Trap update from a script (8, 'on').
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


class OverrideWeatherSimControl(object):
    """An example of the override class for the TANGO device class 'SimControl'.
    It provides all the implementations of the command handler functions for the
    commands required to stimulate a running TANGO device in real time.
    """

    def test_action_setattributemaxvalue(self, model, tango_dev=None, data_input=None):
        """This command sets an attribute value to its maximum value to set its quality to
        Alarm state to warning.
        """
        quantity_name = data_input
        try:
            simulated_quantity = model.sim_quantities[quantity_name]
        except KeyError:
            raise WeatherSimError(
                "Quantity {} not in the Weather model".format(quantity_name)
            )

        try:
            maximum_value = simulated_quantity.max_bound
        except AttributeError:
            raise WeatherSimError(
                "Quantity {} is a ConstantQuantity instance".format(simulated_quantity)
            )
        else:
            simulated_quantity.last_val = maximum_value

    def test_action_stimulateattributeconfigurationerror(
        self, model, tango_dev=None, data_input=None
    ):
        """This command sets the attribute maximum allowed value to be the same as that
        minimum allowed value.
        """
        quantity_name = data_input
        try:
            model.sim_quantities[quantity_name]
        except KeyError:
            raise WeatherSimError(
                "Quantity {} not in the Weather model".format(quantity_name)
            )
        else:
            tango_dev.get_attribute_config(quantity_name)[
                0
            ].max_value = tango_dev.get_attribute_config(quantity_name)[0].min_value

    def test_action_simulatefaultdevicestate(
        self, model, tango_dev=None, data_input=None
    ):
        """This command sets the current device state to fault/on."""
        if str(tango_dev.get_status()) in ["FAULT"]:
            tango_dev.set_state(DevState.ON)
        else:
            tango_dev.set_state(DevState.FAULT)

    def test_action_stopquantitysimulation(self, model, tango_dev=None, data_input=None):
        """Totally sets the simulated quantities` values to a constant value of zero."""
        for quantity in data_input:
            try:
                simulated_quantity = model.sim_quantities[quantity]
            except KeyError:
                raise WeatherSimError(
                    "Quantity {} not in the Weather model".format(quantity)
                )
            else:
                if hasattr(simulated_quantity, "max_bound"):
                    simulated_quantity.max_bound = 0.0
                else:
                    MODULE_LOGGER.debug(
                        "Quantity %s is not a GaussianSlewLimited" " instance.",
                        simulated_quantity,
                    )

    def test_action_stoprainfall(self, model, tango_dev=None, data_input=None):
        """Totally sets the simulated quantity rainfall to a constant value of zero."""
        try:
            quant_rainfall = model.sim_quantities["rainfall"]
        except KeyError:
            raise WeatherSimError("Quantity 'rainfall' is not in the Weather model")
        else:
            quant_rainfall.max_bound = 0.0

    def test_action_setoffwindstorm(self, model, tango_dev=None, data_input=None):

        try:
            quant_wind_speed = model.sim_quantities["wind_speed"]
        except KeyError:
            raise WeatherSimError("Quantity 'wind_speed' is not in the Weather model.")
        else:
            quant_wind_speed.max_bound = 1000.0 * float(
                quant_wind_speed.meta["max_value"]
            )
            quant_wind_speed.mean = 1000.0 * float(quant_wind_speed.meta["max_value"])

    def test_action_stopwindstorm(self, model, tango_dev=None, data_input=None):

        try:
            quant_wind_speed = model.sim_quantities["wind_speed"]
        except KeyError:
            raise WeatherSimError("Quantity 'wind_speed' is not in the Weather model.")
        else:
            quant_wind_speed.max_bound = float(quant_wind_speed.meta["max_bound"])
            quant_wind_speed.mean = 1.00

    def test_action_setoffrainstorm(self, model, tango_dev=None, data_input=None):

        try:
            quant_rainfall = model.sim_quantities["rainfall"]
        except KeyError:
            raise WeatherSimError("Quantity 'rainfall' is not in the Weather model.")
        else:
            quant_rainfall.max_bound = 1000.0 * float(quant_rainfall.meta["max_value"])
            quant_rainfall.mean = 1000.0 * float(quant_rainfall.meta["max_value"])

    def test_action_stoprainstorm(self, model, tango_dev=None, data_input=None):

        try:
            quant_rainfall = model.sim_quantities["rainfall"]
        except KeyError:
            raise WeatherSimError("Quantity 'rainfall' is not in the Weather model.")
        else:
            quant_rainfall.max_bound = float(quant_rainfall.meta["max_bound"])
            quant_rainfall.mean = 1.00


class OverrideDish(object):
    AZIM_DRIVE_MAX_RATE = 2.0
    ELEV_DRIVE_MAX_RATE = 1.0

    def _configureband(self, model, timestamp, band_number):
        _allowed_modes = ("STANDBY-FP", "OPERATE")
        dish_mode_quant = model.sim_quantities["dishMode"]
        current_mode_enum_val = dish_mode_quant.last_val
        current_mode_str_val = dish_mode_quant.meta["enum_labels"][
            int(current_mode_enum_val)
        ]
        if current_mode_str_val in _allowed_modes:
            set_mode = dish_mode_quant.meta["enum_labels"].index("CONFIG")
            model.sim_quantities["dishMode"].set_val(set_mode, float(timestamp))
            MODULE_LOGGER.info(
                "Configuring DISH to operate in frequency band {}.".format(band_number)
            )
            MODULE_LOGGER.info(
                "Done configuring DISH to operate in frequency band {}.".format(
                    band_number
                )
            )
            MODULE_LOGGER.info(
                "Dish reverting back to '{}' mode.".format(current_mode_str_val)
            )
            model.sim_quantities["dishMode"].set_val(
                current_mode_enum_val, model.time_func()
            )
        else:
            Except.throw_exception(
                "DISH Command Failed",
                "DISH is not in {} mode.".format(_allowed_modes),
                "ConfigureBand{}()".format(band_number),
                ErrSeverity.WARN,
            )

    def action_configureband1(self, model, tango_dev=None, data_input=None):
        """This command triggers the Dish to transition to the CONFIGURE Dish Element
        Mode, and returns to the caller. To configure the Dish to operate in frequency
        band 1. On completion of the band configuration, Dish will automatically
        revert to the previous Dish mode (OPERATE or STANDBY-FP).

        data_input: str
            timestamp
        """
        self._configureband(model, data_input, 1)

    def action_configureband2(self, model, tango_dev=None, data_input=None):
        """This command triggers the Dish to transition to the CONFIGURE Dish Element
        Mode, and returns to the caller. To configure the Dish to operate in frequency
        band 2. On completion of the band configuration, Dish will automatically
        revert to the previous Dish mode (OPERATE or STANDBY-FP).

        data_input: str
            timestamp
        """
        self._configureband(model, data_input, 2)

    def action_configureband3(self, model, tango_dev=None, data_input=None):
        """This command triggers the Dish to transition to the CONFIGURE Dish Element
        Mode, and returns to the caller. To configure the Dish to operate in frequency
        band 3. On completion of the band configuration, Dish will automatically
        revert to the previous Dish mode (OPERATE or STANDBY-FP).

        data_input: str
            timestamp
        """
        self._configureband(model, data_input, 3)

    def action_configureband4(self, model, tango_dev=None, data_input=None):
        """This command triggers the Dish to transition to the CONFIGURE Dish Element
        Mode, and returns to the caller. To configure the Dish to operate in frequency
        band 4. On completion of the band configuration, Dish will automatically
        revert to the previous Dish mode (OPERATE or STANDBY-FP).

        data_input: str
            timestamp
        """
        self._configureband(model, data_input, 4)

    def action_configureband5(self, model, tango_dev=None, data_input=None):
        """This command triggers the Dish to transition to the CONFIGURE Dish Element
        Mode, and returns to the caller. To configure the Dish to operate in frequency
        band 5. On completion of the band configuration, Dish will automatically
        revert to the previous Dish mode (OPERATE or STANDBY-FP).

        data_input: str
            timestamp
        """
        self._configureband(model, data_input, 5)

    def action_lowpower(self, model, tango_dev=None, data_input=None):
        """This command triggers the Dish to transition to the LOW power
        state. All subsystems go into a low power state to power only the
        essential equipment. Specifically the Helium compressor will be set
        to a low power consumption, and the drives will be disabled. When
        issued a STOW command while in LOW power, the DS controller
        should be able to turn the drives on, stow the dish and turn the
        drives off again. The purpose of this mode is to enable the
        observatory to perform power management (load curtailment), and
        also to conserve energy for non-operating dishes.

        data_input: None

        """
        _allowed_modes = ("STOW", "MAINTENANCE")
        dish_mode_quant = model.sim_quantities["dishMode"]
        current_mode_enum_val = dish_mode_quant.last_val
        current_mode_str_val = dish_mode_quant.meta["enum_labels"][
            int(current_mode_enum_val)
        ]
        if current_mode_str_val in _allowed_modes:
            power_state_quant = model.sim_quantities["powerState"]
            set_mode = power_state_quant.meta["enum_labels"].index("LOW")
            power_state_quant.set_val(set_mode, model.time_func())
            MODULE_LOGGER.info("Dish transitioning to LOW power state.")
        else:
            Except.throw_exception(
                "DISH Command Failed",
                "DISH is not in {} mode.".format(_allowed_modes),
                "LowPower()",
                ErrSeverity.WARN,
            )

    def action_setmaintenancemode(self, model, tango_dev=None, data_input=None):
        """This command triggers the Dish to transition to the MAINTENANCE
        Dish Element Mode, and returns to the caller. To go into a state that
        is safe to approach the Dish by a maintainer, and to enable the
        Engineering interface to allow direct access to low level control and
        monitoring by engineers and maintainers. This mode will also enable
        engineers and maintainers to upgrade SW and FW. Dish also enters
        this mode when an emergency stop button is pressed.

        data_input: None
        """
        _allowed_modes = ("STANDBY-LP", "STANDBY-FP")
        dish_mode_quant = model.sim_quantities["dishMode"]
        current_mode_enum_val = dish_mode_quant.last_val
        current_mode_str_val = dish_mode_quant.meta["enum_labels"][
            int(current_mode_enum_val)
        ]
        if current_mode_str_val in _allowed_modes:
            set_mode = dish_mode_quant.meta["enum_labels"].index("MAINTENANCE")
            model.sim_quantities["dishMode"].set_val(set_mode, model.time_func())
            MODULE_LOGGER.info("Dish transition to the OPERATE Dish Element mode.")
        else:
            Except.throw_exception(
                "DISH Command Failed",
                "DISH is not in {} mode.".format(_allowed_modes),
                "SetMaintenanceMode()",
                ErrSeverity.WARN,
            )

    def action_setoperatemode(self, model, tango_dev=None, data_input=None):
        """This command triggers the Dish to transition to the OPERATE Dish
        Element Mode, and returns to the caller. This mode fulfils the main
        purpose of the Dish, which is to point to designated directions while
        capturing data and transmitting it to CSP.

        data_input: None
        """
        _allowed_modes = "STANDBY-FP"
        dish_mode_quant = model.sim_quantities["dishMode"]
        current_mode_enum_val = dish_mode_quant.last_val
        current_mode_str_val = dish_mode_quant.meta["enum_labels"][
            int(current_mode_enum_val)
        ]
        if current_mode_str_val in _allowed_modes:
            set_mode = dish_mode_quant.meta["enum_labels"].index("OPERATE")
            model.sim_quantities["dishMode"].set_val(set_mode, model.time_func())
            MODULE_LOGGER.info("Dish transition to the OPERATE Dish Element Mode.")
        else:
            Except.throw_exception(
                "DISH Command Failed",
                "DISH is not in {} mode.".format(_allowed_modes),
                "SetOperateMode()",
                ErrSeverity.WARN,
            )

    def action_setstandbyfpmode(self, model, tango_dev=None, data_input=None):
        """This command triggers the Dish to transition to the STANDBY-FP Dish
        Element Mode, and returns to the caller. To prepare all subsystems
        for active observation, once a command is received by TM to go to the
        FULL_POWER mode.

        data_input: None
        """
        _allowed_modes = ("STANDBY-LP", "STOW", "OPERATE", "MAINTENANCE")
        dish_mode_quant = model.sim_quantities["dishMode"]
        current_mode_enum_val = dish_mode_quant.last_val
        current_mode_str_val = dish_mode_quant.meta["enum_labels"][
            int(current_mode_enum_val)
        ]
        if current_mode_str_val in _allowed_modes:
            set_mode = dish_mode_quant.meta["enum_labels"].index("STANDBY-FP")
            model.sim_quantities["dishMode"].set_val(set_mode, model.time_func())
            MODULE_LOGGER.info("Dish transition to the STANDBY-FP Dish Element Mode.")
        else:
            Except.throw_exception(
                "DISH Command Failed",
                "DISH is not in {} mode.".format(_allowed_modes),
                "SetStandbyFPMode()",
                ErrSeverity.WARN,
            )

    def action_setstandbylpmode(self, model, tango_dev=None, data_input=None):
        """This command triggers the Dish to transition to the STANDBY-LP Dish Element
        Mode, and returns to the caller. Standby_LP is the default mode when the Dish
        is configured for low power consumption, and is the mode wherein Dish ends after
        a start up procedure.

        data_input: None
        """
        _allowed_modes = (
            "OFF",
            "STARTUP",
            "SHUTDOWN",
            "STANDBY-LP",
            "STANDBY-FP",
            "MAINTENANCE",
            "STOW",
            "CONFIG",
            "OPERATE",
        )
        dish_mode_quant = model.sim_quantities["dishMode"]
        current_mode_enum_val = dish_mode_quant.last_val
        current_mode_str_val = dish_mode_quant.meta["enum_labels"][
            int(current_mode_enum_val)
        ]
        if current_mode_str_val in _allowed_modes:
            set_mode = dish_mode_quant.meta["enum_labels"].index("STANDBY-LP")
            model.sim_quantities["dishMode"].set_val(set_mode, model.time_func())
            MODULE_LOGGER.info("Dish transition to the STANDBY-LP Dish Element Mode.")
        else:
            Except.throw_exception(
                "DISH Command Failed",
                "DISH is not in {} mode.".format(_allowed_modes),
                "SetStandbyLPMode()",
                ErrSeverity.WARN,
            )

    def action_setstowmode(self, model, tango_dev=None, data_input=None):
        """This command triggers the Dish to transition to the STOW Dish
        Element Mode, and returns to the caller. To point the dish in a
        direction that minimises the wind loads on the structure, for survival
        in strong wind conditions. The Dish is able to observe in the stow
        position, for the purpose of transient detection.

        data_input: None
        """
        _allowed_modes = (
            "OFF",
            "STARTUP",
            "SHUTDOWN",
            "STANDBY-LP",
            "STANDBY-FP",
            "MAINTENANCE",
            "STOW",
            "CONFIG",
            "OPERATE",
        )
        dish_mode_quant = model.sim_quantities["dishMode"]
        current_mode_enum_val = dish_mode_quant.last_val
        current_mode_str_val = dish_mode_quant.meta["enum_labels"][
            int(current_mode_enum_val)
        ]
        if current_mode_str_val not in _allowed_modes:
            Except.throw_exception(
                "DISH Command Failed",
                "DISH is not in {} mode.".format(_allowed_modes),
                "SetStowMode()",
                ErrSeverity.WARN,
            )
        try:
            pointing_state_quant = model.sim_quantities["pointingState"]
        except KeyError:
            Except.throw_exception(
                "DISH Command Failed",
                "The quantity 'pointingState' is not in the Dish model.",
                "Slew()",
                ErrSeverity.WARN,
            )

        model_time = model.time_func()
        pointing_state_enum_val = pointing_state_quant.last_val
        pointing_state_str_val = pointing_state_quant.meta["enum_labels"][
            int(pointing_state_enum_val)
        ]
        if pointing_state_str_val != "STOW":
            set_mode = pointing_state_quant.meta["enum_labels"].index("STOW")
            pointing_state_quant.set_val(set_mode, model_time)
        else:
            Except.throw_exception(
                "DISH Command Failed",
                "Dish pointing state already in STOW mode.",
                "SetStowMode()",
                ErrSeverity.WARN,
            )

        model.sim_quantities["desiredElevation"].set_val(90, model_time)
        set_mode = dish_mode_quant.meta["enum_labels"].index("STOW")
        model.sim_quantities["dishMode"].set_val(set_mode, model_time)
        MODULE_LOGGER.info("Dish transition to the STOW Dish Element Mode.")

    def action_slew(self, model, tango_dev=None, data_input=None):
        """The Dish is tracking the commanded pointing positions within the
        specified TRACK pointing accuracy.

        data_input: list
            [Timestamp]
            [azimuth]
            [elevation]
        """
        _allowed_modes = "OPERATE"
        dish_mode_quant = model.sim_quantities["dishMode"]
        current_mode_enum_val = dish_mode_quant.last_val
        current_mode_str_val = dish_mode_quant.meta["enum_labels"][
            int(current_mode_enum_val)
        ]
        if current_mode_str_val not in _allowed_modes:
            Except.throw_exception(
                "DISH Command Failed",
                "DISH is not in {} mode.".format(_allowed_modes),
                "Slew()",
                ErrSeverity.WARN,
            )

        try:
            pointing_state_quant = model.sim_quantities["pointingState"]
        except KeyError:
            Except.throw_exception(
                "DISH Command Failed",
                "The quantity 'pointingState' is not in the Dish model.",
                "Slew()",
                ErrSeverity.WARN,
            )

        model_time = model.time_func()
        pointing_state_enum_val = pointing_state_quant.last_val
        pointing_state_str_val = pointing_state_quant.meta["enum_labels"][
            int(pointing_state_enum_val)
        ]
        if pointing_state_str_val != "SLEW":
            set_mode = pointing_state_quant.meta["enum_labels"].index("SLEW")
            pointing_state_quant.set_val(set_mode, model_time)
        else:
            Except.throw_exception(
                "DISH Command Failed",
                "Dish pointing state already in SLEW mode.",
                "Slew()",
                ErrSeverity.WARN,
            )

        model.sim_quantities["desiredAzimuth"].set_val(data_input[1], model_time)
        model.sim_quantities["desiredElevation"].set_val(data_input[2], model_time)
        model.sim_quantities["desiredPointing"].set_val(
            [data_input[1], data_input[2]], model_time
        )

    def pre_update(self, sim_model, sim_time, dt):
        MODULE_LOGGER.info("***Pre-updating from the override class***")
        pointing_state_quant = sim_model.sim_quantities["pointingState"]
        current_pnt_state_enum_val = pointing_state_quant.last_val
        current_pnt_state_str_val = pointing_state_quant.meta["enum_labels"][
            int(current_pnt_state_enum_val)
        ]

        if current_pnt_state_str_val == "READY":
            MODULE_LOGGER.info(
                "Skipping quantity updates. Dish quantity state" " already in READY mode."
            )
            return

        azim_slew_rate = self.AZIM_DRIVE_MAX_RATE
        elev_slew_rate = self.ELEV_DRIVE_MAX_RATE

        azim_max_slew = azim_slew_rate * dt
        elev_max_slew = elev_slew_rate * dt

        try:
            achieved_azim = sim_model.sim_quantities["achievedAzimuth"].last_val
            achieved_elev = sim_model.sim_quantities["achievedElevation"].last_val
            desired_azim = sim_model.sim_quantities["desiredAzimuth"].last_val
            desired_elev = sim_model.sim_quantities["desiredElevation"].last_val
        except KeyError:
            Except.throw_exception(
                "Dish pre-update method failed",
                "One of these quantities (achievedAzimuth, achievedElevation"
                ", desiredAzimuth, desiredElevation) is not in the Dish model.",
                "update()",
                ErrSeverity.WARN,
            )

        current_delta_azim = abs(achieved_azim - desired_azim)
        current_delta_elev = abs(achieved_elev - desired_elev)
        move_delta_azim = min(azim_max_slew, current_delta_azim)
        move_delta_elev = min(elev_max_slew, current_delta_elev)
        new_position_azim = (
            achieved_azim + cmp(desired_azim, achieved_azim) * move_delta_azim
        )
        sim_model.sim_quantities["achievedAzimuth"].set_val(new_position_azim, sim_time)
        new_position_elev = (
            achieved_elev + cmp(desired_elev, achieved_elev) * move_delta_elev
        )
        sim_model.sim_quantities["achievedElevation"].set_val(new_position_elev, sim_time)

        sim_model.sim_quantities["achievedPointing"].set_val(
            [
                sim_model.sim_quantities["achievedAzimuth"].last_val,
                sim_model.sim_quantities["achievedElevation"].last_val,
            ],
            sim_time,
        )

        if self._almost_equal(
            sim_model.sim_quantities["achievedAzimuth"].last_val,
            sim_model.sim_quantities["desiredAzimuth"].last_val,
        ) and self._almost_equal(
            sim_model.sim_quantities["achievedElevation"].last_val,
            sim_model.sim_quantities["desiredElevation"].last_val,
        ):
            pointing_state_quant.set_val(
                pointing_state_quant.meta["enum_labels"].index("READY"), sim_time
            )

    def _almost_equal(self, x, y, abs_threshold=1e-2):
        """Takes two values return true if they are almost equal"""
        return abs(x - y) <= abs_threshold
