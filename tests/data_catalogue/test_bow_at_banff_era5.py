import hydromt
import xarray as xr
from hydromt.log import setuplog
import numpy as np
import geopandas as gpd
import easymore as easymore

from cwarhm.model_agnostic_processing import HRU as hru

# set datacatalog
logger = setuplog('test_datacatalog',log_level=10)
data_catalog = hydromt.DataCatalog('datacatalog.yml', logger=logger)

# remap era5 forcing data
# open datasets
ds_era5_preslev = data_catalog.get_rasterdataset('era5_pressure_level')
ds_era5_surf = data_catalog.get_rasterdataset('era5_surface_level')

# open shapefiles
gpd_basins = data_catalog.get_geodataframe('river_basins')
gpd_hrus = data_catalog.get_geodataframe('basins_hru')

# calculate directionless windspeed and drop directional variables
ds_era5_preslev['windspd'] = np.sqrt(ds_era5_preslev['wind-u']*ds_era5_preslev['wind-v'])
ds_era5_preslev = ds_era5_preslev.drop(['wind-u','wind-v'])

ds_era5 = xr.merge([ds_era5_surf,ds_era5_preslev])
#ds_era5.to_netcdf('merge_era5_test.nc')

# initializing EASYMORE object
hru.map_forcing_data(data_catalog['river_basins'].path, 'merge_era5_test.nc', './output/',
                    var_names=list(ds_era5.keys()),  var_lon='longitude', var_lat='latitude', var_time='time',
                    case_name='BowAtBanff',temp_dir='./esmr_temp/', format_list=['f4'],
                    fill_value_list = ['-999'], save_csv = False
                    )

# alternative zonal stats
zstats_era5 = ds_era5.raster.zonal_stats(gpd_hrus,'mean',all_touched=True)

# comparison
ds_era5_ref = xr.open_dataset('/Users/ayx374/Documents/project/chwarm_test_results/domain_BowAtBanff/forcing/3_basin_averaged_data/BowAtBanff_remapped_2008-02-01-00-00-00.nc')