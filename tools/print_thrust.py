#!/usr/bin/env python3

from argparse import Namespace, ArgumentParser
import time
from device import Device


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument('port', type=str, help='Serial port to connect to')
    parser.add_argument('-d', '--delay_ms', type=float, default=0.1, help='Delay between prints')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    print(f'Connecting to port {args.port}')
    device = Device()
    device.start(args.port)

    print(f'Let\'s go, waiting {args.delay_ms}ms between prints')
    time.sleep(1)

    while True:
        print(device.get_latest_data().thrust)
        time.sleep(args.delay_ms)