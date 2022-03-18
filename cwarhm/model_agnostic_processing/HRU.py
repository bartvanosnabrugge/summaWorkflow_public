'''Functions that relate to aggregating to HRUs:
Hydrological Response Units'''

import xarray as xr
import rasterio
import geopandas as gpd
import numpy as np
import pandas as pd
from rasterstats import zonal_stats
import datetime
from easymore.easymore import easymore

def hru_zonal_statistics(input_raster: str,input_shape: str,
    input_ddb: str,out_parameter: str):
    """WIP: from MESH workflow see
    https://wiki.usask.ca/display/MESH/MESH+vector-based+workflow+using+EASYMORE#MESHvectorbasedworkflowusingEASYMORE-2.3.Calculatelandcoverzonalhistogram

    :param input_raster: _description_
    :type input_raster: str
    :param input_shape: _description_
    :type input_shape: str
    :param input_ddb: _description_
    :type input_ddb: str
    :param out_parameter: _description_
    :type out_parameter: str
    """    

    #%% reading the inputs 
    gridded_class_data = rasterio.open(input_raster)
    gru_shapes = gpd.read_file(input_shape)
    drainage_db = xr.open_dataset(input_ddb)

    # %% extract indices of lc based on the drainage database
    n = len(drainage_db.hruId)
    ind = []
    hruid =  drainage_db.variables['hruId']

    for i in range(n):
        fid = np.where(np.int32(gru_shapes['COMID'].values) == hruid[i].values)[0]
        ind = np.append(ind, fid)

    ind = np.int32(ind)    

    #%% Read the raster values
    sand = gridded_class_data.read(1)

    # Get the affine
    affine = gridded_class_data.transform

    #%% calculate zonal status 
    zs = zonal_stats(gru_shapes, sand, affine=affine, stats='majority')
    zs  = pd.DataFrame(zs)

    # reorder the zonal stats from Rank1 to RankN
    zs_reorder = zs.values[ind] 

    # %% convert the distributed parameters as a dataset and save it as netcdf
    lon = drainage_db['lon'].values
    lat = drainage_db['lat'].values
    tt = drainage_db['time'].values

    dist_param =  xr.Dataset(
        {
            "GRU": (["subbasin", "gru"], zs_reorder),
        },
        coords={
            "lon": (["subbasin"], lon),
            "lat": (["subbasin"], lat),
        },
    )

    # meta data attributes 
    dist_param.attrs['Conventions'] = 'CF-1.6'
    dist_param.attrs['history']     = 'Created ' + datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    dist_param.attrs['featureType'] = 'point'          

    # editing lat attribute
    dist_param['lat'].attrs['standard_name'] = 'latitude'
    dist_param['lat'].attrs['units'] = 'degrees_north'
    dist_param['lat'].attrs['axis'] = 'Y'
    
    # editing lon attribute
    dist_param['lon'].attrs['standard_name'] = 'longitude'
    dist_param['lon'].attrs['units'] = 'degrees_east'
    dist_param['lon'].attrs['axis'] = 'X'

    # coordinate system
    dist_param['crs'] = drainage_db['crs'].copy()

    dist_param.to_netcdf(out_parameter)

def hru_fraction_from_counts(basin_class_counts: gpd.geodataframe.GeoDataFrame):
    """calculate fractions based on counts across classes in polygon

    Assumes the columns (names not important) [GRU_ID, HRU_ID, 
    center_lat, center_lon, HRU_area]. And then the columns that have 
    the count for each class, last column is the geometries.
    This is the shapefile as generated by 3_find_HRU_land_classes.py
    in cwarhm-summa.

    :param landclass_counts: geopandas dataframe with counts for each class (see long description)
    :type landclass_counts: geopandas.geodataframe.GeoDataFrame
    :return: geopandas dataframe with fractions for each class
    :rtype: geopandas.geodataframe.GeoDataFrame
    """    

    # this can be changed to select the columns based on an identifier
    count_columns = basin_class_counts.iloc[:,5:-1]
    # convert to array for calculation
    count_columns_array = count_columns.values
    # number of columns
    n = len(count_columns.columns)
    # number of total counts - in an 1D array
    total_counts_per_basin = count_columns.sum(axis=1).values
    # calculate fraction per basin of each landclass
    # the first transpose is to make numpy divide each element in a row with the sum
    # the second transpose is to fit again with the geopandas array
    fraction_per_basin = np.divide(count_columns_array.transpose(),total_counts_per_basin).transpose()
    # create new geopandas object with fractional values
    new_frac_headers = [c+'_frac' for c in count_columns.columns]
    new_headers = list(basin_class_counts.columns[0:5]) + list(new_frac_headers) + ['geometry']
    # make hard copy of old frame
    fraction_per_basin_gdf = basin_class_counts.copy()
    # replace headers
    fraction_per_basin_gdf.columns = new_headers
    # replace column values
    fraction_per_basin_gdf.iloc[:,5:-1]=fraction_per_basin

    return fraction_per_basin_gdf

def gru_fraction_from_hru_counts(basin_class_counts: gpd.geodataframe.GeoDataFrame):
    """calculate class fraction for each GRU

    Assumes the columns (names of GRU_ID should match) [GRU_ID, HRU_ID, 
    center_lat, center_lon, HRU_area]. And then the columns that have 
    the count for each class for each HRU, last column is the geometries.
    This is the shapefile as generated by 3_find_HRU_land_classes.py
    in cwarhm-summa.

    :param basin_class_counts: a geopandas dataframe with GRU_IDs, and counts per HRU_IDs (see long description)
    :type basin_class_counts: gpd.geodataframe.GeoDataFrame
    :return: data frame with fractions per class type as columns
    :rtype: pandas.core.frame.DataFrame
    """    
    #set index to GRU_ID and select count columns
    count_columns = basin_class_counts.iloc[:,5:-1]
    count_columns['GRU_ID'] = basin_class_counts['GRU_ID']
    # calculate number of classes
    n_classes = len(count_columns.columns)-1
    # group df by GRU_ID
    gru_groups = count_columns.groupby('GRU_ID')
    # set up np.array for results
    frac_array = np.empty((len(gru_groups),n_classes))
    # calculate fraction for each GRU in total
    for i, (gru_id, counts) in enumerate(gru_groups):
        #print(counts.head())
        counts_id = counts.set_index('GRU_ID')
        counts_per_class = counts_id.sum(axis=0)
        total_counts = counts_per_class.sum()
        fraction_per_class = counts_per_class/total_counts
        # fill array
        frac_array[i,:]=fraction_per_class

    # create dataframe
    df = pd.DataFrame(frac_array)
    df['GRU_ID'] = gru_groups.groups.keys()
    df.columns = count_columns.columns
    df =df.set_index('GRU_ID')

    return df

def map_forcing_data(basin,forcing_data, output_dir,
                    var_names:list,  var_lon='lon', var_lat='lat', var_time='time',
                    case_name='workflow',temp_dir='./esmr_temp/', format_list=['f4'],
                    fill_value_list = ['-999'], save_csv = False,
                    **esmr_kwargs
                    ):
    print(esmr_kwargs)
    # %% initializing EASYMORE object
    esmr = easymore()
    
    # specifying EASYMORE objects
    # name of the case; the temporary, remapping and remapped file names include case name            
    esmr.case_name                 = case_name             
    # temporary path that the EASYMORE generated GIS files and remapped file will be saved
    esmr.temp_dir                 = temp_dir
    # name of target shapefile that the source netcdf files should be remapped to
    esmr.target_shp               = basin
    
    # name of netCDF file(s); multiple files can be specified with *
    esmr.source_nc                 =  forcing_data

    esmr.var_names                 = var_names
    # rename the variables from source netCDF file(s) in the remapped files;
    # it will be the same as source if not provided
    # esmr.var_names_remapped      = ['PR','RDRS_v2_P_FI_SFC','FB','RDRS_v2_P_TT_09944','UV','RDRS_v2_P_P0_SFC','HU']
    if 'var_names_remapped' in esmr_kwargs:
        print('renaming variables')
        esmr.var_names_remapped   = esmr_kwargs['var_names_remapped']
    
    # name of variable longitude in source netCDF files
    esmr.var_lon                  = var_lon
    # name of variable latitude in source netCDF files
    esmr.var_lat                  = var_lat
    # name of variable time in source netCDF file; should be always time
    esmr.var_time                 = var_time
    # location where the remapped netCDF file will be saved
    esmr.output_dir               = output_dir
    # format of the variables to be saved in remapped files,
    # if one format provided it will be expanded to other variables
    esmr.format_list              = format_list
    # fill values of the variables to be saved in remapped files,
    # if one value provided it will be expanded to other variables
    esmr.fill_value_list          = fill_value_list
    # if required that the remapped values to be saved as csv as well
    esmr.save_csv                 = save_csv

    #execute EASYMORE
    # Note:  remapped forcing has the precision of float32
    esmr.nc_remapper()