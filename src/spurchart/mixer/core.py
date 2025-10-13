"""Core methods and functions for spurchart."""

import itertools as it

_LIGHT_GRAY = [0.9, 0.9, 0.9]
_DARK_GRAY = [0.6, 0.6, 0.6]
_FREQUENCY_UNITS = "GHz"
_THRESHOLD = -100


def mixer_products(max_n: int, max_m: int):
    """Compute possible n,m combinations."""
    # cartesian product
    intermods = it.product(range(-max_n, max_n + 1), range(-max_m, max_m + 1))

    # eliminate impossible spurs
    intermods = [(n, m) for n, m in intermods if n > 0 or m > 0]

    return intermods


def _lo_supression(gain: float = -8, isolation: float = 40, rf_power=0, lo_power=20):
    """Compute suppression for (m,n) = (1,0) based on conversion gain and LO-IF or LO-RF isolation.

    conversion gain in dB, 'gain',  can be positive or negative

    isolation in dB should be greater than 0 dB

    rf_power is the input power to the mixer
    lo_power is the LO power to the mixer

    """
    if isolation < 0:
        raise ValueError

    return (lo_power - isolation) - (rf_power + gain)


def _if_supression(gain: float = -8, isolation: float = 25):
    """Compute suppression for (m,n) = (0,1) based on conversion gain and RF-IF isolation.

    conversion gain in dB, 'gain',  can be positive or negative

    RF-IF isolation in dB should be greater than 0 dB
    """
    if isolation < 0:
        raise ValueError

    return -gain - isolation
