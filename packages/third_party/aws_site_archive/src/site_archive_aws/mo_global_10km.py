import pathlib

import xarray

from pyearthtools.data import Petdt
from pyearthtools.data.indexes import ArchiveIndex
from pyearthtools.data.transforms import Transform, TransformCollection
from pyearthtools.data.archive import register_archive

class MO_UKV_AWS(ArchiveIndex):
    """
    """
    MO_GLOBAL_AWS_ROOT_PATH = 's3://met-office-atmospheric-model-data/global-deterministic-10km/'
    MO_GLOBAL_AWS_DIR_TEMPLATE = MO_UKV_AWS_ROOT_PATH + '{vt_str}'
    MO_GLOBAL__FNAME_TEMPLATE = '{vt_str}-PT0000H00M-{var_name}.nc'

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

        for var_name in self._variables:
            try:
                current_fname = MO_UKV.MO_UKV_FNAME_TEMPLATE.format(vt_str=vt_template.format(dt=querytime),
                                                                    var_name=var_name)
                current_dir = MO_UKV.MO_UKV_AWS_DIR_TEMPLATE.format(vt_str=vt_template.format(dt=querytime))
                current_path = f'{current_dir}/{current_fname}'
                paths += [current_path]
            except KeyError:
                print(f'No data for var {var_name}')

        print(paths)
        return paths

    def load(self, *args, **kwargs):
        ds = xarray.merge([xarray.open_dataset(path1, **open_args) for path1 in args[0]])
        return ds

        return ds

    def __desc__(self):
        return {
            "singleline": "Met Office UKV Forecast Analysis ",
            "range": "June 2026",
            "Documentation": "https://registry.opendata.aws/met-office-uk-deterministic/",
        }

