"""Compare battery simulation DataFrames with Matplotlib.

Dependencies: numpy, pandas, matplotlib.
Single run: plot_results(results)
Comparison: plot_results({"SR-17": results, "SR-18 5p": results2})
All inputs use seconds, watts, volts, amps, ohms, degrees C, and SOC 0-1.
"""

from collections.abc import Mapping
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Each signal is (column, legend suffix, line style, display multiplier).
PANELS = {
    "power": (
        "Requested power (kW)",
        [
            ("pack_power_W", "requested", "-", 0.001),
        ],
    ),
    "current": (
        "Pack current (A)",
        [
            ("predicted_pack_current_a", "", "-", 1),
        ],
    ),
    "voltage": (
        "Pack voltage (V)",
        [
            ("predicted_pack_voltage_v", "", "-", 1),
        ],
    ),
    "heating": (
        "Total cell heating (kW)",
        [
            ("cell_heat_w", "", "-", 0.001),
        ],
    ),
    "temperature": (
        "Temperature (\N{DEGREE SIGN}C)",
        [
            ("predicted_cell_temp_c", "cells", "-", 1),
            ("predicted_enclosure_temp_c", "enclosure", "--", 1),
        ],
    ),
    "soc": (
        "State of charge (%)",
        [
            ("soc", "", "-", 100),
        ],
    ),
    "resistance": (
        "Pack resistance (m\N{GREEK CAPITAL LETTER OMEGA})",
        [
            ("pack_resistance_ohm", "", "-", 1000),
        ],
    ),
    "heat_transfer": (
        "Heat transfer (kW)",
        [
            ("cells_to_enclosure_heat_w", "cells to enclosure", "-", 0.001),
            ("enclosure_to_ambient_heat_w", "enclosure to ambient", "--", 0.001),
        ],
    ),
}

MEASURED = {
    "current": [("pack_current_a", "current")],
    "voltage": [("pack_voltage_v", "voltage")],
    "temperature": [("cell_temp_avg_c", "average cells")],
}


def _as_runs(data):
    if isinstance(data, pd.DataFrame):
        runs = {"Pack": data}
    elif isinstance(data, Mapping) and data:
        runs = dict(data)
    else:
        raise ValueError(
            "Pass a DataFrame or a nonempty {pack_name: DataFrame} dictionary."
        )

    for name, frame in runs.items():
        if not isinstance(name, str) or not isinstance(frame, pd.DataFrame):
            raise ValueError("Each run needs a string name and a DataFrame.")
        if frame.empty or "time_s" not in frame.columns:
            raise ValueError(f"{name}: provide a nonempty DataFrame with time_s.")
        if not frame.columns.is_unique:
            raise ValueError(f"{name}: duplicate column names are not supported.")
        t = frame["time_s"].to_numpy(dtype=float)
        if not np.isfinite(t).all() or np.any(np.diff(t) <= 0):
            raise ValueError(f"{name}: time_s must be finite and strictly increasing.")
    return runs


def summarize_results(data):
    """Return full-run metrics; do not modify the input DataFrames.

    Net requested energy uses left-held input power. Heat energy uses the same
    rule on the sampled cell_heat_w column, so it approximates substep heating.
    Different-length runs are summarized over their own recorded durations.
    """
    records = []
    for name, frame in _as_runs(data).items():
        t = frame["time_s"].to_numpy(dtype=float)

        def values(column):
            return frame[column].to_numpy(dtype=float) if column in frame else None

        def extreme(column, operation, absolute=False):
            y = values(column)
            if y is None:
                return np.nan
            y = y[np.isfinite(y)]
            return operation(np.abs(y) if absolute else y) if len(y) else np.nan

        def integral(column, divisor):
            y = values(column)
            if y is None or len(t) < 2 or not np.isfinite(y[:-1]).all():
                return np.nan
            return float(np.dot(y[:-1], np.diff(t)) / divisor)

        soc = values("soc")
        records.append(
            {
                "Pack": name,
                "Duration (min)": (t[-1] - t[0]) / 60,
                "Peak cells (C)": extreme("predicted_cell_temp_c", np.max),
                "Min voltage (V)": extreme("predicted_pack_voltage_v", np.min),
                "Peak |current| (A)": extreme("predicted_pack_current_a", np.max, True),
                "Final SOC (%)": soc[-1] * 100 if soc is not None else np.nan,
                "Net input (kWh)": integral("pack_power_W", 3_600_000),
                "Cell heat (Wh)": integral("cell_heat_w", 3600),
            }
        )
    return pd.DataFrame(records).set_index("Pack")


def plot_results(
    data,
    show=True,
    *,
    panels=None,
    title="Battery pack comparison",
    time_unit="min",
    time_range_s=None,
    show_measured=True,
    measured_from=None,
    temperature_limit_C=None,
    show_summary=True,
    save_path=None,
):
    """Plot one results DataFrame or a dictionary of named results.

    Returns (figure, 1-D array of chart axes), matching the original function.
    Panels without available signals are omitted. Available panel names:
    power, current, voltage, heating, temperature, soc, resistance, heat_transfer.

    Measured channels are drawn ONLY from measured_from (default: first run).
    Their labels identify that source; they do not validate the other packs.
    time_range_s changes the displayed range; summaries always cover full runs.
    No resampling, time shifting, or modification of the input data is performed.
    """
    runs = _as_runs(data)
    if time_unit not in {"s", "min"}:
        raise ValueError("time_unit must be 's' or 'min'.")
    scale = 60 if time_unit == "min" else 1
    if time_range_s is not None:
        if (
            len(time_range_s) != 2
            or not np.isfinite(time_range_s).all()
            or time_range_s[0] >= time_range_s[1]
        ):
            raise ValueError("time_range_s must be (start_s, end_s), with start < end.")
    if temperature_limit_C is not None and not np.isfinite(temperature_limit_C):
        raise ValueError("temperature_limit_C must be finite.")

    reference_name = next(iter(runs)) if measured_from is None else measured_from
    if reference_name not in runs:
        raise ValueError("measured_from must name one of the supplied packs.")
    reference = runs[reference_name]
    selected = (
        list(panels)
        if panels is not None
        else [
            "power",
            "current",
            "voltage",
            "heating",
            "temperature",
            "soc",
        ]
    )
    if len(selected) != len(set(selected)) or any(p not in PANELS for p in selected):
        raise ValueError(f"Choose unique panel names from {list(PANELS)}.")
    selected = [
        p
        for p in selected
        if (
            any(col in df for df in runs.values() for col, *_ in PANELS[p][1])
            or (
                show_measured
                and any(col in reference for col, _ in MEASURED.get(p, []))
            )
        )
    ]
    if not selected:
        raise ValueError("No recognized signals are available in the selected panels.")

    palette = [
        "#0072B2",
        "#D55E00",
        "#009E73",
        "#CC79A7",
        "#E69F00",
        "#56B4E9",
        "#332288",
        "#882255",
    ]
    colors = {name: palette[i % len(palette)] for i, name in enumerate(runs)}
    ncols = min(2, len(selected))
    nrows = int(np.ceil(len(selected) / ncols))
    fig = plt.figure(
        figsize=(14, 3.0 * nrows + (2 if show_summary else 0)),
        layout="constrained",
        facecolor="white",
    )
    grid = fig.add_gridspec(
        nrows + int(show_summary),
        ncols,
        height_ratios=[1] * nrows + ([0.62] if show_summary else []),
    )
    axes = []

    for index, panel in enumerate(selected):
        ax = fig.add_subplot(
            grid[index // ncols, index % ncols], sharex=axes[0] if axes else None
        )
        axes.append(ax)
        ylabel, signals = PANELS[panel]

        # Shared requested power is displayed once instead of three overlapping lines.
        power_frames = [(name, df) for name, df in runs.items() if "pack_power_W" in df]
        shared_power = (
            panel == "power"
            and len(power_frames) > 1
            and all(
                np.array_equal(
                    df["time_s"].to_numpy(), power_frames[0][1]["time_s"].to_numpy()
                )
                and np.array_equal(
                    df["pack_power_W"].to_numpy(),
                    power_frames[0][1]["pack_power_W"].to_numpy(),
                    equal_nan=True,
                )
                for _, df in power_frames[1:]
            )
        )
        plot_runs = dict(power_frames[:1]) if shared_power else runs
        for name, frame in plot_runs.items():
            for column, suffix, style, multiplier in signals:
                if column not in frame:
                    continue
                label = (
                    "Shared input"
                    if shared_power
                    else f"{name}: {suffix}" if suffix else name
                )
                ax.plot(
                    frame["time_s"].to_numpy(dtype=float) / scale,
                    frame[column].to_numpy(dtype=float) * multiplier,
                    color="#555555" if shared_power else colors[name],
                    linestyle=style,
                    linewidth=1.65,
                    label=label,
                )

        if show_measured:
            for column, label in MEASURED.get(panel, []):
                if column in reference:
                    ax.plot(
                        reference["time_s"].to_numpy(dtype=float) / scale,
                        reference[column].to_numpy(dtype=float),
                        color="#222222",
                        linestyle=":",
                        linewidth=1.6,
                        alpha=0.8,
                        label=f"Measured {label} ({reference_name})",
                    )

        if panel == "temperature" and temperature_limit_C is not None:
            ax.axhline(
                temperature_limit_C,
                color="#B22222",
                linestyle="-.",
                linewidth=1.1,
                label=f"Limit: {temperature_limit_C:g} C",
            )
        if panel in {"power", "current", "heat_transfer"}:
            ax.axhline(0, color="#9CA3AF", linewidth=0.6, zorder=0)
        ax.set_ylabel(ylabel)
        ax.set_xlabel(f"Time ({time_unit})")
        ax.set_title(ylabel.split(" (")[0], loc="left", fontsize=11, fontweight="bold")
        ax.grid(True, alpha=0.18)
        ax.spines[["top", "right"]].set_visible(False)
        ax.margins(x=0)
        if time_range_s is not None:
            ax.set_xlim(
                left=float(time_range_s[0]) / scale,
                right=float(time_range_s[1]) / scale,
            )
        ax.legend(fontsize=8, framealpha=0.9, ncol=2 if len(ax.lines) > 4 else 1)

    if show_summary:
        summary = summarize_results(runs)
        table_ax = fig.add_subplot(grid[-1, :])
        table_ax.axis("off")
        columns = [
            "Peak cells (C)",
            "Min voltage (V)",
            "Peak |current| (A)",
            "Final SOC (%)",
            "Net input (kWh)",
            "Cell heat (Wh)",
        ]
        labels = [
            "Peak cells / C",
            "Min voltage / V",
            "Peak |I| / A",
            "Final SOC / %",
            "Net input / kWh",
            "Cell heat / Wh",
        ]
        text = [
            ["--" if not np.isfinite(row[c]) else f"{row[c]:.2f}" for c in columns]
            for _, row in summary.iterrows()
        ]
        table = table_ax.table(
            cellText=text,
            rowLabels=summary.index.tolist(),
            colLabels=labels,
            loc="center",
            cellLoc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.5)
        for (row, column), cell in table.get_celld().items():
            cell.set_edgecolor("#E5E7EB")
            if row == 0:
                cell.set_facecolor("#E8EEF5")
                cell.set_text_props(weight="bold")
            elif column == -1:
                cell.set_text_props(color=colors[summary.index[row - 1]], weight="bold")
        table_ax.set_title(
            "Full-run summary (heat energy estimated from recorded samples)",
            fontsize=9,
            loc="left",
            pad=8,
        )

    fig.suptitle(title, fontsize=16, fontweight="bold")
    if save_path is not None:
        destination = Path(save_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(destination, dpi=180, bbox_inches="tight")
    if show:
        plt.show()
    return fig, np.asarray(axes, dtype=object)
