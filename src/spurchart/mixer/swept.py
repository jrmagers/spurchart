"""Swept spurchart class."""

from dataclasses import dataclass
from typing import Tuple, Union

import colorcet
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
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


@dataclass(kw_only=True)
class SweptBase:
    """Base class for a swept frequency spur chart."""

    flo: Tuple[float, float]
    lo_power: float = 20
    bw: float
    threshold: float = _THRESHOLD
    order: Tuple[int, int] = (5, 5)
    units: str = _FREQUENCY_UNITS
    gain: float = -8
    rf_if: float = 25
    lo_rf: float = 40
    lo_if: float = 40
    in_power: float = 0
    levels: bool = True

    def _annotate_axes(self):
        ax = self.ax
        units = self.units

        if self.direction == "tx":
            xlimits = self.fout
            fixed_frequency = self.fin
            if self.conversion == "up":
                sweep_label = "RF Out"
                fixed_frequency_name = "IF"
            if self.conversion == "down":
                sweep_label = "IF Out"
                fixed_frequency_name = "RF"

        else:
            xlimits = self.fin
            fixed_frequency = self.fout
            if self.conversion == "up":
                sweep_label = "IF In"
                fixed_frequency_name = "RF"
            if self.conversion == "down":
                sweep_label = "RF In"
                fixed_frequency_name = "IF"

        if self.conversion == "up":
            equation = "n·LO+m·IF=RF"
        if self.conversion == "down":
            equation = "n·LO+m·RF=IF"

        # title and axis labels

        title_str1 = f"{self.conversion.capitalize()}converting {self.direction.upper()}: "
        title_str2 = [
            f"{fixed_frequency_name} = {fixed_frequency} {units}",
            f"$BW$ = {self.bw} {units}\n",
        ]

        info_str = [
            f"$P_{{IN}}$ = {self.in_power:+0.0f} dBm",
            f"$P_{{LO}}$ = {self.lo_power:+0.0f} dBm",
            f"$L_{{C}}$ = {-self.gain} dB",
            f"$I_{{RF-IF}}$ = {self.rf_if} dB",
            f"$I_{{LO-RF}}$ = {self.lo_rf} dB",
            f"$I_{{LO-IF}}$ = {self.lo_if} dB",
        ]
        ax.text(
            x=xlimits[0],
            y=self.flo[1],
            s=", ".join(info_str),
            fontsize="medium",
            va="bottom",
            zorder=11,
        )

        ax.set_title(title_str1 + ", ".join(title_str2), loc="left")
        ax.set_xlabel(f"{sweep_label} Frequency [{units}]")
        ax.set_ylabel(f"LO Frequency [{units}]")

        # axes grid and scale

        # get scale factor k to pick some appropriate ticks
        if self.units == "MHz":
            k = 1000
        elif self.units == "GHz":
            k = 1
        else:
            raise ValueError

        # xaxis

        ax.set_xlim(xlimits)
        xrange = xlimits[1] - xlimits[0]

        if xrange * k <= 10 * k:
            xstep = 1
            ax.grid(visible=True, which="minor", axis="x", color=_LIGHT_GRAY)
        elif 10 * k > xrange >= 50 * k:
            xstep = 5
            ax.grid(visible=True, which="minor", axis="x", color=_LIGHT_GRAY)
        else:
            xstep = 10

        ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(xstep))
        # ax.xaxis.set_major_locator(ticker.MultipleLocator(xstep))

        # yaxis

        ax.set_ylim(self.flo)
        yrange = self.flo[1] - self.flo[0]

        if yrange * k <= 10 * k:
            ystep = 1
            ax.grid(visible=True, which="minor", axis="y", color=_LIGHT_GRAY)
        elif 10 * k > xrange >= 50 * k:
            xstep = 5
            ax.grid(visible=True, which="minor", axis="y", color=_LIGHT_GRAY)
        else:
            ystep = 10

        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(ystep))
        # ax.yaxis.set_major_locator(ticker.MultipleLocator(ystep))

        # ax.grid(visible=True, which="both", color=_LIGHT_GRAY, linestyle="-")
        ax.grid(visible=True, which="major", color=_LIGHT_GRAY, linestyle="-", axis="both")

        # ax.grid(visible=True, which="major", axis="x", color=_DARK_GRAY)
        # ax.grid(visible=True, which="major", axis="y", color=_LIGHT_GRAY)

        # legend

        legend_text = [
            "(n,m) spurs:",
            equation,
            f"≥{self.threshold:0.0f} dBc, |n|≤{self.order[0]}, |m|≤{self.order[1]}",
        ]

        ncol = 1
        width_scale = 0.875
        if self.spurs.shape[0] > 20:
            ncol = 2
            width_scale = 0.75

        leg = ax.legend(
            loc="upper left",
            bbox_to_anchor=(1, 1),
            ncol=ncol,
            frameon=False,
            fontsize="small",
            title="\n".join(legend_text) + "\n",
        )
        leg._legend_box.align = "left"

        # Shink current axis by width_scale
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * width_scale, box.height])

    def describe(self):
        """Docstring."""
        # print("Downconverting Receiver with Fixed IF Output")
        print(f"class: {self.__class__.__name__}")
        print(f"direction: {self.direction}")
        print(f"conversion: {self.conversion}")
        # print(f"RF = {self.frf}")
        # print(f"IF = {self.fif}")
        # print(f"LO = {self.flo}")

        # print(f"{self.conversion.capitalize()}converting Transmiter with Fixed IF Input")
        # print("Receiver with [] GHz RF Input Downconverted to x GHz IF Output")


@dataclass
class SweptTransmit(SweptBase):
    """Plot the swept spurchart of a transmitter."""

    frf: Union[float, Tuple[float, float]]
    fif: Union[float, Tuple[float, float]]

    # TODO: indicate RF/IF level in dBm and LO level for spur model:
    #         downconversion: PRF = -10 dBm
    #         upconversion    PIF = -10 dBm

    def __post_init__(self):
        self.direction = "tx"

        # Whether this is an upconverter or downconverter will be inferred from the length, or
        # more succinctly, from whether self.frf and self.fif have a __len__ attribute which
        # indicates that they are arraylike or not.

        if hasattr(self.fif, "__len__") and not hasattr(self.frf, "__len__"):
            self.fin = self.frf
            self.fout = self.fif
            self.conversion = "down"
        elif hasattr(self.frf, "__len__") and not hasattr(self.fif, "__len__"):
            self.fin = self.fif
            self.fout = self.frf
            self.conversion = "up"
        else:
            error_msg = [
                "One of the arguments frf or fif must be arraylike with a length of 2 and the ",
                "other argument must be scalar. Whether this is an upconversion or ",
                "downconversion will be inferred from the length of these arguments",
            ]
            raise ValueError("".join(error_msg))

        self._generate_spur_table()
        self._plot_spur_table()

    def _plotspur(self, row):
        ax = self.ax

        fin = self.fin
        bw = self.bw
        fout = self.fout

        # label helpers
        if self.conversion == "up":
            outport = "RF"
            inport = "IF"
        if self.conversion == "down":
            outport = "IF"
            inport = "RF"

        if row.m == 0:
            if row.n == 1:
                label = f"{outport} = LO: {row.level:0.0f} dBc"
            else:
                label = f"{outport} = {row.n}·LO: {row.level:0.0f} dBc"

            p = ax.plot(self.fout, row.flo_min, label=label)

        elif row.n == 0:
            if_edge = fin * row.m - bw / 2 * row.m

            width = bw * row.m
            if_center = fin * row.m

            if row.m == 1:
                label = f"{outport} = {inport}: {row.level:0.0f} dBc"
            else:
                label = f"{outport} = {row.m}·{inport}: {row.level:0.0f} dBc"

            cond1 = min(self.fout) <= if_edge <= max(self.fout)
            cond2 = min(self.fout) <= if_edge + width <= max(self.fout)

            if not (cond1 or cond2):
                # the spur is not within the x-axis limits, so hide it
                label = "_"

            rect = Rectangle(
                (if_edge, self.flo[0]),
                width=width,
                height=self.flo[1] - self.flo[0],
                label=label,
                color=row.color,
                alpha=0.5,
                zorder=5,
            )
            p = ax.add_patch(rect)

            ax.vlines(
                if_center,
                self.flo[0],
                self.flo[1],
                label="_",
                lw=0.5,
                color=row.color,
                zorder=5,
            )

        # all other spurs

        else:
            label = f"({row.n},{row.m})"
            if self.levels:
                label += f": {row.level:0.0f} dBc"

            # plot with bandwidth
            p = ax.fill_between(
                fout, row.flo_min, row.flo_max, label=label, color=row.color, alpha=0.5, zorder=10
            )

            # plot band center
            ax.plot(
                fout,
                (row.flo_min + row.flo_max) / 2,
                color=row.color,
                label="_",
                lw=0.5,
            )

        return p

    @staticmethod
    def upconvert_lo(row, fout, fin):
        """Upconversion: RF = nLO + mIF."""
        fout = np.array(fout)  # cast to numpy array

        if row.n == 0:
            flo = np.inf
        else:
            flo = (fout - row.m * fin) / row.n
        return flo

    def band(self, n: int, m: int, f: Tuple[float, float], bw=None, **kwargs):
        """Annotate a band on the spurchart using a rectangle.

        Parameters
        ----------
        n : int
            intermod n
        m : int
            intermod m
        f : tuple
            beginning and ending frequency of band
        bw : float
            instantaneous bandwidth. Default is self.bw.

        Other Parameters
        ----------------
        **kwargs : `matplotlib.patches.Patch` properties
            Patch properties passed to matplotlib.patches.Rectangle

        """
        f1 = min(f)
        f2 = max(f)

        kwargs.setdefault("fill", False)
        kwargs.setdefault("linewidth", 2)
        kwargs.setdefault("zorder", 10)
        kwargs.setdefault("label", f"Band: [{f1},{f2}] {self.units}")

        # determine LO frequencies
        flo1 = (f1 - m * self.fin) / n
        flo2 = (f2 - m * self.fin) / n

        if bw is None:
            bw = self.bw

        width = f2 - f1
        height = flo2 - flo1 - bw
        xy = (f1, flo1 + bw / 2)

        rect = Rectangle(xy=xy, width=width, height=height, **kwargs)
        self.ax.add_patch(rect)

    def _generate_spur_table(self):
        intermods = mixer_products(*self.order)
        spurs = pd.DataFrame(intermods, columns=["n", "m"])
        spurs["level"] = [
            henderson(n, m, Plo=self.lo_power, Prf=self.in_power) for n, m in intermods
        ]

        spurs.loc[spurs[(spurs.n == 0) & (spurs.m == 1)].index, "level"] = _if_supression(
            self.gain, self.rf_if
        )  # correct (0,1) spur based on conversion gain and RF-IF isolation

        isolation = self.lo_rf

        spurs.loc[spurs[(spurs.n == 1) & (spurs.m == 0)].index, "level"] = _lo_supression(
            self.gain, isolation, self.in_power, self.lo_power
        )  # correct (1,0) spur based on conversion gain and isolation

        colormap = getattr(colorcet, "glasbey")
        spurs["color"] = colormap[: len(spurs)]

        fout = self.fout
        flo = self.flo
        fin = self.fin
        bw = self.bw

        spurs["flo_min"] = spurs.apply(self.upconvert_lo, args=(fout, fin - bw / 2), axis=1)
        spurs["flo_max"] = spurs.apply(self.upconvert_lo, args=(fout, fin + bw / 2), axis=1)

        cond1 = (spurs.flo_min.apply(np.max) > flo[0] - bw / 2) | (
            (spurs.n.apply(np.abs) == 0) & (spurs.m > 0)
        )
        spurs = spurs[cond1]

        cond2 = (spurs.flo_max.apply(np.min) < flo[1] + bw / 2) | (
            (spurs.n.apply(np.abs) == 0) & (spurs.m > 0)
        )
        spurs = spurs[cond2]

        # eliminate spurs below threshold
        spurs = spurs[spurs["level"] >= self.threshold]

        # sort spurs by reverse suppression order
        # spurs.sort_values(by=["level"], ascending=False, inplace=True)

        self.spurs = spurs

    def _plot_spur_table(self):
        self.fig, self.ax = plt.subplots(1, figsize=(10, 5.5))

        self.spurs["level"] = self.spurs.apply(self._plotspur, axis=1)

        self._annotate_axes()


@dataclass
class SweptReceive(SweptBase):
    """Plot the swept spurchart of a receiver."""

    frf: Union[float, Tuple[float, float]]
    fif: Union[float, Tuple[float, float]]

    # TODO: indicate RF/IF level in dBm and LO level for spur model:
    #         downconversion: PRF = -10 dBm
    #         upconversion    PIF = -10 dBm

    def __post_init__(self):
        self.direction = "rx"

        # Whether this is an upconverter or downconverter will be inferred from the length, or
        # more succinctly, from whether self.frf and self.fif have a __len__ attribute which
        # indicates that they are arraylike or not.

        if hasattr(self.frf, "__len__") and not hasattr(self.fif, "__len__"):
            self.fin = self.frf
            self.fout = self.fif
            self.conversion = "down"
        elif hasattr(self.fif, "__len__") and not hasattr(self.frf, "__len__"):
            self.fin = self.fif
            self.fout = self.frf
            self.conversion = "up"
        else:
            error_msg = [
                "One of the arguments frf or fif must be arraylike with a length of 2 and the ",
                "other argument must be scalar. Whether this is an upconversion or ",
                "downconversion will be inferred from the length of these arguments",
            ]
            raise ValueError("".join(error_msg))

        self._generate_spur_table()
        self._plot_spur_table()

    def _plotspur(self, row):
        ax = self.ax

        fout = self.fout
        bw = self.bw
        fin = self.fin

        # label helpers
        if self.conversion == "up":
            inport = "IF"
            outport = "RF"
        if self.conversion == "down":
            inport = "RF"
            outport = "IF"

        if row.m == 0:
            if row.n == 1:
                label = f"{inport} = LO: {row.level:0.0f} dBc"
            else:
                label = f"{inport} = LO/{row.n}: {row.level:0.0f} dBc"

            p = ax.plot(self.fin, row.flo_min, label=label)

        elif row.n == 0:
            if_edge = fout / row.m - bw / 2 / row.m

            width = bw / row.m
            if_center = fout / row.m

            if row.m == 1:
                label = f"{inport} = {outport}: {row.level:0.0f} dBc"
            else:
                label = f"{inport} = {outport}/{row.m}: {row.level:0.0f} dBc"

            cond1 = min(self.fin) <= if_edge <= max(self.fin)
            cond2 = min(self.fin) <= if_edge + width <= max(self.fin)

            if not (cond1 or cond2):
                # the spur is not within the x-axis limits, so hide it
                label = "_"

            rect = Rectangle(
                (if_edge, self.flo[0]),
                width=width,
                height=self.flo[1] - self.flo[0],
                label=label,
                color=row.color,
                alpha=0.5,
                zorder=5,
            )
            p = ax.add_patch(rect)

            ax.vlines(
                if_center,
                self.flo[0],
                self.flo[1],
                label="_",
                lw=0.5,
                color=row.color,
                zorder=5,
            )

        # all other spurs

        else:
            label = f"({row.n},{row.m})"
            if self.levels:
                label += f": {row.level:0.0f} dBc"

            # plot with bandwidth
            p = ax.fill_between(
                fin, row.flo_min, row.flo_max, label=label, color=row.color, alpha=0.5, zorder=10
            )

            # plot band center
            ax.plot(
                fin,
                (row.flo_min + row.flo_max) / 2,
                color=row.color,
                label="_",
                lw=0.5,
            )

        return p

    @staticmethod
    def downconvert_lo(row, fin, fout):
        """Downconversion: IF = nLO + mRF."""
        fin = np.array(fin)  # ca

        if row.n == 0:
            flo = np.inf

        elif row.m == 0:
            flo = row.n * fin

        else:
            flo = (fout - row.m * fin) / row.n

        return flo

    def band(self, n: int, m: int, f: Tuple[float, float], bw=None, **kwargs):
        """Annotate a band on the spurchart using a rectangle.

        Parameters
        ----------
        n : int
            intermod n
        m : int
            intermod m
        f : tuple
            beginning and ending frequency of band
        bw : float
            instantaneous bandwidth. Default is self.bw.

        Other Parameters
        ----------------
        **kwargs : `matplotlib.patches.Patch` properties
            Patch properties passed to matplotlib.patches.Rectangle
        """
        f1 = min(f)
        f2 = max(f)

        kwargs.setdefault("fill", False)
        kwargs.setdefault("linewidth", 2)
        kwargs.setdefault("zorder", 10)
        kwargs.setdefault("label", f"Band: [{f1},{f2}] {self.units}")

        # determine LO frequencies
        flo1 = (f1 - m * self.fout) / n
        flo2 = (f2 - m * self.fout) / n

        if bw is None:
            bw = self.bw

        width = f2 - f1
        height = abs(flo2 - flo1) - bw

        if n > 0 and m > 0:
            xy = (f1, -flo1 - height - bw / 2)  # TODO: <-- is correct?
            print(">> NEED TO TEST n>0,m>0")
        elif n < 0 and m > 0:
            xy = (f1, -flo1 - bw / 2)  # TODO: <-- is correct?
            print(">> NEED TO TEST n<0,m>0")
        else:
            xy = (f1, flo1 + bw / 2)  # tested -- works correctly

        rect = Rectangle(xy=xy, width=width, height=height, **kwargs)
        self.ax.add_patch(rect)

    def _generate_spur_table(self):
        intermods = mixer_products(*self.order)
        spurs = pd.DataFrame(intermods, columns=["n", "m"])
        spurs["level"] = [
            henderson(n, m, Plo=self.lo_power, Prf=self.in_power) for n, m in intermods
        ]

        spurs.loc[spurs[(spurs.n == 0) & (spurs.m == 1)].index, "level"] = _if_supression(
            self.gain, self.rf_if
        )  # correct (0,1) spur based on conversion gain and RF-IF isolation

        isolation = self.lo_if

        spurs.loc[spurs[(spurs.n == 1) & (spurs.m == 0)].index, "level"] = _lo_supression(
            self.gain, isolation, self.in_power, self.lo_power
        )  # correct (1,0) spur based on conversion gain and isolation

        colormap = getattr(colorcet, "glasbey")
        spurs["color"] = colormap[: len(spurs)]

        fin = self.fin
        flo = self.flo
        fout = self.fout
        bw = self.bw

        spurs["flo_min"] = spurs.apply(self.downconvert_lo, args=(fin, fout - bw / 2), axis=1)
        spurs["flo_max"] = spurs.apply(self.downconvert_lo, args=(fin, fout + bw / 2), axis=1)

        cond1 = (spurs.flo_min.apply(np.max) > flo[0] - bw) | (
            (spurs.n.apply(np.abs) == 0) & (spurs.m > 0)
        )
        spurs = spurs[cond1]

        cond2 = (spurs.flo_max.apply(np.min) < flo[1] + bw) | (
            (spurs.n.apply(np.abs) == 0) & (spurs.m > 0)
        )
        spurs = spurs[cond2]

        # eliminate spurs below threshold
        spurs = spurs[spurs["level"] >= self.threshold]

        # sort spurs by reverse suppression order
        # spurs.sort_values(by=["level"], ascending=False, inplace=True)

        self.spurs = spurs

    def _plot_spur_table(self):
        self.fig, self.ax = plt.subplots(1, figsize=(10, 5.5))

        self.spurs["level"] = self.spurs.apply(self._plotspur, axis=1)

        self._annotate_axes()
