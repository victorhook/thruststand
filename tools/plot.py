#!/usr/bin/env python3

import pandas as pd
from argparse import ArgumentParser, Namespace
import matplotlib.pyplot as plt

def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument('file', type=str, help='CSV file to plot')
    return parser.parse_args()


MOT_PWM_MIN   = 1000
MOT_PWM_MAX   = 2000
MOT_THST_EXPO = 0.5
MOT_SPIN_ARM  = 0.1
MOT_SPIN_MIN  = 0.25
MOT_SPIN_MAX  = 0.95

PWM_AT_MOT_SPIN_MIN = MOT_PWM_MIN + (MOT_SPIN_MIN*(MOT_PWM_MAX-MOT_PWM_MIN))
PWM_AT_MOT_SPIN_MAX = MOT_PWM_MIN + (MOT_SPIN_MAX*(MOT_PWM_MAX-MOT_PWM_MIN))

# -- Normalized Throttle
# =OM(isnumber(A12),(C12/max($C$12:$C$2000))*max(0,(A12-$G$5)/($G$6-$G$5)),"")
# voltage / max(voltage) * max(0, (pwm-PWM_AT_MOT_SPIN_MIN)/(PWM_AT_MOT_SPIN_MAX-PWM_AT_MOT_SPIN_MIN))

# -- Normalized Thrust
#=OM(isnumber(A12),max((1-$B$6)*E12+$B$6*E12*E12,0),"")
# max(1 - MOT_THST_EXPO) * normalized_throttle + MOT_THST_EXPO*normalized_throttle*normalized_throttle

# G7 : Thrust at MOT_SPIN_MIN
# G8 : Thrust at MOT_SPIN_MAX

# -- Corrected Thrust
#=OM(isnumber(A12),F12*$G$8+$G$7,"")
#normalized_thrust * thrust_at_MOT_SPIN_MAX + thrust_at_MOT_SPIN_MIN

if __name__ == '__main__':
    args = parse_args()
    print(PWM_AT_MOT_SPIN_MIN)
    print(PWM_AT_MOT_SPIN_MAX)

    df = pd.read_csv(args.file)

    thrust_at_MOT_SPIN_MIN = df.loc[(df['pwm'] - PWM_AT_MOT_SPIN_MIN).abs().idxmin(), 'thrust']
    thrust_at_MOT_SPIN_MAX = df.loc[(df['pwm'] - PWM_AT_MOT_SPIN_MAX).abs().idxmin(), 'thrust']
    df['voltage'] = 8

    print(thrust_at_MOT_SPIN_MIN)
    print(thrust_at_MOT_SPIN_MAX)

    normalized_throttle = (df['voltage'] / df['voltage'].max()) * ( (df['pwm']-PWM_AT_MOT_SPIN_MIN)/(PWM_AT_MOT_SPIN_MAX-PWM_AT_MOT_SPIN_MIN) ).clip(lower=0)
    normalized_thrust = ((1 - MOT_THST_EXPO) * normalized_throttle + MOT_THST_EXPO*normalized_throttle*normalized_throttle).clip(lower=0)
    corrected_thrust = normalized_thrust * thrust_at_MOT_SPIN_MAX + thrust_at_MOT_SPIN_MIN

    df['normalized_throttle'] = normalized_throttle
    df['normalized_thrust'] = normalized_thrust
    df['corrected_thrust'] = corrected_thrust


    plt.plot(df['normalized_throttle'], df['thrust'], label='Measured thrust', color='red')
    plt.plot(df['normalized_throttle'], df['corrected_thrust'], label='Corrected thrust', color='blue')
    plt.xlabel('Normalized throttle [0-1]')
    plt.ylabel('Thrust [kgf]')
    plt.legend()
    plt.show()

