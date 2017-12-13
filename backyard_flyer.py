# -*- coding: utf-8 -*-
"""
Created on Tue Oct 24 16:17:28 2017

@author: steve
"""

from drone import Drone
from enum import Enum
from connection import message_types as mt
from controllers import PDController
import numpy as np
import time


class States(Enum):
    MANUAL = 0
    ARMING = 1
    TAKEOFF = 2
    WAYPOINT = 3
    LANDING = 4
    DISARMING = 5


class BackyardFlyer(Drone):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller = PDController()
        self.target_position = np.array([0.0, 0.0, 0.0])
        self.all_waypoints = []
        self.in_mission = True
        self.check_state = {}

        # initial state
        self.flight_state = States.MANUAL

    def use_controller(self):
        # avoids bug where local position is still global position
        if self.local_position[0] > 1e6 or self.local_position[1] > 1e6:
            return
        thrust, pitch_rate, yaw_rate, roll_rate = self.controller.update(
            self.local_position, self.target_position, self.euler_angles, self.local_velocity, self.gyro_raw
        )
        self.cmd_attitude_rate(roll_rate, pitch_rate, yaw_rate, thrust)

    def callbacks(self):
        """ Define your callbacks within here"""
        super().callbacks()

        # TODO: Change this msg ?
        @self.msg_callback(mt.MSG_EULER_ANGLES)
        def hil_state_callback(msg_name, msg):
            if self.flight_state == States.TAKEOFF or self.flight_state == States.WAYPOINT or self.flight_state == States.LANDING:
                self.use_controller()

        @self.msg_callback(mt.MSG_LOCAL_POSITION)
        def local_position_callback(msg_name, msg):
            if self.flight_state == States.MANUAL:
                pass
            elif self.flight_state == States.ARMING:
                pass
            elif self.flight_state == States.TAKEOFF:
                if -1.0 * msg.down > 0.95 * self.target_position[2]:
                    self.all_waypoints = self.calculate_box()
                    self.waypoint_transition()
            elif self.flight_state == States.WAYPOINT:
                if np.linalg.norm(self.target_position[0:2] - self.local_position[0:2]) < 1.0:
                    if len(self.all_waypoints) > 0:
                        self.waypoint_transition()
                    else:
                        self.landing_transition()
            elif self.flight_state == States.LANDING:
                pass
            elif self.flight_state == States.DISARMING:
                pass

        @self.msg_callback(mt.MSG_VELOCITY)
        def velocity_callback(msg_name, msg):
            if self.flight_state == States.MANUAL:
                pass
            elif self.flight_state == States.ARMING:
                pass
            elif self.flight_state == States.TAKEOFF:
                pass
            elif self.flight_state == States.WAYPOINT:
                pass
            elif self.flight_state == States.LANDING:
                if self.global_position[2] - self.global_home[2] < 0.1:
                    if abs(msg.down) < 0.01:
                        self.disarming_transition()
            elif self.flight_state == States.DISARMING:
                pass

        @self.msg_callback(mt.MSG_STATE)
        def state_callback(msg_name, msg):
            if self.in_mission:
                if self.flight_state == States.MANUAL:
                    self.arming_transition()
                elif self.flight_state == States.ARMING:
                    if msg.armed:
                        self.takeoff_transition()

                elif self.flight_state == States.TAKEOFF:
                    pass
                elif self.flight_state == States.WAYPOINT:
                    pass
                elif self.flight_state == States.LANDING:
                    pass
                elif self.flight_state == States.DISARMING:
                    if not msg.armed:
                        self.manual_transition()

    def calculate_box(self):
        print("Setting Home")
        local_waypoints = [[10.0, 0.0, 3.0], [10.0, 10.0, 3.0], [0.0, 10.0, 3.0], [0.0, 0.0, 3.0]]
        return local_waypoints

    def arming_transition(self):
        print("arming transition")
        self.take_control()
        self.arm()
        self.set_home_position(self.global_position[0], self.global_position[1], self.global_position[2])

        self.flight_state = States.ARMING

    def takeoff_transition(self):
        print("takeoff transition")
        target_altitude = 3.0
        self.target_position[2] = target_altitude
        self.takeoff(target_altitude)
        self.flight_state = States.TAKEOFF

    def waypoint_transition(self):
        print("waypoint transition")
        self.target_position = self.all_waypoints.pop(0)
        self.cmd_position(self.target_position[0], self.target_position[1], self.target_position[2], 0.0)
        self.flight_state = States.WAYPOINT

    def landing_transition(self):
        print("landing transition")
        self.target_position[2] = 0
        self.land()
        self.flight_state = States.LANDING

    def disarming_transition(self):
        print("disarm transition")
        self.disarm()
        self.flight_state = States.DISARMING

    def manual_transition(self):
        print("manual transition")
        self.release_control()
        self.stop()
        self.in_mission = False
        self.flight_state = States.MANUAL

    def start(self):

        self.start_log("Logs", "NavLog.txt")
        # self.connect()

        print("starting connection")
        # self.connection.start()

        super().start()

        # Only required if they do threaded
        # while self.in_mission:
        #    pass

        self.stop_log()


if __name__ == "__main__":
    drone = BackyardFlyer(threaded=False)
    print("Sleeping")
    time.sleep(3)
    drone.start()