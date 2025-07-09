
from serial import Serial
from queue import Queue
from threading import Thread, Lock
import json
from dataclasses import dataclass
from argparse import Namespace, ArgumentParser
import time
from datetime import datetime
import sys
import struct
from pathlib import Path


@dataclass
class Data:
    timestamp: int
    throttle: int
    thrust: float
    thrust_raw: float

class Device:

    SYNC_BYTE = 0x42
    CALIBRATION_WEIGHT_GRAMS = 490
    CALIBRATION_THRUST_AT_MEASURED_WEIGHT = 220000

    def __init__(self, csv_file = None) -> None:
        self._rx = Queue()
        self._tx = Queue()
        self._serial: Serial = None
        self._data = []
        self._lock = Lock()
        self._latest_data = None
        self.csv_file = csv_file

    def get_latest_data(self) -> Data:
        with self._lock:
            return self._latest_data

    def start(self, port: str, baud: int = 115200) -> None:
        self._serial = Serial(port, baud, timeout=1, write_timeout=1)
        Thread(target=self._rx_thread, name='Device RX', daemon=True).start()
        Thread(target=self._tx_thread, name='Device TX', daemon=True).start()

    def reboot(self) -> None:
        self._tx.put(f'reboot\n')

    def set_throttle(self, pwm: int) -> None:
        self._tx.put(f'{pwm}\n')

    def _rx_thread(self) -> None:
        while True:
            if self._serial is None:
                break

            try:
                data = self._serial.readline()
                timestamp, throttle, thrust_raw = data.decode('ascii').strip().replace(' ', '').split(',')
                thrust = -1 * float(thrust_raw) * (self.CALIBRATION_WEIGHT_GRAMS / self.CALIBRATION_THRUST_AT_MEASURED_WEIGHT)
                new_data = Data(timestamp, throttle, int(thrust), thrust_raw)
                self._rx.put(new_data)
                with self._lock:
                    self._latest_data = new_data
                if self.csv_file:
                    # Write thrust in kgf
                    self.csv_file.write(f'{timestamp},{throttle},{(thrust/1000.0):.3f},{thrust_raw}\n')
            except Exception as e:
                print(f'Error reading: {e}')

        print('RX done!')
            
    def _tx_thread(self) -> None:
        while True:
            if self._serial is None:
                break

            try:
                tx = self._tx.get()
                if not tx.endswith('\n'):
                    tx += '\n'
                self._serial.write(tx.encode('ascii'))
            except Exception as e:
                print(f'Error reading: {e}')

        print('TX done!')



if __name__ == '__main__':
    device = Device(None)
    device.start('/dev/ttyACM0', baud=921600)

    while True:
        throttle = input('> New throttle: ')
        try:
            device.set_throttle(int(throttle))
            print(f'Throttle: {device.get_latest_data().throttle}')
        except Exception as e:
            print(e)