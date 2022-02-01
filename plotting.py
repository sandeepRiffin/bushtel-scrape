# %%
import winsound

import random
from numpy.lib.arraysetops import setdiff1d
import pandas as pd
import numpy as np

import geopandas as gpd
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

#spec_sublist = list(itertools.repeat({'type':'choroplethmapbox'}, 5))
#spec_list = list(itertools.repeat(spec_sublist, 19))

#N = len(unique_projects)
#HSV_tuples = [(x*1.0/N, 0.5, 0.5) for x in range(N)]
#RGB_tuples = list(map(lambda x: colorsys.hsv_to_rgb(*x), HSV_tuples))

def beeper():
    freq=100
    dur=1000
    for i in range(0,10):
        winsound.Beep(freq,dur)
        freq+=50

token = 'pk.eyJ1Ijoic2FuZGVlcG5la2lzdGljYSIsImEiOiJja3d2cTRleXYyMG94Mm9wNGcyN21kNHJ1In0.f9JeFY4MKIFP-tmhiXLt5Q'

df1 = pd.read_csv('community_projects_list.csv', header=0, usecols=[6,7,8,9])
df2 = pd.read_csv('all_communities_profile_data.csv', header=0, usecols=[1,2,10,11])
df3 = pd.read_csv('grants_and_variations_merged.csv')

df1['GA ID'] = df1['Project ID'].apply(lambda x: x[:-3] if '-V' in x else x)

merge1_df = pd.merge(df1, df3, on='GA ID')
merge2_df = pd.merge(df2, merge1_df, on='Community ID')

merge2_df['Value (AUD)'] = merge2_df['Value (AUD)'].apply(lambda x: float(x.replace(',','')))
#merge2_df.to_csv('communities_and_projects_details_v2.csv')

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

# Reading in projects and profiles information
community_projects_df = pd.read_csv('community_projects_list.csv', index_col=None, usecols=[1,2,3,4,5,6,7]).drop_duplicates()
community_projects_df.Value = community_projects_df.Value.str.replace(',','').astype('float')

community_profiles_df = pd.read_csv('all_communities_profile_data.csv', index_col=None, usecols=[1,2,3,4,5,6,7,8,9,10,11])

id_lga_dict = dict(zip(list(community_profiles_df['Community ID']) ,list(community_profiles_df['Local Government'])))
id_landcouncil_dict = dict(zip(list(community_profiles_df['Community ID']) ,list(community_profiles_df['Land Council'])))
id_lat_dict = dict(zip(list(community_profiles_df['Community ID']) ,list(community_profiles_df['Latitude'])))
id_lon_dict = dict(zip(list(community_profiles_df['Community ID']) ,list(community_profiles_df['Longitude'])))
id_name_dict = dict(zip(list(community_profiles_df['Community ID']) ,list(community_profiles_df['Community Name'])))
id_pop_dict = dict(zip(list(community_profiles_df['Community ID']) ,list(community_profiles_df['Population'])))

community_projects_df['Local Government'] = community_projects_df['Community ID'].apply(lambda x: id_lga_dict[x])
community_projects_df['Land Council'] = community_projects_df['Community ID'].apply(lambda x: id_landcouncil_dict[x])
#%%
# looking at projects and seeing which communities benefited from it
unique_projects = np.unique(community_projects_df['Project ID'])

df = pd.DataFrame()
while len(df) < 4:
    project_id = random.choice(unique_projects)
    df = community_projects_df.loc[community_projects_df['Project ID'] == project_id]
lats = df['Community ID'].apply(lambda x: id_lat_dict[x])
lons = df['Community ID'].apply(lambda x: id_lon_dict[x])
comm_names = df['Community ID'].apply(lambda x: id_name_dict[x])
populations = df['Community ID'].apply(lambda x: id_pop_dict[x])

# option for zoom on communities vs zoom on region vs zoom on state
zoom, center = get_plotting_zoom_level_and_center_coordinates_from_lonlat_tuples(lons, lats)

fig = go.Figure()

fig.add_trace(
    go.Scattermapbox(
        lat=lats,
        lon=lons,
        mode='markers+text',
        text=comm_names,
        textposition='top right',
        marker=go.scattermapbox.Marker(
            size=8,
            #color=,
            #opacity=,
        )
    )
)

first_project_name = df['Project Name'].iloc[0]
project_value = int(np.round(df['Value'].iloc[0], decimals=0))
project_hyperlink = 'https://www.grants.gov.au/Search/KeywordSearch?keyword=' + project_id

fig.update_layout(
mapbox_style='open-street-map',
mapbox_accesstoken=token,
mapbox_center={'lat': center[1], 'lon': center[0]},
mapbox_zoom=zoom,
title = f'{first_project_name} <br>Grant Sum Awarded : ${project_value} <br>More information: <a href={project_hyperlink}>{project_id}</a>'
)

fig.update_geos(fitbounds='locations', visible=False)
#fig.update_layout(margin={"r":30,"t":30,"l":30,"b":30})
fig.show()

# %% communities for each grant (all project variations)
unique_projects = np.unique(merge2_df['GA ID'])
df = pd.DataFrame()
while len(df) < 4:
    ga_id = random.choice(unique_projects)
    df = merge2_df.loc[merge2_df['GA ID'] == ga_id].dropna(axis='columns')

lons = df['Longitude']
lats = df['Latitude']
comm_names = df['Community Name']

# option for zoom on communities vs zoom on region vs zoom on state
zoom, center = get_plotting_zoom_level_and_center_coordinates_from_lonlat_tuples(lons, lats)
# sometimes this function produces too high a zoom value, in which case we'll revert to a zoom of 5
if zoom > 11:
    zoom = 7.75

fig = go.Figure()

fig.add_trace(
    go.Scattermapbox(
        mode='markers+text',
        lat=list(lats),
        lon=list(lons),
        text=list(comm_names),
        textposition='top right',
        marker={'size':8},
        textfont={"color":"black","size":10, "family":"Courier New"},
        showlegend=False
    )
)

project_name = df['Project Title'].iloc[0]
grant_name = df['Grant Program'].iloc[0]
project_value = int(np.round(df['Value (AUD)'].iloc[0], decimals=0))
project_hyperlink = 'https://www.grants.gov.au/Search/KeywordSearch?keyword=' + ga_id

fig.update_traces(
    textposition = 'top right'
)

fig.update_layout(
mapbox_style='outdoors',
mapbox_accesstoken=token,
mapbox_center={'lat': center[1], 'lon': center[0]},
mapbox_zoom=zoom,
title = f'<b>{project_name}</b> <br><span style="font-size: 12px;">Grant Award (Present Value): ${project_value}, under Program: {grant_name}</span><br><span style="font-size: 12px;"><i>More information: <a href={project_hyperlink}>{ga_id}</a></i></span>'
)

fig.update_geos(fitbounds='locations', visible=False)
fig.update_layout(margin={"r":25,"t":100,"l":25,"b":25})
fig.show()
print(zoom)

# %% communities awarded under each category
unique_categories = np.unique(merge2_df['Category'])
#category = random.choice(unique_categories)
for category in unique_categories:
    df = merge2_df.loc[merge2_df['Category'] == category].dropna(axis='columns')

    fig = go.Figure()

    for ga_id in np.unique(df['GA ID']):
        df_redux = df[df['GA ID'] == ga_id]
        project_id = df_redux['Project ID'].iloc[0]

        fig.add_trace(
        go.Scattermapbox(
            mode='markers+text',
            lat=list(df_redux['Latitude']),
            lon=list(df_redux['Longitude']),
            text=list(df_redux['Community Name']),
            textposition='top right',
            marker={'size':8},
            textfont={"color":"black","size":10, "family":"Courier New"},
            name=project_id
        )
    )

    lons = df['Longitude']
    lats = df['Latitude']
    comm_names = df['Community Name']

    # option for zoom on communities vs zoom on region vs zoom on state
    zoom, center = get_plotting_zoom_level_and_center_coordinates_from_lonlat_tuples(lons, lats)
    # sometimes this function produces too high a zoom value, in which case we'll revert to a lower zoom
    if zoom > 11:
        zoom = 7.75

    category_name = df['Category'].iloc[0]
    total_grant_award_for_category = int(df.groupby(['GA ID']).max()['Value (AUD)'].sum())
    if total_grant_award_for_category // 1000000 >= 1:
        total_grant_award_for_category = str(np.round(total_grant_award_for_category/1000000, 2)) + 'M'
    elif total_grant_award_for_category // 100000 >= 1:
        total_grant_award_for_category = str(np.round(total_grant_award_for_category/1000, 2)) + 'K'

    total_communities_awarded = len(np.unique(df['Community ID']))
    total_grants_awarded = len(np.unique(df['GA ID']))

    fig.update_layout(
    mapbox_style='light',
    mapbox_accesstoken=token,
    mapbox_center={'lat': center[1], 'lon': center[0]},
    mapbox_zoom=zoom,
    title = f'<b>Awardee communities under grant category: {category_name}</b> <br><span style="font-size: 12px;">Total Category Grant Award (Present Value): <b>${total_grant_award_for_category}</b>. Number of communities impacted: {total_communities_awarded}<br><span style="font-size: 12px;">Number of grants awarded: {total_grants_awarded} (each marker color represents a different grant under this category)</span>'
    )

    fig.update_layout(
        #margin={"r":25,"t":100,"l":25,"b":25},
        legend=dict(orientation='h'),
        legend_title_text='Grant ID',
        autosize=False, width=900, height=900
    )

    if len(df['GA ID']) > 10:
        fig.update_layout(showlegend=False)

    fig.write_image(f"plots/awardee_communities_{category}.jpeg")

# %% chloropleth of grant awards for each category into LGAs
lga_and_category_investment = merge2_df.drop_duplicates(subset=['Project ID']).groupby(['Category','Local Government']).sum().reset_index()#.drop(['Community ID','Longitude','Latitude','Variation 0 Grant Term Commencement','Variation 0 Grant Term Termination','Variation 0 Grant Value (AUD)','Variation 9 Grant Term Commencement','Variation 9 Grant Term Termination','Variation 9 Grant Value (AUD)'], axis=1)
lga_and_category_investment['Local Government'] = lga_and_category_investment['Local Government'].apply(lambda x: lga_names_dict[x])
#lga_and_category_investment.to_csv('lga and category investment.csv')

geo_df = gpd.GeoDataFrame.from_features(lga_shapes_NT[['geometry','Local Government']]).merge(lga_and_category_investment, on='Local Government').set_index('Local Government')

unique_categories = np.unique(geo_df['Category'].astype('string'))
#category = random.choice(unique_categories)
for category in unique_categories:
    geo_df_redux = geo_df[geo_df['Category']==category]

    # filling in the remaining polygon info, skipping 'No usual address (NT)', 'Migratory - Offshore - Shipping (NT)'
    missing_lgas = list(np.setdiff1d(np.array(lga_shapes_NT['Local Government'][:-2]), np.array(geo_df_redux.index)))
    missing_lga_geometry_rows = lga_shapes_NT.loc[lga_shapes_NT.isin(missing_lgas).any(axis=1)]
    missing_lga_geometry_rows = missing_lga_geometry_rows[['Local Government','geometry']].reset_index().drop(['index'], axis=1).set_index('Local Government')
    geo_df_redux = pd.concat([geo_df_redux, missing_lga_geometry_rows])
    geo_df_redux['Value (AUD)'].fillna(0, inplace=True)

    fig = go.Figure(
        go.Choroplethmapbox(
        geojson=json.loads(geo_df_redux.geometry.to_json()),
        locations=geo_df_redux.index,
        z=geo_df_redux["Value (AUD)"], colorscale='oranges',
        )
    )
    fig.add_trace(
        go.Scattermapbox(
            lat=list(geo_df_redux.geometry.centroid.y),
            lon=list(geo_df_redux.geometry.centroid.x),
            mode='text',
            text=list(geo_df_redux.index.astype('string')),
            textfont={"color":"black","size":12, "family":"Courier New"}
        )
    )
    fig.add_trace(
        go.Scattermapbox(
            lat=list(geo_df_redux.geometry.centroid.y.apply(lambda x: x-0.3)),
            lon=list(geo_df_redux.geometry.centroid.x),
            mode='text',
            text=list(geo_df_redux['Value (AUD)'].apply(lambda x: '$' + str(np.round(x/1000000,2)) + 'M')),
            textfont={"color":"black","size":11, "family":"Courier New"}
        )
    )
    total_category_award = np.round(geo_df_redux['Value (AUD)'].sum()/1000000,2)
    fig.update_layout(
        mapbox_accesstoken=token,
        mapbox_center={'lat': -18.75, 'lon': 133.3578},
        mapbox_style="outdoors",
        mapbox_zoom=5.5,
        margin={"r":25,"t":100,"l":25,"b":25},
        autosize=False, width=900, height=1200,
        title=f'<span style="text-align:center; font-size: 16px;">Cumulative Grant Award (Present Value) For Category <b>{category}</b><br>across Local Government Areas. Total Awarded in NT: <b>${total_category_award}M<b></span>',
        showlegend=False
    )
    fig.write_image(f"plots/lga_investment_{category}.jpeg")
    #fig.show()
# %% grant recipient's location for each category (postcode)
poa_shapes = gpd.read_file(r'POA_2021_AUST_GDA94_SHP\POA_2021_AUST_GDA94.shp')
poa_shapes['geometry'] = poa_shapes['geometry'].replace('None', np.NaN)
poa_shapes.dropna(how='any', inplace=True)
poa_shapes['POA_CODE21'] = poa_shapes['POA_CODE21'].astype('string')
poa_shapes.rename(columns={'POA_CODE21':'Grant Recipient Postcode'}, inplace=True)
#poa_shapes.head(5)

merge2_df['Grant Recipient Postcode'] = merge2_df['Grant Recipient Postcode'].apply(lambda x: '0' + str(x) if len(str(x)) == 3 else str(x))
merge2_df['Grant Recipient Postcode'] = merge2_df['Grant Recipient Postcode'].astype('string')
#merge2_df['Grant Recipient Postcode'].head(5)
#%%
postcode_town_dict = dict(zip(list(merge2_df['Grant Recipient Postcode']), list(merge2_df['Grant Recipient Town/City'])))

df_redux = merge2_df[merge2_df['Category'] == 'Indigenous Education']
recipient_postcodes_list = []
for grant_id in list(np.unique(df_redux['GA ID'])):
    df_grant_redux = df_redux[df_redux['GA ID'] == grant_id]
    recipient_postcodes_list.append(list(df_grant_redux.drop_duplicates(subset=['GA ID'])['Grant Recipient Postcode'])[0])

category_postcode_counts = pd.DataFrame(pd.Series(recipient_postcodes_list).value_counts())
category_postcode_counts = category_postcode_counts.reset_index().rename(columns={'index':'Grant Recipient Postcode',0:'Counts'})

geo_df = gpd.GeoDataFrame.from_features(poa_shapes[['geometry','Grant Recipient Postcode']]).merge(category_postcode_counts, on='Grant Recipient Postcode')
geo_df['Grant Recipient Location'] = geo_df['Grant Recipient Postcode'].apply(lambda x: str(postcode_town_dict[x]).upper() if x != np.NAN else 'UNKNOWN')
geo_df.set_index('Grant Recipient Postcode', inplace=True)
#%%
fig = go.Figure(
    go.Choroplethmapbox(
    geojson=json.loads(geo_df.geometry.to_json()),
    locations=geo_df.index,
    z=geo_df["Counts"], colorscale='oranges',
    )
)

fig.add_trace(
    go.Scattermapbox(
        lat=list(geo_df.geometry.centroid.y),
        lon=list(geo_df.geometry.centroid.x),
        mode='text',
        text=list(geo_df['Grant Recipient Location'].astype('string')),
        textfont={"color":"black","size":12, "family":"Courier New"}
    )
)

fig.add_trace(
    go.Scattermapbox(
        lat=list(geo_df.geometry.centroid.y.apply(lambda x: x-0.3)),
        lon=list(geo_df.geometry.centroid.x),
        mode='text',
        text=list(geo_df['Counts'].astype('string')),
        textfont={"color":"black","size":11, "family":"Courier New"}
    )
)

fig.update_layout(
    mapbox_accesstoken=token,
    mapbox_center={'lat': -18.75, 'lon': 133.3578},
    mapbox_style="outdoors",
    mapbox_zoom=3,
    showlegend=False,
)
#fig.show()
fig.write_image('plots/postal_area.png')
beeper()
#%% counts of selection process out of overall
for category in list(np.unique(merge2_df['Category'])):
    df = merge2_df[merge2_df['Category']==category].drop_duplicates(subset=['GA ID'])
    try:
        process_counts_dict = df['Selection Process'].value_counts(sort=False).to_dict()
        process_counts_df = pd.DataFrame.from_dict(process_counts_dict, orient='index').rename(columns={0:'counts'})
        fig = go.Figure(go.Pie(labels=process_counts_df.index, values=process_counts_df.counts))
        fig.update_layout(
            title=f'Selection process proportion across grants for category: <br><b>{category}<b>',
            title_x=0.5,
            legend=dict(
                orientation='h',
                yanchor='top',
                xanchor='center',
                x=0.5,
                y=-0.05
            )
        )
        fig.write_image(f"plots/selection_proc_pie_{category}.jpeg")
    except:
        continue
    #fig.show()
# %%

# %% grant recipient's location for each category (suburb)
sal_shapes = gpd.read_file(r'SAL_2021_AUST_GDA94_SHP\SAL_2021_AUST_GDA94.shp')
sal_shapes['geometry'] = sal_shapes['geometry'].replace('None', np.NaN)
sal_shapes.dropna(how='any', inplace=True)
sal_shapes['SAL_NAME21'] = sal_shapes['SAL_NAME21'].astype('string')
'University of Melbourne' in sal_shapes['SAL_NAME21']

sal_shapes.rename(columns={'SAL_NAME21':'Grant Recipient Town/City'}, inplace=True)
#sal_shapes.head(5)

merge2_df['Grant Recipient Town/City'] = merge2_df['Grant Recipient Town/City'].apply(lambda x: str(x).title())
merge2_df['Grant Recipient Town/City'] = merge2_df['Grant Recipient Town/City'].astype('string')
#merge2_df['Grant Recipient Postcode'].head(5)
#%%
df_redux = merge2_df[merge2_df['Category'] == 'Indigenous Education']
recipient_suburbs_list = []
for grant_id in list(np.unique(df_redux['GA ID'])):
    df_grant_redux = df_redux[df_redux['GA ID'] == grant_id]
    recipient_suburbs_list.append(list(df_grant_redux.drop_duplicates(subset=['GA ID'])['Grant Recipient Town/City'])[0])
#%%
category_suburb_counts = pd.DataFrame(pd.Series(recipient_suburbs_list).value_counts())
category_suburb_counts = category_suburb_counts.reset_index().rename(columns={'index':'Grant Recipient Town/City',0:'Counts'})

geo_df = gpd.GeoDataFrame.from_features(sal_shapes[['geometry','Grant Recipient Town/City']]).merge(category_suburb_counts, on='Grant Recipient Town/City')
#geo_df['Grant Recipient Location'] = geo_df['Grant Recipient Postcode'].apply(lambda x: str(postcode_town_dict[x]).upper() if x != np.NAN else 'UNKNOWN')
geo_df.set_index('Grant Recipient Town/City', inplace=True)

fig = go.Figure()
#fig.add_trace(
#    go.Choroplethmapbox(
#    geojson=json.loads(geo_df.geometry.to_json()),
#    locations=geo_df.index,
#    z=geo_df["Counts"], 
#    #colorscale='oranges',
#    )
#)
fig.add_trace(
    go.Scattermapbox(
        lat=list(geo_df.geometry.centroid.y),
        lon=list(geo_df.geometry.centroid.x),
        mode='markers+text',
        marker_size=geo_df['Counts']*3,
        text=list(geo_df.index.astype('string')),
        textfont={"color":"black","size":12, "family":"Courier New"}
    )
)
fig.update_layout(
    mapbox_accesstoken=token,
    mapbox_center={'lat': -18.75, 'lon': 133.3578},
    mapbox_style="light",
    mapbox_zoom=3,
    #showlegend=False,
)
fig.show()
# %%
