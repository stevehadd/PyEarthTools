# (C) British Crown Copyright 2024-2026, Met Office.
# Please see LICENSE for licence details.

"""
Met Office MOGREPS-UK (UK Regional Ensemble) – AWS ASDI accessor.

MOGREPS-UK is the Met Office's operational UK-domain ensemble prediction system.
It produces 18-member ensemble forecasts at approximately 2.2 km horizontal
grid spacing over the United Kingdom, out to 54 hours.  Data are published to
AWS S3 as part of the
`Met Office Atmospheric Model Data
<https://registry.opendata.aws/uk-met-office/>`_ open dataset.

Like the UKV, MOGREPS-UK uses a rotated-pole coordinate system.  This accessor
normalises ``grid_latitude`` → ``latitude`` and ``grid_longitude`` →
``longitude`` automatically.

S3 path convention
------------------
Files live under ``ROOT_DIRECTORIES["MOGREPSUK"]``
(default: ``s3://met-office-ensemble-model-data/uk-ensemble/``).
Key layout::

    <YYYYMMDD>T<HH>Z/
        <YYYYMMDD>T<HH>Z_mogreps-uk_<member>_<variable>.nc
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
    MOGREPS_UK_VARIABLES,
    MOGREPS_UK_SURFACE_VARIABLES,
    MOGREPS_UK_PRESSURE_VARIABLES,
    MOGREPS_UK_PRESSURE_LEVELS,
    MOGREPS_UK_N_MEMBERS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Temporal resolution of MOGREPS-UK: 3-hourly analyses.
MOGREPS_UK_RESOLUTION = (3, "h")

#: Default S3 root for the MOGREPS-UK dataset.
DEFAULT_S3_ROOT = "s3://met-office-ensemble-model-data/uk-ensemble/"

#: Model identifier in file naming.
MODEL_ID = "mogreps-uk"

#: Number of ensemble members.
N_MEMBERS = MOGREPS_UK_N_MEMBERS

#: Coordinate rename for rotated-pole grids.
UKV_COORD_RENAME = {
    "grid_latitude": "latitude",
    "grid_longitude": "longitude",
}


# ---------------------------------------------------------------------------
# Accessor class
# ---------------------------------------------------------------------------


@register_archive("MOGREPSUK", sample_kwargs=dict(variable="2t"))
class MOGREPSUK(ArchiveIndex):
    """
    Met Office MOGREPS-UK Regional Ensemble – AWS ASDI accessor.

    Provides time-indexed access to the 18-member MOGREPS-UK ensemble at
    ~2.2 km resolution over the UK, returned with a ``realization`` coordinate.

    Example::

        import site_archive_aws
        # Load all members for 10-metre wind components
        ens = site_archive_aws.MOGREPSUK(["10u", "10v"])
        ds = ens["2023-06-01T03:00"]
        # Ensemble-mean wind speed
        speed = (ds["x_wind"] ** 2 + ds["y_wind"] ** 2) ** 0.5
        speed.mean("realization").isel(time=0).plot()

    Args:
        variables (list[str] | str):
            Short variable names from
            :data:`~site_archive_aws.ancilliary.variables.MOGREPS_UK_VARIABLES`.
        level_value (int | float | list | None):
            Pressure level(s) in hPa for upper-air variables.
        members (list[int] | None):
            Member indices to load (0-based, 0–17).  Defaults to all members.
        forecast_hour (int | None):
            Lead time in hours.  Defaults to T+0 (analysis).
        anon (bool):
            Use anonymous S3 access.
        transforms (Transform | TransformCollection | None):
            Additional transforms to apply.
    """

    @property
    def _desc_(self):
        return {
            "singleline": "Met Office MOGREPS-UK 18-member Regional Ensemble (AWS ASDI)",
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
        members: list[int] | None = None,
        forecast_hour: int | None = None,
        anon: bool = False,
        transforms: Transform | TransformCollection | None = None,
    ):
        self.variables = [variables] if isinstance(variables, str) else list(variables)
        self.level_value = level_value
        self.members = members if members is not None else list(range(N_MEMBERS))
        self.forecast_hour = forecast_hour
        self.anon = anon

        # Validate variable names
        unknown = set(self.variables) - set(MOGREPS_UK_VARIABLES)
        if unknown:
            raise ValueError(
                f"Unknown variable(s) {unknown!r}. "
                f"Available: {sorted(MOGREPS_UK_VARIABLES)}"
            )

        # Validate member indices
        invalid_members = [m for m in self.members if m < 0 or m >= N_MEMBERS]
        if invalid_members:
            raise ValueError(
                f"Invalid member indices {invalid_members}. "
                f"Valid range: 0–{N_MEMBERS - 1}."
            )

        # Build transform chain
        base_transform = pyearthtools.data.transforms.variables.Trim(self.variables)

        # Normalise rotated-pole coordinate names
        base_transform += pyearthtools.data.transforms.attributes.Rename(UKV_COORD_RENAME)

        if level_value is not None:
            base_transform += pyearthtools.data.transforms.coordinates.Select(
                {coord: level_value for coord in ["level", "pressure_level"]},
                ignore_missing=True,
            )

        super().__init__(
            transforms=base_transform + (transforms or TransformCollection()),
            data_interval=MOGREPS_UK_RESOLUTION,
        )
        self.record_initialisation()

    # ------------------------------------------------------------------
    # S3 path construction
    # ------------------------------------------------------------------

    def _build_s3_key(self, querytime: Petdt, variable: str, member: int) -> str:
        """
        Construct the S3 URI for one member file.

        Args:
            querytime (Petdt): Model initialisation time.
            variable (str): Short variable name.
            member (int): 0-based member index.

        Returns:
            str: Full S3 URI.
        """
        root = self.ROOT_DIRECTORIES.get("MOGREPSUK", DEFAULT_S3_ROOT)
        date_key = querytime.strftime("%Y%m%dT%H%MZ")
        member_str = f"{member:03d}"

        if self.forecast_hour is not None:
            lead = f"_T+{self.forecast_hour:03d}"
        else:
            lead = ""

        filename = f"{date_key}_{MODEL_ID}_{member_str}_{variable}{lead}.nc"
        return join_s3(root, date_key, filename)

    # ------------------------------------------------------------------
    # filesystem()
    # ------------------------------------------------------------------

    def filesystem(
        self,
        querytime: str | Petdt,
    ) -> dict[str, str]:
        """
        Return ``{key: S3_URI}`` for all requested variables and members.

        Args:
            querytime (str | Petdt): Model initialisation time.

        Returns:
            dict[str, str]: URI map keyed as ``"<variable>_<member>"``

        Raises:
            DataNotFoundError: If any expected file is missing from S3.
        """
        querytime = Petdt(querytime)

        resolution_hours = MOGREPS_UK_RESOLUTION[0]
        if int(querytime.hour) % resolution_hours != 0:
            warnings.warn(
                f"MOGREPS-UK data is at {resolution_hours}-hourly intervals; "
                f"{querytime} is not aligned. Rounding down.",
                IndexWarning,
            )

        paths: dict[str, str] = {}
        for variable in self.variables:
            for member in self.members:
                uri = self._build_s3_key(querytime, variable, member)
                if not cached_s3_exists(uri, anon=self.anon):
                    raise DataNotFoundError(
                        f"Cannot find MOGREPS-UK data for variable={variable!r}, "
                        f"member={member} at {querytime}.\n"
                        f"Expected S3 URI: {uri}"
                    )
                paths[f"{variable}_{member:03d}"] = uri
        return paths

    # ------------------------------------------------------------------
    # __getitem__
    # ------------------------------------------------------------------

    def __getitem__(self, key) -> xr.Dataset:
        """
        Load and concatenate all ensemble members for the given time.

        Args:
            key: Datetime string or :class:`~pyearthtools.data.Petdt`.

        Returns:
            xr.Dataset: Dataset with ``realization`` dimension and standard
                ``latitude``/``longitude`` coordinates.
        """
        querytime = Petdt(key)
        uri_map = self.filesystem(querytime)

        per_variable: dict[str, list[xr.Dataset]] = {v: [] for v in self.variables}

        for key_str, uri in uri_map.items():
            variable = "_".join(key_str.split("_")[:-1])
            member_idx = int(key_str.split("_")[-1])

            logger.debug("Opening MOGREPS-UK %s member %03d from %s", variable, member_idx, uri)
            ds = open_s3_dataset(uri, engine="h5netcdf", anon=self.anon)
            ds = ds.expand_dims({"realization": [member_idx]})
            per_variable[variable].append(ds)

        merged_vars = []
        for variable, member_datasets in per_variable.items():
            concat_ds = xr.concat(member_datasets, dim="realization")
            merged_vars.append(concat_ds)

        merged = xr.merge(merged_vars) if len(merged_vars) > 1 else merged_vars[0]
        merged = postprocess_dataset(merged)
        return self._apply_transforms(merged)

    @property
    def _import(self):
        return "site_archive_aws.MOGREPSUK"

