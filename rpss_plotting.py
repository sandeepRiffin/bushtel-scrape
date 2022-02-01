# %%
from urllib import request
import winsound

import random
from numpy.lib.arraysetops import setdiff1d
import pandas as pd
import numpy as np

import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point, MultiPoint
from plotly import subplots
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import itertools
import json
import colorsys

import plotly.io as pio
pio.renderers.default = "notebook"
builtin_colorscales_list = px.colors.named_colorscales()

def beeper():
    freq=100
    dur=1000
    for i in range(0,10):
        winsound.Beep(freq,dur)
        freq+=50

token = 'pk.eyJ1Ijoic2FuZGVlcG5la2lzdGljYSIsImEiOiJja3d2cTRleXYyMG94Mm9wNGcyN21kNHJ1In0.f9JeFY4MKIFP-tmhiXLt5Q'

# plotting zoom level and centre coords function for plotly mapbox obtained here:
# https://community.plotly.com/t/dynamic-zoom-for-mapbox/32658/12
def get_plotting_zoom_level_and_center_coordinates_from_lonlat_tuples(longitudes=None, latitudes=None):
    """Function documentation:\n
    Basic framework adopted from Krichardson under the following thread:
    https://community.plotly.com/t/dynamic-zoom-for-mapbox/32658/7

    # NOTE:
    # THIS IS A TEMPORARY SOLUTION UNTIL THE DASH TEAM IMPLEMENTS DYNAMIC ZOOM
    # in their plotly-functions associated with mapbox, such as go.Densitymapbox() etc.

    Returns the appropriate zoom-level for these plotly-mapbox-graphics along with
    the center coordinate tuple of all provided coordinate tuples.
    """

    # Check whether both latitudes and longitudes have been passed,
    # or if the list lenghts don't match
    if ((latitudes is None or longitudes is None)
            or (len(latitudes) != len(longitudes))):
        # Otherwise, return the default values of 0 zoom and the coordinate origin as center point
        return 0, (0, 0)

    # Get the boundary-box 
    b_box = {} 
    b_box['height'] = latitudes.max()-latitudes.min()
    b_box['width'] = longitudes.max()-longitudes.min()
    b_box['center']= (np.mean(longitudes), np.mean(latitudes))

    # get the area of the bounding box in order to calculate a zoom-level
    area = b_box['height'] * b_box['width']

    # * 1D-linear interpolation with numpy:
    # - Pass the area as the only x-value and not as a list, in order to return a scalar as well
    # - The x-points "xp" should be in parts in comparable order of magnitude of the given area
    # - The zpom-levels are adapted to the areas, i.e. start with the smallest area possible of 0
    # which leads to the highest possible zoom value 20, and so forth decreasing with increasing areas
    # as these variables are antiproportional
    zoom = np.interp(x=area,
                     xp=[0, 5**-10, 4**-10, 3**-10, 2**-10, 1**-10, 1**-5],
                     fp=[20, 15,    14,     13,     12,     7,      5])

    # Finally, return the zoom level and the associated boundary-box center coordinates
    return zoom, b_box['center']
#%%
# Reading in projects and profiles information
#community_projects_df = pd.read_csv('community_projects_list.csv', index_col=None, usecols=[1,2,3,4,5,6,7]).drop_duplicates()
#community_projects_df.Value = community_projects_df.Value.str.replace(',','').astype('float')
#community_profiles_df = pd.read_csv('all_communities_profile_data.csv', index_col=None, usecols=[1,2,3,4,5,6,7,8,9,10,11])

ranger_groups = pd.read_csv('indigenous_ranger_groups_coordinates.csv', header=0, index_col=0)
ies_comm_dir_complete = pd.read_csv('community_profiles_businesses_locations.csv', header=0, index_col=0)

lga_shapes = gpd.read_file(r'LGA_2021_AUST_GDA94_SHP\LGA_2021_AUST_GDA94.shp')
lga_shapes_NT = lga_shapes.loc[lga_shapes.STE_NAME21 == 'Northern Territory']
lga_shapes_NT.rename(columns={'LGA_NAME21':'Local Government'}, inplace=True)

# Making sure the LGA names in the projects list are the same as those in the LGA shapefile
lga_names_dict = dict(
    zip(
        ['Alice Springs', 'Barkly', 'Belyuen', 'Central Desert', 'Coomalie',
       'East Arnhem', 'Katherine', 'Litchfield', 'Macdonnell',
       'Palmerston', 'Roper Gulf', 'Tiwi Islands',
       'Un-Incorporated (alyangula)', 'Un-Incorporated (cox-Daly)',
       'Un-Incorporated (nhulunbuy)', 'Un-Incorporated (yulara)',
       'Victoria Daly','West Arnhem', 'West Daly'],
        ['Alice Springs', 'Barkly', 'Belyuen', 'Central Desert', 'Coomalie',
       'East Arnhem', 'Katherine', 'Litchfield', 'MacDonnell',
       'Palmerston', 'Roper Gulf', 'Tiwi Islands', 'Unincorporated NT',
       'Unincorporated NT','Unincorporated NT','Unincorporated NT',
       'Victoria Daly','West Arnhem', 'West Daly'],
    )
)

id_lga_dict = dict(zip(list(ies_comm_dir_complete['COMMUNITY_ID']) ,list(ies_comm_dir_complete['LOCAL_GOVT COUNCIL'])))
id_landcouncil_dict = dict(zip(list(ies_comm_dir_complete['COMMUNITY_ID']) ,list(ies_comm_dir_complete['LAND_COUNCIL'])))
id_lat_dict = dict(zip(list(ies_comm_dir_complete['COMMUNITY_ID']) ,list(ies_comm_dir_complete['Latitude'])))
id_lon_dict = dict(zip(list(ies_comm_dir_complete['COMMUNITY_ID']) ,list(ies_comm_dir_complete['Longitude'])))
id_name_dict = dict(zip(list(ies_comm_dir_complete['COMMUNITY_ID']) ,list(ies_comm_dir_complete['COMMUNITY_NAME'])))
id_pop_dict = dict(zip(list(ies_comm_dir_complete['COMMUNITY_ID']) ,list(ies_comm_dir_complete['POPULATION_COUNT'])))
id_lang_dict = dict(zip(list(ies_comm_dir_complete['COMMUNITY_ID']) ,list(ies_comm_dir_complete['MAIN_LANGUAGE'])))
#%% Communities and Ranger Stations clustered by LGAs
fig = go.Figure()

status_symbol_dict={'Y':'star','N':'circle'}

for setup_community_status in ['Y','N']:
    df_setup = ies_comm_dir_complete.loc[ies_comm_dir_complete['Previous SETuP Community']==setup_community_status].drop_duplicates(subset=['COMMUNITY_ID'])
    lats = df_setup['COMMUNITY_ID'].apply(lambda x: id_lat_dict[x])
    lons = df_setup['COMMUNITY_ID'].apply(lambda x: id_lon_dict[x])
    comm_names = df_setup['COMMUNITY_ID'].apply(lambda x: id_name_dict[x])
    comm_pops = df_setup['COMMUNITY_ID'].apply(lambda x: id_pop_dict[x])
    comm_langs = df_setup['COMMUNITY_ID'].apply(lambda x: id_lang_dict[x])
    comm_lgas = df_setup['COMMUNITY_ID'].apply(lambda x: id_lga_dict[x])
    comm_landcouncils = df_setup['COMMUNITY_ID'].apply(lambda x: id_landcouncil_dict[x])
    fig.add_trace(
        go.Scattermapbox(
            mode='markers+text', textposition='top right',
            lat=lats,
            lon=lons,
            text=comm_names,
            marker={
                # scaling the populations: https://stackoverflow.com/a/5295202
                'size': df_setup['POPULATION_COUNT'].apply(lambda x: ((x-df_setup['POPULATION_COUNT'].min())/(df_setup['POPULATION_COUNT'].max()-df_setup['POPULATION_COUNT'].min()))*50),
                'symbol':status_symbol_dict[setup_community_status],
                'color':'red',
                #opacity=,
            },
            #hovertemplate = "<b>%{text}</b><br><extra></extra>", 
            #                "Population: %{comm_pops}<br>" + 
            #                "Main Language: %{comm_langs}<br>" + 
            #                "Local Govt.: %{comm_lgas}<br>" + 
            #                "Land Council: %{comm_landcouncils}<extra></extra>",
            name=f'Previous SETuP Community:{setup_community_status}'
        )
    )

lgas_list = list(np.unique(ies_comm_dir_complete['LOCAL_GOVT COUNCIL']))
multipoint_list = []
number_of_points = []
for lga in lgas_list:
    df_lga = ies_comm_dir_complete.loc[ies_comm_dir_complete['LOCAL_GOVT COUNCIL']==lga].drop_duplicates(subset=['COMMUNITY_ID'])
    number_of_points.append(len(df_lga))
    coordinates_set = list(zip(list(df_lga.Latitude),list(df_lga.Longitude)))
    multipoint_list.append(MultiPoint(coordinates_set))
    
s = gpd.GeoSeries(multipoint_list)
s_convex_hull = s.convex_hull
boundaries = s_convex_hull.boundary

for i in [0,2,3,6,7,8,9,10,11]:
    x,y = boundaries[i].coords.xy
    lats = list(x)
    lons = list(y)
    fig.add_trace(
        go.Scattermapbox(
            lat=lats,
            lon=lons,
            mode='lines+text',
            fill='toself',
            #text=lga,
            #textposition='middle center',
            marker={
                'size':6,
                'symbol':status_symbol_dict[setup_community_status],
                #'color':'red',
                #opacity=,
            },
        name=lgas_list[i]
        )
    )    

fig.add_trace(
    go.Scattermapbox(
        lat=ranger_groups.Latitude_DD,
        lon=ranger_groups.Longitude_DD,
        mode='markers+text',
        text=ranger_groups.Project,
        textposition='top right',
        marker={
            'size':10,
            'symbol':'campsite'
            #color=,
            #opacity=,
        },
        name='Ranger Stations'
    )
)


fig.update_layout(
                #showlegend=False,
                legend=dict(orientation='h'),
                autosize=False, width=1200, height=1200,
                mapbox_style='outdoors',
                mapbox_accesstoken=token,
                mapbox_center={'lat': -18.75, 'lon': 133.3578},
                mapbox_zoom=5, #zoom,
                title = '<b>IES Communities and Ranger Stations - Clustered by Local Government Council Areas</b>',
                title_x=0.5
)

fig.update_geos(fitbounds='locations', visible=False)
#fig.update_layout(margin={"r":30,"t":30,"l":30,"b":30})
fig.show()

fig.write_html("rpss_viz_lgas.html")
#%% Communities and Ranger Stations clustered by Land Councils
fig = go.Figure()

status_symbol_dict={'Y':'star','N':'circle'}

for setup_community_status in ['Y','N']:
    df_setup = ies_comm_dir_complete.loc[ies_comm_dir_complete['Previous SETuP Community']==setup_community_status].drop_duplicates(subset=['COMMUNITY_ID'])
    lats = df_setup['COMMUNITY_ID'].apply(lambda x: id_lat_dict[x])
    lons = df_setup['COMMUNITY_ID'].apply(lambda x: id_lon_dict[x])
    comm_names = df_setup['COMMUNITY_ID'].apply(lambda x: id_name_dict[x])
    comm_pops = df_setup['COMMUNITY_ID'].apply(lambda x: id_pop_dict[x])
    comm_langs = df_setup['COMMUNITY_ID'].apply(lambda x: id_lang_dict[x])
    comm_lgas = df_setup['COMMUNITY_ID'].apply(lambda x: id_lga_dict[x])
    comm_landcouncils = df_setup['COMMUNITY_ID'].apply(lambda x: id_landcouncil_dict[x])
    fig.add_trace(
        go.Scattermapbox(
            mode='markers+text', textposition='top right',
            lat=lats,
            lon=lons,
            text=comm_names,
            marker={
                'size': df_setup['POPULATION_COUNT'].apply(lambda x: ((x-df_setup['POPULATION_COUNT'].min())/(df_setup['POPULATION_COUNT'].max()-df_setup['POPULATION_COUNT'].min()))*100),
                'symbol':status_symbol_dict[setup_community_status],
                'color':'red',
                #opacity=,
            },
            #hovertemplate = "<b>%{text}</b><br><extra></extra>", 
            #                "Population: %{comm_pops}<br>" + 
            #                "Main Language: %{comm_langs}<br>" + 
            #                "Local Govt.: %{comm_lgas}<br>" + 
            #                "Land Council: %{comm_landcouncils}<extra></extra>",
            name=f'Previous SETuP Community:{setup_community_status}'
        )
    )

landcouncils_list = list(np.unique(ies_comm_dir_complete['LAND_COUNCIL']))
multipoint_list = []
number_of_points = []
for lc in landcouncils_list:
    df_lc = ies_comm_dir_complete.loc[ies_comm_dir_complete['LAND_COUNCIL']==lc].drop_duplicates(subset=['COMMUNITY_ID'])
    number_of_points.append(len(df_lc))
    coordinates_set = list(zip(list(df_lc.Latitude),list(df_lc.Longitude)))
    multipoint_list.append(MultiPoint(coordinates_set))
    
s = gpd.GeoSeries(multipoint_list)
s_convex_hull = s.convex_hull
boundaries = s_convex_hull.boundary

for i in [0,1,2,3]:
    x,y = boundaries[i].coords.xy
    lats = list(x)
    lons = list(y)
    fig.add_trace(
        go.Scattermapbox(
            lat=lats,
            lon=lons,
            mode='lines+text',
            fill='toself',
            #text=lga,
            #textposition='middle center',
            marker={
                'size':6,
                'symbol':status_symbol_dict[setup_community_status],
                #'color':'red',
                #opacity=,
            },
        name=landcouncils_list[i]
        )
    )    

fig.add_trace(
    go.Scattermapbox(
        lat=ranger_groups.Latitude_DD,
        lon=ranger_groups.Longitude_DD,
        mode='markers+text',
        text=ranger_groups.Project,
        textposition='top right',
        marker={
            'size':10,
            'symbol':'campsite'
            #color=,
            #opacity=,
        },
        name='Ranger Stations'
    )
)

fig.update_layout(
                #showlegend=False,
                legend=dict(orientation='h'),
                autosize=False, width=1200, height=1200,
                mapbox_style='outdoors',
                mapbox_accesstoken=token,
                mapbox_center={'lat': -18.75, 'lon': 133.3578},
                mapbox_zoom=5, #zoom,
                title = '<b>IES Communities and Ranger Stations - Clustered by Land Councils</b>',
                title_x=0.5
)

fig.update_geos(fitbounds='locations', visible=False)
#fig.update_layout(margin={"r":30,"t":30,"l":30,"b":30})
fig.show()

fig.write_html("rpss_viz_landcouncils.html")
# %%
"""
BARKLY 7
BELYUEN 1
CENTRAL DESERT 11
EAST ARNHEM 9
KATHERINE 1
LITCHFIELD 1
MACDONNELL 13
ROPER GULF 11
TIWI ISLANDS 3
VICTORIA DALY 8
WEST ARNHEM 4
WEST DALY 3
"""
multipoint_list = []
number_of_points = []
for lga in lgas_list:
    df_lga = ies_comm_dir_complete.loc[ies_comm_dir_complete['LOCAL_GOVT COUNCIL']==lga].drop_duplicates(subset=['COMMUNITY_ID'])
    number_of_points.append(len(df_lga))
    coordinates_set = list(zip(list(df_lga.Latitude),list(df_lga.Longitude)))
    multipoint_list.append(MultiPoint(coordinates_set))
    
s = gpd.GeoSeries(multipoint_list)
s_convex_hull = s.convex_hull
d = pd.DataFrame({'LOCAL_GOVT COUNCIL':lgas_list,'NUMBER_OF_COMMUNITIES':number_of_points},
                index=list(np.arange(len(lgas_list))))
#d = d.set_index('LOCAL_GOVT COUNCIL')
d['GEOMETRY_COMMUNITIES'] = s
d['GEOMETRY_CONVEX_HULL'] = s_convex_hull

boundary = s_convex_hull.boundary
x,y = boundary[0].coords.xy
not_geo_df = pd.DataFrame({'LAT':x,'LON':y})
#%%
geo_df = gpd.GeoDataFrame({'lga':lgas_list, 'comms_count':number_of_points, 'geometry':s}).set_index('lga') #gpd.GeoDataFrame.from_features(s_convex_hull)

fig = go.Figure(
    go.Choroplethmapbox(
    geojson=json.loads(geo_df.geometry.to_json()),
    locations=geo_df.index,
    z=geo_df.comms_count, 
    #colorscale='oranges',
    )
)
fig.update_layout(
    mapbox_accesstoken=token,
    mapbox_center={'lat': -18.75, 'lon': 133.3578},
    mapbox_style="outdoors",
    mapbox_zoom=5.5,
)
fig.show()
# %%
df = px.data.election()
geojson = px.data.election_geojson()

fig = px.choropleth_mapbox(df, geojson=geojson, color="Bergeron",
                           locations="district", featureidkey="properties.district",
                           center={"lat": 45.5517, "lon": -73.7073},
                           mapbox_style="carto-positron", zoom=9)
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
fig.show()
# %%

# %%
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from project_paths import CHROMEDRIVER_PATH

def chromedriver_initialise():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    driver = webdriver.Chrome(
        executable_path=CHROMEDRIVER_PATH / 'chromedriver', options=chrome_options
        )
    return driver
#%%
driver = chromedriver_initialise()
url = 'https://labs.mapbox.com/maki-icons/'
driver.get(url)
time.sleep(3)
source = driver.page_source
soup = BeautifulSoup(source, 'lxml')
# %%
symbols = [div.text for div in soup.find_all('div',class_='inline pad1')]
starting_lat = -18.75
starting_lon = 133.3578
lats = [starting_lat]
lons = [starting_lon]
for i in range(1,18):
    lats.append(starting_lat + i*0.5)
for j in range(1,13):
    lons.append(starting_lon + j*0.5)
#%%
#[tuple(lats[i],lons[j]) for i in range(1,18) and j in range(1,13)]
latlontuples=[]
for i in range(0,17):
    for j in range(0,12):
        latlontuples.append((lats[i], lons[j]))
symbol_coords_dict={}
for i in range(204):
    symbol_coords_dict.update({symbols[i]:latlontuples[i]})
# %%
fig = go.Figure()

for symbol in symbols:
    fig.add_trace(
        go.Scattermapbox(
            lat=[symbol_coords_dict[symbol][0]],
            lon=[symbol_coords_dict[symbol][1]],
            mode='markers+text',
            text=symbol[:-4],
            textposition='top right',
            marker={
                'size':8,
                'symbol':symbol[:-4]
                #color=,
                #opacity=,
            },
            name=symbol
        )
    )

fig.update_layout(
                showlegend=False,
                legend=dict(orientation='h'),
                autosize=False, width=1200, height=1200,
                mapbox_style='outdoors',
                mapbox_accesstoken=token,
                mapbox_center={'lat': -18.75, 'lon': 133.3578},
                mapbox_zoom=5, #zoom,
                title = '<b>IES Communities and Ranger Stations - Clustered by Land Councils</b>',
                title_x=0.5
)
fig.show()
# %%
