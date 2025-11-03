"""Spectrum class."""

import pathlib
from dataclasses import dataclass
from typing import Tuple

import colorcet
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import skrf
import textalloc
from matplotlib.patches import Rectangle

from .core import (
    _DARK_GRAY,
    _FREQUENCY_UNITS,
    _if_supression,
    _LIGHT_GRAY,
    _lo_supression,
    _THRESHOLD,
    mixer_products,
)
from .models import henderson

_PATCH_ARGS = {"alpha": 0.5, "linewidth": 1}


@dataclass(kw_only=True)
class SpectrumBase:
    """Base class for mixer spectrum plots.

    TODO: is there a way to prevent this class from being instantiated? Potentially use ABC?

    """

    flo: float
    lo_power: float = 20
    bw: float
    order: Tuple[int, int] = (5, 5)
    gain: float = -8
    rf_if: float = 25
    lo_rf: float = 40
    lo_if: float = 40
    threshold: float = _THRESHOLD
    units: str = _FREQUENCY_UNITS

    def __post_init__(self):
        self._intermods = mixer_products(*self.order)
        spurs = pd.DataFrame(self._intermods, columns=["n", "m"])

        colormap = getattr(colorcet, "glasbey")
        spurs["color"] = colormap[: len(spurs)]

        self.spurs = spurs

    def _make_patches(self):
        spurs = self.spurs
        threshold = self.threshold

        # filter spurs below threshold
        spurs = spurs[spurs["level"] >= threshold]

        if "if1" in self.spurs.columns:
            begin = "if1"
            end = "if2"
            bandlimits = getattr(self, "fif")
        else:
            begin = "rf1"
            end = "rf2"
            bandlimits = getattr(self, "frf")

        # filter spurs out of range

        out_of_range = (spurs[begin] > bandlimits[1]) & (spurs[end] > bandlimits[1])
        spurs = spurs[~out_of_range]

        out_of_range = (spurs[begin] < bandlimits[0]) & (spurs[end] < bandlimits[0])
        spurs = spurs[~out_of_range]

        # sort
        xmin = spurs[[begin, end]].min(axis=1)
        xmax = spurs[[begin, end]].max(axis=1)

        width = xmax - xmin
        height = abs(threshold) + spurs.level

        patches = pd.DataFrame({"width": width, "height": height, "x": xmin})
        patches = pd.concat((patches, spurs), axis=1)

        # replace infinite height
        patches["height"] = patches["height"].replace(np.inf, -threshold)

        self._patches = patches

    def _annotate_axes(self):
        ax = self.ax

        # x-axis

        if "if1" in self.spurs.columns:
            lowerlimit, upperlimit = getattr(self, "fif")
            upperlimit = min(upperlimit, self.spurs.if2.max())
        else:
            lowerlimit, upperlimit = getattr(self, "frf")
            upperlimit = min(upperlimit, self.spurs.rf2.max())

        ax.set_xlim(lowerlimit, upperlimit)

        xrange = upperlimit - lowerlimit

        ax.grid(visible=True, which="major", axis="x", color=_DARK_GRAY)
        ax.grid(visible=True, which="major", axis="y", color=_LIGHT_GRAY)

        # pick some appropriate xticks
        if self.units == "MHz":
            k = 1000
        elif self.units == "GHz":
            k = 1
        else:
            raise ValueError

        if xrange * k <= 10 * k:
            step = 1
            ax.grid(visible=True, which="minor", axis="x", color=_LIGHT_GRAY)

        elif 10 * k > xrange >= 50 * k:
            step = 5
            ax.grid(visible=True, which="minor", axis="x", color=_LIGHT_GRAY)

        else:
            step = 10

        ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(step))
        # ax.xaxis.set_major_locator(ticker.MultipleLocator(step / 2))

        # y-axis

        ax.yaxis.set_major_locator(ticker.MultipleLocator(10))
        ax.set_ylim(self.threshold, 0)
        ax.set_axisbelow(True)

    def _annotate_legend(self, legend_title):
        ax = self.ax

        ax.legend()

        if ax.get_legend() is None:
            # legend doesn't exist

            # make room for the legend to the right of the current axis
            # Shink current axis by 20%
            box = ax.get_position()
            ax.set_position([box.x0, box.y0, box.width * 0.75, box.height])

        else:
            # legend already exists
            ax.get_legend().remove()

        ncol = 1
        if len(ax.lines) + len(ax.patches) > 20:
            ncol = 2

        leg = ax.legend(
            loc="upper left",
            bbox_to_anchor=(1, 1),
            ncol=ncol,
            fancybox=False,
            shadow=False,
            frameon=False,
            fontsize="small",
            title=legend_title,
        )
        leg._legend_box.align = "left"

    def touchstone(
        self,
        io: str | pathlib.Path | skrf.Network,
        m: int = 2,
        n: int = 1,
        color: str = "blue",
        name: str = None,
    ):
        """Plot a touchstone (s-parameter) file.

        io: str, pathlib.Path, or skrf.Network()

        m: int
        n: int
        """
        if isinstance(io, str):
            io = pathlib.Path(io)  # cast string to pathlib.Path
            ntwk = skrf.Network(io)

        elif isinstance(io, pathlib.Path):
            ntwk = skrf.Network(io)

        elif isinstance(io, skrf.Network):
            ntwk = io

        else:
            raise ValueError

        ntwk.frequency.unit = self.units

        if name is None:
            name = f"S{m}{n}: f{ntwk.name}"

        self.ax.plot(ntwk.frequency.f_scaled, ntwk.s_db[:, m - 1, n - 1], label=name, color=color)


@dataclass
class TxUp(SpectrumBase):
    """Plot the spectrum of an upconverting transmitter.

    Parameters
    ----------
    fif : float
        The IF frequency, in `units`
    if_power : float, optional
        The IF power in dBm. Default is 0 dBm.
    frf : tuple, optional
        The RF frequency range (x-axis) of the spectrum in `units`. Default is (0,inf).
    flo : float
        The LO frequency, in `units`.
    lo_power : float, optional
        The LO power in dBm. Default is +20 dBm.
    bw : float
        The bandwidth.
    order : tuple, optional
        The max order of n and m, given as (n,m). Default is (5,5).
    gain : float, optional
        conversion gain of the mixer in dB. Default is -8 dB.
    rf_if : float, optional
        RF to IF isolation of the mixer in dB. Default is 25 dB.
    lo_rf : float, optional
        LO to RF isolation of the mixer in dB. Default is 40 dB.
    lo_if : float, optional
        LO to IF isolation of the mixer in dB. Default is 40 dB.
    threshold : float, optional
        Minimum spur level to plot (minimum of the y-axis) in dBc. Default is -100 dBc.
    units : str, optional
        Frequency units, can be "MHz" or "GHz". Default is "GHz".

    """

    fif: float
    if_power: float = 0
    frf: Tuple[float, float] = (0, np.inf)

    def __post_init__(self):
        super().__post_init__()

        spurs = self.spurs

        spurs["level"] = [
            henderson(n, m, Plo=self.lo_power, Prf=self.if_power) for n, m in self._intermods
        ]

        spurs.loc[spurs[(spurs.n == 0) & (spurs.m == 1)].index, "level"] = _if_supression(
            self.gain, self.rf_if
        )  # correct (0,1) spur based on conversion gain and RF-IF isolation

        spurs.loc[spurs[(spurs.n == 1) & (spurs.m == 0)].index, "level"] = _lo_supression(
            self.gain, self.lo_rf, self.if_power, self.lo_power
        )  # correct (1,0) spur based on conversion gain and isolation

        bw = self.bw
        flo = self.flo

        ifband = self.fif + np.array([-bw, bw]) / 2

        rf1 = spurs.n * flo + spurs.m * ifband[0]
        rf2 = spurs.n * flo + spurs.m * ifband[1]

        # sort so that rf1 < rf2
        spurs["rf1"] = np.min((rf1, rf2), axis=0)
        spurs["rf2"] = np.max((rf1, rf2), axis=0)

        # filter spurs that have negative frequency
        pos_frequency_spurs = (spurs.rf1 >= 0) | (spurs.rf2 >= 0)
        spurs = spurs[pos_frequency_spurs]

        self.spurs = spurs

        self.plot()

    def plot(self):
        """Plot the spectrum."""
        self._make_patches()

        threshold = self.threshold
        units = self.units

        self.fig, ax = plt.subplots(1, figsize=(10, 5.5))

        ax.set_xlabel(f"RF Output Frequency [{units}]")
        ax.set_ylabel("Level Relative to RF Output [dBc]")

        self.ax = ax

        legend_text = [
            "(n,m) spurs:",
            "n·LO+m·IF=RF",
            f"≥{threshold:0.0f} dBc, |n|≤{self.order[0]}, |m|≤{self.order[1]}",
        ]

        self._annotate_axes()

        # plot spurs
        # NOTE: nLO is not plotted in RX case. Should do it?

        spurlabel_text = []
        spurlabel_x = []
        spurlabel_y = []
        spurlabel_textcolor = []

        for _, patch in self._patches.iterrows():
            if patch.m == 0:
                # nLO + mIF = RF --> RF = nLO
                rf = patch.n * self.flo
                label = f"RF = {patch.n:0.0f}·LO"
                if patch.n == 1:
                    label = "RF = LO"

                ax.vlines(
                    rf,
                    threshold,
                    threshold + patch.height,
                    lw=2,
                    label=label,
                    color=patch.color,
                )

                spurlabel_text.append(f"({patch.n:0.0f},{patch.m:0.0f})")
                spurlabel_x.append(patch.x)  # + patch.width / 2)
                spurlabel_y.append(threshold + patch.height)
                spurlabel_textcolor.append(patch.color)

            else:
                if patch.n == 0:
                    # nLO + mIF = RF --> RF = mIF
                    label = f"RF = {patch.m:0.0f}·IF"
                    if patch.m == 1:
                        label = "RF = IF"
                else:
                    label = f"({patch.n:0.0f},{patch.m:0.0f}): {patch.rf1:0.6g} to {patch.rf2:0.6g}"

                rect = Rectangle(
                    xy=(patch.x, threshold),
                    width=patch.width,
                    height=patch.height,
                    label=label,
                    color=patch.color,
                    **_PATCH_ARGS,
                )
                ax.add_patch(rect)

                spurlabel_text.append(f"({patch.n:0.0f},{patch.m:0.0f})")
                spurlabel_x.append(patch.x)  # + patch.width) / 2)
                spurlabel_y.append(threshold + patch.height)
                spurlabel_textcolor.append(patch.color)

            textalloc.allocate(
                ax,
                x=spurlabel_x,
                y=spurlabel_y,
                text_list=spurlabel_text,
                # x_scatter=spurlabel_x,
                # y_scatter=spurlabel_y,
                # direction="south",
                ylims=(threshold, 0),  # seems like this doesn't work
                xlims=self.frf,  # seems like this doesn't work
                textcolor=spurlabel_textcolor,
                max_distance=0.004,
                min_distance=0.003,
                draw_lines=False,
            )

        ax.set_title(
            f"TX Spectrum: IF = {self.fif:0.6g} {units}, BW = {self.bw:0.6g} {units},"
            + f" LO = {self.flo:0.6g} {units}",
        )

        self._annotate_legend("\n".join(legend_text) + "\n")


@dataclass
class TxDown(SpectrumBase):
    """Plot the spectrum of an downconverting transmitter.

    Parameters
    ----------
    ...
    """

    frf: float
    rf_power: float = 0
    fif: Tuple[float, float] = (0, np.inf)

    def __post_init__(self):
        super().__post_init__()

        spurs = self.spurs

        spurs["level"] = [
            henderson(n, m, Plo=self.lo_power, Prf=self.rf_power) for n, m in self._intermods
        ]

        spurs.loc[spurs[(spurs.n == 0) & (spurs.m == 1)].index, "level"] = _if_supression(
            self.gain, self.rf_if
        )  # correct (0,1) spur based on conversion gain and RF-IF isolation

        spurs.loc[spurs[(spurs.n == 1) & (spurs.m == 0)].index, "level"] = _lo_supression(
            self.gain, self.lo_rf, self.rf_power, self.lo_power
        )  # correct (1,0) spur based on conversion gain and isolation

        bw = self.bw
        flo = self.flo

        rfband = self.frf + np.array([-bw, bw]) / 2

        if1 = spurs.n * flo + spurs.m * rfband[0]
        if2 = spurs.n * flo + spurs.m * rfband[1]

        # sort so that rf1 < rf2
        spurs["if1"] = np.min((if1, if2), axis=0)
        spurs["if2"] = np.max((if1, if2), axis=0)

        # filter spurs that have negative frequency
        pos_frequency_spurs = (spurs.if1 >= 0) | (spurs.if2 >= 0)
        spurs = spurs[pos_frequency_spurs]

        self.spurs = spurs

        self.plot()

    def plot(self):
        """Plot the spectrum."""
        self._make_patches()

        threshold = self.threshold
        units = self.units

        self.fig, ax = plt.subplots(1, figsize=(10, 5.5))

        ax.set_xlabel(f"IF Output Frequency [{units}]")
        ax.set_ylabel("Level Relative to IF Output [dBc]")

        self.ax = ax

        legend_text = [
            "(n,m) spurs:",
            "n·LO+m·RF=IF",
            f"≥{threshold:0.0f} dBc, |n|≤{self.order[0]}, |m|≤{self.order[1]}",
        ]

        self._annotate_axes()

        # NOTE: nLO is not plotted in RX case. Should do it?

        for _, patch in self._patches.iterrows():
            if patch.m == 0:
                # nLO + mRF = RF --> IF = nLO
                fif = patch.n * self.flo
                label = f"IF = {patch.n:0.0f}·LO"
                if patch.n == 1:
                    label = "IF = LO"

                ax.vlines(
                    fif,
                    threshold,
                    threshold + patch.height,
                    lw=2,
                    label=label,
                    color=patch.color,
                )

            else:
                if patch.n == 0:
                    # nLO + mRF = IF --> IF = mRF
                    label = f"IF = {patch.m:0.0f}·RF"
                    if patch.m == 1:
                        label = "IF = RF"
                else:
                    # TODO: is this correct?
                    label = f"({patch.n:0.0f},{patch.m:0.0f}): {patch.if1:0.6g} to {patch.if2:0.6g}"

                rect = Rectangle(
                    xy=(patch.x, threshold),
                    width=patch.width,
                    height=patch.height,
                    label=label,
                    color=patch.color,
                    **_PATCH_ARGS,
                )
                ax.add_patch(rect)

        ax.set_title(
            f"TX Spectrum: RF = {self.frf:0.6g} {units}, BW = {self.bw:0.6g} {units},"
            + f" LO = {self.flo:0.6g} {units}",
        )

        self._annotate_legend("\n".join(legend_text) + "\n")


@dataclass
class RxUp(SpectrumBase):
    """Plot the spectrum of an upconverting receiver.

    Parameters
    ----------
    ...
    """

    frf: float
    if_power: float = 0
    fif: Tuple[float, float] = (0, np.inf)

    def __post_init__(self):
        super().__post_init__()

        spurs = self.spurs

        spurs["level"] = [
            henderson(n, m, Plo=self.lo_power, Prf=self.if_power) for n, m in self._intermods
        ]

        spurs.loc[spurs[(spurs.n == 0) & (spurs.m == 1)].index, "level"] = _if_supression(
            self.gain, self.rf_if
        )  # correct (0,1) spur based on conversion gain and RF-IF isolation

        spurs.loc[spurs[(spurs.n == 1) & (spurs.m == 0)].index, "level"] = _lo_supression(
            self.gain, self.lo_rf, self.if_power, self.lo_power
        )  # correct (1,0) spur based on conversion gain and isolation

        bw = self.bw
        flo = self.flo

        rfband = self.frf + np.array([-bw, bw]) / 2

        if1 = (rfband[0] - spurs.n * flo) / spurs.m
        if2 = (rfband[1] - spurs.n * flo) / spurs.m

        # sort so that if1 < if2
        spurs["if1"] = np.min((if1, if2), axis=0)
        spurs["if2"] = np.max((if1, if2), axis=0)

        # NOTE: not sure why the above commands cause the following:
        #       spurs.loc[spurs.m == 0, "if1"] = -inf
        #       spurs.loc[spurs.m == 0, "if2"] = -inf
        #
        # fix if1 and if2 frequencies for m=0: n*LO + 0*IF = RF --> RF = n*LO
        n = spurs.loc[spurs.m == 0, "n"]
        spurs.loc[spurs.m == 0, "if1"] = n * self.flo
        spurs.loc[spurs.m == 0, "if2"] = n * self.flo

        # filter spurs that have negative frequency
        pos_frequency_spurs = (spurs.if1 >= 0) | (spurs.if2 >= 0)
        spurs = spurs[pos_frequency_spurs]

        self.spurs = spurs

        self.plot()

    def plot(self):
        """Plot the spectrum."""
        self._make_patches()

        threshold = self.threshold
        units = self.units

        self.fig, ax = plt.subplots(1, figsize=(10, 5.5))

        ax.set_xlabel(f"IF Input Frequency [{units}]")
        ax.set_ylabel("Level Relative to IF Input [dBc]")

        self.ax = ax

        legend_text = [
            "(n,m) spurs:",
            "n·LO+m·IF=RF",
            f"≥{threshold:0.0f} dBc, |n|≤{self.order[0]}, |m|≤{self.order[1]}",
        ]

        self._annotate_axes()

        for _, patch in self._patches.iterrows():
            if patch.n == 0:
                # nLO + mIF = RF --> IF = RF/m

                rfband = self.frf + np.array([-self.bw, self.bw]) / 2
                fif = rfband / patch.m
                label = f"IF = RF/{patch.m:0.0f}: {fif[0]:0.6g} to {fif[1]:0.6g}"
                if patch.m == 1:
                    label = f"IF = RF: {fif[0]:0.6g} to {fif[1]:0.6g}"

                rect = Rectangle(
                    xy=(patch.x, threshold),
                    width=patch.width,
                    height=patch.height,
                    label=label,
                    color=patch.color,
                    **_PATCH_ARGS,
                )
                ax.add_patch(rect)

            elif patch.m == 0:
                # nLO + mIF = RF --> nLO = RF
                fif = patch.if1

                if patch.n == 1:
                    label = f"LO: {fif:0.6g}"
                else:
                    label = f"{patch.n:0.0f}·LO: {fif:0.6g}"

                ax.vlines(
                    fif,
                    threshold,
                    threshold + patch.height,
                    lw=2,
                    label=label,
                    color=patch.color,
                )

            else:
                label = f"({patch.n:0.0f},{patch.m:0.0f}): {patch.if1:0.6g} to {patch.if2:0.6g}"

                rect = Rectangle(
                    xy=(patch.x, threshold),
                    width=patch.width,
                    height=patch.height,
                    label=label,
                    color=patch.color,
                    **_PATCH_ARGS,
                )
                ax.add_patch(rect)

        ax.set_title(
            f"RX Spectrum: RF = {self.frf:0.6g} {units}, BW = {self.bw:0.6g} {units},"
            + f" LO = {self.flo:0.6g} {units}",
        )

        self._annotate_legend("\n".join(legend_text) + "\n")


@dataclass
class RxDown(SpectrumBase):
    """Plot the spectrum of an downconverting receiver.

    Parameters
    ----------
    ...
    """

    fif: float
    rf_power: float = 0
    frf: Tuple[float, float] = (0, np.inf)

    def __post_init__(self):
        super().__post_init__()

        spurs = self.spurs

        spurs["level"] = [
            henderson(n, m, Plo=self.lo_power, Prf=self.rf_power) for n, m in self._intermods
        ]

        spurs.loc[spurs[(spurs.n == 0) & (spurs.m == 1)].index, "level"] = _if_supression(
            self.gain, self.rf_if
        )  # correct (0,1) spur based on conversion gain and RF-IF isolation

        spurs.loc[spurs[(spurs.n == 1) & (spurs.m == 0)].index, "level"] = _lo_supression(
            self.gain, self.lo_if, self.rf_power, self.lo_power
        )  # correct (1,0) spur based on conversion gain and isolation

        bw = self.bw
        flo = self.flo

        ifband = self.fif + np.array([-bw, bw]) / 2

        rf1 = (ifband[0] - spurs.n * flo) / spurs.m
        rf2 = (ifband[1] - spurs.n * flo) / spurs.m

        # sort so that rf1 < rf2
        spurs["rf1"] = np.min((rf1, rf2), axis=0)
        spurs["rf2"] = np.max((rf1, rf2), axis=0)

        # LO and harmonics
        n_vals = spurs.loc[spurs.m == 0, "n"]
        spurs.loc[spurs.m == 0, "rf1"] = flo * n_vals
        spurs.loc[spurs.m == 0, "rf2"] = flo * n_vals

        # filter spurs that have negative frequency
        pos_frequency_spurs = (spurs.rf1 >= 0) | (spurs.rf2 >= 0)
        spurs = spurs[pos_frequency_spurs]

        self.spurs = spurs

        self.plot()

    def plot(self):
        """Plot the spectrum."""
        self._make_patches()

        threshold = self.threshold
        units = self.units

        self.fig, ax = plt.subplots(1, figsize=(10, 5.5))

        ax.set_xlabel(f"RF Input Frequency [{units}]")
        ax.set_ylabel("Level Relative to RF Input [dBc]")

        self.ax = ax

        legend_text = [
            "(n,m) spurs:",
            "n·LO+m·RF=IF",
            f"≥{threshold:0.0f} dBc, |n|≤{self.order[0]}, |m|≤{self.order[1]}",
        ]

        self._annotate_axes()

        # NOTE: nLO is not plotted in RX case. Should do it?

        for _, patch in self._patches.iterrows():
            if patch.n == 0:
                # nLO + mRF = IF --> RF = IF/m
                # TODO: level is not correct for IF/1: Need to incorporate RF-IF isolation
                ifband = self.fif + np.array([-self.bw, self.bw]) / 2
                rf = ifband / patch.m
                label = f"RF = IF/{patch.m:0.0f}: {rf[0]:0.6g} to {rf[1]:0.6g}"
                if patch.m == 1:
                    label = f"RF = IF: {rf[0]:0.6g} to {rf[1]:0.6g}"

                rect = Rectangle(
                    xy=(patch.x, threshold),
                    width=patch.width,
                    height=patch.height,
                    label=label,
                    color=patch.color,
                    **_PATCH_ARGS,
                )
                ax.add_patch(rect)

            elif patch.m == 0:
                # nLO + mRF = IF --> nLO = IF
                rf = patch.rf1

                if patch.n == 1:
                    label = f"LO: {rf:0.6g}"
                else:
                    label = f"{patch.n:0.0f}·LO: {rf:0.6g}"

                ax.vlines(
                    rf,
                    threshold,
                    threshold + patch.height,
                    lw=2,
                    label=label,
                    color=patch.color,
                )

            else:
                label = f"({patch.n:0.0f},{patch.m:0.0f}): {patch.rf1:0.6g} to {patch.rf2:0.6g}"

                rect = Rectangle(
                    xy=(patch.x, threshold),
                    width=patch.width,
                    height=patch.height,
                    label=label,
                    color=patch.color,
                    **_PATCH_ARGS,
                )
                ax.add_patch(rect)

        ax.set_title(
            f"RX Spectrum: IF = {self.fif:0.6g} {units}, BW = {self.bw:0.6g} {units},"
            + f" LO = {self.flo:0.6g} {units}",
        )

        self._annotate_legend("\n".join(legend_text) + "\n")


@dataclass
class NormalLog:
    """Create a normalized logrithmic spurchart."""

    # todo: change this to an interactive bokeh plot
    order: tuple = (5, 1)
    lo_power: float = 20

    def __post_init__(self):
        intermods = mixer_products(*self.order)
        spurs = pd.DataFrame(intermods, columns=["n", "m"])
        spurs["level"] = [henderson(n, m) for n, m in intermods]
        colormap = getattr(colorcet, "glasbey")
        spurs["color"] = colormap[: len(spurs)]

        self.spurs = spurs

        self._plot()

    def _plot(self):
        rf = np.logspace(np.log10(0.1), np.log10(10), num=200)

        fig, ax = plt.subplots(1, figsize=(8, 8), dpi=100)

        for _, spur in self.spurs.iterrows():
            if spur.n != 0:
                lo = 1 / spur.n - spur.m / spur.n * rf
                ax.loglog(rf, lo, label=f"({spur.n},{spur.m})", color=spur.color)

        self.ax = ax
        self.fig = fig
        self._annotate_axes()

    def _annotate(self):
        ticks = [0.1, 0.2, 0.3, 0.5, 0.7, 1, 2, 3, 5, 7, 10]
        limits = (ticks[0], ticks[-1])

        ax = self.ax
        # TODO: IF/n or nLO depending on tx or rx
        ax.loglog(limits, limits, label="LO rerad")
        ax.vlines(1, *limits, label="RF feedthru")

        ax.set_xticks(ticks)
        ax.set_yticks(ticks)
        ax.set_xticklabels(ticks)
        ax.set_yticklabels(ticks)
        ax.set_xlim(*limits)
        ax.set_ylim(*limits)
        ax.set_xlabel("RF/IF")
        ax.set_ylabel("LO/IF")
        ax.set_title(f"Normalized Spurs: |n|≤{self.order[0]}, |m|≤{self.order[1]}")
        ax.grid()
        leg = ax.legend(ncol=4, loc="upper left", fontsize="x-small")
        leg._legend_box.align = "left"
