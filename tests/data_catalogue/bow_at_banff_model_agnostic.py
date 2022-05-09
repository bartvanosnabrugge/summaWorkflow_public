import hydromt
import xarray as xr
from hydromt.log import setuplog
import numpy as np
import os
from scipy import stats

from cwarhm.model_agnostic_processing import HRU as hru
import cwarhm.util.util as utl

# additional functions (to be placed elsewhere)
#%% start example

# read control file
control_options = utl.read_summa_workflow_control_file('control_Bow_at_Banff_test.txt')
utl.build_folder_structure(control_options)

# set datacatalog
# the data catalog lists all available data that can be used in this workflow
# see https://deltares.github.io/hydromt/latest/user_guide/data.html
logger = setuplog('test_datacatalog',log_level=10)
data_catalog = hydromt.DataCatalog('datacatalog.yml', logger=logger)

#%% set some recurring variables
bbox = [float(i) for i in control_options['forcing_raw_space'].split('/')]
bbox_hydromt = [bbox[1],bbox[2],bbox[3],bbox[0]]

#%% open general datasets from datacatalogue
# open shapefiles
gpd_basins = data_catalog.get_geodataframe('river_basins')
gpd_hrus = data_catalog.get_geodataframe('basins_hru')

#%% remap era5 forcing data
# open datasets
ds_era5_preslev = data_catalog.get_rasterdataset('era5_pressure_level')
ds_era5_surf = data_catalog.get_rasterdataset('era5_surface_level')

# calculate directionless windspeed and drop directional variables
ds_era5_preslev['windspd'] = np.sqrt(np.square(ds_era5_preslev['wind-u'])+
                            np.square(ds_era5_preslev['wind-v']))
ds_era5_preslev = ds_era5_preslev.drop(['wind-u','wind-v'])

ds_era5 = xr.merge([ds_era5_surf,ds_era5_preslev])
forcing_merged_path = os.path.join(control_options['forcing_merged_path'],
                                'forcing_merged.nc')
ds_era5.to_netcdf(forcing_merged_path)
# exchange old object with reference to newly saved netcdf file
ds_era5 = xr.open_dataset(forcing_merged_path)

# alternative zonal stats
zstats_era5 = ds_era5.raster.zonal_stats(gpd_hrus,'mean',all_touched=True)
zstats_era5 = hru.add_basin_attributes_to_zonal_stats(zstats_era5,gpd_hrus)

forcing_basin_avg_path = os.path.join(control_options['forcing_basin_avg_path'],
                                'forcing_remapped.nc')
zstats_era5.to_netcdf(forcing_basin_avg_path)

#%% remap merit dem
# open merit dem
mdem = data_catalog.get_rasterdataset('merit_hydro_vrt',bbox=bbox_hydromt)

zstats = mdem.raster.zonal_stats(gpd_hrus,'mean')
gpd_hrus.insert(len(gpd_hrus.columns)-1,'elev_mean',zstats.elevtn_mean.values)
# save result
intersect_dem_path = os.path.join(control_options['intersect_dem_path'],
                                control_options['intersect_dem_name'])
gpd_hrus.to_file(intersect_dem_path)

#%% remap soil class
# open usda soilclass
ds_soil = data_catalog.get_rasterdataset('usda_soilclass',bbox=bbox_hydromt)

#gpd_basins_soilclass = count_per_class(ds_soil,gpd_basins,range(13),class_abbrev='USGS_')
gpd_hrus_soilclass = hru.count_per_class(ds_soil,gpd_hrus,range(13),class_abbrev='USGS_')
intersect_soil_path = os.path.join(control_options['intersect_soil_path'],
                                control_options['intersect_soil_name'])
gpd_hrus_soilclass.to_file(intersect_soil_path)

#%% remap land classes
#open dataset
ds_land = data_catalog.get_rasterdataset('modis_landclass_vrt4326',bbox=bbox_hydromt)
# each year is read as variable, stack them under dimension time
ds_land_stack = ds_land.to_stacked_array(new_dim='years',sample_dims=['x','y'])
# calculate mode across years dimension, stored in np.array
modestat = stats.mode(ds_land_stack,axis=2)[0].squeeze()
# create data array from np.array
ds_landclass_mode = xr.DataArray(modestat,{'y':ds_land.y,'x': ds_land.x})
ds_landclass_mode.name = 'landclass'
# generate class list from classes in array
class_list = np.unique(ds_landclass_mode)
gpd_hrus_landclassmode = hru.count_per_class(ds_landclass_mode,gpd_hrus,class_list,'IGBP_')
intersect_land_path = os.path.join(control_options['intersect_land_path'],
                                control_options['intersect_land_name'])
gpd_hrus_soilclass.to_file(intersect_land_path)

