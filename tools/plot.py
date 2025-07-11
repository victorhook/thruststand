#!/usr/bin/env python3

import pandas as pd
from argparse import ArgumentParser, Namespace
import matplotlib.pyplot as plt
import tkinter as tk
from threading import Thread

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument('file', type=str, help='CSV file to plot')
    return parser.parse_args()

class Gui(tk.Tk):

    STYLE = {'bg': 'white'}
    TEXT_STYLE = {'font': 'Helvetica 18'}
    

    class Param:

        def __init__(self, master, name: str, value: float, min_value: float, max_value: float, step: float, row: str, optimize: callable = None) -> None:
            pad = {'padx': 5, 'pady': 2, 'ipadx': 2, 'ipady': 2}
            self._var = tk.StringVar()
            self._var.set(value)
            self.max_value = max_value
            self.min_value = min_value
            self.step = step

            tk.Label(master, text=name, **Gui.TEXT_STYLE, **Gui.STYLE).grid(row=row, column=0, sticky=tk.W, **pad)
            entry = tk.Entry(master, width=10, textvariable=self._var, **Gui.TEXT_STYLE, **Gui.STYLE)
            entry.grid(row=row, column=1, **pad)
            tk.Scale(master, width=10, length=600, orient=tk.HORIZONTAL, variable=self._var, from_=min_value, to_=max_value, resolution=step, **Gui.STYLE).grid(row=row, column=2, **pad)
            if optimize:
                tk.Button(master, text='Optimize', command=lambda: optimize(name), **Gui.TEXT_STYLE, **Gui.STYLE).grid(row=row, column=3, **pad)

        def do_bind_callback(self, on_update: callable) -> None:
            self._var.trace_add('write', lambda *_: on_update())

        def get(self) -> float:
            return float(self._var.get())
        
        def set(self, new_value: float) -> None:
            self._var.set(new_value)
        
    class Label:

        def __init__(self, master, name: str, value: str, row: str) -> None:
            pad = {'padx': 5, 'pady': 2, 'ipadx': 2, 'ipady': 2}
            self._var = tk.StringVar()
            self._var.set(value)
            tk.Label(master, text=name, **Gui.TEXT_STYLE, **Gui.STYLE).grid(row=row, column=0, sticky=tk.W, **pad)
            tk.Label(master, width=10, textvariable=self._var, **Gui.TEXT_STYLE, **Gui.STYLE).grid(row=row, column=1, **pad)

        def set(self, new_value: str) -> None:
            self._var.set(new_value)

        def get(self) -> str:
            return self._var.get()

    def __init__(self, csv_file: str) -> None:
        super().__init__()
        self.title('Thrust curve')
        self.geometry('1200x800')
        self.config(**self.STYLE)

        self.df = pd.read_csv(csv_file)

        self.param_frame = tk.LabelFrame(self, text='Ardupilot Parameters', **self.STYLE)
        self.plot_frame = tk.Frame(self, **self.STYLE)

        # -- Parameter frame -- #
        self.params = {
            'MOT_PWM_MIN':   self.Param(self.param_frame, 'MOT_PWM_MIN',   1000, 1000, 2000, 1,    0, optimize=self.optimize),
            'MOT_PWM_MAX':   self.Param(self.param_frame, 'MOT_PWM_MAX',   2000, 1000, 2000, 1,    1, optimize=self.optimize),
            'MOT_THST_EXPO': self.Param(self.param_frame, 'MOT_THST_EXPO', 0.5,  0.0,  1.0,  0.01, 2, optimize=self.optimize),
            'MOT_SPIN_ARM':  self.Param(self.param_frame, 'MOT_SPIN_ARM',  0.1,  0.0,  1.0,  0.01, 3),
            'MOT_SPIN_MIN':  self.Param(self.param_frame, 'MOT_SPIN_MIN',  0.25, 0.0,  1.0,  0.01, 4, optimize=self.optimize),
            'MOT_SPIN_MAX':  self.Param(self.param_frame, 'MOT_SPIN_MAX',  0.95, 0.0,  1.0,  0.01, 5, optimize=self.optimize),
        }
        for p in self.params.values():
            p.do_bind_callback(self.update_plot)

        self.error_label = self.Label(self.param_frame, 'MAE', '0', 6)
        self.mae = 0

        # -- Plots -- #
        self.calculate_corrected_thrust()

        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.line_measured, = self.ax.plot(self.df['normalized_throttle'], self.df['thrust'], label='Measured thrust', color='red')
        self.line_corrected, = self.ax.plot(self.df['normalized_throttle'], self.df['corrected_thrust'], label='Corrected thrust', color='blue')

        canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)  # A tk.DrawingArea.
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, anchor=tk.N, fill=tk.BOTH, expand=1)

        toolbar = NavigationToolbar2Tk(canvas, self.plot_frame)
        toolbar.update()
        canvas.get_tk_widget().pack(side=tk.TOP, anchor=tk.N, fill=tk.BOTH, expand=1)


        self.param_frame.pack(fill=tk.X, ipadx=10, ipady=10, expand=False, side=tk.TOP, anchor=tk.N)
        self.plot_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP, anchor=tk.N)

    def optimize(self, param_name: str) -> None:
        def _optimize():
            print(f'Optimizing parameter {param_name}')

            param = self.params[param_name]
            param.set(param.min_value)
            
            mae_min = float('inf')
            param_value_at_min = 0

            while param.get() < param.max_value:
                self.calculate_corrected_thrust()
                if self.mae < mae_min:
                    mae_min = self.mae
                    param_value_at_min = param.get()

                param.set(param.get() + param.step)

            print(f'Lowest MAE: {mae_min:.4f} at {param_name}={param_value_at_min:.2f}')
            param.set(param_value_at_min)

        Thread(target=_optimize, name='Optimizer', daemon=True).start()

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

        normalized_throttle = (self.df['voltage'] / self.df['voltage'].max()) * ( (self.df['pwm']-PWM_AT_MOT_SPIN_MIN)/(PWM_AT_MOT_SPIN_MAX-PWM_AT_MOT_SPIN_MIN) ).clip(lower=0)
        normalized_thrust = ((1 - MOT_THST_EXPO) * normalized_throttle + MOT_THST_EXPO*normalized_throttle*normalized_throttle).clip(lower=0)
        corrected_thrust = normalized_thrust * thrust_at_MOT_SPIN_MAX + thrust_at_MOT_SPIN_MIN

        self.df['normalized_throttle'] = normalized_throttle
        self.df['normalized_thrust'] = normalized_thrust
        self.df['corrected_thrust'] = corrected_thrust

        self.mae = self.evaluate_fit()
        self.error_label.set(f'{self.mae:.4f}')

    def evaluate_fit(self) -> float:
        return (self.df['thrust'] - self.df['corrected_thrust']).abs().mean()


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
