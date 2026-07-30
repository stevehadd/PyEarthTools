# (C) British Crown Copyright 2024-2026, Met Office.
# Please see LICENSE for licence details.

"""
Shared utilities for the AWS site archive accessors.

Provides:
- S3-aware file listing and existence caching (backed by ``s3fs``)
- Local filesystem equivalents for testing without AWS credentials
- Dataset post-processing helpers (staggered-grid regridding, coord cleanup)
- A lightweight configuration helper for reading S3 roots from the
  PyEarthTools config file
"""

from __future__ import annotations

import functools
import logging
import os
from pathlib import Path
from typing import Union

import xarray as xr

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# S3 filesystem singleton
# ---------------------------------------------------------------------------

_S3_FS = None  # lazily initialised


def get_s3fs(anon: bool = False):
    """
    Return a cached ``s3fs.S3FileSystem`` instance.

    Args:
        anon (bool):
            If ``True`` use anonymous (unsigned) access.  This works for
            publicly accessible buckets (e.g. the Met Office ASDI buckets)
            but will fail for private resources.  Defaults to ``False``,
            which reads credentials from the standard boto3 chain
            (environment variables, ``~/.aws/credentials``, IAM roles …).

    Returns:
        s3fs.S3FileSystem: A configured filesystem instance.
    """
    global _S3_FS
    if _S3_FS is None:
        try:
            import s3fs  # imported here so the rest of utilities works without s3fs
        except ImportError as exc:
            raise ImportError(
                "s3fs is required for AWS access. Install it with: pip install s3fs"
            ) from exc
        _S3_FS = s3fs.S3FileSystem(anon=anon)
    return _S3_FS


def reset_s3fs():
    """Clear the cached S3FileSystem (useful when switching credentials)."""
    global _S3_FS
    _S3_FS = None


# ---------------------------------------------------------------------------
# Cached directory listing and existence checks (S3 and local)
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=256)
def cached_s3_ls(s3_prefix: str, anon: bool = False) -> list[str]:
    """
    List the contents of an S3 prefix, with LRU caching.

    Args:
        s3_prefix (str): An S3 URI such as ``s3://bucket/prefix/``.
        anon (bool): Use anonymous access if ``True``.

    Returns:
        list[str]: Full S3 URIs of objects immediately under the prefix.
    """
    fs = get_s3fs(anon=anon)
    try:
        return [f"s3://{p}" for p in fs.ls(s3_prefix.replace("s3://", ""), detail=False)]
    except FileNotFoundError:
        logger.debug("S3 prefix not found: %s", s3_prefix)
        return []


@functools.lru_cache(maxsize=512)
def cached_s3_exists(s3_path: str, anon: bool = False) -> bool:
    """
    Check whether an S3 object or prefix exists, with LRU caching.

    Args:
        s3_path (str): An S3 URI.
        anon (bool): Use anonymous access if ``True``.

    Returns:
        bool: ``True`` if the path exists.
    """
    fs = get_s3fs(anon=anon)
    return fs.exists(s3_path.replace("s3://", ""))


@functools.lru_cache()
def cached_iterdir(path: Path) -> list[Path]:
    """
    List a local directory, with LRU caching.

    This mirrors the helper in site_archive_met_office/jasmin and is provided
    for use in local/test scenarios where data has been downloaded from S3.

    Args:
        path (Path): Local filesystem directory.

    Returns:
        list[Path]: Contents of the directory.
    """
    return list(path.iterdir())


@functools.lru_cache()
def cached_exists(path: Path) -> bool:
    """
    Check whether a local path exists, with LRU caching.

    Args:
        path (Path): Local filesystem path.

    Returns:
        bool: ``True`` if the path exists.
    """
    return path.exists()


# ---------------------------------------------------------------------------
# xarray / dataset helpers
# ---------------------------------------------------------------------------


def open_s3_dataset(
    s3_uri: str,
    engine: str = "cfgrib",
    anon: bool = False,
    **kwargs,
) -> xr.Dataset:
    """
    Open a dataset directly from an S3 URI using xarray.

    This helper wraps ``xr.open_dataset`` with the correct ``fsspec`` storage
    options so that data can be streamed from S3 without a local copy.

    Args:
        s3_uri (str):
            Full S3 URI, e.g. ``s3://met-office-atmospheric-model-data/…``.
        engine (str):
            xarray engine to use.  Common choices:

            * ``"cfgrib"`` – for GRIB2 files (requires *cfgrib* + *eccodes*)
            * ``"scipy"`` / ``"h5netcdf"`` – for NetCDF files
            * ``"zarr"`` – for Zarr stores

            Defaults to ``"cfgrib"``.
        anon (bool):
            Use anonymous (unsigned) S3 access.  Works for open buckets.
        **kwargs:
            Additional keyword arguments forwarded to ``xr.open_dataset``.

    Returns:
        xr.Dataset: The opened dataset (lazily loaded by default).
    """
    storage_options = {"anon": anon}

    if engine == "zarr":
        # Zarr stores can be opened directly via fsspec
        import fsspec

        mapper = fsspec.get_mapper(s3_uri, **storage_options)
        return xr.open_dataset(mapper, engine="zarr", **kwargs)
    else:
        return xr.open_dataset(
            s3_uri,
            engine=engine,
            storage_options=storage_options,
            **kwargs,
        )


def postprocess_dataset(ds: xr.Dataset) -> xr.Dataset:
    """
    Post-process a raw Met Office NWP dataset loaded from S3.

    Specifically:

    1. Interpolates any staggered-grid variables (e.g. ``latitude_0``,
       ``longitude_0``) back onto the centred grid so all variables share
       common coordinate arrays.
    2. Drops ancillary coordinates that are not ``latitude``, ``longitude``,
       or ``time``, keeping the dataset tidy.

    Args:
        ds (xr.Dataset): Raw dataset as returned by xarray.

    Returns:
        xr.Dataset: Cleaned dataset.
    """
    for var in ds.data_vars:
        arr = ds[var]
        dims = arr.dims

        # --- latitude stagger ---
        for stag, target in [("latitude_0", "latitude"), ("grid_latitude_0", "latitude")]:
            if stag in dims and target in ds.dims:
                arr = arr.isel({stag: slice(0, ds.sizes[target])})
                arr = arr.rename({stag: target})
                arr = arr.assign_coords({target: ds[target]})

        # --- longitude stagger ---
        for stag, target in [("longitude_0", "longitude"), ("grid_longitude_0", "longitude")]:
            if stag in dims and target in ds.dims:
                arr = arr.isel({stag: slice(0, ds.sizes[target])})
                arr = arr.rename({stag: target})
                arr = arr.assign_coords({target: ds[target]})

        ds[var] = arr

    # Drop non-essential coordinates
    keep = {"latitude", "longitude", "time", "realization", "forecast_period", "level"}
    to_drop = [c for c in ds.coords if c not in keep]
    if to_drop:
        ds = ds.drop_vars(to_drop)

    return ds


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


def build_s3_uri(bucket: str, key: str) -> str:
    """
    Construct a well-formed S3 URI.

    Args:
        bucket (str): S3 bucket name (without ``s3://`` prefix).
        key (str): Object key path within the bucket.

    Returns:
        str: Full S3 URI, e.g. ``s3://bucket/key``.
    """
    bucket = bucket.rstrip("/")
    key = key.lstrip("/")
    return f"s3://{bucket}/{key}"


def join_s3(*parts: str) -> str:
    """
    Join S3 URI path segments, similar to ``os.path.join`` for S3 URIs.

    Args:
        *parts (str): Path segments.  The first may include the ``s3://``
            scheme and bucket name.

    Returns:
        str: Joined URI.

    Example:
        >>> join_s3("s3://my-bucket/prefix/", "2023/01/01", "file.nc")
        's3://my-bucket/prefix/2023/01/01/file.nc'
    """
    # Split off the scheme+bucket from the first component
    first, *rest = parts
    prefix = ""
    if first.startswith("s3://"):
        prefix = "s3://"
        first = first[len("s3://"):]
    segments = [first.strip("/")] + [p.strip("/") for p in rest]
    return prefix + "/".join(s for s in segments if s)

