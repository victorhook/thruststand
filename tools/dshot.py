import struct

DSHOT_MAX = 2047
DSHOT_MIN = 48
PWM_MAX = 2000
PWM_MIN = 1000


def dshot_throttle(pwm_us: int) -> int:
    return round(((pwm_us - PWM_MIN) / (PWM_MAX-PWM_MIN)) * (DSHOT_MAX - DSHOT_MIN) + DSHOT_MIN)

def pwm_throttle(dshot: int) -> int:
    return round(((dshot - DSHOT_MIN) / (DSHOT_MAX-DSHOT_MIN)) * (PWM_MAX - PWM_MIN) + PWM_MIN)


def decode_dshot_frame(data: str) -> object:
    throttle = int(data[:11], 2)
    telem = int(data[11])
    crc = int(data[12:], 2)

    #value = struct.unpack('H', int(data, 2).to_bytes(2, 'little'))[0]
    #expected_crc = (value ^ (value >> 4) ^ (value >> 8)) & 0x0F
    checksum_data = int(data[:12], 2)
    expected_crc = (checksum_data >> 8) ^ ((checksum_data >> 4) & 0b1111) ^ (checksum_data & 0b1111)
    print(data[:11], expected_crc)
    
    return throttle, telem, crc

#throttle, telem, crc = decode_dshot_frame('0001000000000001')
#throttle, telem, crc = decode_dshot_frame('0001000011001101')
#throttle, telem, crc = decode_dshot_frame('0001111100001110')
throttle, telem, crc = decode_dshot_frame('00010010100010110')


print(f'throttle: {throttle} ({pwm_throttle(throttle)}), telem: {telem}, crc: {crc}')

