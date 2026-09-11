import pathlib

import xarray

import pyearthtools
import pyearthtools.data

from pyearthtools.data import Petdt
from pyearthtools.data.indexes import ArchiveIndex
from pyearthtools.data.transforms import Transform, TransformCollection
from pyearthtools.data.archive import register_archive

@register_archive("MOGlobal10km", sample_kwargs=dict(variable="temperature_on_pressure_levels"))
class MOGlobal10km(ArchiveIndex):
    """
    """
    MO_GLOBAL_AWS_ROOT_PATH = 's3://met-office-atmospheric-model-data/global-deterministic-10km/'
    MO_GLOBAL_AWS_DIR_TEMPLATE = MO_GLOBAL_AWS_ROOT_PATH + '{vt_str}'
    MO_GLOBAL_FNAME_TEMPLATE = '{vt_str}-PT0000H00M-{var_name}.nc'

    def __init__(
            self,
            variables: list[str] | str,
            *,
            transforms: Transform | TransformCollection | None = None,
    ):
        """
        Init function for Merra2 accessor base class.
        """
        self._variables = variables
        self._open_args = {
            'engine':"h5netcdf", #
            'storage_options': {"anon": True},
        }
        self._mf_args = {
            'concat_dim' : 'time',
            'combine' :'nested'
        }
            
        super_transforms = TransformCollection(
            [pyearthtools.data.transforms.variables.Trim(self._variables), ]) + transforms

        # call the base class
        super().__init__(
            transforms=super_transforms,
        )
        self.record_initialisation()

    def filesystem(
            self,
            querytime: str | Petdt,
    ) -> pathlib.Path | dict[str, str | pathlib.Path]:

        querytime = Petdt(querytime)
        paths = []
        vt_template= '{dt.year:04d}{dt.month:02d}{dt.day:02d}T{dt.hour:02d}{dt.minute:02d}Z'
        _fname_template = '{vt_str}-PT0000H00M-{var_name}.nc'
        
        for var_name in self._variables:
            try:
                current_fname = MOGlobal10km.MO_GLOBAL_FNAME_TEMPLATE.format(vt_str=vt_template.format(dt=querytime),
                                                                    var_name=var_name)
                current_dir = MOGlobal10km.MO_GLOBAL_AWS_DIR_TEMPLATE.format(vt_str=vt_template.format(dt=querytime))
                current_path = f'{current_dir}/{current_fname}'
                paths += [current_path]
            except KeyError:
                print(f'No data for var {var_name}')

        print(paths)
        return paths

    def load(self, *args, **kwargs):
        ds = xarray.merge([xarray.open_dataset(path1, **self._open_args) for path1 in args[0]])
        return ds

        return ds

    def __desc__(self):
        return {
            "singleline": "Met Office 10km Global Determinsitic Forecast Analysis ",
            "range": "June 2026",
            "Documentation": "https://registry.opendata.aws/met-office-uk-deterministic/",
        }

