# (C) British Crown Copyright 2024-2026, Met Office.
# Please see LICENSE for licence details.

"""
Variable name constants and metadata for Met Office AWS datasets.

Each dataset section provides:
- ``VARIABLES``: mapping from short user-facing names to the GRIB/NetCDF
  variable names stored in the files.
- ``PRESSURE_LEVELS``: list of available pressure levels (hPa) for
  pressure-level fields, where applicable.
- ``SURFACE_VARIABLES``: subset of variables that are surface/single-level.
- ``PRESSURE_VARIABLES``: subset of variables that require a pressure level.
"""

# ---------------------------------------------------------------------------
# Met Office Global 10 km Deterministic
# ---------------------------------------------------------------------------

# Variables are CF convention standard names:
# https://cfconventions.org/Data/cf-standard-names/current/build/cf-standard-name-table.html
# variables names in orgininal data is taken from Met Office documentation
# https://www.metoffice.gov.uk/api/assets/file/global-10km-ps47-asdi-pdf-updates-20pdf?prefix=assets
MOGLOBAL_10KM_VARIABLES = {
    # Surface / single-level fields
    "air_temperature": "temperature_on_pressure_levels",                     # 2-metre temperature [K]
    "x_wind": "",                              # 10-metre U wind [m/s]
    "y_wind": "y_wind",                              # 10-metre V wind [m/s]
    "air_pressure_at_mean_sea_level": "pressure_at_mean_sea_level",           # Mean sea-level pressure [Pa]
    "wind_speed": "wind_speed_at_10m"
    "tp": "stratiform_rainfall_amount",            # Total precipitation [kg/m²]
    "tcc": "cloud_area_fraction",                 # Total cloud cover [1]
    "vis": "visibility_in_air",                   # Visibility [m]
    "ws": "wind_speed",                           # Wind speed [m/s]
    # Pressure-level fields
    "t": "air_temperature",                       # Temperature [K]
    "u": "eastward_wind",                         # U-component of wind [m/s]
    "v": "northward_wind",                        # V-component of wind [m/s]
    "z": "geopotential_height",                   # Geopotential height [m]
    "q": "specific_humidity",                     # Specific humidity [kg/kg]
    "rh": "relative_humidity",                    # Relative humidity [%]
}

MOGLOBAL_10KM_SURFACE_VARIABLES = {
    "2t", "10u", "10v", "msl", "lsm", "tp", "tcc", "vis", "ws"
}

MOGLOBAL_10KM_PRESSURE_VARIABLES = {"t", "u", "v", "z", "q", "rh"}

MOGLOBAL_10KM_PRESSURE_LEVELS = [
    1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 50
]

# ---------------------------------------------------------------------------
# Met Office UKV (UK Variable-Resolution Model)
# ---------------------------------------------------------------------------

MOUKV_VARIABLES = {
    # Surface / single-level fields
    "2t": "air_temperature",
    "10u": "x_wind",
    "10v": "y_wind",
    "msl": "air_pressure_at_sea_level",
    "lsm": "land_binary_mask",
    "tp": "stratiform_rainfall_amount",
    "tcc": "cloud_area_fraction",
    "vis": "visibility_in_air",
    "ws": "wind_speed",
    "cape": "atmosphere_convective_available_potential_energy",
    # Pressure-level fields
    "t": "air_temperature",
    "u": "eastward_wind",
    "v": "northward_wind",
    "z": "geopotential_height",
    "q": "specific_humidity",
    "rh": "relative_humidity",
    "w": "lagrangian_tendency_of_air_pressure",   # Vertical velocity [Pa/s]
}

MOUKV_SURFACE_VARIABLES = {
    "2t", "10u", "10v", "msl", "lsm", "tp", "tcc", "vis", "ws", "cape"
}

MOUKV_PRESSURE_VARIABLES = {"t", "u", "v", "z", "q", "rh", "w"}

MOUKV_PRESSURE_LEVELS = [
    1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100
]

# ---------------------------------------------------------------------------
# MOGREPS-G (Met Office Global Ensemble)
# ---------------------------------------------------------------------------

MOGREPS_GLOBAL_VARIABLES = {
    # Surface / single-level fields
    "2t": "air_temperature",
    "10u": "x_wind",
    "10v": "y_wind",
    "msl": "air_pressure_at_sea_level",
    "tp": "stratiform_rainfall_amount",
    "tcc": "cloud_area_fraction",
    # Pressure-level fields
    "t": "air_temperature",
    "u": "eastward_wind",
    "v": "northward_wind",
    "z": "geopotential_height",
    "q": "specific_humidity",
}

MOGREPS_GLOBAL_SURFACE_VARIABLES = {"2t", "10u", "10v", "msl", "tp", "tcc"}

MOGREPS_GLOBAL_PRESSURE_VARIABLES = {"t", "u", "v", "z", "q"}

MOGREPS_GLOBAL_PRESSURE_LEVELS = [
    1000, 850, 700, 500, 300, 250, 200
]

# Number of ensemble members in MOGREPS-G
MOGREPS_GLOBAL_N_MEMBERS = 18

# ---------------------------------------------------------------------------
# MOGREPS-UK (Met Office UK Regional Ensemble)
# ---------------------------------------------------------------------------

MOGREPS_UK_VARIABLES = {
    # Surface / single-level fields
    "2t": "air_temperature",
    "10u": "x_wind",
    "10v": "y_wind",
    "msl": "air_pressure_at_sea_level",
    "tp": "stratiform_rainfall_amount",
    "tcc": "cloud_area_fraction",
    "vis": "visibility_in_air",
    "ws": "wind_speed",
    # Pressure-level fields
    "t": "air_temperature",
    "u": "eastward_wind",
    "v": "northward_wind",
    "z": "geopotential_height",
    "q": "specific_humidity",
    "rh": "relative_humidity",
}

MOGREPS_UK_SURFACE_VARIABLES = {
    "2t", "10u", "10v", "msl", "tp", "tcc", "vis", "ws"
}

MOGREPS_UK_PRESSURE_VARIABLES = {"t", "u", "v", "z", "q", "rh"}

MOGREPS_UK_PRESSURE_LEVELS = [
    1000, 925, 850, 700, 500, 300, 250, 200
]

# Number of ensemble members in MOGREPS-UK
MOGREPS_UK_N_MEMBERS = 18

