"""Top Level mixer spurchart.

Contains logic to decide what kind of spur chart is being asked for.
"""
import textwrap
from typing import Tuple, Union


_ERROR_MSG = """
One of the arguments frf or fif must be arraylike with a length of 2 and the other argument must be
scalar. Whether this is an upconversion or downconversion will be inferred from the length of these
arguments."""


def transmit(
    frf: Union[float, Tuple[float, float]],
    fif: Union[float, Tuple[float, float]],
    flo: Union[float, Tuple[float, float]],
    bw: float,
    **args,
):
    """Create a spur chart for a transmitter.

    The x-axis represents the frequencies at which the transmiiter generates intermodulation
    products, i.e. the frequencies at which they will be converted to the swept frequency output.

    The spur chart can be a swept spur chart or a spectrum plot. The type of chart will be inferred
    from the `flo` parameter: if `flo` is arraylike, then a swept spur chart will be plotted; if
    `flo` is scalar, then a spectrum plot will be plotted.

    The direction, either upconversion or downconversion, will be inferred from the parameters `frf`
    and `fif` as follows:
     - if `frf` is scalar and `fif` is arraylike, then downconversion
     - if `frf` is arraylike and `fif` is scalar, then upconversion

    The levels of the intermodulation products will be determined from Bert Henderson's model.

    Parameters
    ----------
    frf : arraylike with 2 elements or scalar
        RF frequency or frequencies
    fif : arraylike with 2 elements or scalar
        IF frequency or frequencies
    flo : arraylike with 2 elements or scalar
        LO frequency or frequencies
    bw : float
        instantaneous bandwidth

    Optional Parameters
    -------------------
    gain : float, default -8
        conversion gain in dB
    rf_if : float, default 25
        RF to IF isolation in dB
    lo_rf : float, default 40
        LO to RF isolation in dB
    lo_if : float, default 40
        LO to IF isolation in dB
    lo_power: float, default 20
        LO power in dBm
    order: tuple, default (5, 5)
        max order of n and m
    threshold: float, default is -100
        minimum relative spur level in dBc
    units : str, default is 'GHz'
        frequency units
    in_power: float, default 0
        mixer input power in dBm
    levels: bool, default True
        plot relative spur levels in legend on spectrum plots

    Reference
    ---------
    Henderson, Bert C. "Predicting intermodulation suppression in double-balanced mixers."
        97-98 RF and Microwave Designer's Handbook (1993): 495-501.

        http://read.pudn.com/downloads145/ebook/631954/RFCD_22.pdf

    """
    # Whether this is an upconverter or downconverter will be inferred from the length, or
    # more succinctly, from whether frf and fif have a __len__ attribute which
    # indicates that they are arraylike or not.

    # If flo is a scalar, then the spectrum will be plotted. Otherwise, a swept spurchart
    # will be plotted

    swept_lo = hasattr(flo, "__len__")
    swept_rf = hasattr(frf, "__len__")
    swept_if = hasattr(fif, "__len__")

    if swept_if and not swept_rf:
        # downconversion

        if swept_lo:
            # swept downconversion

            from spurchart.mixer.swept import SweptTransmit

            return SweptTransmit(frf=frf, fif=fif, flo=flo, bw=bw, **args)
        else:
            # spectrum downconversion

            from spurchart.mixer.spectrum import TxDown

            return TxDown(frf=frf, fif=fif, flo=flo, bw=bw, **args)

    elif swept_rf and not swept_if:
        # upconversion

        if swept_lo:
            # swept upconversion
            from spurchart.mixer.swept import SweptTransmit

            return SweptTransmit(frf=frf, fif=fif, flo=flo, bw=bw, **args)
        else:
            # spectrum upconversion
            from spurchart.mixer.spectrum import TxUp

            return TxUp(frf=frf, fif=fif, flo=flo, bw=bw, **args)

    else:
        raise ValueError(textwrap.fill(textwrap.dedent(_ERROR_MSG)))


def receive(
    frf: Union[float, Tuple[float, float]],
    fif: Union[float, Tuple[float, float]],
    flo: Union[float, Tuple[float, float]],
    bw: float,
    **args,
):
    """Create a spur chart for a receiver.

    The x-axis represents the frequencies at which the receiver is sensitive to intermodulation
    products, i.e. the frequencies at which they will be converted to within the bandwidth of the
    fixed frequency output.

    The spur chart can be a swept spur chart or a spectrum plot. The type of chart will be inferred
    from the `flo` parameter: if `flo` is arraylike, then a swept spur chart will be plotted; if
    `flo` is scalar, then a spectrum plot will be plotted.

    The direction, either upconversion or downconversion, will be inferred from the parameters `frf`
    and `fif` as follows:
     - if `frf` is scalar and `fif` is arraylike, then upconversion
     - if `frf` is arraylike and `fif` is scalar, then downconversion

    The levels of the intermodulation products will be determined from Bert Henderson's model.

    Parameters
    ----------
    frf : arraylike with 2 elements or scalar
        RF frequency or frequencies
    fif : arraylike with 2 elements or scalar
        IF frequency or frequencies
    flo : arraylike with 2 elements or scalar
        LO frequency or frequencies
    bw : float
        instantaneous bandwidth

    Optional Parameters
    -------------------
    gain : float, default -8
        conversion gain in dB
    rf_if : float, default 25
        RF to IF isolation in dB
    lo_rf : float, default 40
        LO to RF isolation in dB
    lo_if : float, default 40
        LO to IF isolation in dB
    lo_power: float, default 20
        LO power in dBm
    order: tuple, default (5, 5)
        max order of n and m
    threshold: float, default is -100
        minimum relative spur level in dBc
    units : str, default is 'GHz'
        frequency units
    in_power: float, default 0
        mixer input power in dBm
    levels: bool, default True
        plot relative spur levels in legend on spectrum plots

    Reference
    ---------
    Henderson, Bert C. "Predicting intermodulation suppression in double-balanced mixers."
        97-98 RF and Microwave Designer's Handbook (1993): 495-501.

        http://read.pudn.com/downloads145/ebook/631954/RFCD_22.pdf
    """
    # Whether this is an upconverter or downconverter will be inferred from the length, or
    # more succinctly, from whether frf and fif have a __len__ attribute which
    # indicates that they are arraylike or not.

    # If flo is a scalar, then the spectrum will be plotted. Otherwise, a swept spurchart
    # will be plotted

    swept_lo = hasattr(flo, "__len__")
    swept_rf = hasattr(frf, "__len__")
    swept_if = hasattr(fif, "__len__")

    if swept_rf and not swept_if:
        # downconversion

        if swept_lo:
            # swept downconversion

            from spurchart.mixer.swept import SweptReceive

            return SweptReceive(frf=frf, fif=fif, flo=flo, bw=bw, **args)
        else:
            # spectrum downconversion

            from spurchart.mixer.spectrum import RxDown

            return RxDown(frf=frf, fif=fif, flo=flo, bw=bw, **args)

    elif swept_if and not swept_rf:
        # upconversion

        if swept_lo:
            # swept upconversion

            from spurchart.mixer.swept import SweptReceive

            return SweptReceive(frf=frf, fif=fif, flo=flo, bw=bw, **args)
        else:
            # spectrum upconversion
            from spurchart.mixer.spectrum import RxUp

            return RxUp(frf=frf, fif=fif, flo=flo, bw=bw, **args)

    else:
        raise ValueError(textwrap.fill(textwrap.dedent(_ERROR_MSG)))
