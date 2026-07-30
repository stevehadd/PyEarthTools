# (C) British Crown Copyright 2024-2026, Met Office.
# Please see LICENSE for licence details.

"""
Met Office Global 10 km Deterministic NWP – AWS ASDI accessor.

The Met Office Global Atmospheric High Resolution Model produces operational
deterministic forecasts at approximately 10 km horizontal grid spacing.
Data are published to AWS S3 as part of the
`Met Office Atmospheric Model Data
<https://registry.opendata.aws/uk-met-office/>`_ open dataset.

S3 path convention
------------------
All files live under the root configured in ``ROOT_DIRECTORIES["MOGlobal10km"]``
(defaults to ``s3://met-office-atmospheric-model-data/global-deterministic/``).
Within that root the key structure is::

    <YYYYMMDD>T<HH>Z/
        <YYYYMMDD>T<HH>Z_<model>_<variable>[_<level>].nc

For example::

    s3://met-office-atmospheric-model-data/global-deterministic/
        20230601T0000Z/
            20230601T0000Z_global-10km_2t.nc

.. note::
    The exact S3 key layout may evolve as the ASDI programme develops.
    Adjust ``_build_s3_key`` if your data uses a different layout.
"""

from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING

import xarray as xr

import pyearthtools.data
from pyearthtools.data import Petdt
from pyearthtools.data.exceptions import DataNotFoundError
from pyearthtools.data.warnings import IndexWarning
from pyearthtools.data.indexes import ArchiveIndex, decorators
from pyearthtools.data.transforms import Transform, TransformCollection
from pyearthtools.data.archive import register_archive

from site_archive_aws.utilities import (
    cached_s3_ls,
    cached_s3_exists,
    open_s3_dataset,
    postprocess_dataset,
    join_s3,
)
from site_archive_aws.ancilliary.variables import (
    MOGLOBAL_10KM_VARIABLES,
    MOGLOBAL_10KM_SURFACE_VARIABLES,
    MOGLOBAL_10KM_PRESSURE_VARIABLES,
    MOGLOBAL_10KM_PRESSURE_LEVELS,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Temporal resolution of the Global 10km dataset: one analysis / forecast
#: output every 6 hours (00Z, 06Z, 12Z, 18Z).
MOGLOBAL10KM_RESOLUTION = (6, "h")

#: Default AWS S3 root for this dataset (public, no auth required).
DEFAULT_S3_ROOT = "s3://met-office-atmospheric-model-data/global-deterministic/"

#: Model identifier used in S3 key construction.
MODEL_ID = "global-10km"


# ---------------------------------------------------------------------------
# Accessor class
# ---------------------------------------------------------------------------


@register_archive("MOGlobal10km", sample_kwargs=dict(variable="2t"))
class MOGlobal10km(ArchiveIndex):
    """
    Met Office Global 10 km Deterministic NWP – AWS ASDI accessor.

    Provides time-indexed access to operational Met Office Global NWP
    analyses and short-range forecasts (T+0 to T+54) at ~10 km resolution,
    served from AWS S3.

    The accessor follows the standard :class:`pyearthtools.data.indexes.ArchiveIndex`
    interface: index with a datetime string or :class:`~pyearthtools.data.Petdt`
    to retrieve an :class:`xarray.Dataset`.

    Example::

        import site_archive_aws
        accessor = site_archive_aws.MOGlobal10km("2t")
        ds = accessor["2023-06-01T00:00"]
        ds["air_temperature"].plot()

    Args:
        variables (list[str] | str):
            One or more short variable names from
            :data:`~site_archive_aws.ancilliary.variables.MOGLOBAL_10KM_VARIABLES`.
            E.g. ``"2t"``, ``["10u", "10v"]``, ``"t"``.
        level_value (int | float | list | None):
            Pressure level(s) in hPa to select for pressure-level variables.
            Ignored for surface variables.  Available levels:
            ``[1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 50]``.
        forecast_hour (int | None):
            Lead time (hours) to retrieve.  If ``None`` the T+0 analysis
            is returned.  Valid range: 0–54 in 6-hour steps.
        anon (bool):
            If ``True`` use anonymous S3 access (works for public buckets).
            Defaults to ``False`` (standard boto3 credential chain).
        transforms (Transform | TransformCollection | None):
            Additional transforms to apply after loading.
    """

    @property
    def _desc_(self):
        """Human-readable description used by pyearthtools catalogue."""
        return {
            "singleline": "Met Office Global 10 km Deterministic NWP (AWS ASDI)",
            "range": "2019–present",
            "Documentation": (
                "https://registry.opendata.aws/uk-met-office/"
            ),
        }

    @decorators.alias_arguments(
        level_value=["pressure", "level"],
        variables=["variable"],
    )
    @decorators.variable_modifications(variable_keyword="variables", remove_variables=False)
    def __init__(
        self,
        variables: list[str] | str,
        *,
        level_value: int | float | list[int | float] | None = None,
        forecast_hour: int | None = None,
        anon: bool = False,
        transforms: Transform | TransformCollection | None = None,
    ):
        self.variables = [variables] if isinstance(variables, str) else list(variables)
        self.level_value = level_value
        self.forecast_hour = forecast_hour  # None → analysis (T+0)
        self.anon = anon

        # Validate variables
        unknown = set(self.variables) - set(MOGLOBAL_10KM_VARIABLES)
        if unknown:
            raise ValueError(
                f"Unknown variable(s) {unknown!r}. "
                f"Available: {sorted(MOGLOBAL_10KM_VARIABLES)}"
            )

        # Build base transform chain
        base_transform = pyearthtools.data.transforms.variables.Trim(self.variables)

        if level_value is not None:
            # Select specific pressure levels
            base_transform += pyearthtools.data.transforms.coordinates.Select(
                {coord: level_value for coord in ["level", "pressure_level"]},
                ignore_missing=True,
            )

        super().__init__(
            transforms=base_transform + (transforms or TransformCollection()),
            data_interval=MOGLOBAL10KM_RESOLUTION,
        )
        self.record_initialisation()

    # ------------------------------------------------------------------
    # S3 path construction
    # ------------------------------------------------------------------

    def _build_s3_key(self, querytime: Petdt, variable: str) -> str:
        """
        Construct the S3 URI for a specific variable at a given time.

        The path convention mirrors the Met Office ASDI key layout::

            <root>/<YYYYMMDD>T<HH>Z/<YYYYMMDD>T<HH>Z_<model>_<varname>.nc

        Args:
            querytime (Petdt): Model initialisation time.
            variable (str): Short variable name (e.g. ``"2t"``).

        Returns:
            str: Full S3 URI.
        """
        root = self.ROOT_DIRECTORIES.get("MOGlobal10km", DEFAULT_S3_ROOT)
        date_key = querytime.strftime("%Y%m%dT%H%MZ")  # e.g. 20230601T0000Z
        varname = variable  # use the short name; files may be named e.g. "2t.nc"

        # Optional: append lead time suffix if a forecast hour is requested
        if self.forecast_hour is not None:
            lead = f"_T+{self.forecast_hour:03d}"
        else:
            lead = ""

        filename = f"{date_key}_{MODEL_ID}_{varname}{lead}.nc"
        return join_s3(root, date_key, filename)

    # ------------------------------------------------------------------
    # filesystem() – required by ArchiveIndex
    # ------------------------------------------------------------------

    def filesystem(
        self,
        querytime: str | Petdt,
    ) -> dict[str, str]:
        """
        Return a mapping of {variable_name: S3_URI} for the given time.

        This method is called by the base :class:`ArchiveIndex` machinery
        when the accessor is indexed with a datetime.  It constructs the
        expected S3 URIs and verifies (with caching) that they exist.

        Args:
            querytime (str | Petdt): Model initialisation date/time.

        Returns:
            dict[str, str]: Mapping from variable name to S3 URI.

        Raises:
            DataNotFoundError: If no data file is found for this time.
            IndexWarning: If ``querytime`` is not aligned to the 6-hourly
                analysis cycle and is silently rounded down.
        """
        querytime = Petdt(querytime)

        # Warn if time is not on a 6-hourly boundary
        resolution_hours = MOGLOBAL10KM_RESOLUTION[0]
        if int(querytime.hour) % resolution_hours != 0:
            warnings.warn(
                f"Global 10km data is available at {resolution_hours}-hourly intervals; "
                f"{querytime} is not aligned. Rounding down to nearest valid time.",
                IndexWarning,
            )

        paths: dict[str, str] = {}
        for variable in self.variables:
            uri = self._build_s3_key(querytime, variable)
            if not cached_s3_exists(uri, anon=self.anon):
                raise DataNotFoundError(
                    f"Cannot find data for variable={variable!r} at {querytime}.\n"
                    f"Expected S3 URI: {uri}\n"
                    "Check that your ROOT_DIRECTORIES['MOGlobal10km'] is correct and "
                    "that you have access to the bucket."
                )
            paths[variable] = uri
        return paths

    # ------------------------------------------------------------------
    # __getitem__ – override for S3-aware loading
    # ------------------------------------------------------------------

    def __getitem__(self, key) -> xr.Dataset:
        """
        Load and return a dataset for the given time key.

        Overrides the base class to use S3-aware xarray loading via
        :func:`~site_archive_aws.utilities.open_s3_dataset`.

        Args:
            key: A datetime string, :class:`~pyearthtools.data.Petdt`, or
                 slice accepted by the base class.

        Returns:
            xr.Dataset: The loaded and post-processed dataset.
        """
        querytime = Petdt(key)
        uri_map = self.filesystem(querytime)

        datasets = []
        for variable, uri in uri_map.items():
            logger.debug("Opening %s from %s", variable, uri)
            ds = open_s3_dataset(uri, engine="h5netcdf", anon=self.anon)
            datasets.append(ds)

        # Merge all variable datasets into one
        merged = xr.merge(datasets) if len(datasets) > 1 else datasets[0]
        merged = postprocess_dataset(merged)

        # Apply any user-specified transforms
        return self._apply_transforms(merged)

    @property
    def _import(self):
        """Dotted import path (used by pyearthtools serialisation)."""
        return "site_archive_aws.MOGlobal10km"

