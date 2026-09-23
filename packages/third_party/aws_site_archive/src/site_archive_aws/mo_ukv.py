# Copyright Commonwealth of Australia, Bureau of Meteorology 2026.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pathlib

import xarray

import pyearthtools
import pyearthtools.data

from pyearthtools.data import Petdt
from pyearthtools.data.indexes import ArchiveIndex
from pyearthtools.data.transforms import Transform, TransformCollection
from pyearthtools.data.archive import register_archive

@register_archive("MOUKV", sample_kwargs=dict(variable="temperature_on_pressure_levels"))
class MOUKV(ArchiveIndex):
    """
    Data Accessor for accessing Met Office data through the AWS Sustainable Data initiative.
    """
    MO_UKV_AWS_ROOT_PATH = 's3://met-office-atmospheric-model-data/uk-deterministic-2km/'
    MO_UKV_AWS_DIR_TEMPLATE = MO_UKV_AWS_ROOT_PATH + '{vt_str}'
    MO_UKV_FNAME_TEMPLATE = '{vt_str}-PT0000H00M-{var_name}.nc'

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

        if not self._variables:
            raise pyearthtools.data.DataNotFoundError('No variables specified to load.')
            
        querytime = Petdt(querytime)
        paths = []

        vt_template= '{dt.year:04d}{dt.month:02d}{dt.day:02d}T{dt.hour:02d}{dt.minute:02d}Z'
        _fname_template = '{vt_str}-PT0000H00M-{var_name}.nc'
        
        for var_name in self._variables:
            try:
                current_fname = MOUKV.MO_UKV_FNAME_TEMPLATE.format(vt_str=vt_template.format(dt=querytime),
                                                                    var_name=var_name)
                current_dir = MOUKV.MO_UKV_AWS_DIR_TEMPLATE.format(vt_str=vt_template.format(dt=querytime))
                current_path = f'{current_dir}/{current_fname}'
                paths += [current_path]
            except KeyError:
                print(f'No data for var {var_name}')
        print(paths)
        return paths

    def load(self, *args, **kwargs):
        ds = xarray.merge([xarray.open_dataset(path1, **self._open_args) for path1 in args[0]])
        return ds

    def __desc__(self):
        return {
            "singleline": "Met Office UKV Forecast Analysis ",
            "range": "June 2026",
            "Documentation": "https://registry.opendata.aws/met-office-uk-deterministic/",
        }

