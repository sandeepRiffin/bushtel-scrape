#%%
import pandas as pd
import numpy as np

import winsound
def beeper():
    freq=100
    dur=1000
    for i in range(0,10):
        winsound.Beep(freq,dur)
        freq+=50
#%%
community_profiles = pd.read_csv(
    'all_communities_profile_data.csv',
    header=0,
    index_col=0
)

aliases_and_id_dict = dict(
    zip(
        list(community_profiles['Community ID']),
        list(community_profiles['Aliases'])
    )
)

communities_and_projects = pd.read_csv(
    'communities_and_projects_details_v2.csv',
    header=0,
    index_col=0
    )

communities_and_projects['Aliases'] = communities_and_projects['Community ID'].apply(lambda x: aliases_and_id_dict[x])

borroloola_outstations = pd.Series(
    ['Bauhinia Downs',
    'Black Craggie',
    'Bull Rush',
    'Campbell Springs',
    'Cow Lagoon',
    'Garrinjinny',
    'Goolminyini',
    'Jungalina',
    'Kiana',
    'Lightning Ridge',
    'Milibundurra',
    'Minyalini',
    'Mooloowa',
    'Numultja',
    'Sandridge',
    'Twenty Mile',
    'Two Dollar Creek',
    'Wada Wadalla',
    'Wada Warra',
    'Wandangula',
    'Wathunga/Yuthunga (South West Island)',
    'Mumathumburru (West Island)',
    'Wurlbu',
    'Yameerie'
    ]
)
# %%
match_dfs_list = []
for outstation in borroloola_outstations:
    match_df = communities_and_projects.loc[(communities_and_projects['Community Name'].str.contains(outstation)) | (communities_and_projects['Aliases'].str.contains(outstation))]
    match_dfs_list.append(match_df)

outstations_projects_df = pd.concat(match_dfs_list)
outstations_projects_df = outstations_projects_df.drop_duplicates().dropna(how='all',axis=1)
aliases = outstations_projects_df.pop('Aliases')
loc_gov = outstations_projects_df.pop('Local Government')
land_council = outstations_projects_df.pop('Land Council')
outstations_projects_df.insert(loc=1, column='Aliases', value=aliases)
outstations_projects_df.insert(loc=2, column='Local Government', value=loc_gov)
outstations_projects_df.insert(loc=3, column='Land Council', value=land_council)
# %%
outstations_projects_df.to_csv('outstations_projects_funding.csv', index=False)
# %%
