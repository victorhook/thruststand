#!/usr/bin/env python3

from serial import Serial
from queue import Queue
from threading import Thread, Lock
import json
from dataclasses import dataclass
from argparse import Namespace, ArgumentParser
import time
from datetime import datetime
import sys
from pathlib import Path
from device import Device


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument('port', type=str, help='Serial port to connect to')
    parser.add_argument('-o', '--output', type=str, default='results', help='Output directory')
    return parser.parse_args()


from pymavlink import mavutil
master = mavutil.mavlink_connection('/dev/ttyACM1', baud=921600)
print("Waiting for heartbeat...")
master.wait_heartbeat()

if __name__ == '__main__':
    args = parse_args()

    datetime_str = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
    csv_filename = f'run_{datetime_str}.csv'
    base_dir = Path(args.output)
    csv_filepath = base_dir.joinpath(csv_filename)
    print(f'Writing results to {csv_filepath}')

    if not base_dir.exists():
        base_dir.mkdir(parents=True)

    with open(csv_filepath, 'w') as f:
        f.write('timestamp,pwm,thrust\n')

        print(f'Connecting to port {args.port}')
        device = Device(f)
        device.start(args.port)

        print('Let\'s go!')
        time.sleep(.3)

        pwm_min = 1000
        pwm_max = 2000
        pwm = pwm_min
        inc_step = 1
        delay_s = 0.1

        try:
            while pwm <= pwm_max:
                pwm += inc_step

                master.mav.command_long_send(
                    master.target_system,
                    master.target_component,
                    mavutil.mavlink.MAV_CMD_DO_MOTOR_TEST,
                    0,
                    2,
                    1,
                    pwm,
                    1,
                    0, 0, 0
                )

                device.set_throttle(pwm)
                latest = device.get_latest_data()
                print(latest)
                time.sleep(delay_s)
        finally:
            for i in range(5):
                device.set_throttle(1000)
                master.mav.command_long_send(
                    master.target_system,
                    master.target_component,
                    mavutil.mavlink.MAV_CMD_DO_MOTOR_TEST,
                    0,
                    2,
                    1,
                    1000,
                    1,
                    0, 0, 0
                )
                time.sleep(.05)
