#!/usr/bin/env python3
# (C) British Crown Copyright 2024-2026, Met Office.
# Please see LICENSE for licence details.
"""
Demo script: Met Office MOGREPS-G (Global Ensemble) – AWS ASDI.

This script demonstrates how to:
1. Load 2-m temperature from all (or a subset of) MOGREPS-G ensemble members.
2. Produce a multi-panel plot of individual members.
3. Compute and plot the ensemble mean and spread.

Usage
-----
    python demo_mogreps_global.py [--time YYYY-MM-DDTHH:MM] [--members N]
                                   [--anon] [--outdir DIR]

Examples
--------
    # Load 4 members with anonymous S3 access
    python demo_mogreps_global.py --time 2023-06-01T00:00 --members 4 --anon
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
from site_archive_aws import MOGREPSGlobal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def plot_members(t2m, query_time: str, outdir: Path) -> None:
    """
    Plot individual ensemble members as a multi-panel figure.

    Args:
        t2m: DataArray with dims (realization, lat, lon), units °C.
        query_time: Datetime string for the plot title.
        outdir: Output directory.
    """
    n = len(t2m["realization"])
    ncols = min(4, n)
    nrows = int(np.ceil(n / ncols))

    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(ncols * 5, nrows * 3.5),
        subplot_kw={"projection": ccrs.PlateCarree()},
        squeeze=False,
    )
    levels = np.linspace(-40, 40, 33)

    for idx in range(nrows * ncols):
        row, col = divmod(idx, ncols)
        ax = axes[row][col]
        if idx >= n:
            ax.set_visible(False)
            continue
        member = int(t2m["realization"].values[idx])
        field = t2m.isel(realization=idx)
        im = ax.contourf(
            field["longitude"], field["latitude"], field.values,
            levels=levels, cmap="RdBu_r",
            transform=ccrs.PlateCarree(), extend="both",
        )
        ax.add_feature(cfeature.COASTLINE, linewidth=0.4)
        ax.set_title(f"Member {member:03d}", fontsize=9)
        plt.colorbar(im, ax=ax, label="°C", shrink=0.85)

    fig.suptitle(
        f"MOGREPS-G – 2-m Temperature (°C) – {query_time}",
        fontsize=13, y=1.01,
    )
    plt.tight_layout()
    outpath = outdir / "mogreps_g_members.png"
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved member panel to %s", outpath)


def plot_mean_spread(t2m, query_time: str, outdir: Path) -> None:
    """
    Plot ensemble mean and standard deviation side by side.

    Args:
        t2m: DataArray with dims (realization, lat, lon), units °C.
        query_time: Datetime string for the plot title.
        outdir: Output directory.
    """
    ens_mean = t2m.mean("realization")
    ens_std  = t2m.std("realization")

    fig, (ax1, ax2) = plt.subplots(
        1, 2,
        figsize=(18, 6),
        subplot_kw={"projection": ccrs.PlateCarree()},
    )

    im1 = ax1.contourf(
        ens_mean["longitude"], ens_mean["latitude"], ens_mean.values,
        levels=np.linspace(-40, 40, 33), cmap="RdBu_r",
        transform=ccrs.PlateCarree(), extend="both",
    )
    ax1.add_feature(cfeature.COASTLINE, linewidth=0.5)
    plt.colorbar(im1, ax=ax1, label="°C", shrink=0.8)
    ax1.set_title("Ensemble Mean – 2-m Temperature", fontsize=12)

    im2 = ax2.contourf(
        ens_std["longitude"], ens_std["latitude"], ens_std.values,
        levels=np.linspace(0, 10, 21), cmap="YlOrRd",
        transform=ccrs.PlateCarree(), extend="max",
    )
    ax2.add_feature(cfeature.COASTLINE, linewidth=0.5)
    plt.colorbar(im2, ax=ax2, label="°C (spread)", shrink=0.8)
    ax2.set_title("Ensemble Spread (Std Dev) – 2-m Temperature", fontsize=12)

    fig.suptitle(f"MOGREPS-G – {query_time} (UTC)", fontsize=14, y=1.02)
    plt.tight_layout()
    outpath = outdir / "mogreps_g_mean_spread.png"
    plt.savefig(outpath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved mean/spread figure to %s", outpath)


def parse_args(argv=None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--time", default="2023-06-01T00:00",
                        metavar="YYYY-MM-DDTHH:MM")
    parser.add_argument("--members", type=int, default=4,
                        help="Number of ensemble members to load (0-based, max 18). "
                             "Default: %(default)s")
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
    logger.info("Query time: %s | members: %s | anon: %s",
                args.time, member_list, args.anon)

    logger.info("Loading MOGREPS-G 2-m temperature for %d members …", n_members)
    accessor = MOGREPSGlobal("2t", members=member_list, anon=args.anon)
    ds = accessor[args.time]

    t2m = ds["air_temperature"].squeeze(dim="time", drop=True) - 273.15

    plot_members(t2m, args.time, outdir)
    plot_mean_spread(t2m, args.time, outdir)

    logger.info("All done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

