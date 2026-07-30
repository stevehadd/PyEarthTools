# (C) British Crown Copyright 2024-2026, Met Office.
# Please see LICENSE for licence details.

"""
Met Office UKV (UK Variable-Resolution Model) – AWS ASDI accessor.

The UKV is the Met Office's operational high-resolution deterministic model
covering the United Kingdom and surrounding waters at approximately 1.5 km
horizontal grid spacing.  It is published to AWS S3 as part of the
`Met Office Atmospheric Model Data
<https://registry.opendata.aws/uk-met-office/>`_ open dataset.

The UKV uses a rotated-pole grid, which means latitude and longitude
coordinates in the files are named ``grid_latitude`` and ``grid_longitude``.
This accessor applies a rename transform so that downstream code always sees
``latitude`` and ``longitude``.

S3 path convention
------------------
Files live under ``ROOT_DIRECTORIES["MOUKV"]``
(default: ``s3://met-office-atmospheric-model-data/uk-deterministic/``).
Key layout::

    <YYYYMMDD>T<HH>Z/<YYYYMMDD>T<HH>Z_ukv_<variable>[_<level>].nc
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
    cached_s3_exists,
    open_s3_dataset,
    postprocess_dataset,
    join_s3,
)
from site_archive_aws.ancilliary.variables import (
    MOUKV_VARIABLES,
    MOUKV_SURFACE_VARIABLES,
    MOUKV_PRESSURE_VARIABLES,
    MOUKV_PRESSURE_LEVELS,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Temporal resolution of the UKV dataset – hourly analyses.
MOUKV_RESOLUTION = (1, "h")

#: Default S3 root for the UKV dataset.
DEFAULT_S3_ROOT = "s3://met-office-atmospheric-model-data/uk-deterministic/"

#: Model identifier used in file naming.
MODEL_ID = "ukv"

#: Coordinate rename mapping to normalise rotated-pole coordinates.
UKV_COORD_RENAME = {
    "grid_latitude": "latitude",
    "grid_longitude": "longitude",
}


# ---------------------------------------------------------------------------
# Accessor class
# ---------------------------------------------------------------------------


@register_archive("MOUKV_AWS", sample_kwargs=dict(variable="2t"))
class MOUKV(ArchiveIndex):
    """
    Met Office UKV (UK Variable-Resolution Model) – AWS ASDI accessor.

    Provides time-indexed access to operational Met Office UKV analyses and
    short-range forecasts at ~1.5 km resolution over the UK, served from
    AWS S3.

    The UKV has a rotated-pole coordinate system; this accessor automatically
    renames ``grid_latitude`` → ``latitude`` and ``grid_longitude`` →
    ``longitude`` for consistency with other accessors.

    Example::

        import site_archive_aws
        accessor = site_archive_aws.MOUKV("2t")
        ds = accessor["2023-06-01T06:00"]
        ds["air_temperature"].isel(time=0).plot()

    Args:
        variables (list[str] | str):
            One or more short variable names from
            :data:`~site_archive_aws.ancilliary.variables.MOUKV_VARIABLES`.
        level_value (int | float | list | None):
            Pressure level(s) in hPa to select for upper-air variables.
        forecast_hour (int | None):
            Lead time (hours).  If ``None`` the analysis (T+0) is returned.
            Valid range: 0–36 hours.
        anon (bool):
            Use anonymous S3 access for public buckets.
        transforms (Transform | TransformCollection | None):
            Additional pyearthtools transforms to apply after loading.
    """

    @property
    def _desc_(self):
        return {
            "singleline": "Met Office UKV (~1.5 km) Model (AWS ASDI)",
            "range": "2019–present",
            "Documentation": "https://registry.opendata.aws/uk-met-office/",
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
        self.forecast_hour = forecast_hour
        self.anon = anon

        # Validate variable names
        unknown = set(self.variables) - set(MOUKV_VARIABLES)
        if unknown:
            raise ValueError(
                f"Unknown variable(s) {unknown!r}. Available: {sorted(MOUKV_VARIABLES)}"
            )

        # Build transform chain
        base_transform = pyearthtools.data.transforms.variables.Trim(self.variables)

        # Rename rotated-pole coordinates to standard names
        base_transform += pyearthtools.data.transforms.attributes.Rename(UKV_COORD_RENAME)

        if level_value is not None:
            base_transform += pyearthtools.data.transforms.coordinates.Select(
                {coord: level_value for coord in ["level", "pressure_level"]},
                ignore_missing=True,
            )

        super().__init__(
            transforms=base_transform + (transforms or TransformCollection()),
            data_interval=MOUKV_RESOLUTION,
        )
        self.record_initialisation()

    # ------------------------------------------------------------------
    # S3 path construction
    # ------------------------------------------------------------------

    def _build_s3_key(self, querytime: Petdt, variable: str) -> str:
        """
        Construct the S3 URI for a UKV variable at a given time.

        Args:
            querytime (Petdt): Model initialisation time.
            variable (str): Short variable name (e.g. ``"2t"``).

        Returns:
            str: Full S3 URI.
        """
        root = self.ROOT_DIRECTORIES.get("MOUKV_AWS", DEFAULT_S3_ROOT)
        date_key = querytime.strftime("%Y%m%dT%H%MZ")

        if self.forecast_hour is not None:
            lead = f"_T+{self.forecast_hour:03d}"
        else:
            lead = ""

        filename = f"{date_key}_{MODEL_ID}_{variable}{lead}.nc"
        return join_s3(root, date_key, filename)

    # ------------------------------------------------------------------
    # filesystem()
    # ------------------------------------------------------------------

    def filesystem(
        self,
        querytime: str | Petdt,
    ) -> dict[str, str]:
        """
        Return ``{variable: S3_URI}`` for the given model time.

        Args:
            querytime (str | Petdt): Model initialisation date/time.

        Returns:
            dict[str, str]: Mapping from variable name to S3 URI.

        Raises:
            DataNotFoundError: If no data are found for this time.
        """
        querytime = Petdt(querytime)

        paths: dict[str, str] = {}
        for variable in self.variables:
            uri = self._build_s3_key(querytime, variable)
            if not cached_s3_exists(uri, anon=self.anon):
                raise DataNotFoundError(
                    f"Cannot find UKV data for variable={variable!r} at {querytime}.\n"
                    f"Expected S3 URI: {uri}"
                )
            paths[variable] = uri
        return paths

    # ------------------------------------------------------------------
    # __getitem__
    # ------------------------------------------------------------------

    def __getitem__(self, key) -> xr.Dataset:
        """
        Load a UKV dataset for the given time key.

        Args:
            key: Datetime string, :class:`~pyearthtools.data.Petdt`, or slice.

        Returns:
            xr.Dataset: Loaded and post-processed dataset with standard
                ``latitude``/``longitude`` coordinates.
        """
        querytime = Petdt(key)
        uri_map = self.filesystem(querytime)

        datasets = []
        for variable, uri in uri_map.items():
            logger.debug("Opening UKV %s from %s", variable, uri)
            ds = open_s3_dataset(uri, engine="h5netcdf", anon=self.anon)
            datasets.append(ds)

        merged = xr.merge(datasets) if len(datasets) > 1 else datasets[0]
        merged = postprocess_dataset(merged)
        return self._apply_transforms(merged)

    @property
    def _import(self):
        return "site_archive_aws.MOUKV"

