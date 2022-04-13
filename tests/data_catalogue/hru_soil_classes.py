import hydromt
import xarray as xr
from hydromt.log import setuplog
import numpy as np
import geopandas as gpd
import easymore as easymore

# set datacatalog
logger = setuplog('test_datacatalog',log_level=10)
data_catalog = hydromt.DataCatalog('datacatalog.yml', logger=logger)

# open usda soilclass
ds_soil = data_catalog.get_rasterdataset('usda_soilclass',bbox=[-116.55,50.95,-115.52,51.74])

# open river basins file
# open hru basins file
gpd_basins = data_catalog.get_geodataframe('river_basins')
gpd_hrus = data_catalog.get_geodataframe('basins_hru')

def count_per_class(darr, gpd_shape,class_list,class_abbrev=''):
    for i in class_list:
        single_class = darr.where(darr==i)
        zstats = single_class.raster.zonal_stats(gpd_shape,'count')
        gpd_shape['{}{}'.format(class_abbrev,i)] = zstats[darr.name+'_count'].values
    gpd_shape = gpd_shape.loc[:, (gpd_shape != 0).any(axis=0)]
    return gpd_shape

gpd_basins = count_per_class(ds_soil,gpd_basins,range(13),class_abbrev='USGS_')
gpd_hrus = count_per_class(ds_soil,gpd_hrus,range(13),class_abbrev='USGS_')

# compare with reference
soil_ref = gpd.read_file('/Users/ayx374/Documents/project/chwarm_test_results/domain_BowAtBanff/shapefiles/catchment_intersection/with_soilgrids/catchment_with_soilgrids.shp')

difference = gpd_hrus['USGS_3'] - soil_ref['USGS_3']