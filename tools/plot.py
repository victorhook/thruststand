#!/usr/bin/env python3

import pandas as pd
from argparse import ArgumentParser, Namespace
import matplotlib.pyplot as plt
import tkinter as tk

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure

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

class Gui(tk.Tk):

    class Param:

        def __init__(self, master, update_callback: callable, name: str, value: float, min_value: float, max_value: float, step: float, row: str) -> None:
            self.master = master
            pad = {'padx': 10, 'pady': 5}
            self._var = tk.StringVar()
            self._var.set(value)
            self._var.trace_add('write', lambda *_: update_callback())

            tk.Label(master, text=name).grid(row=row, column=0, **pad)
            entry = tk.Entry(master, width=10, textvariable=self._var)
            entry.grid(row=row, column=1, **pad)
            tk.Scale(master, width=10, length=500, orient=tk.HORIZONTAL, variable=self._var, from_=min_value, to_=max_value, resolution=step).grid(row=row, column=2, **pad)

        def get(self) -> float:
            return float(self._var.get())

    def __init__(self, csv_file: str) -> None:
        super().__init__()
        self.title('Thrust curve')
        self.geometry('800x600')

        self.df = pd.read_csv(csv_file)


        self.param_frame = tk.Frame(self)
        self.plot_frame = tk.Frame(self)

        # -- Parameter frame -- #
        self.params = {
            'MOT_PWM_MIN':   self.Param(self.param_frame, self.update_plot, 'MOT_PWM_MIN',   1000, 1000, 2000, 1,    0),
            'MOT_PWM_MAX':   self.Param(self.param_frame, self.update_plot, 'MOT_PWM_MAX',   2000, 1000, 2000, 1,    1),
            'MOT_THST_EXPO': self.Param(self.param_frame, self.update_plot, 'MOT_THST_EXPO', 0.5,  0.0,  1.0,  0.01, 2),
            'MOT_SPIN_ARM':  self.Param(self.param_frame, self.update_plot, 'MOT_SPIN_ARM',  0.1,  0.0,  1.0,  0.01, 3),
            'MOT_SPIN_MIN':  self.Param(self.param_frame, self.update_plot, 'MOT_SPIN_MIN',  0.25, 0.0,  1.0,  0.01, 4),
            'MOT_SPIN_MAX':  self.Param(self.param_frame, self.update_plot, 'MOT_SPIN_MAX',  0.95, 0.0,  1.0,  0.01, 5),
        }

        # -- Plots -- #
        self.calculate_corrected_thrust()

        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.line_measured, = self.ax.plot(self.df['normalized_throttle'], self.df['thrust'], label='Measured thrust', color='red')
        self.line_corrected, = self.ax.plot(self.df['normalized_throttle'], self.df['corrected_thrust'], label='Corrected thrust', color='blue')

        canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)  # A tk.DrawingArea.
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        toolbar = NavigationToolbar2Tk(canvas, self.plot_frame)
        toolbar.update()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)


        self.param_frame.pack(fill=tk.X, expand=True)
        self.plot_frame.pack(fill=tk.BOTH, expand=True)

    def update_plot(self) -> None:
        self.calculate_corrected_thrust()

        # Update plot lines
        self.line_measured.set_data(self.df['normalized_throttle'], self.df['thrust'])
        self.line_corrected.set_data(self.df['normalized_throttle'], self.df['corrected_thrust'])

        self.ax.relim()
        self.ax.autoscale_view()
        self.fig.canvas.draw_idle()

    def calculate_corrected_thrust(self):
        MOT_PWM_MIN = self.params['MOT_PWM_MIN'].get()
        MOT_PWM_MAX = self.params['MOT_PWM_MAX'].get()
        MOT_THST_EXPO = self.params['MOT_THST_EXPO'].get()
        MOT_SPIN_ARM = self.params['MOT_SPIN_ARM'].get()
        MOT_SPIN_MIN = self.params['MOT_SPIN_MIN'].get()
        MOT_SPIN_MAX = self.params['MOT_SPIN_MAX'].get()

        PWM_AT_MOT_SPIN_MIN = MOT_PWM_MIN + (MOT_SPIN_MIN*(MOT_PWM_MAX-MOT_PWM_MIN))
        PWM_AT_MOT_SPIN_MAX = MOT_PWM_MIN + (MOT_SPIN_MAX*(MOT_PWM_MAX-MOT_PWM_MIN))

        thrust_at_MOT_SPIN_MIN = self.df.loc[(self.df['pwm'] - PWM_AT_MOT_SPIN_MIN).abs().idxmin(), 'thrust']
        thrust_at_MOT_SPIN_MAX = self.df.loc[(self.df['pwm'] - PWM_AT_MOT_SPIN_MAX).abs().idxmin(), 'thrust']
        self.df['voltage'] = 8

        print(thrust_at_MOT_SPIN_MIN)
        print(thrust_at_MOT_SPIN_MAX)

        normalized_throttle = (self.df['voltage'] / self.df['voltage'].max()) * ( (self.df['pwm']-PWM_AT_MOT_SPIN_MIN)/(PWM_AT_MOT_SPIN_MAX-PWM_AT_MOT_SPIN_MIN) ).clip(lower=0)
        normalized_thrust = ((1 - MOT_THST_EXPO) * normalized_throttle + MOT_THST_EXPO*normalized_throttle*normalized_throttle).clip(lower=0)
        corrected_thrust = normalized_thrust * thrust_at_MOT_SPIN_MAX + thrust_at_MOT_SPIN_MIN

        self.df['normalized_throttle'] = normalized_throttle
        self.df['normalized_thrust'] = normalized_thrust
        self.df['corrected_thrust'] = corrected_thrust



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

    gui = Gui(args.file)
    gui.mainloop()

    #plt.plot(df['normalized_throttle'], df['thrust'], label='Measured thrust', color='red')
    #plt.plot(df['normalized_throttle'], df['corrected_thrust'], label='Corrected thrust', color='blue')
    #plt.xlabel('Normalized throttle [0-1]')
    #plt.ylabel('Thrust [kgf]')
    #plt.legend()
    #plt.show()

