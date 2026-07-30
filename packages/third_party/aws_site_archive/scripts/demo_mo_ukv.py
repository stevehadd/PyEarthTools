#!/usr/bin/env python3
# (C) British Crown Copyright 2024-2026, Met Office.
# Please see LICENSE for licence details.
"""
Demo script: Met Office UKV Model – AWS ASDI.

This script demonstrates how to:
1. Load 2-m temperature from the Met Office UKV model.
2. Load total precipitation.
3. Produce regional UK maps and save them as PNG files.

Usage
-----
    python demo_mo_ukv.py [--time YYYY-MM-DDTHH:MM] [--anon] [--outdir DIR]

Examples
--------
    python demo_mo_ukv.py --time 2023-06-01T06:00 --anon
"""

import argparse
import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeature

import site_archive_aws
from site_archive_aws import MOUKV

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Geographic extent for UK regional maps
UK_EXTENT = [-10, 3, 49, 61]  # [west, east, south, north]


def plot_temperature(ds, query_time: str, outdir: Path) -> None:
    """
    Plot a regional UK map of UKV 2-m temperature and save to PNG.

    Args:
        ds: xarray.Dataset containing ``air_temperature``.
        query_time: Datetime string for the plot title.
        outdir: Output directory.
    """
    t2m = ds["air_temperature"].squeeze() - 273.15  # K → °C

    fig, ax = plt.subplots(
        figsize=(8, 10),
        subplot_kw={"projection": ccrs.PlateCarree()},
    )

    im = ax.contourf(
        t2m["longitude"],
        t2m["latitude"],
        t2m.values,
        levels=np.linspace(-5, 30, 36),
        cmap="RdBu_r",
        transform=ccrs.PlateCarree(),
        extend="both",
    )

    ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5)
    ax.add_feature(cfeature.RIVERS.with_scale("10m"), linewidth=0.3, alpha=0.5)
    ax.gridlines(draw_labels=True, linewidth=0.3)
    ax.set_extent(UK_EXTENT, crs=ccrs.PlateCarree())

    plt.colorbar(im, ax=ax, label="2-m Temperature (°C)", shrink=0.7)
    ax.set_title(
        f"Met Office UKV – 2-m Temperature\n{query_time} (UTC)",
        fontsize=13,
    )

    outpath = outdir / "ukv_2t.png"
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved temperature figure to %s", outpath)


def plot_precipitation(ds, query_time: str, outdir: Path) -> None:
    """
    Plot a regional UK map of UKV total precipitation and save to PNG.

    Args:
        ds: xarray.Dataset containing ``stratiform_rainfall_amount``.
        query_time: Datetime string for the plot title.
        outdir: Output directory.
    """
    precip = ds["stratiform_rainfall_amount"].squeeze()  # kg/m² ≈ mm

    fig, ax = plt.subplots(
        figsize=(8, 10),
        subplot_kw={"projection": ccrs.PlateCarree()},
    )

    im = ax.contourf(
        precip["longitude"],
        precip["latitude"],
        precip.values,
        levels=[0, 0.1, 0.5, 1, 2, 4, 8, 16, 32, 64],
        cmap="Blues",
        transform=ccrs.PlateCarree(),
        extend="max",
    )

    ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5)
    ax.set_extent(UK_EXTENT, crs=ccrs.PlateCarree())
    ax.gridlines(draw_labels=True, linewidth=0.3)

    plt.colorbar(im, ax=ax, label="Total Precipitation (mm)", shrink=0.7)
    ax.set_title(
        f"Met Office UKV – Total Precipitation\n{query_time} (UTC)",
        fontsize=13,
    )

    outpath = outdir / "ukv_precip.png"
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved precipitation figure to %s", outpath)


def parse_args(argv=None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--time", default="2023-06-01T06:00",
                        metavar="YYYY-MM-DDTHH:MM",
                        help="Model initialisation time (UTC). Default: %(default)s")
    parser.add_argument("--anon", action="store_true",
                        help="Use anonymous S3 access.")
    parser.add_argument("--outdir", default=".",
                        help="Output directory for PNG files.")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    """Entry point."""
    args = parse_args(argv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    logger.info("site_archive_aws version: %s", site_archive_aws.__version__)
    logger.info("Query time: %s | anon: %s | outdir: %s",
                args.time, args.anon, outdir)

    logger.info("Loading UKV 2-m temperature …")
    ds_2t = MOUKV("2t", anon=args.anon)[args.time]
    plot_temperature(ds_2t, args.time, outdir)

    logger.info("Loading UKV total precipitation …")
    ds_precip = MOUKV("tp", anon=args.anon)[args.time]
    plot_precipitation(ds_precip, args.time, outdir)

    logger.info("All done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

