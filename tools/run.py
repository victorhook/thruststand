#!/usr/bin/env python3

from dataclasses import dataclass
from argparse import Namespace, ArgumentParser
import time
from datetime import datetime
from pathlib import Path
from device import Device
from pymavlink import mavutil
import sys


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument('port', type=str, help='Serial port to connect to')
    parser.add_argument('-a', '--ap', default=None, required=False, type=str, help='Ardupilot port to connect to')
    parser.add_argument('-o', '--output', type=str, default='results', help='Output directory')
    parser.add_argument('-d', '--dry', action='store_true', default=False, help='If true, dry run, no PWM values set, only thrust measurement')
    return parser.parse_args()


def set_motor_pwm(master: object, motor_nbr: int, pwm: int) -> None:
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_DO_MOTOR_TEST,
        0,
        motor_nbr,
        1,
        pwm,
        5,
        0, 0, 0
    )

if __name__ == '__main__':
    args = parse_args()

    print('')

    dryrun = args.dry
    motor_nbr = 2

    if not dryrun:
        if args.ap is None:
            print('Must supply AP port "--ap"')
            sys.exit(0)

        master = mavutil.mavlink_connection(args.ap, baud=921600)
        print(f'Waiting for heartbeat from AP..., using motor {motor_nbr}')
        master.wait_heartbeat()

    datetime_str = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
    csv_filename = f'run_{datetime_str}.csv'
    base_dir = Path(args.output)
    csv_filepath = base_dir.joinpath(csv_filename)
    print(f'Writing results to {csv_filepath}')
    print('')

    if not base_dir.exists():
        base_dir.mkdir(parents=True)


    with open(csv_filepath, 'w') as f:
        f.write('timestamp,pwm,thrust,thrust_raw\n')

        print(f'Connecting to port {args.port}')
        device = Device(f)
        device.start(args.port)

        print('Let\'s go!')
        time.sleep(.3)

        pwm_min = 1000
        pwm_max = 2000
        pwm = pwm_min
        inc_step = 1
        delay_s = 0.02
        hold_final_s = 3

        try:
            while pwm <= pwm_max:
                pwm += inc_step

                if not dryrun:
                    set_motor_pwm(master, motor_nbr, pwm)

                device.set_throttle(pwm)
                latest = device.get_latest_data()

                done = ((pwm - pwm_min) / (pwm_max - pwm_min) ) * 100

                print(f'[{latest.timestamp}] {latest.throttle:3}/{pwm_max:3} ({round(done):3}%) -> {latest.thrust}')
                time.sleep(delay_s)

            # Hold final for 3 sec
            print(f'Holding final PWM for {hold_final_s}s')
            time.sleep(hold_final_s)

            downramp_dec_step = 10
            downramp_dec_delay = 0.01
            if pwm > pwm_max:
                pwm = pwm_max
            
            print(f'Done, ramping down from {pwm} to {pwm_min}, steps of {downramp_dec_step}, delay {downramp_dec_delay}s')
            
            while pwm > pwm_min:
                if not dryrun:
                    set_motor_pwm(master, motor_nbr, pwm)
                pwm -= downramp_dec_step
                time.sleep(downramp_dec_delay)
        finally:
            for i in range(5):
                device.set_throttle(1000)
                if not dryrun:
                    set_motor_pwm(master, motor_nbr, pwm)
                time.sleep(.05)

    print('')
    print('Done!')
    print('')