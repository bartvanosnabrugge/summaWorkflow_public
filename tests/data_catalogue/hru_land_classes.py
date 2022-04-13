import hydromt
import xarray as xr
from hydromt.log import setuplog
import numpy as np
import geopandas as gpd
import easymore as easymore
from scipy import stats

# set datacatalog
logger = setuplog('test_datacatalog',log_level=10)
data_catalog = hydromt.DataCatalog('datacatalog.yml', logger=logger)

ds_land = data_catalog.get_rasterdataset('modis_landclass_vrt4326',bbox=[-116.55,50.95,-115.52,51.74])
# open river basins file
# open hru basins file
gpd_basins = data_catalog.get_geodataframe('river_basins')
gpd_hrus = data_catalog.get_geodataframe('basins_hru')

# each year is read as variable, stack them in time to form arrays
ds_land_stack = ds_land.to_stacked_array(new_dim='years',sample_dims=['x','y'])
# calculate mode across years axis
modestat = stats.mode(ds_land_stack,axis=2)[0].squeeze()
# create data array
ds_landclass_mode = xr.DataArray(modestat,{'y':ds_land.y,'x': ds_land.x})

def count_per_class(darr, gpd_shape,class_list,class_abbrev=''):
    for i in class_list:
        single_class = darr.where(darr==i)
        zstats = single_class.raster.zonal_stats(gpd_shape,'count')
        gpd_shape['{}{}'.format(class_abbrev,i)] = zstats[darr.name+'_count'].values
    gpd_shape = gpd_shape.loc[:, (gpd_shape != 0).any(axis=0)]
    return gpd_shape

class_list = np.unique(ds_landclass_mode)
gpd_hrus = count_per_class(ds_landclass_mode,gpd_hrus,class_list,'IGBP_')
gpd_basins = count_per_class(ds_landclass_mode,gpd_basins,class_list,'IGBP_')

# compare with reference
land_ref = gpd.read_file('/Users/ayx374/Documents/project/chwarm_test_results/domain_BowAtBanff/shapefiles/catchment_intersection/with_modis/catchment_with_modis.shp')

difference = gpd_hrus['IGBP_1'] - land_ref['IGBP_1']