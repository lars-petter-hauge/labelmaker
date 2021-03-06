#! /usr/bin/env python3

import argparse
import math
import numpy as np
import segyio
import sys

import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib import patches
from matplotlib.lines import Line2D

class polybuilder(object):
    def __init__(self, control, ax):
        self.x = list(control.get_xdata())
        self.y = list(control.get_ydata())
        self.canvas = control.figure.canvas
        self.control = control
        self.ax = ax

        self.polys = []
        self.last_removed = None
        self.pick = None

        self.canvas.mpl_connect('button_release_event', self.onrelease)
        self.canvas.mpl_connect('key_press_event', self.complete)
        self.canvas.mpl_connect('pick_event', self.onpick)

        self.keys = {   'escape': self.clear,
                        'enter': self.mkpoly,
                        'd': self.rmpoly,
                        'u': self.undo,
                    }

    def onrelease(self, event):
        if self.pick is not None:
            self.pick = None
            return

        if self.canvas.manager.toolbar._active is not None: return
        if event.inaxes != self.control.axes: return
        if event.button != 1: return

        self.x.append(event.xdata)
        self.y.append(event.ydata)

        self.control.set_data(self.x, self.y)
        self.canvas.draw()

    def clear(self, *_):
        self.x, self.y = [], []
        self.control.set_data(self.x, self.y)

    def mkpoly(self, *_):
        poly = patches.Polygon(list(zip(self.x, self.y)), alpha = 0.5)
        self.ax.add_patch(poly)

        self.polys.append(poly)
        self.clear()

    def rmpoly(self, event):
        if event.inaxes != self.control.axes: return

        for poly in self.polys:
            if not poly.contains(event)[0]: continue
            poly.remove()
            self.last_removed = poly
            self.polys.remove(poly)

    def undo(self, *_ ):
        # TODO: undo last added dot
        if self.last_removed is None: return
        if len(self.polys) > 0 and self.polys[-1] is self.last_removed: return
        self.polys.append(self.last_removed)
        self.ax.add_patch(self.last_removed)

    def complete(self, event):
        if event.key not in self.keys: return

        self.keys[event.key](event)
        self.canvas.draw()

    def onpick(self, event):
        if event.artist is not self.control: return
        self.pick = 1

def main(argv):
    parser = argparse.ArgumentParser(prog = argv[0],
                                     description='Label those slices yo')
    parser.add_argument('input', type=str, help='input file')
    args = parser.parse_args(args = argv[1:])

    with segyio.open(args.input) as f:
        traces = f.trace.raw[:]
        low, high = np.nanmin(traces), np.nanmax(traces)

        _, ax = plt.subplots()
        ax.imshow(traces, aspect='auto', cmap = plt.get_cmap('BuPu'))

        line = Line2D([], [], ls='--', c='#666666',
                      marker='x', mew=2, mec='#204a87', picker = 5)
        ax.add_line(line)
        pb = polybuilder(line, ax)

        plt.show()

if __name__ == '__main__':
    main(sys.argv)
