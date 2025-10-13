"""Mixer spur rejection models."""

import pathlib
from math import factorial
from numpy import sin, cos, log10, nan, sqrt, pi
from scipy.special import gamma as gamma


def henderson(n, m, d=(0.85, 0.95, 1.05), Prf=0, Plo=20, lo_iso=10.45757, rf_iso=10.45757):
    """Bert Henderson's spur rejectino model.

    The default arguments are the values used in the reference document.

    DEFAULTS:
    -----------
    RF Power = 0 dBm
    LO Power = +20 dBm
    L Balun Isolation = 10.45757 dB (α = 0.7)
    R Balun Isolation = 10.45757 dB (β = 0.7)

    EXAMPLE
    -------
    Create Classic spur chart per Henderson's table:

    >>> from spurchart import henderson
    >>> import itertools
    >>> suppression = {}
    >>> for intermod in itertools.product((1,2,3,4,5),(1,2,3,4,5,6,7)):
    >>>    suppression[n,m] = henderson(*intermod)

    REFERENCE
    ---------
    Henderson, Bert C. "Predicting intermodulation suppression in double-balanced
    mixers." 97-98 RF and Microwave Designer's Handbook (1993): 495-501.
    http://read.pudn.com/downloads145/ebook/631954/RFCD_22.pdf
    """
    𝛿2, 𝛿3, 𝛿4 = d

    # VL is RF voltage across diode in Volts-peak in 50 ohm system
    VL = sqrt(10 ** (Plo / 10) * 50 / 125) / 2

    # VF is RF voltage across diode in Volts-peak in 50 ohm system
    VF = sqrt(10 ** (Prf / 10) * 50 / 125) / 2

    α = 1 - 10 ** (-lo_iso / 20)
    β = 1 - 10 ** (-rf_iso / 20)

    n = abs(n)
    m = abs(m)

    Bif = 1 + 𝛿4 + α * (𝛿3 + 𝛿2) - 1 * (𝛿4 - 𝛿2 + α * (𝛿3 + 𝛿2) - β * (𝛿3 + 𝛿4))
    Boo = 1 + 𝛿4 + α * (𝛿3 + 𝛿2) - m * (𝛿4 - 𝛿2 + α * (𝛿3 + 𝛿2) - β * (𝛿3 + 𝛿4))
    Bee = -1 + 𝛿4 - α * (𝛿3 - 𝛿2) - m * (𝛿4 - 𝛿2 - α * (𝛿3 - 𝛿2) + β * (𝛿3 - 𝛿4))
    Boe = m * (-𝛿4 - 𝛿2 + α * (𝛿3 + 𝛿2) + β * (𝛿4 - 𝛿3))
    Beo = m * (𝛿4 + 𝛿2 + α * (𝛿3 - 𝛿2) - β * (𝛿4 + 𝛿3))

    ssBoo = sin(n * pi / 2) * sin(m * pi / 2) * Boo
    ccBee = cos(n * pi / 2) * cos(m * pi / 2) * Bee
    scBoe = sin(n * pi / 2) * cos(m * pi / 2) * Boe
    csBeo = cos(n * pi / 2) * sin(m * pi / 2) * Beo

    if not (m == 0 and n == 0):
        part1 = gamma((n + m - 1) / 2) / gamma((n - m + 3) / 2) * 0.5 * (ssBoo + ccBee)
        part2 = gamma((n + m) / 2) / gamma((n - m + 2) / 2) * VF / VL * (scBoe + csBeo)
        Ap = part1 + part2

    else:
        Ap = nan

    A = 20 * log10(abs(Ap / (Bif * factorial(m))))

    # ratio of RF power to LO power in dB
    ΔP = Prf - Plo

    # spur suppression relative to IF
    return (m - 1) * ΔP + A


def from_file(filename: str | pathlib.Path):
    """Load a spur model from a file."""
    raise NotImplementedError
