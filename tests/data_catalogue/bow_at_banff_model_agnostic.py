import hydromt
import xarray as xr
from hydromt.log import setuplog
import numpy as np
import geopandas as gpd
import easymore as easymore

from cwarhm.model_agnostic_processing import HRU as hru

# additional functions (to be placed elsewhere)
def add_basin_attributes_to_zonal_stats(zstats,gpd_hrus,attrs_dict = {}):
    # fix names to original
    var_names = list(zstats.keys())
    var_names_stripped = [n.split('_mean')[0] for n in var_names]
    zstats = zstats.rename(dict(zip(var_names, var_names_stripped)))
    zstats = zstats.rename({'index':'subbasin'})
    zstats['longitude'] = (['subbasin'],gpd_hrus['center_lon'])
    zstats['latitude'] = (['subbasin'],gpd_hrus['center_lat'])
    zstats['hruId'] = (['subbasin'],gpd_hrus['HRU_ID'])
    zstats['geometry'] = (['subbasin'],gpd_hrus['geometry'])
    zstats = zstats.set_coords([ 'longitude', 'latitude','hruId','geometry'])
    zstats.attrs = attrs_dict
    return zstats

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

# alternative zonal stats
zstats_era5 = ds_era5.raster.zonal_stats(gpd_hrus,'mean',all_touched=True)
zstats_era5 = add_basin_attributes_to_zonal_stats(zstats_era5,gpd_hrus)



