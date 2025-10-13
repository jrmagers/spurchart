# %%
import schemdraw
from schemdraw import dsp
import pathlib

assets_folder = pathlib.Path.cwd().parent / "spurchart" / "docs" / "assets"
# drawing_config = {"fontsize": 12, "bgcolor": "white"}
drawing_config = {"fontsize": 12, "color": "grey"}

# %% Downconversion Receive
with schemdraw.Drawing() as d:
    d.config(**drawing_config)
    d += dsp.Arrow().length(d.unit / 3).label("RF").label("in", "left", ofst=0.2)
    d += (mix := dsp.Mixer())
    d += dsp.Line().at(mix.S).down(d.unit / 4)
    d += dsp.Oscillator().right().anchor("N").label("LO", "right", ofst=0.2)
    d += dsp.Arrow().at(mix.E).right(d.unit / 3).label("IF")
    d += dsp.Filter(response="bp").anchor("W")
    d += dsp.Arrow().right(d.unit / 4).label("out", "right", ofst=0.2)
    d.save(assets_folder / "RxDown.svg", transparent=True)

# %% Upconversion Receive
with schemdraw.Drawing() as d:
    d.config(**drawing_config)
    d += dsp.Arrow().length(d.unit / 3).label("IF").label("in", "left", ofst=0.2)
    d += (mix := dsp.Mixer())
    d += dsp.Line().at(mix.S).down(d.unit / 4)
    d += dsp.Oscillator().right().anchor("N").label("LO", "right", ofst=0.2)
    d += dsp.Arrow().at(mix.E).right(d.unit / 3).label("RF")
    d += dsp.Filter(response="bp").anchor("W")
    d += dsp.Arrow().right(d.unit / 4).label("out", "right", ofst=0.2)
    d.save(assets_folder / "RxUp.svg", transparent=True)

# %% Transmit Downconversion
with schemdraw.Drawing() as d:
    d.config(**drawing_config)
    d += dsp.Arrow().length(d.unit / 4).label("in", "left", ofst=0.2)
    d += dsp.Filter(response="bp")  # .anchor('W')
    d += dsp.Arrow().right(d.unit / 3).label("RF")
    d += (mix := dsp.Mixer())
    d += dsp.Line().at(mix.S).down(d.unit / 4)
    d += dsp.Oscillator().right().anchor("N").label("LO", "right", ofst=0.2)
    d += dsp.Arrow().at(mix.E).right(d.unit / 3).label("IF").label("out", "right", ofst=0.2)
    d.save(assets_folder / "TxDown.svg", transparent=True)


# %% Transmit Downconversion
with schemdraw.Drawing() as d:
    d.config(**drawing_config)
    d += dsp.Arrow().length(d.unit / 4).label("in", "left", ofst=0.2)
    d += dsp.Filter(response="bp")  # .anchor('W')
    d += dsp.Arrow().right(d.unit / 3).label("IF")
    d += (mix := dsp.Mixer())
    d += dsp.Line().at(mix.S).down(d.unit / 4)
    d += dsp.Oscillator().right().anchor("N").label("LO", "right", ofst=0.2)
    d += dsp.Arrow().at(mix.E).right(d.unit / 3).label("RF").label("out", "right", ofst=0.2)
    d.save(assets_folder / "TxUp.svg", transparent=True)
