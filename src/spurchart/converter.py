"""Converter (DAC/ADC) spurchart class."""

import itertools as it
from dataclasses import dataclass, field
from typing import List, Tuple

import colorcet
import numpy as np
import pandas as pd


def import_bokeh():
    """Import bokeh."""
    # from bokeh.io import curdoc, export_png
    # from bokeh.models import ColumnDataSource, HoverTool, Range1d, Title
    # from bokeh.plotting import figure, output_file, output_notebook, save, show
    # from bokeh.plotting import figure

    if is_notebook():
        output_notebook()  # make in-line Bokeh plots in Jupyter Notebook / VS Code


def is_notebook() -> bool:
    """Check if running in a Jupyter notebook."""
    try:
        shell = get_ipython().__class__.__name__
        if shell == "ZMQInteractiveShell":
            return True  # Jupyter notebook or qtconsole
        elif shell == "TerminalInteractiveShell":
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False  # Probably standard Python interpreter


def nyquist_zone(f, fs):
    """Return which Nyquist zone the frequency f is in given the sample rate fs.

    Parameters
    ----------
    f : ndarray or scalar
        frequency
    fs : scalar
        sample rate

    Returns
    -------
    ndarray of int
        an array of Nyquist zones

    """
    f = np.atleast_1d(f)

    fn = fs / 2  # Nyquist or "folding" frequency

    zone = np.ceil(f / fn).astype(int) + np.logical_not(np.sign(np.mod(f / fn, 1)))

    # is this accurate?
    # properly shift negative zones
    # zone[zone <= 0] = zone[zone <= 0] - 1

    return zone


def _reduce(x, y):
    """Reduce a fraction to its lowest form, return as string.

    TODO: handle y = -1?
    """
    d = np.gcd(x, y)
    x = x // d
    y = y // d

    if y == 1:
        result = f"{x}"
    else:
        result = f"{x}/{y}"

    return result


def converter_products(n: int, k: int, m: int):
    """Determine valid converter products.

    Reference
    ---------
    Lin, X. "Spurs Analysis in the RF Sampling ADC." *Texas Instruments* (2018).
    """

    # setting M = 1 collapses to Equation 1
    nonlinear_parameters = it.product(range(-n, n + 1), range(-k, k + 1), [1])

    # k >= 0, n = 0 results in Equation 2
    offset_mismatch = it.product([0], range(0, k + 1), [m])

    # k >= 0 results in Equation 3 and 4

    # The reference appears to be incorrect by suggesting that k >= 0. Measurement of PXIe-5860 in
    # loopback suggests that k < 0 is a valid spur.

    # gain_phase_mismatch = it.product(range(-n, n + 1), range(0, k + 1), [m]) <-- needs k < 0
    gain_phase_mismatch = it.product(range(-n, n + 1), range(-k, k + 1), [m])

    return set(it.chain(nonlinear_parameters, offset_mismatch, gain_phase_mismatch))


def _expand_to_zones(fa, fb, fs):
    """Cut a frequency range defined by interval (fa,fb) into Nyquist zones according to fs."""
    swap_cols = False

    if fb < fa:
        swap_cols = True
        fa, fb = fb, fa

    fn = fs / 2

    start_nz = np.floor(fa / fn)
    stop_nz = np.ceil(fb / fn)

    zones = fn * np.arange(start_nz, stop_nz + 1)

    zones[0] = max(zones[0], fa)
    zones[-1] = min(zones[-1], fb)

    f1 = zones[range(len(zones) - 1)]
    f2 = zones[range(1, len(zones))]

    if swap_cols:
        f1, f2 = f2, f1

    return pd.DataFrame(zip(f1, f2), columns=["ftune1", "ftune2"])


def _line_intersection(p1, p2, p3, p4):
    """Intersection of two lines L1 and L2 in 2D space.

    L1 is defined by p1 = (x1,y1) and p2 = (x2,y2).
    L2 is defined by p3 = (x3,y3) and p4 = (x4,y4).

    When the two lines are parallel or coincident, the denominator is zero.

    Reference
    ---------
    https://en.wikipedia.org/wiki/Line%E2%80%93line_intersection#Given_two_points_on_each_line

    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    x_numerator = (x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)
    y_numerator = (x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)

    px = x_numerator / denominator

    py = y_numerator / denominator

    return px, py


def _points_to_segments(p1, p2):
    """Given points p1 and p2, return the lines associated.

    returns a tuple of two points ((x1,y1),(x2,y2)) representing a line segment

    """
    x1, y1 = p1
    x2, y2 = p2

    p3 = (x1, y2)
    p4 = (x2, y1)

    line1 = (p1, p3)
    line2 = (p3, p2)
    line3 = (p2, p4)
    line4 = (p4, p1)

    return (line1, line2, line3, line4)


@dataclass
class Band:
    """Spurchart band class."""

    fa: float
    fb: float
    n: int
    k: int
    M: int
    name: str = ""
    color: str = "yellow"

    def __post_init__(self):
        pass

    def compute_alias(self, fs, input_zone, tune_zone):
        """Alias a signal from one zone to another."""
        # compute ftune
        ftune1 = self.n * self.fa + self.k / self.M * fs
        ftune2 = self.n * self.fb + self.k / self.M * fs

        fn = fs / 2

        # number of Nyquist Zones to shift
        zones_to_shift = tune_zone - input_zone

        # frequency shift
        frequency_shift = zones_to_shift * fn

        # which are even number zones
        is_odd_shift = np.mod(zones_to_shift, 2).astype(bool)

        # even shift
        ftune1_nz1 = ftune1 + frequency_shift
        ftune2_nz1 = ftune2 + frequency_shift

        if is_odd_shift:
            # reflect_frequency = 2 * center of target nyquist zone
            reflect_frequency = 2 * fn * (tune_zone - 0.5)

            # for odd shifts, add a "reflect" about the center of tne target Nyquist zone
            ftune1_nz1 = reflect_frequency - ftune1_nz1
            ftune2_nz1 = reflect_frequency - ftune2_nz1

        return ftune1_nz1, ftune2_nz1


@dataclass
class Conversion:
    """Create a spur chart for a A/D or D/A Converter.

    Sweep Nyquist Zone 'input_zone' and plot the 'input_zone' vs 'tune_zone'

    fs : sample rate

    input_zone : sweep the input over input_zone
    tune_zone: plot output frequencies aliased to 'tune_zone'. Default is 1.

    order: tuple of max order of spurs (n,k)  for ftune = n*fin + k/M*fs

    units: annotate these units

    """

    fs: float
    input_zone: int = 1
    tune_zone: int = 1
    order: Tuple[int, int] = (5, 3)
    M: int = 2
    units: str = "GHz"
    bands: List[Band] = field(default_factory=list)
    deduplicate: bool = True

    def addband(self, fa, fb, n=1, k=0, M=1, name="", color="yellow"):
        """Add a band."""
        b = Band(fa, fb, n, k, M, name, color)
        self.bands.append(b)

    def __post_init__(self):
        pd.set_option("display.max_rows", None)

        self._generate_spurs()
        self._compute_aliased_spurs()
        self._compute_aliased_inputs()

        if self.deduplicate:
            # self._deduplicate_by_lowest_order()
            self._deduplicate_by_lowest_n()

        self._fix_vertical_spurs()

        from bokeh.plotting import figure

        self.graph = figure(width=800, height=800, toolbar_location="right")

    def _generate_spurs(self):
        fs = self.fs
        fin = fs / 2 * np.array([self.input_zone - 1, self.input_zone])
        self.fin = fin

        intermods = converter_products(*self.order, self.M)
        spurs = pd.DataFrame(intermods, columns=["n", "k", "M"])

        spurs["ftune1"] = spurs.n * fin[0] + spurs.k / spurs.M * fs
        spurs["ftune2"] = spurs.n * fin[1] + spurs.k / spurs.M * fs

        # split spurs into Nyquist zones
        spurs_by_nyquist_zone = []

        for _, spur in spurs.iterrows():
            df = _expand_to_zones(spur.ftune1, spur.ftune2, fs)
            df["n"] = spur.n
            df["k"] = spur.k
            df["M"] = spur.M

            if not df.empty:
                spurs_by_nyquist_zone.append(df)

        spurs_by_zone = pd.concat(spurs_by_nyquist_zone, ignore_index=True)

        # which Nyquist zone is each frequency band in?
        midband = (spurs_by_zone.ftune1 + spurs_by_zone.ftune2) / 2
        spurs_by_zone["nz"] = nyquist_zone(midband, fs)

        # cleanup: cast to integer
        spurs_by_zone.n = spurs_by_zone.n.astype(int)
        spurs_by_zone.k = spurs_by_zone.k.astype(int)
        spurs_by_zone.M = spurs_by_zone.M.astype(int)

        cols = ["n", "k", "nz"]
        spurs_by_zone["label"] = spurs_by_zone[cols].apply(
            lambda row: ", ".join(row.values.astype(str)), axis=1
        )

        spurs_by_zone["order"] = spurs_by_zone.n.abs() + spurs_by_zone.k.abs()

        # eliminate negative frequencies
        positive_frequency_spurs = (spurs_by_zone.ftune1 >= 0) & (spurs_by_zone.ftune2 >= 0)
        spurs_by_zone = spurs_by_zone[positive_frequency_spurs]

        # eliminate k=0 and M>1
        k_is_zero_and_m_gt_one = (spurs_by_zone.k == 0) & (spurs_by_zone.M > 1)
        spurs_by_zone = spurs_by_zone[~k_is_zero_and_m_gt_one]

        self.spurs = spurs_by_zone

    def _compute_aliased_inputs(self):
        s = self.spurs

        s["fin1"] = (s.ftune1 - s.k / s.M * self.fs) / s.n
        s["fin2"] = (s.ftune2 - s.k / s.M * self.fs) / s.n

        self.spurs = s

    def _compute_aliased_spurs(self):
        s = self.spurs
        fn = self.fs / 2

        # number of Nyquist Zones to shift
        zones_to_shift = self.tune_zone - s.nz

        # frequency shift
        frequency_shift = zones_to_shift * fn

        # which are even number zones
        is_odd_shift = np.mod(zones_to_shift, 2).astype(bool)

        # even shift
        s["ftune1_nz1"] = s.ftune1 + frequency_shift
        s["ftune2_nz1"] = s.ftune2 + frequency_shift

        # reflect_frequency = 2 * center of target nyquist zone
        reflect_frequency = 2 * fn * (self.tune_zone - 0.5)

        # for odd shfits, add a "reflect" about the center of tne target Nyquist zone
        s.loc[is_odd_shift, "ftune1_nz1"] = reflect_frequency - s.loc[is_odd_shift, "ftune1_nz1"]
        s.loc[is_odd_shift, "ftune2_nz1"] = reflect_frequency - s.loc[is_odd_shift, "ftune2_nz1"]

        self.spurs = s

    def _fix_vertical_spurs(self):
        spurs = self.spurs
        spurs.loc[spurs["fin1"].isna(), "fin1"] = (self.input_zone - 1) * self.fs / 2
        spurs.loc[spurs["fin2"].isna(), "fin2"] = (self.input_zone) * self.fs / 2
        self.spurs = spurs

    def harmonic_distortion(self):
        """Return a table of harmonic distortion only.

        nf + k/M*fs, where k == 0

        """
        return self.spurs[self.spurs.k == 0]

    def interleaving_spurs(self, k=1):
        """Return low-order interleaving spurs: M > 1."""
        spurs = self.spurs

        return spurs[(np.abs(spurs.n) == 1) & (np.abs(spurs.k) == k) & (np.abs(spurs.M) > 1)]

    def in_interval(self, fa, fb):
        """Return spurs in over frequency interval [fa,fb]."""
        # intersecting lines:
        # https://stackoverflow.com/questions/48352036/how-can-i-measure-the-overlap-between-a-line-and-a-rectangle
        # https://en.wikipedia.org/wiki/Line%E2%80%93line_intersection#Given_two_points_on_each_line

        intersections = dict()
        rect_points = (
            (fa, fa),
            (fb, fb),
        )  # TODO: this needs to be adjusted by input_zone and tune_zone
        index = set()

        spurs = self.spurs
        x3 = spurs.ftune1_nz1
        x4 = spurs.ftune2_nz1
        y3 = spurs.fin1
        y4 = spurs.fin2

        for line_segment in _points_to_segments(*rect_points):
            z = _line_intersection(*line_segment, (x3, y3), (x4, y4))
            df = pd.DataFrame(data=z).transpose()
            df.columns = ["x", "y"]

            df = df[(df >= fa) & (df <= fb)].dropna()

            intersections[line_segment] = df
            index = index | set(df.index.values)

        return spurs.loc[list(index)].sort_values("order")

    def spurs_at_fin(self, fin):
        """Compute spurs at a given frequency fin."""
        # intersecting lines:
        # https://stackoverflow.com/questions/48352036/how-can-i-measure-the-overlap-between-a-line-and-a-rectangle
        # https://en.wikipedia.org/wiki/Line%E2%80%93line_intersection#Given_two_points_on_each_line

        spurs = self.spurs
        fn = self.fs / 2

        x3 = spurs.ftune1_nz1
        x4 = spurs.ftune2_nz1
        y3 = spurs.fin1
        y4 = spurs.fin2

        line_segment = ((0, fin), (fn / 2, fin))  # horizontal line

        coords = _line_intersection(*line_segment, (x3, y3), (x4, y4))
        intersection_coords = pd.DataFrame(data=coords, index=["ftune", "fin"]).transpose()

        cond1 = intersection_coords.ftune >= (self.tune_zone - 1) * fn
        cond2 = intersection_coords.ftune <= self.tune_zone * fn
        intersection_coords = intersection_coords[cond1 & cond2]

        cols = "n k nz order".split()
        spurs_at_coords = spurs[cols].loc[intersection_coords.index]
        table = pd.concat((intersection_coords, spurs_at_coords), axis=1)
        table = table.drop(columns=["fin"]).sort_values("ftune").set_index("ftune")

        return table

    def spurs_at_ftune(self, ftune):
        """Compute spurs at a given frequency ftune."""
        # intersecting lines:
        # https://stackoverflow.com/questions/48352036/how-can-i-measure-the-overlap-between-a-line-and-a-rectangle
        # https://en.wikipedia.org/wiki/Line%E2%80%93line_intersection#Given_two_points_on_each_line

        spurs = self.spurs
        fn = self.fs / 2

        x3 = spurs.ftune1_nz1
        x4 = spurs.ftune2_nz1
        y3 = spurs.fin1
        y4 = spurs.fin2

        line_segment = ((ftune, 0), (ftune, fn / 2))  # vertical line

        coords = _line_intersection(*line_segment, (x3, y3), (x4, y4))
        intersection_coords = pd.DataFrame(data=coords, index=["ftune", "fin"]).transpose()

        cond1 = intersection_coords.fin >= (self.input_zone - 1) * fn
        cond2 = intersection_coords.fin <= self.input_zone * fn
        intersection_coords = intersection_coords[cond1 & cond2]

        cols = "n k nz order".split()
        spurs_at_coords = spurs[cols].loc[intersection_coords.index]
        table = pd.concat((intersection_coords, spurs_at_coords), axis=1)
        table = table.drop(columns=["ftune"]).sort_values("fin").set_index("fin")

        return table

    def _deduplicate_by_lowest_n(self):
        """Remove duplicate spurs.

        for spurs which share the same input frequencies (fin1, fin2) and aliased output frequencies
        (ftune1_nz1, ftune2_nz1), remove the duplicates.

        The dataframe is first sorted in ascending order by 'n'.
        Then, the lowest order is kept for each duplicate.

        """
        cols = ["ftune1_nz1", "ftune2_nz1", "fin1", "fin2"]

        precision = 10  # round to precision avoids floating point errors

        spurs = self.spurs
        spurs = spurs.sort_values(by="n")

        duplicates = spurs.round(precision).duplicated(subset=cols, keep="first")
        self.spurs = spurs[~duplicates]
        self.duplicate_spurs = spurs[duplicates]

    def _deduplicate_by_lowest_order(self):
        """Remove duplicate spurs.

        for spurs which share the same input frequencies (fin1, fin2) and aliased output frequencies
        (ftune1_nz1, ftune2_nz1), remove the duplicates.

        The dataframe is first sorted in ascending order by 'order', where order = |n|+|k|+|M|.
        Then, the lowest order is kept for each duplicate.

        """
        cols = ["ftune1_nz1", "ftune2_nz1", "fin1", "fin2"]

        precision = 10  # round to precision avoids floating point errors

        spurs = self.spurs
        spurs = spurs.sort_values(by="order")

        duplicates = spurs.round(precision).duplicated(subset=cols, keep="first")
        self.spurs = spurs[~duplicates]
        self.duplicate_spurs = spurs[duplicates]

    def __get_colormap(self):
        numlines = self.spurs.shape[0]
        colormap = getattr(colorcet, "glasbey")

        # duplicate colormap to make sure there are enough entries
        length_of_colormap = len(colormap)
        colormap = colormap * (int(numlines / length_of_colormap) + 1)

        return colormap[:numlines]   

    def plot(self, filename=None, legend=False, hide=False):
        """Plot spurchart using bokeh."""
        # from bokeh.io import curdoc, export_png
        from bokeh.models import ColumnDataSource, HoverTool, Range1d, Title
        from bokeh.plotting import show

        graph = self.graph
        units = self.units

        if is_notebook():
            from bokeh.plotting import output_notebook

            output_notebook()  # make in-line Bokeh plots in Jupyter Notebook / VS Code

        # sort by order
        spurs = self.spurs.sort_values(by="order", ascending=False)

        colormap = self.__get_colormap()

        data = {
            "x": spurs[["ftune1_nz1", "ftune2_nz1"]].values.tolist(),
            "y": spurs[["fin1", "fin2"]].values.tolist(),
            "n": spurs.n.values,
            "k": spurs.k.values,
            "M": spurs.M.values,
            "colors": colormap,
            "labels": spurs.label,
            "nz": spurs.nz,
        }

        source = ColumnDataSource(data)

        ml = graph.multi_line(
            xs="x",
            ys="y",
            color="colors",
            legend_field="labels",
            source=source,
            line_width=2,
            muted_color="colors",
            muted_alpha=0.2,
        )

        xrange = self.fs / 2 * np.array([self.tune_zone - 1, self.tune_zone])
        yrange = self.fs / 2 * np.array([self.input_zone - 1, self.input_zone])

        hover_tool_ml = HoverTool(
            line_policy="interp",
            renderers=[ml],
            tooltips=[
                ("n, k", "@n, @k"),
                ("NZ", "@nz"),
                ("Input", f"$y [{units}]"),
                ("Tune (NCO)", f"$x [{units}]"),
            ],
        )

        n, k = self.order

        title_str = (
            f"Nyquist Zone {self.input_zone} Input Sweep [{self.fin[0]},{self.fin[1]}] {units} "
            + f"for Sample-rate of {self.fs} {units[0]}S/s"
        )

        # subtitle_str = f"n·fin + k·fs/{self.M} = ftune, |n| ≤ {n}, |k| ≤ {k}"
        subtitle_str = rf"$$n·f_{{IN}} + k·fs/{self.M} = f_{{TUNE}}, |n| ≤ {n}, |k| ≤ {k}$$"

        graph.add_layout(Title(text=subtitle_str, text_font_size="10pt", text_font_style = "normal"), "above")
        graph.add_layout(Title(text=title_str, text_font_size="12pt"), "above")
        
        # graph.yaxis.axis_label = f"Input Frequency [{units}]"
        graph.yaxis.axis_label = rf"Input Frequency $$f_{{IN}}$$ [{units}]"

        # graph.xaxis.axis_label = f"Tune Frequency [{units}]"
        graph.xaxis.axis_label = rf"NCO Tune Frequency $$f_{{TUNE}}$$ [{units}]"        
        graph.add_tools(hover_tool_ml)
        graph.x_range = Range1d(*xrange, bounds="auto")
        graph.y_range = Range1d(*yrange, bounds="auto")
        graph.toolbar.logo = None

        xstep = 1
        graph.xaxis.ticker = np.arange(xrange[0], xrange[1] + xstep, xstep)

        ystep = 1
        graph.yaxis.ticker = np.arange(yrange[0], yrange[1] + ystep, ystep)

        graph.axis.axis_label_text_font_style = "normal"  # non-italic axis labels

        for band in self.bands:
            ftune1_nz1, ftune2_nz1 = band.compute_alias(self.fs, self.input_zone, self.tune_zone)
            x = (ftune1_nz1 + ftune2_nz1) / 2
            y = (band.fa + band.fb) / 2
            width = abs(ftune2_nz1 - ftune1_nz1)
            height = abs(band.fb - band.fa)
            graph.rect(x, y, width, height, color=band.color, alpha=0.5)

        # graph.legend.click_policy = "mute"
        graph.legend.visible = legend
        graph.legend.title = "n, k, nz"

        if not hide:
            show(graph)

        if filename is not None:
            suffix = filename.split(".")[-1].lower()

            if suffix == "html":
                from bokeh.plotting import output_file, save

                output_file(filename)
                save(graph)

            if suffix == "png":
                export_png(filename)

        self.graph = graph
