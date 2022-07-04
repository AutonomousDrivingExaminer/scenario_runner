#!/usr/bin/env python

# Copyright (c) 2020 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

"""
This module provides a weather class and py_trees behavior
to simulate weather in CARLA according to the astronomic
behavior of the sun.
"""

import py_trees
import carla

from srunner.scenariomanager.carla_data_provider import CarlaDataProvider


class RouteLightsBehavior(py_trees.behaviour.Behaviour):

    """
    Behavior responsible for turning the street lights on and off depending on the weather conditions.
    Only those around the ego vehicle will be turned on, regardless of weather conditions
    """
    SUN_ALTITUDE_THRESHOLD_1 = 15
    SUN_ALTITUDE_THRESHOLD_2 = 165

    # For higher fog and cloudness values, the amount of light in scene starts to rapidly decrease
    CLOUDINESS_THRESHOLD = 95
    FOG_THRESHOLD = 40

    def __init__(self, ego_vehicle, radius=50, name="LightsBehavior"):
        """
        Setup parameters
        """
        super().__init__(name)
        self._ego_vehicle = ego_vehicle
        self._radius = radius
        self._world = CarlaDataProvider.get_world()
        self._light_manager = self._world.get_lightmanager()
        self._light_manager.set_day_night_cycle(False)
        self._vehicle_lights = carla.VehicleLightState.Position | carla.VehicleLightState.LowBeam

        self._prev_night_mode = False

    def update(self):
        """
        Turns on / off all the lghts around a radius of the ego vehicle
        """
        new_status = py_trees.common.Status.RUNNING

        location = CarlaDataProvider.get_location(self._ego_vehicle)
        if not location:
            return new_status

        night_mode = self._get_night_mode(self._world.get_weather())
        if night_mode:
            self._turn_close_lights_on(location)
        elif self._prev_night_mode:
            self._turn_all_lights_off()

        self._prev_night_mode = night_mode
        return new_status

    def _get_night_mode(self, weather):
        """Check wheather or not the street lights need to be turned on"""
        if weather.sun_altitude_angle <= self.SUN_ALTITUDE_THRESHOLD_1 \
                or weather.sun_altitude_angle >= self.SUN_ALTITUDE_THRESHOLD_2:
            return True
        if weather.cloudiness >= self.CLOUDINESS_THRESHOLD:
            return True
        if weather.fog_density >= self.FOG_THRESHOLD:
            return True
        return False

    def _turn_close_lights_on(self, location):
        """Turns on the lights of all the objects close to the ego vehicle"""
        ego_speed = CarlaDataProvider.get_velocity(self._ego_vehicle)
        radius = max(self._radius, 5 * ego_speed)

        # Street lights
        on_lights = []
        off_lights = []

        all_lights = self._light_manager.get_all_lights()
        for light in all_lights:
            if light.location.distance(location) > radius:
                if light.is_on:
                    off_lights.append(light)
            else:
                if not light.is_on:
                    on_lights.append(light)

        self._light_manager.turn_on(on_lights)
        self._light_manager.turn_off(off_lights)

        # Vehicles
        all_vehicles = self._world.get_actors().filter('*vehicle.*')
        scenario_vehicles = [v for v in all_vehicles if v.attributes['role_name'] == 'scenario']

        for vehicle in scenario_vehicles:
            if vehicle.get_location().distance(location) > radius:
                lights = vehicle.get_light_state()
                lights &= ~self._vehicle_lights  # Remove those lights
                vehicle.set_light_state(carla.VehicleLightState(lights))
            else:
                lights = vehicle.get_light_state()
                lights |= self._vehicle_lights  # Add those lights
                vehicle.set_light_state(carla.VehicleLightState(lights))

        # Ego vehicle
        lights = self._ego_vehicle.get_light_state()
        lights |= self._vehicle_lights
        self._ego_vehicle.set_light_state(carla.VehicleLightState(lights))

    def _turn_all_lights_off(self):
        """Turns off the lights of all object"""
        all_lights = self._light_manager.get_all_lights()
        off_lights = [l for l in all_lights if l.is_on]
        self._light_manager.turn_off(off_lights)

        # Vehicles
        all_vehicles = self._world.get_actors().filter('*vehicle.*')
        scenario_vehicles = [v for v in all_vehicles if v.attributes['role_name'] == 'scenario']

        for vehicle in scenario_vehicles:
            lights = vehicle.get_light_state()
            lights &= ~self._vehicle_lights  # Remove those lights
            vehicle.set_light_state(carla.VehicleLightState(lights))

        # Ego vehicle
        lights = self._ego_vehicle.get_light_state()
        lights &= ~self._vehicle_lights  # Remove those lights
        self._ego_vehicle.set_light_state(carla.VehicleLightState(lights))

    def terminate(self, new_status):
        self._light_manager.set_day_night_cycle(True)
        return super().terminate(new_status)