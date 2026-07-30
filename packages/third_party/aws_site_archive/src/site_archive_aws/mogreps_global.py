# (C) British Crown Copyright 2024-2026, Met Office.
# Please see LICENSE for licence details.

"""
Met Office MOGREPS-G (Global Ensemble Prediction System) – AWS ASDI accessor.

MOGREPS-G is the Met Office global ensemble prediction system.  It produces
18-member ensemble forecasts at approximately 20 km horizontal grid spacing
out to 7 days.  Data are published to AWS S3 as part of the
`Met Office Atmospheric Model Data
<https://registry.opendata.aws/uk-met-office/>`_ open dataset.

The ensemble dimension is accessible via the ``realization`` coordinate, which
takes integer values 0–17 (corresponding to the control plus 17 perturbed
members).

S3 path convention
------------------
Files live under ``ROOT_DIRECTORIES["MOGREPSGlobal"]``
(default: ``s3://met-office-ensemble-model-data/global-ensemble/``).
Key layout::

    <YYYYMMDD>T<HH>Z/
        <YYYYMMDD>T<HH>Z_mogreps-g_<member>_<variable>.nc

where ``<member>`` is a zero-padded integer, e.g. ``000``, ``001``, … ``017``.
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
    cached_s3_ls,
    open_s3_dataset,
    postprocess_dataset,
    join_s3,
)
from site_archive_aws.ancilliary.variables import (
    MOGREPS_GLOBAL_VARIABLES,
    MOGREPS_GLOBAL_SURFACE_VARIABLES,
    MOGREPS_GLOBAL_PRESSURE_VARIABLES,
    MOGREPS_GLOBAL_PRESSURE_LEVELS,
    MOGREPS_GLOBAL_N_MEMBERS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Temporal resolution of MOGREPS-G: analyses every 6 hours.
MOGREPS_GLOBAL_RESOLUTION = (6, "h")

#: Default S3 root for the MOGREPS-G dataset.
DEFAULT_S3_ROOT = "s3://met-office-ensemble-model-data/global-ensemble/"

#: Model identifier used in file naming.
MODEL_ID = "mogreps-g"

#: Total number of ensemble members (control + perturbed).
N_MEMBERS = MOGREPS_GLOBAL_N_MEMBERS


# ---------------------------------------------------------------------------
# Accessor class
# ---------------------------------------------------------------------------


@register_archive("MOGREPSGlobal", sample_kwargs=dict(variable="2t"))
class MOGREPSGlobal(ArchiveIndex):
    """
    Met Office MOGREPS-G Global Ensemble – AWS ASDI accessor.

    Provides time-indexed access to the 18-member MOGREPS-G ensemble,
    returning data with a ``realization`` (member) dimension.

    All ensemble members for the requested variables are loaded and
    concatenated along a ``realization`` dimension, giving an
    :class:`xarray.Dataset` of shape
    ``(realization, time, latitude, longitude)`` for surface fields or
    ``(realization, time, level, latitude, longitude)`` for pressure fields.

    Example::

        import site_archive_aws
        # Load 2-m temperature for all 18 ensemble members
        ensemble = site_archive_aws.MOGREPSGlobal("2t")
        ds = ensemble["2023-06-01T00:00"]
        # ds["air_temperature"] has dims (realization, time, latitude, longitude)
        ds["air_temperature"].mean("realization").isel(time=0).plot()

    Args:
        variables (list[str] | str):
            One or more short variable names from
            :data:`~site_archive_aws.ancilliary.variables.MOGREPS_GLOBAL_VARIABLES`.
        level_value (int | float | list | None):
            Pressure level(s) in hPa to select for upper-air variables.
        members (list[int] | None):
            Ensemble member indices to load (0-based).  If ``None`` all
            :data:`N_MEMBERS` members are loaded.
        forecast_hour (int | None):
            Lead time in hours.  If ``None`` T+0 is returned.
        anon (bool):
            Use anonymous S3 access.
        transforms (Transform | TransformCollection | None):
            Additional transforms.
    """

    @property
    def _desc_(self):
        return {
            "singleline": "Met Office MOGREPS-G 18-member Global Ensemble (AWS ASDI)",
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
        unknown = set(self.variables) - set(MOGREPS_GLOBAL_VARIABLES)
        if unknown:
            raise ValueError(
                f"Unknown variable(s) {unknown!r}. "
                f"Available: {sorted(MOGREPS_GLOBAL_VARIABLES)}"
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

        if level_value is not None:
            base_transform += pyearthtools.data.transforms.coordinates.Select(
                {coord: level_value for coord in ["level", "pressure_level"]},
                ignore_missing=True,
            )

        super().__init__(
            transforms=base_transform + (transforms or TransformCollection()),
            data_interval=MOGREPS_GLOBAL_RESOLUTION,
        )
        self.record_initialisation()

    # ------------------------------------------------------------------
    # S3 path construction
    # ------------------------------------------------------------------

    def _build_s3_key(self, querytime: Petdt, variable: str, member: int) -> str:
        """
        Construct the S3 URI for one member of a MOGREPS-G variable.

        Args:
            querytime (Petdt): Model initialisation time.
            variable (str): Short variable name.
            member (int): 0-based ensemble member index.

        Returns:
            str: Full S3 URI.
        """
        root = self.ROOT_DIRECTORIES.get("MOGREPSGlobal", DEFAULT_S3_ROOT)
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

        The keys are formatted as ``"<variable>_<member>"`` (e.g. ``"2t_000"``).

        Args:
            querytime (str | Petdt): Model initialisation time.

        Returns:
            dict[str, str]: URI map.

        Raises:
            DataNotFoundError: If any expected file is absent.
        """
        querytime = Petdt(querytime)

        resolution_hours = MOGREPS_GLOBAL_RESOLUTION[0]
        if int(querytime.hour) % resolution_hours != 0:
            warnings.warn(
                f"MOGREPS-G data is at {resolution_hours}-hourly intervals; "
                f"{querytime} is not aligned. Rounding down.",
                IndexWarning,
            )

        paths: dict[str, str] = {}
        for variable in self.variables:
            for member in self.members:
                uri = self._build_s3_key(querytime, variable, member)
                if not cached_s3_exists(uri, anon=self.anon):
                    raise DataNotFoundError(
                        f"Cannot find MOGREPS-G data for variable={variable!r}, "
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
            key: Datetime string, :class:`~pyearthtools.data.Petdt`, or slice.

        Returns:
            xr.Dataset: Dataset with a ``realization`` dimension containing
                all requested ensemble members.
        """
        querytime = Petdt(key)
        uri_map = self.filesystem(querytime)

        # Group URIs by variable, then concatenate members
        per_variable: dict[str, list[xr.Dataset]] = {v: [] for v in self.variables}

        for key_str, uri in uri_map.items():
            # key_str format: "<variable>_<member_int>"
            variable = "_".join(key_str.split("_")[:-1])
            member_idx = int(key_str.split("_")[-1])

            logger.debug("Opening MOGREPS-G %s member %03d from %s", variable, member_idx, uri)
            ds = open_s3_dataset(uri, engine="h5netcdf", anon=self.anon)
            # Tag this dataset with its member index
            ds = ds.expand_dims({"realization": [member_idx]})
            per_variable[variable].append(ds)

        # Concatenate members for each variable, then merge variables
        merged_vars = []
        for variable, member_datasets in per_variable.items():
            concat_ds = xr.concat(member_datasets, dim="realization")
            merged_vars.append(concat_ds)

        merged = xr.merge(merged_vars) if len(merged_vars) > 1 else merged_vars[0]
        merged = postprocess_dataset(merged)
        return self._apply_transforms(merged)

    @property
    def _import(self):
        return "site_archive_aws.MOGREPSGlobal"

