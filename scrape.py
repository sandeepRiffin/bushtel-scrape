# %%
from operator import index
import winsound
import re
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import requests
from pprint import pprint

def beeper():
    freq=100
    dur=1000
    for i in range(0,10):
        winsound.Beep(freq,dur)
        freq+=50

from project_paths import CHROMEDRIVER_PATH

alphabet_list = [chr(i) for i in range(65,91)]
profile_letters_list = [f'/profile?letter={alphabet}' for alphabet in alphabet_list]

bushtel_base_url = 'https://bushtel.nt.gov.au'
bushtel_projects_url = 'https://bushtel.nt.gov.au/projects'
grantsconnect_base_url = 'https://www.grants.gov.au/'

# dms to decimal degrees conversion, source https://stackoverflow.com/a/54294962
def dms2dd(lat):
    deg, minutes, seconds, direction =  re.split('[°\'"]', lat)
    dd = (float(deg) + float(minutes)/60 + float(seconds)/(60*60)) * (-1 if direction.strip() in ['W', 'S'] else 1)
    return dd

def get_community_json(community_id : int):
    url = f"{bushtel_base_url}/api/Community/{community_id:0.0f}"
    resp = requests.get(url)
    return resp.json()

def chromedriver_initialise():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    driver = webdriver.Chrome(
        executable_path=CHROMEDRIVER_PATH / 'chromedriver', options=chrome_options
        )
    return driver

def community_profile_link_fetcher():
    driver = chromedriver_initialise()
    profile_links = []

    # grabbing links to each community's profile page from the alphabetically ordered list of communities on the "Profiles" landing page
    for profile_letter in profile_letters_list:
        page_url = bushtel_base_url + profile_letter
        driver.get(page_url)
        time.sleep(3)

        pageSource = driver.page_source
        soup_selenium = BeautifulSoup(pageSource, 'lxml')

        # grab all <a>...</a> tags from the page source as they contain the hrefs (links)
        all_links = soup_selenium.find_all('a', href=True)

        # filtering for only the community profile page links
        for i in range(0, len(all_links)):
            link = all_links[i]

            # link['href'] gives only the href out of the the grabbed <a>...</a> tag
            if '/profile' in link['href'] and '?letter' not in link['href']:
                profile_links.append(link['href'])

    # removing duplicates by converting list to set and back to list
    profile_links = list(set(profile_links))

    # removing the lone '/profile' from list
    profile_links.remove('/profile')

    return profile_links

def grants_weblink_fetcher():
    community_projects_df = pd.read_csv('community_projects_list.csv', index_col=None, usecols=[1,2,3,4,5,6,7]).drop_duplicates()
    grant_weblinks_dict = {}

    # grabbing links to each community's profile page from the alphabetically ordered list of communities on the "Profiles" landing page
    for project_id in community_projects_df['Project ID']:
        if '-V' in project_id:
            split_strings = project_id.split('-')
            project_id = split_strings[0]
        else:
            project_id = project_id
        
        if project_id not in grant_weblinks_dict.keys():
            print(f'Now fetching grant info for project ID: {project_id}')
            
            driver = chromedriver_initialise()
            page_url = grantsconnect_base_url + f'Search/KeywordSearch?keyword={project_id}'
            driver.get(page_url)
            time.sleep(3)
            pageSource = driver.page_source
            soup_selenium = BeautifulSoup(pageSource, 'lxml')

            title=project_id 
            # grab all <a>...</a> tags from the page source as they contain the hrefs (links)
            grant_weblinks_dict.update({project_id:[a['href'] for a in soup_selenium.find_all('a', class_='u', href=True, title=title)][0]})
        else:
            continue
        
    return grant_weblinks_dict

def variations_info_fetcher(soup_selenium, project_id):
    grant_variations_weblinks = [a['href'] for a in soup_selenium.find_all('a') if project_id in a.text]

    variations_particulars_dict = {}
    driver = chromedriver_initialise()
    for link in grant_variations_weblinks:
        page_url = grantsconnect_base_url + link
        driver.get(page_url)
        time.sleep(3)
        pageSource = driver.page_source
        soup_selenium = BeautifulSoup(pageSource, 'lxml')
        
        variation_project_title = [div.text.strip('\n').strip() for div in soup_selenium.find_all('div', class_='box boxY boxYD2 r9 heigh-auto')][0]
        variation_scraped_text = [div.text.strip('\n').strip() for div in soup_selenium.find_all('div', class_='list-desc')]
        variation_split_scraped_text = [heading.split(':') for heading in variation_scraped_text]
        grant_id = variation_split_scraped_text[0][1].strip('\n')

        grant_variation_info_dict = {}
        grant_variation_info_dict.update({'Project Title': variation_project_title})
        
        for sublist in variation_split_scraped_text:
            if sublist != ['Grant Recipient Details'] and sublist != ['Grant Recipient Location'] and sublist != ['Grant Delivery Location']:
                try:
                    grant_variation_info_dict.update({sublist[0].strip(' \n\t'): sublist[1].strip(' \n\t')})

                except Exception as e:
                    print(e)
                    unparsed_grants_list.append(grant_id)
                    continue

        variation_number = grant_variation_info_dict['GA ID'][-1]
        variation = 'Variation ' + variation_number
        start_date = grant_variation_info_dict['Grant Term'].split(' to ')[0]
        end_date = grant_variation_info_dict['Grant Term'].split(' to ')[1]
        value = grant_variation_info_dict['Value (AUD)'].split('\n')[0].strip('$,')

        variations_particulars_dict.update(
            {
                f'{variation} Grant Term Commencement':start_date,
                f'{variation} Grant Term Termination':end_date,
                f'{variation} Grant Value (AUD)':value
        }
        )
    
    variations_info_df = pd.DataFrame.from_dict(variations_particulars_dict, orient='index', columns=['Data']).T
    
    return variations_info_df

def variations_df_compiler():
    grants_weblinks_df = pd.read_csv('grants_weblinks.csv', index_col=0, skiprows=1, header=None)
    grant_weblinks = grants_weblinks_df.to_dict()[1]
    variations_dfs = []
    
    driver = chromedriver_initialise()
    for link in list(grant_weblinks.values()):
        page_url = grantsconnect_base_url + link
        driver.get(page_url)
        time.sleep(3)
        pageSource = driver.page_source
        soup_selenium = BeautifulSoup(pageSource, 'lxml')
        
        scraped_text = [div.text.strip('\n').strip() for div in soup_selenium.find_all('div', class_='list-desc')]
        split_scraped_text = [heading.split(':') for heading in scraped_text]
        
        grant_id = split_scraped_text[0][1].strip('\n')
        print(f'Now processing grant ID {grant_id}')
        
        df = variations_info_fetcher(soup_selenium=soup_selenium, project_id=grant_id)
        df['GA ID'] = grant_id

        variations_dfs.append(df)

    all_grants_variations = pd.concat(variations_dfs).reset_index().drop(['index'], axis=1)
    all_grants_variations = all_grants_variations.sort_index(axis=1)
    all_grants_variations['GA ID'] = all_grants_variations['GA ID'].astype('string')
    all_grants_variations = all_grants_variations.drop_duplicates(subset=['GA ID'])
    return all_grants_variations
#%%
grant_weblinks = grants_weblink_fetcher()
print(len(grant_weblinks.values()))
print(len(list(set(grant_weblinks.values()))))
grants_weblinks_df = pd.DataFrame.from_dict(grant_weblinks, orient='index')
grants_weblinks_df.to_csv('grants_weblinks.csv')
beeper()
# %%
driver = chromedriver_initialise()
community_dfs = []
unparsed_comms_list = []
profile_links = community_profile_link_fetcher()

# going to each community's profile page and scraping its name, ID, and other attributes
for profile_link in profile_links:
    # you get the community ID after the ninth character in the link
    print(f'Now processing Community: {profile_link[9:]}')

    page_url = bushtel_base_url + profile_link
    driver.get(page_url)
    time.sleep(3)

    pageSource = driver.page_source
    soup_selenium = BeautifulSoup(pageSource, 'lxml')

    try:
        profile_attributes_dict = {}

        # might be more prudent in the future to identify elements by relative xpaths rather than class names
        profile_name = [a.text for a in soup_selenium.find_all('span', class_='profile-tab-header ng-binding')]
        print(f'Community name is: {profile_name[0]}')
        comm_id = [a.text[14:] for a in soup_selenium.find_all('h5', class_='h5-responsive ng-binding')]

        profile_attributes_dict.update(dict(zip(['Community Name','Community ID'],(profile_name + comm_id))))

        attributes_list = [attribute.text for attribute in soup_selenium.find_all('p', class_='ng-binding')][0:10]
        headers_list = [
            'Aliases',
            'Local Government',
            'Main Language',
            'Land Council',
            'Other Languages',
            'Electorate',
            'Population',
            'Longitude',
            'Latitude',
            'Location'
        ]
        # creating a dict by zipping two lists, one containing keys and the other containing values
        profile_attributes_dict.update(dict(zip(headers_list,attributes_list)))

        # converting that dict into a dataframe
        df = pd.DataFrame.from_dict(profile_attributes_dict, orient='index').T
        community_dfs.append(df)

    except Exception as e:
        print(f'Could not parse community ID: {profile_link[9:]} due to {e}')
        unparsed_comms_list.append(profile_link)
        continue

all_comms_profile_data = pd.concat(community_dfs)
all_comms_profile_data.index = pd.Index(np.arange(0,776))

# final cleanups
cleaned_profile_data = all_comms_profile_data.copy()

cleaned_profile_data['Community ID'] = cleaned_profile_data['Community ID'].replace('', np.NaN) #.astype('Int64')
cleaned_profile_data.Longitude = cleaned_profile_data.Longitude.apply(lambda x: x[11:]).replace('', np.NaN).astype('float')
cleaned_profile_data.Latitude = cleaned_profile_data.Latitude.apply(lambda x: x[10:]).replace('', np.NaN).astype('float')
cleaned_profile_data.Population = cleaned_profile_data.Population.apply(lambda x: re.findall('\d+', x)).apply(lambda x: x if x else [np.NaN,np.NaN]).apply(lambda x: float(x[0]))

cleaned_profile_data.sort_values(by=['Community Name']).replace('-', np.NaN).dropna(how='all').to_csv('all_communities_profile_data_v2.csv')
#%%
cleaned_profile_data = pd.read_csv(
    'all_communities_profile_data.csv',
    index_col=0,
    header=0
    )

cleaned_profile_data.dropna(subset=['Land Council']).groupby(['Land Council']).sum().drop(['Community ID','Longitude','Latitude'], axis=1)
cleaned_profile_data.dropna(subset=['Local Government']).groupby(['Local Government']).sum().drop(['Community ID','Longitude','Latitude'], axis=1)

community_projects_list = []
unparsed_comms_list = []

driver = chromedriver_initialise()

for id in cleaned_profile_data['Community ID']:
    try:
        print(f'Now processing Community ID {str(int(id))}')

        driver.get(bushtel_projects_url)
        time.sleep(3)

        community_name_text_field = driver.find_element_by_xpath('//*[@id="container-index"]/div/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/input')
        community_name_text_field.click()
        community_name_text_field.send_keys(str(int(id)))

        projects_search_button = driver.find_element_by_xpath('//*[@id="container-index"]/div/div[1]/div[1]/div[1]/div[1]/div[5]/div/button[2]')
        projects_search_button.click()

        time.sleep(3)

        search_results_source = driver.page_source
        soup_search = BeautifulSoup(search_results_source, 'lxml')

        results_table_contents = [td.text for td in soup_search.find_all('td')][5:]
        results_table_contents = [element for element in results_table_contents if (element != '')]
        chunked_results_table_contents = [results_table_contents[i:i+3] for i in range(0,len(results_table_contents),3)]

        table_contents_dict = {
            'Start Date':[],
            'End Date':[],
            'Project Name':[]
        }

        for sublist in chunked_results_table_contents:
            table_contents_dict['Start Date'].append(sublist[0])
            table_contents_dict['End Date'].append(sublist[1])
            table_contents_dict['Project Name'].append(sublist[2])

        df = pd.DataFrame().from_dict(table_contents_dict, orient='columns')

        master_details_dfs = []
        master_detail_rows = []

        # go down the table and click each project row, to reveal the master detail row which contains further info
        for i in range(1,len(chunked_results_table_contents)+2):
            project_row_xpath = f'//*[@id="grdSearchResults"]/div/div[6]/div/div/div[1]/div/table/tbody/tr[{i}]'
            
            # using javascript executor here to click cuz the selenium click method returns a ElementClickInterceptedException
            btn = driver.find_element_by_xpath(project_row_xpath)
            driver.execute_script("arguments[0].click();",btn)

            #time.sleep(1)

            search_results_source = driver.page_source
            soup_search = BeautifulSoup(search_results_source, 'lxml')

            master_detail_rows.append([div.text.strip() for div in soup_search.find_all('div', class_='col-xs-10')])

        master_detail_contents_dict = {
        'Recipient':[],
        'Value':[],
        'Project ID':[]
        }

        # something weird going on here where the first master detail row is being scraped twice,
        # so skipping the first occurrence of in the list
        for sublist in master_detail_rows[1:]:
            master_detail_contents_dict['Recipient'].append(sublist[0])
            master_detail_contents_dict['Value'].append(sublist[1].lstrip('$'))
            master_detail_contents_dict['Project ID'].append(sublist[2])

        df_m = pd.DataFrame().from_dict(master_detail_contents_dict, orient='columns')
        df_m['Community ID'] = str(int(id))

        df_full_detail = pd.concat([df, df_m], axis=1)
        
        first_project_name = df_full_detail.iloc[0]['Project Name']
        first_project_value = df_full_detail.iloc[0]['Value']
        print(f'The first project that received a grant for this community was {first_project_name}, with a sum award of ${first_project_value}')
        community_projects_list.append(df_full_detail)

    except Exception as e:
        print(f'Could not process community due to error {e}')
        unparsed_comms_list.append(int(id))
        continue

community_projects_df = pd.concat(community_projects_list)

# appending information about LGA and Land Council
community_profiles_df = pd.read_csv('all_communities_profile_data.csv', index_col=None, usecols=[1,2,3,4,5,6,7,8,9,10,11])
id_lga_dict = dict(zip(list(community_profiles_df['Community ID']) ,list(community_profiles_df['Local Government'])))
id_landcouncil_dict = dict(zip(list(community_profiles_df['Community ID']) ,list(community_profiles_df['Land Council'])))
community_projects_df['Local Government'] = community_projects_df['Community ID'].apply(lambda x: id_lga_dict[int(x)])
community_projects_df['Land Council'] = community_projects_df['Community ID'].apply(lambda x: id_landcouncil_dict[int(x)])

community_projects_df.to_csv('community_projects_list.csv')
#%%
driver = chromedriver_initialise()
community_dfs = []
unparsed_comms_list = []
profile_links = community_profile_link_fetcher()
#%%
# going to each community's profile page and scraping its name, ID, and other attributes
for profile_link in profile_links[:1]:
    # you get the community ID after the ninth character in the link
    print(f'Now processing Community: {profile_link[9:]}')

    page_url = 'https://bushtel.nt.gov.au/profile/42?tab=businessdirectory' #bushtel_base_url + profile_link + '?tab=businessdirectory'
    driver.get(page_url)
    time.sleep(3)

    pageSource = driver.page_source
    soup_selenium = BeautifulSoup(pageSource, 'lxml')
#%%
[div.text.strip().split('   ') for div in soup_selenium.find_all('div', class_='row pad-b-5 bus-directory-list-row ng-scope') if '(08)' in div.text]
#%% scraping community directory data from the profiles
community_profiles_df = pd.read_csv('all_communities_profile_data.csv', index_col=None, usecols=[1,2,3,4,5,6,7,8,9,10,11])

ies_comms = pd.read_csv('IES Communities  - Basic information.csv',
                        index_col=None, header=0,
                        dtype={'COMMUNITY_ID':'int64',
                               'COMMUNITY_NAME':'string',
                               'COMMUNITY_ALIASES':'string'})

setup_comms = pd.read_csv('NT Setup communities.csv',
                        index_col=None, header=0,
                        dtype={'Community':'string',
                               'Dual Input Atonometrics':'string'},
                        parse_dates=True)

setup_comms['Diesel Generation Actual MWh'] = setup_comms['Diesel Generation Actual MWh'].apply(lambda x: str(x).replace(',','')).astype('float64')
setup_comms['Community'] = setup_comms['Community'].apply(lambda x: x.replace('\n',' ').upper())

split_names = setup_comms['Community'].apply(lambda x: x.split(sep=' ('))
setup_comms['Community'] = split_names.apply(lambda x: x[0])
setup_comms['Community AKA'] = split_names.apply(lambda x: x[1].replace(')','') if len(x) == 2 else None)

community_names_aliases = list(np.unique(setup_comms['Community'])) + list(np.unique(setup_comms['Community AKA'].astype('string').dropna()))
rows_list = []
for community_name in community_names_aliases:
    rows_list.append(ies_comms[ies_comms['COMMUNITY_NAME'].str.contains(community_name)])
    rows_list.append(ies_comms[ies_comms['COMMUNITY_ALIASES'].str.contains(community_name)])

ies_setup_comms = pd.concat(rows_list).drop_duplicates()

ies_comms['Previous SETuP Community'] = ies_comms['COMMUNITY_NAME'].apply(lambda x: 'Y' if x in list(ies_setup_comms['COMMUNITY_NAME']) else 'N')

# method source: https://stackoverflow.com/a/67659260
df2 = community_profiles_df[['Community Name','Community ID','Latitude','Longitude']].copy()
df3 = ies_comms.merge(df2, how='cross')

# this filter is case sensitive!!! Won't work if both strings are not upper/lower case
mask = df3.apply(lambda x: (re.search(rf"\b{x['COMMUNITY_NAME']}\b", str(x['Community Name'].upper()))) != None, axis=1)
df_out = df3.loc[mask]
df_out.drop(['Community Name','Community ID'], axis=1, inplace=True)
df_out.to_csv('ies_bushtel_merge.csv')
#%%
comm_dirs_list = []
unparsed_commdirs_list  = []
for comm_id in list(ies_comms.COMMUNITY_ID):
    print(f'Now processing community ID {comm_id}')
    out = get_community_json(comm_id)
    try:
        entities = pd.DataFrame.from_dict(out['Businesses'], orient='columns').reset_index().rename({'index':'parent_index','EntityName':'Entity Name'}, axis=1)

        organisations_list = []
        for ix, dict_list in enumerate(entities.Businesses):
            df = pd.concat([pd.DataFrame.from_dict(biz_dict, orient='columns') for biz_dict in dict_list])
            df.insert(0,column='parent_index',value=ix)
            organisations_list.append(df)

        businesses = pd.concat(organisations_list)
        businesses = businesses.rename(
                                    columns={
                                        'Name':'Operating As',
                                        'Email':'Organisation Email',
                                        'Website':'Organisation Website'
                                        }
                                    )
        
        locations_list = []
        for ix, dict_list in enumerate(businesses.Locations):
            df = pd.DataFrame.from_dict(dict((k,pd.Series(v)) for k,v in dict_list.items()), orient='columns')
            row_to_drop = ['Address','Latitude','Longitude','PostCode', 'State','Suburb']
            for row in row_to_drop:
                if row in df.index:
                    df = df.drop([row])
                else:
                    continue
            col_to_drop = ['Point','StreetAddress','PostalAddress','Services']
            for col in col_to_drop:
                if col in df.columns:
                    df = df.drop([col],axis=1)
                else:
                    continue
            df.insert(0,column='parent_index',value=ix)
            locations_list.append(df)

        locations = pd.concat(locations_list)
        locations = locations.reset_index().drop(['index','parent_index'], axis=1)
        locations = locations.rename(
                                columns={
                                    'Email':'Business Email',
                                    'Website':'Business Website',
                                    }
                                )

        aka_list = []
        for ix, dict_list in enumerate(locations.Aka):
            if type(dict_list) == dict:
                aka_list.append(pd.DataFrame(dict_list, index=[ix]))
            else:
                aka_list.append(pd.DataFrame({'Name':dict_list, 'ModifiedDate':dict_list}, index=[ix]))

        aka_df = pd.concat(aka_list)
        aka_df = aka_df.rename(
                            columns={
                                'Name':'Also Known As',
                                }
                            )
        
        comm_dir = entities.merge(businesses, on='parent_index').drop(['Businesses'], axis=1) 
        comm_dir = pd.concat([comm_dir, aka_df, locations], axis=1).drop(['Locations','Aka'], axis=1)

        comm_dir.insert(0, column='COMMUNITY_ID', value=comm_id)
        comm_dirs_list.append(comm_dir)    
    except Exception as e:
        unparsed_commdirs_list.append([comm_id,e])
        continue
#%%
all_comm_dirs_df = pd.concat(comm_dirs_list)
datemod_cols = [col for col in all_comm_dirs_df.columns if 'Modif' in col]
all_comm_dirs_df = all_comm_dirs_df.reset_index()
all_comm_dirs_df = all_comm_dirs_df.drop(datemod_cols + ['index','parent_index'], axis=1)

unparsed_commdirs_df = pd.concat([pd.DataFrame({'COMMUNITY_ID':commid_error_list[0]}, index=[ix]) for ix,commid_error_list in enumerate(unparsed_commdirs_list)])
all_comm_dirs_df = all_comm_dirs_df.merge(unparsed_commdirs_df, how='outer')

all_comm_dirs_df.to_csv('comm_businesses_directory.csv', encoding='utf-8-sig')
all_comm_dirs_df
#%%
comm_biz_locs_df = df_out.drop(['Coordinates','Community based Aboriginal Corporations\n','Community based Aboriginal business\n•'], axis=1).merge(all_comm_dirs_df, on='COMMUNITY_ID')
comm_biz_locs_df.to_csv('community_profiles_businesses_locations.csv')
#%%
ranger_groups = pd.read_csv('indigenous_ranger_groups.csv', header=0, index_col=None, dtype={'Latitude':'string', 'Longitude':'string'})
ranger_groups.Latitude = ranger_groups.Latitude + ' S'
ranger_groups.Longitude = ranger_groups.Longitude + ' E'
ranger_groups.rename(columns={'Latitude':'Latitude_DMS', 'Longitude':'Longitude_DMS'}, inplace=True)

ranger_groups['Latitude_DD'] = ranger_groups.Latitude_DMS.apply(lambda x: dms2dd(x))
ranger_groups['Longitude_DD'] = ranger_groups.Longitude_DMS.apply(lambda x: dms2dd(x))
ranger_groups.to_csv('indigenous_ranger_groups_coordinates.csv')
#%%
"""
pine_creek_bushtel_projects_url = bushtel_base_url + '/profile/10270?tab=projects'

chrome_options = Options()
chrome_options.add_argument('--headless')
driver = webdriver.Chrome(
    executable_path=CHROMEDRIVER_PATH / 'chromedriver', options=chrome_options
    )

driver.get(pine_creek_bushtel_projects_url)
time.sleep(3)

pageSource = driver.page_source
soup_selenium = BeautifulSoup(pageSource, 'lxml')

elements_to_click = driver.find_elements_by_class_name("col-lg-2")

for element in elements_to_click:
    try:
        element.click()
    except Exception as e:
        print(e)
        continue

[div for div in soup_selenium.find_all('div', class_='col-xs-10 ng-binding')]
#%%
# By default, when the page is first loaded, unfinished projects will be shown first.
[div.text for div in soup_selenium.find_all('div', class_='col-lg-4 col-md-5 col-sm-8 col-xs-11 ng-binding')]
#%%
[div for div in soup_selenium.find_all('div', class_='col-xs-10 ng-binding')]
# %%
#%%
unfinished_projects_radio = driver.find_element_by_id("feedback_why_other")
finished_projects_radio = driver.find_element_by_id("feedback_why_compliment")

unfinished_projects_select_state = unfinished_projects_radio.is_selected()
finished_projects_select_state = finished_projects_radio.is_selected()

if finished_projects_select_state == False:
    finished_projects_radio.click()
else:
    pass

"""
# %% scraping project pages from grants connect
if grant_weblinks == None:
    grants_weblinks_df = pd.read_csv('grants_weblinks.csv', index_col=0, skiprows=1, header=None)
    grant_weblinks = grants_weblinks_df.to_dict()[1]

driver = chromedriver_initialise()

headings_list = []
grants_info_dfs = []
unparsed_grants_list = []

for link in list(grant_weblinks.values()):
    page_url = grantsconnect_base_url + link
    driver.get(page_url)
    time.sleep(3)
    pageSource = driver.page_source
    soup_selenium = BeautifulSoup(pageSource, 'lxml')
    
    project_title = [div.text.strip('\n').strip() for div in soup_selenium.find_all('div', class_='box boxY boxYD2 r9 heigh-auto')][0]
    scraped_text = [div.text.strip('\n').strip() for div in soup_selenium.find_all('div', class_='list-desc')]

    split_scraped_text = [heading.split(':') for heading in scraped_text]
    for sublist in split_scraped_text[-9:-4]: # Adding a sub-string here to differentiate between recipient and delivery fields
        sublist[0] = 'Grant Recipient ' + sublist[0]

    for sublist in split_scraped_text[-3:]: # Adding a sub-string here to differentiate between recipient and delivery fields
        sublist[0] = 'Grant Delivery ' + sublist[0]

    grant_id = split_scraped_text[0][1].strip('\n')
    print(f'Now processing grant {grant_id}, with the project title: {project_title}')

    grant_info_dict = {}
    grant_info_dict.update({'Project Title': project_title})

    for sublist in split_scraped_text:  
        if sublist != ['Grant Recipient Details'] and sublist != ['Grant Recipient Location'] and sublist != ['Grant Delivery Location']:
            try:
                grant_info_dict.update({sublist[0].strip(' \n\t'): sublist[1].strip(' \n\t')})

            except Exception as e:
                print(e)
                unparsed_grants_list.append(grant_id)
                continue
    
    if 'Variations' in grant_info_dict.keys() and '\n' in grant_info_dict['Variations']:
        separated_variations = [variation.strip(' \n') for variation in grant_info_dict['Variations'].split('\n') if variation.strip(' \n') != '']
        grant_info_dict['Variations'] = separated_variations

    if '\n' in grant_info_dict['Grant Term']:
        grant_info_dict['Grant Term'] = [element for element in grant_info_dict['Grant Term'].split('\n')][0]

    if '\n' in grant_info_dict['Value (AUD)']:
        grant_info_dict['Value (AUD)'] = [element for element in grant_info_dict['Value (AUD)'].split('\n')][0].strip('$,')

    df = pd.DataFrame.from_dict(grant_info_dict, orient='index', columns=['Data']).T
    
    grants_info_dfs.append(df)

beeper()
grants_info_df = pd.concat(grants_info_dfs).reset_index().drop('index', axis=1)

grants_info_df['GA ID'] = grants_info_df['GA ID'].astype('string')
grants_info_df.drop_duplicates(subset=['GA ID'])
grants_info_df.to_csv('grants_info_df.csv')
#%%
# if grants_variations_info_df.csv doesn't exist in directory, then
variations_df = variations_df_compiler()
variations_df.to_csv('grants_variations_info_df.csv')
beeper()
#%%
grants_info_df = pd.read_csv('grants_info_df.csv', index_col=0, header=0)
#variations_df = pd.read_csv('grants_variations_info_df.csv')

df1 = grants_info_df.drop_duplicates(subset=['GA ID'])
df2 = variations_df.sort_index(axis=1).drop_duplicates(subset=['GA ID'])

pd.merge(df1, df2, on='GA ID').set_index('GA ID').to_csv('grants_and_variations_merged.csv')
# %%
df1 = pd.read_csv('community_projects_list.csv', header=0, usecols=[6,7,8,9])
df2 = pd.read_csv('all_communities_profile_data.csv', header=0, usecols=[1,2,10,11])
df3 = pd.read_csv('grants_and_variations_merged.csv')

df1['GA ID'] = df1['Project ID'].apply(lambda x: x[:-3] if '-V' in x else x)

merge1_df = pd.merge(df1, df3, on='GA ID')
merge2_df = pd.merge(df2, merge1_df, on='Community ID')

merge2_df['Value (AUD)'] = merge2_df['Value (AUD)'].apply(lambda x: float(x.replace(',','')))
merge2_df.to_csv('communities_and_projects_details_v2.csv')
# %%
