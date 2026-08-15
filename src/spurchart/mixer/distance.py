"""Spur Distance Module."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import numpy as np
import matplotlib.pyplot as plt


@dataclass
class SpurDistanceBase(ABC):
    rf: tuple
    bw: float
    desired: tuple
    if1: float
    if2: float
    spurs: list[tuple] = field(default_factory=list)
    n: int = 1001

    def __post_init__(self):
        rf_range = np.linspace(*self.rf, self.n)
        flo1 = self.lo_range(sideband=self.desired, rf_range=rf_range, fif=self.if1)
        flo2 = self.lo_range(sideband=self.desired, rf_range=rf_range, fif=self.if2)

        self.rf_range = rf_range

        distances = {}
        for spur in self.spurs:
            edge_args = dict(spur=spur, desired=self.desired, bw=self.bw)
            d1 = self.edge_to_edge_distance(flo=flo1, fif=self.if1, **edge_args)
            d2 = self.edge_to_edge_distance(flo=flo2, fif=self.if2, **edge_args)
            distances[spur] = (d1, d2)

        self.distances = distances

    @property
    def min(self):
        mindistance = self.mindistance
        index_of_min = mindistance.argmin()
        y = mindistance[index_of_min]
        x = self.rf_range[index_of_min]
        return (x, y)

    @staticmethod
    @abstractmethod
    def lo_range():
        pass

    @staticmethod
    @abstractmethod
    def edge_to_edge_distance():
        pass

    @staticmethod
    @abstractmethod
    def spur_extents():
        pass

    def edge_to_edge_distance(self, spur, desired, flo, fif, bw):
        """Compute the edge to edge distance between two intermodulation products."""

        desired_extent = self.spur_extents(product=desired, flo=flo, fif=fif, bw=bw)
        spur_extent = self.spur_extents(product=spur, flo=flo, fif=fif, bw=bw)

        distance = np.zeros_like(desired_extent[:, 0])
        distance_below = spur_extent[:, 1] - desired_extent[:, 0]
        distance_above = spur_extent[:, 0] - desired_extent[:, 1]

        distance = np.where(distance_below < 0, distance_below, distance)
        distance = np.where(distance_above > 0, distance_above, distance)
        return distance

    def plot(self, ylim=(0, 20)):
        fig, ax = plt.subplots(1)

        distances = self.distances
        frf = self.rf_range
        bw = self.bw

        maxdistance_per_spur = {}
        for spur, (distance1, distance2) in distances.items():
            n, m = spur
            (line,) = ax.plot(
                frf,
                abs(distance1),
                ls="-.",
                # label=f"({n},{m}) for IF = {fif1} GHz",
                label="_",
                alpha=0.5,
            )
            color = line.get_color()
            ax.plot(
                frf,
                abs(distance2),
                ls="--",
                # label=f"({n},{m}) for IF = {fif2} GHz",
                label="_",
                color=color,
                alpha=0.5,
            )
            # maxdistance_per_spur[spur] = np.vstack((abs(distance1),abs(distance2))).max(axis=0)
            maxdistance_per_spur[spur] = maxdistance = np.maximum(
                abs(distance1), abs(distance2)
            )
            ax.plot(frf, maxdistance_per_spur[spur], color=color, label=f"({n},{m})")

        mindistance = np.vstack([*maxdistance_per_spur.values()]).min(axis=0)
        ax.plot(frf, mindistance, color="k", label="Max", ls="--")
        self.mindistance = mindistance

        ax.set_ylim(0, 20)
        ax.legend()
        ax.set_ylabel("Absolute Distance to Nearest (n,m) Spur [GHz]")
        ax.set_xlabel("Tune Frequency [GHz]")
        n, m = self.desired
        ax.set_title(
            f"BW = {self.bw}, GHz, IF1 = {self.if1} GHz, IF2 = {self.if2} GHz, Sideband = ({n},{m})",
            fontsize="small",
        )
        return fig, ax


@dataclass
class SpurDistanceTx(SpurDistanceBase):

    @staticmethod
    def spur_extents(product, flo, fif, bw):
        """Compute the extents of a mixer intermodulation product in a transmitter."""
        n, m = product

        rf_edge_1 = n * flo + m * (fif + bw / 2)
        rf_edge_2 = n * flo + m * (fif - bw / 2)

        lower = np.minimum(rf_edge_1, rf_edge_2)
        upper = np.maximum(rf_edge_1, rf_edge_2)

        return np.array([lower, upper]).transpose()

    @staticmethod
    def lo_range(sideband, rf_range, fif):
        """Compute the LO range given RF range, IF, and sideband for a transmitter.

        sideband is of the form (n,m), where n*LO + m*IF = RF

        TODO: might be able to just call spur_extends_tx() with bw=0
        """
        n, m = sideband
        return (rf_range - m * fif) / n


@dataclass
class SpurDistanceRx(SpurDistanceBase):

    @staticmethod
    def spur_extents(product, flo, fif, bw):
        """Compute the extents of a mixer intermodulation product in a receiver."""
        n, m = product

        rf_edge_1 = (fif + bw / 2 - n * flo) / m
        rf_edge_2 = (fif - bw / 2 - n * flo) / m

        lower = np.minimum(rf_edge_1, rf_edge_2)
        upper = np.maximum(rf_edge_1, rf_edge_2)

        return np.array([lower, upper]).transpose()

    @staticmethod
    def lo_range(sideband, rf_range, fif):
        """Compute the LO range given RF range, IF, and sideband for a receiver.

        sideband is of the form (n,m), where n*LO + m*RF = IF

        TODO: might be able to just call spur_extends_rx() with bw=0
        """
        n, m = sideband
        return (fif - m * rf_range) / n
