import os
import shutil
import sys



#%%
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from pathlib import Path
import xarray as xr
import geopandas as gpd
import zipfile
import pandas as pd

from cwarhm.model_specific_processing import mesh as mesh
from cwarhm.model_agnostic_processing import HRU as HRU
import cwarhm.util.util as utl

# set paths
# results_folder_path: path to save the results (and to extract the test data to)
# NOTE: results_folder_path needs to be set here AND in control_Bow_at_Banff_test.txt
# as root_folder
os.chdir(os.path.dirname(os.path.realpath(__file__)))
results_folder_path = Path("/Users/ayx374/Documents/project/chwarm_test_results")

# extract test data to test path
with zipfile.ZipFile('domain_BowAtBanff_mesh.zip') as zip_ref:
    zip_ref.extractall(results_folder_path)
# read control file
control_options = utl.read_summa_workflow_control_file('control_Bow_at_Banff_test.txt')


#%%
# create mesh topology
drain_db_path = os.path.join(control_options['settings_mesh_path'],control_options['settings_mesh_topology'])

mesh.generate_mesh_topology(control_options['river_network_shp_path'], 
    control_options['river_basin_shp_path'],
    drain_db_path,
    control_options['settings_make_outlet'])
ranks, drain_db = mesh.reindex_topology_file(drain_db_path)
# save file
drain_db.to_netcdf(drain_db_path)

# calculate land use fractions for MESH GRUS from CWARHM-SUMMA GRU/HRU land use counts
gdf_land_use_counts = gpd.read_file(os.path.join(
                        control_options['intersect_land_path'],control_options['intersect_land_name']))
df_gru_land_use_fractions = HRU.gru_fraction_from_hru_counts(gdf_land_use_counts)

# set names for discretization
fraction_type = ['Evergreen Needleleaf Forests','Woody Savannas','Savannas',
'Grasslands', 'Permanent Wetlands', 'Urban and Built-up Lands', 'Permanent Snow and Ice',
'Barren','Water Bodies']
# and add fractions and Grouped Response Unit info to the drainage_db
drain_db = mesh.add_gru_fractions_to_drainage_db(drain_db, df_gru_land_use_fractions, fraction_type)
# save file
drain_db.to_netcdf(drain_db_path)

# remap forcing data from grids, to MESH GRUs (CWARHM-SUMMA maps to SUMMA HRUs)
HRU.map_forcing_data(control_options['river_basin_shp_path'],
                    control_options['forcing_merged_path']+'/*200803.nc',
                    control_options['forcing_basin_avg_path']+'/',
                    var_names = ['LWRadAtm', 'SWRadAtm', 'pptrate', 'airpres', 'airtemp', 'spechum', 'windspd'],
                    var_lon='longitude', var_lat='latitude',
                    case_name = control_options['domain_name'] , 
                    temp_dir=control_options['intersect_forcing_path']+'/' ,
                    var_names_remapped=['FI', 'FB', 'PR', 'P0', 'TT', 'HU', 'UV']
                    )
# reindex forcing file generated by EASYMORE to match mesh drainage dbb
input_forcing = xr.open_mfdataset(control_options['forcing_basin_avg_path']+'/*.nc')
input_basin = gpd.read_file(control_options['river_basin_shp_path'])
mesh_forcing = mesh.reindex_forcing_file(input_forcing, drain_db, input_basin)
# save file
mesh_forcing.to_netcdf(os.path.join(control_options['settings_mesh_path'],'MESH_input_era5.nc'))

## mesh CLASS.ini file
deglat = "{:.2f}".format(drain_db.lat.mean().values)
deglon = "{:.2f}".format(drain_db.lon.mean().values)
windspeed_ref_height = '40.00'
temp_humid_ref_height = '40.00'
surface_roughness_height = '50.00'
ground_cover_flag = '-1.0'
ILW = '1'
n_grid = '51'
n_GRU = len(drain_db.gru)
datetime_start = pd.to_datetime(mesh_forcing.time[0].values)

inif = mesh.MeshClassIniFile(os.path.join(control_options['settings_mesh_path'],'MESH_parameters_CLASS.ini'),
                            n_GRU,datetime_start)
inif.set_header("test_bow_blah","bartus","Canmore")
inif.set_area_info(deglat,deglon,windspeed_ref_height=40.00,
                        temp_humid_ref_height=40.00, surface_roughness_height=50.00,
                        ground_cover_flag=-1, ILW=1, n_grid=0)
inif.set_start_end_times(datetime_start)
inif.write_ini_file()

## Run options
optf = mesh.MeshRunOptionsIniFile(os.path.join(control_options['settings_mesh_path'],'MESH_input_run_options.ini'),
                                    drain_db_path)

# hydrological parameters ini file
mhi = mesh.MeshHydrologyIniFile(os.path.join(control_options['settings_mesh_path'],'MESH_parameters_hydrology.ini'),
                                n_gru=11)

# reservoir file (txt dummy version)
resi = mesh.MeshReservoirTxtFile(os.path.join(control_options['settings_mesh_path'],'MESH_parameters_hydrology.ini'))

# soil layers file (default version)
sli = mesh.MeshSoilLevelTxtFile(os.path.join(control_options['settings_mesh_path'],'MESH_parameters_hydrology.ini'))

