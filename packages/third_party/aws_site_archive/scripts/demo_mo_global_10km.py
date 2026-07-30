#!/usr/bin/env python3
# (C) British Crown Copyright 2024-2026, Met Office.
# Please see LICENSE for licence details.
"""
Demo script: Met Office Global 10 km Deterministic NWP – AWS ASDI.

This script demonstrates how to:
1. Load 2-m temperature from the Met Office Global 10 km model.
2. Load 10-m wind components and compute wind speed.
3. Produce publication-quality maps and save them as PNG files.

Usage
-----
    python demo_mo_global_10km.py [--time YYYY-MM-DDTHH:MM] [--anon] [--outdir DIR]

Examples
--------
    # Use default time and anonymous S3 access (no credentials needed)
    python demo_mo_global_10km.py --anon

    # Specify a custom time
    python demo_mo_global_10km.py --time 2023-06-01T12:00 --anon --outdir /tmp/figs
"""

import argparse
import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Use non-interactive backend for batch/script execution
import matplotlib.pyplot as plt
import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeature

import site_archive_aws
from site_archive_aws import MOGlobal10km

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------


def plot_temperature(ds, query_time: str, outdir: Path) -> None:
    """
    Plot a global map of 2-m temperature and save to PNG.

    Args:
        ds: xarray.Dataset containing ``air_temperature``.
        query_time: Human-readable datetime string for the title.
        outdir: Directory in which to save the figure.
    """
    t2m = ds["air_temperature"].squeeze() - 273.15  # K → °C

    fig, ax = plt.subplots(
        figsize=(14, 7),
        subplot_kw={"projection": ccrs.PlateCarree()},
    )

    im = ax.contourf(
        t2m["longitude"],
        t2m["latitude"],
        t2m.values,
        levels=np.linspace(-50, 45, 40),
        cmap="RdBu_r",
        transform=ccrs.PlateCarree(),
        extend="both",
    )

    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    ax.add_feature(cfeature.BORDERS, linewidth=0.3, linestyle="--")
    ax.gridlines(draw_labels=True, linewidth=0.3, color="grey", alpha=0.5)

    plt.colorbar(im, ax=ax, label="2-m Temperature (°C)", shrink=0.7, pad=0.02)
    ax.set_title(
        f"Met Office Global 10 km – 2-m Temperature\n{query_time} (UTC)",
        fontsize=14,
    )

    outpath = outdir / "global_10km_2t.png"
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved temperature figure to %s", outpath)


def plot_wind(ds, query_time: str, outdir: Path) -> None:
    """
    Plot a global map of 10-m wind speed with barbs and save to PNG.

    Args:
        ds: xarray.Dataset containing ``x_wind`` and ``y_wind``.
        query_time: Human-readable datetime string for the title.
        outdir: Directory in which to save the figure.
    """
    u = ds["x_wind"].squeeze()
    v = ds["y_wind"].squeeze()
    speed = np.sqrt(u**2 + v**2)

    logger.info(
        "Wind speed statistics: min=%.1f, max=%.1f, mean=%.1f m/s",
        float(speed.min()),
        float(speed.max()),
        float(speed.mean()),
    )

    fig, ax = plt.subplots(
        figsize=(14, 7),
        subplot_kw={"projection": ccrs.PlateCarree()},
    )

    im = ax.contourf(
        speed["longitude"],
        speed["latitude"],
        speed.values,
        levels=np.linspace(0, 30, 31),
        cmap="YlOrRd",
        transform=ccrs.PlateCarree(),
        extend="max",
    )

    # Subsample for wind barbs
    step = max(1, len(speed.latitude) // 30)
    ax.barbs(
        speed["longitude"].values[::step],
        speed["latitude"].values[::step],
        u.values[::step, ::step],
        v.values[::step, ::step],
        length=4, linewidth=0.5, color="k", alpha=0.5,
        transform=ccrs.PlateCarree(),
    )

    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    plt.colorbar(im, ax=ax, label="10-m Wind Speed (m/s)", shrink=0.7, pad=0.02)
    ax.set_title(
        f"Met Office Global 10 km – 10-m Wind Speed\n{query_time} (UTC)",
        fontsize=14,
    )

    outpath = outdir / "global_10km_wind.png"
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved wind figure to %s", outpath)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args(argv=None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--time",
        default="2023-06-01T00:00",
        metavar="YYYY-MM-DDTHH:MM",
        help="Model initialisation time (UTC).  Default: %(default)s",
    )
    parser.add_argument(
        "--anon",
        action="store_true",
        help="Use anonymous (no-credential) S3 access for public buckets.",
    )
    parser.add_argument(
        "--outdir",
        default=".",
        help="Directory to write output PNG files.  Default: current directory.",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    """Entry point."""
    args = parse_args(argv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    logger.info("site_archive_aws version: %s", site_archive_aws.__version__)
    logger.info("Query time: %s", args.time)
    logger.info("Anonymous S3 access: %s", args.anon)
    logger.info("Output directory: %s", outdir)

    # --- Load and plot 2-m temperature ---
    logger.info("Loading 2-m temperature from Global 10 km model …")
    accessor_2t = MOGlobal10km("2t", anon=args.anon)
    ds_2t = accessor_2t[args.time]
    plot_temperature(ds_2t, args.time, outdir)

    # --- Load and plot 10-m wind ---
    logger.info("Loading 10-m wind components from Global 10 km model …")
    accessor_wind = MOGlobal10km(["10u", "10v"], anon=args.anon)
    ds_wind = accessor_wind[args.time]
    plot_wind(ds_wind, args.time, outdir)

    logger.info("All done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

