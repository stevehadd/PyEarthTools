#!/usr/bin/env python3
# (C) British Crown Copyright 2024-2026, Met Office.
# Please see LICENSE for licence details.
"""
Demo script: Met Office MOGREPS-UK (UK Regional Ensemble) – AWS ASDI.

This script demonstrates how to:
1. Load 2-m temperature from MOGREPS-UK ensemble members.
2. Plot the ensemble-mean temperature over the UK.
3. Compute and plot the probability of temperature exceeding a threshold.

Usage
-----
    python demo_mogreps_uk.py [--time YYYY-MM-DDTHH:MM] [--members N]
                               [--threshold T] [--anon] [--outdir DIR]

Examples
--------
    python demo_mogreps_uk.py --time 2023-06-01T03:00 --members 6 --anon
    python demo_mogreps_uk.py --threshold 25 --anon
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
from site_archive_aws import MOGREPSUK

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

UK_EXTENT = [-10, 3, 49, 61]


def plot_ensemble_mean(t2m, query_time: str, outdir: Path) -> None:
    """
    Plot ensemble-mean 2-m temperature over the UK.

    Args:
        t2m: DataArray (realization, lat, lon), °C.
        query_time: Datetime string for the title.
        outdir: Output directory.
    """
    ens_mean = t2m.mean("realization")

    fig, ax = plt.subplots(
        figsize=(8, 10),
        subplot_kw={"projection": ccrs.PlateCarree()},
    )

    im = ax.contourf(
        ens_mean["longitude"], ens_mean["latitude"], ens_mean.values,
        levels=np.linspace(-5, 30, 36), cmap="RdBu_r",
        transform=ccrs.PlateCarree(), extend="both",
    )
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5)
    ax.set_extent(UK_EXTENT, crs=ccrs.PlateCarree())
    ax.gridlines(draw_labels=True, linewidth=0.3)

    plt.colorbar(im, ax=ax, label="2-m Temperature (°C)", shrink=0.7)
    ax.set_title(
        f"MOGREPS-UK – Ensemble Mean 2-m Temperature\n{query_time} (UTC)",
        fontsize=13,
    )
    outpath = outdir / "mogreps_uk_2t_mean.png"
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved ensemble-mean figure to %s", outpath)


def plot_probability(t2m, threshold: float, query_time: str, outdir: Path) -> None:
    """
    Plot the probability of 2-m temperature exceeding a threshold.

    Args:
        t2m: DataArray (realization, lat, lon), °C.
        threshold: Temperature threshold in °C.
        query_time: Datetime string for the title.
        outdir: Output directory.
    """
    prob = (t2m > threshold).mean("realization") * 100  # %

    fig, ax = plt.subplots(
        figsize=(8, 10),
        subplot_kw={"projection": ccrs.PlateCarree()},
    )

    im = ax.contourf(
        prob["longitude"], prob["latitude"], prob.values,
        levels=np.arange(0, 110, 10), cmap="YlOrRd",
        transform=ccrs.PlateCarree(),
    )
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax.set_extent(UK_EXTENT, crs=ccrs.PlateCarree())
    ax.gridlines(draw_labels=True, linewidth=0.3)

    plt.colorbar(im, ax=ax, label=f"P(T2m > {threshold} °C) [%]", shrink=0.7)
    ax.set_title(
        f"MOGREPS-UK – P(2-m T > {threshold} °C)\n{query_time} (UTC)",
        fontsize=13,
    )
    outpath = outdir / "mogreps_uk_prob_warm.png"
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved probability figure to %s", outpath)


def parse_args(argv=None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--time", default="2023-06-01T03:00",
                        metavar="YYYY-MM-DDTHH:MM")
    parser.add_argument("--members", type=int, default=6,
                        help="Number of ensemble members to load (max 18). Default: %(default)s")
    parser.add_argument("--threshold", type=float, default=20.0,
                        help="Temperature threshold in °C for probability plot. Default: %(default)s")
    parser.add_argument("--anon", action="store_true")
    parser.add_argument("--outdir", default=".")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    """Entry point."""
    args = parse_args(argv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    n_members = min(args.members, 18)
    member_list = list(range(n_members))

    logger.info("site_archive_aws version: %s", site_archive_aws.__version__)
    logger.info("Query time: %s | members: %s | threshold: %.1f °C | anon: %s",
                args.time, member_list, args.threshold, args.anon)

    logger.info("Loading MOGREPS-UK 2-m temperature for %d members …", n_members)
    accessor = MOGREPSUK("2t", members=member_list, anon=args.anon)
    ds = accessor[args.time]

    t2m = ds["air_temperature"].squeeze(dim="time", drop=True) - 273.15

    plot_ensemble_mean(t2m, args.time, outdir)
    plot_probability(t2m, args.threshold, args.time, outdir)

    logger.info("All done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

