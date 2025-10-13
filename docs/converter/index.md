# Converter Spurcharts

## ADC

The x-axis represents the *tune frequency* of a digital down-converter, or DDC, which is a digital implementation of a quadrature downconverter which converts signals in the digital domain down to baseband centered at 0 Hz. The y-axis is the frequency of the input signal to the ADC, denoted $f_{IN}$.  The lines on the plot represent the solutions to the following equation:

${n} \cdot f_{IN} + k \cdot \frac{f_{S}}{M} = f_{TUNE}$

where $f_S$ is the ADC sample rate, $M$ is the number of interleaved ADCs, and $k$ and $n$ are integers. The solutions are combinations of tune frequencies $f_{TUNE}$ and input signals $f_{IN}$ incident on the ADC which produce a signal in the digital domain. Most of these digital signals, called *spurious signals*, are undesired side-effects of the ADC and the digitization process. The desired signal is $(n,k) = (1,0)$ which corresponds to the case of $f_{IN} = f_{TUNE}$ which is typically the most efficient.

## DAC

coming soon....

For an analog-to-digital converter (ADC), the signals at $f_{OUT}$ are created in the digital domain when $f_{IN}$ is the frequency of a sinousoidal signal incident upon the ADC input [1]:

$f_{OUT} = {n}f_{IN} + \frac{k}{M}f_{S}$

where $f_{S}$ is the sample rate, $n$ is an integer, and $k$ is an integer, and $M$ is the number of interleaved ADCs.

> TODO: insert the table from the TI app note.

## DAC

For a digital-to-analog converter (DAC), the same equation holds, but $f_{OUT}$ represents the analog output of the DAC and $f_{IN}$ represents a sinusoidal signal in the digital domain.

## Aliasing Discussion

These products can then be "aliased" or "folded" back to other Nyquist zones due to the nature of discrete time systems.

[1]: Lin, X. "Spurs Analysis in the RF Sampling ADC." *Texas Instruments* (2018).
