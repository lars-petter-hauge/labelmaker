#! /usr/bin/env python3

import argparse
import numpy as np
import segyio
import sys

import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.lines import Line2D
from utility import within_tolerance, closest, axis_lengths

def export(fname, output, prefix = 'labelmade-'):
    print(prefix + fname)
    with segyio.open(fname) as f:
        meta = segyio.tools.metadata(f)
        with segyio.create(prefix + fname, meta) as out:
            out.text[0] = f.text[0]

            for i in range(1, 1 + f.ext_headers):
                out.text[i] = f.text[i]

            out.bin = f.bin
            out.header = f.header
            out.trace = output

class plotter(object):
    def __init__(self, args, traces):
        self.args = args
        self.x = []
        self.y = []
        self.fig = None
        self.canvas = None
        self.ax = None
        self.line = None
        self.threshold = args.threshold
        self.traces = traces
        self.overlaypath = args.compare

        self.polys = []
        self.last_removed = None
        self.pick = None
        self.current_poly_class = 0
        self.cmap = plt.get_cmap('tab10').colors

        self.keys = {'escape': self.clear,
                     'enter': self.mkpoly,
                     'd': self.rmpoly,
                     'u': self.undo,
                     'e': self.export
                     }

        for key in range(1,10):
            self.keys[str(key)] = self.set_class

    def run(self):

        self.fig, self.ax = plt.subplots()
        self.ax.imshow(self.traces, aspect='auto', cmap=plt.get_cmap('BuPu'))

        self.line = Line2D(self.x, self.y, ls='--', c='#666666',
                      marker='x', mew=2, mec='#204a87', picker=5)
        self.ax.add_line(self.line)

        self.canvas = self.line.figure.canvas
        if self.overlaypath is None:
            self.canvas.mpl_connect('button_release_event', self.onrelease)
            self.canvas.mpl_connect('key_press_event', self.complete)
            self.canvas.mpl_connect('pick_event', self.onpick)

        if self.overlaypath is not None:
            self.add_overlay()

        plt.show()

    def add_overlay(self):
        with segyio.open(self.overlaypath) as f:
            traces = f.trace.raw[:]

        self.ax.imshow(traces, aspect='auto', cmap=plt.get_cmap('BuPu'), alpha=0.5)

    def onrelease(self, event):
        if self.pick is not None:
            if self.current_point:
                self.move_point(event.xdata, event.ydata)
            self.pick = None
            return

        if self.canvas.manager.toolbar._active is not None: return
        if event.inaxes != self.line.axes: return
        if event.button != 1: return

        self.x.append(event.xdata)
        self.y.append(event.ydata)

        self.line.set_data(self.x, self.y)
        self.canvas.draw()

    def clear(self, *_):
        self.x, self.y = [], []
        self.line.set_data(self.x, self.y)

    def mkpoly(self, *_):
        if len(self.x) == 0: return

        poly = patches.Polygon(list(zip(self.x, self.y)),
                               alpha=0.5,
                               fc=self.cmap[self.current_poly_class])
        self.ax.add_patch(poly)

        self.polys.append(poly)
        self.clear()

    def rmpoly(self, event):
        if event.inaxes != self.line.axes: return

        for poly in self.polys:
            if not poly.contains(event)[0]: continue
            poly.remove()
            self.last_removed = poly
            self.polys.remove(poly)

    def undo(self, *_ ):
        if self.last_removed is None: return
        if len(self.polys) > 0 and self.polys[-1] is self.last_removed: return
        self.polys.append(self.last_removed)
        self.ax.add_patch(self.last_removed)

    def undo_dot(self, *_):
        if len(self.x) == 0: return
        self.x.pop()
        self.y.pop()

        self.line.set_data(self.x, self.y)
        self.canvas.draw()

    def set_class(self, event):
        for poly in self.polys:
            if not poly.contains(event)[0]: continue
            poly.set_facecolor(self.cmap[int(event.key)-1])

    def complete(self, event):
        if event.key not in self.keys: return

        self.keys[event.key](event)
        self.canvas.draw()

    def onpick(self, event):
        if event.artist is not self.line: return
        self.pick = 1
        xp, yp = event.mouseevent.xdata, event.mouseevent.ydata
        xdata, ydata = self.line.get_data()

        dx, dy = axis_lengths(self.line.axes)
        idx, distance = closest(xp, yp, xdata, ydata, dx, dy)

        if within_tolerance(distance, dx, dy, self.threshold):
            self.current_point = (xdata[idx], ydata[idx], idx)

    def move_point(self, xp, yp):
        _, _, idx = self.current_point

        self.x[idx] = xp
        self.y[idx] = yp

        self.line.set_data(self.x, self.y)
        self.canvas.draw()
        self.current_point = None

    def export(self, *_):
        traces = self.create_output_creates()
        export(self.args.input, traces, prefix = self.args.prefix)

    def create_output_creates(self):
        with segyio.open(self.args.input) as f:
            traces, samples = len(f.trace), len(f.trace[0])
            output = np.zeros((traces, samples), dtype=np.single)
            px, py = np.mgrid[0:traces, 0:samples]
            points = np.c_[py.ravel(), px.ravel()]

            for poly in self.polys:
                mask = poly.get_path().contains_points(points)
                color = poly.get_facecolor()
                value = self.cmap.index((color[0], color[1], color[2])) + 1
                np.place(output, mask, [value])
        return output


def main(argv):
    parser = argparse.ArgumentParser(prog = argv[0],
                                     description='Labelmaker - open segyiofile, '
                                                 'mark areas interactively and export the result')
    parser.add_argument('input', type=str,
                                 help='Input file')
    parser.add_argument('--threshold', type=float,
                                       help='point selection sensitivity',
                                       default = 0.01)
    parser.add_argument('--prefix', type=str,
                                    help='Output file prefix',
                                    default='labelmade-')
    parser.add_argument('-d', '--compare', type=str,
                                           help='Filepath to exported results (for comparing)')
    args = parser.parse_args(args = argv[1:])

    with segyio.open(args.input) as f:
        traces = f.trace.raw[:]

    runner = plotter(args, traces)
    runner.run()

if __name__ == '__main__':
    main(sys.argv)
