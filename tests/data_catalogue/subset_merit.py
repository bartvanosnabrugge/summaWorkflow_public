import hydromt
import xarray as xr
from hydromt.log import setuplog
import numpy as np
import geopandas as gpd
import easymore as easymore

# set datacatalog
logger = setuplog('test_datacatalog',log_level=10)
data_catalog = hydromt.DataCatalog('datacatalog.yml', logger=logger)

# open merit dem
mdem = data_catalog.get_rasterdataset('merit_hydro_vrt',bbox=[-116.55,50.95,-115.52,51.74])

# open river basins file
# open hru basins file
gpd_basins = data_catalog.get_geodataframe('river_basins')
gpd_hrus = data_catalog.get_geodataframe('basins_hru')

# perform zonal stats
zstats = mdem.raster.zonal_stats(gpd_basins,'mean')
gpd_basins['mean_elevation'] = zstats.elevtn_mean.values

zstats = mdem.raster.zonal_stats(gpd_hrus,'mean')
gpd_hrus['mean_elevation'] = zstats.elevtn_mean.values

# compare with reference
dem_ref = gpd.read_file('/Users/ayx374/Documents/project/chwarm_test_results/domain_BowAtBanff/shapefiles/catchment_intersection/with_dem/catchment_with_merit_dem.shp')

gpd_hrus['elev_ref'] = dem_ref['elev_mean']