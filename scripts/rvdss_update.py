from bs4 import BeautifulSoup
import requests
import regex as re
import io
import pandas as pd
import os
from epiweeks import Week
from datetime import datetime, timedelta
import math
import warnings
from dateutil import parser

REQUEST_TIMEOUT = (10, 30)  # Connect and read timeouts, in seconds.


def fetch_url(url, headers=None):
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response

VIRUSES = {
    "parainfluenza": "hpiv",
    "piv": "hpiv",
    "para": "hpiv",
    "adenovirus": "adv",
    "adeno": "adv",
    "human metapneumovirus": "hmpv",
    "enterovirus/rhinovirus": "ev_rv",
    "rhinovirus": "ev_rv",
    "rhv": "ev_rv",
    "entero/rhino": "ev_rv",
    "rhino":"ev_rv",
    "ev/rv":"ev_rv",
    "coronavirus":"hcov",
    "coron":"hcov",
    "coro":"hcov",
    "respiratory syncytial virus":"rsv",
    "influenza":"flu",
    "sars-cov-2":"sarscov2",
}

GEOS = {
    "newfoundland": "nl",
    "newfoundland and labrador": "nl",
    "prince edward island":"pe",
    "nova scotia":"ns",
    "new brunswick":"nb",
    "québec":"qc",
    "quebec":"qc",
    "ontario":"on",
    "manitoba" : "mb",
    "saskatchewan":"sk",
    "alberta": "ab",
    "british columbia" :"bc",
    "yukon" : "yt",
    "northwest territories" : "nt",
    "nunavut" : "nu",
    "canada":"ca",
    "can":"ca" ,
    "at":"atlantic",
    "atl":"atlantic",
    "pr" :"prairies" ,
    "terr" :"territories",
 }

COL_MAPPERS = {   #RESP-DET			POSITIVE TESTS
	'sarscov2tested' :  'sarscov2_tests',
    'sarscov2test' :  'sarscov2_tests',
	'sarscov2_positive_positive_tests': 'sarscov2_positive_tests',
	'sarscov2pos_positive_tests': 'sarscov2_positive_tests',
	'hcovtested' : 'hcov_tests',
    'hcovtest' : 'hcov_tests',
	'hcov_positive_positive_tests':'hcov_positive_tests',
    'hcovpos_positive_tests':'hcov_positive_tests',
	'ev_rvtested': 'ev_rv_tests',
    'ev_rvtest': 'ev_rv_tests',
	'evrvtest': 'ev_rv_tests',
    'evrv_tests': 'ev_rv_tests',
    'entero_rhino_tests': 'ev_rv_tests',
    'evrvtested': 'ev_rv_tests',	
	'ev_rv_positive_positive_tests':'ev_rv_positive_tests',
	'ev_rvpos_positive_tests':'ev_rv_positive_tests',
    'evrv_positive_positive_tests':'ev_rv_positive_tests',
    'evrv_positive_tests':'ev_rv_positive_tests',
    'evrvpos_positive_tests':'ev_rv_positive_tests',
    'entero_rhinotested': 'ev_rv_tests',
    'entero_rhinotest': 'ev_rv_tests',
    'entero_rhino_positive_tests':'ev_rv_positive_tests',
    'entero_rhino_positive_positive_tests':'ev_rv_positive_tests',
    'entero_rhinopos_positive_tests': 'ev_rv_positive_tests',
    'entero_rhino_pct_positive':'ev_rv_pct_positive',
    'evrv_pct_positive':'ev_rv_pct_positive',
	'hmpvtested':'hmpv_tests',
    'hmpvtest':'hmpv_tests',
	'hmpv_positive_positive_tests': 'hmpv_positive_tests',
    'hmpvpos_positive_tests': 'hmpv_positive_tests',
	'advtested':'adv_tests',
    'advtest':'adv_tests',
    'adv_positive_positive_tests': 'adv_positive_tests',
    'advpos_positive_tests': 'adv_positive_tests',
    'rsvtested':'rsv_tests',
    'rsvtest':'rsv_tests',
    'rsv_positive_positive_tests': 'rsv_positive_tests',
    'rsvpos_positive_tests': 'rsv_positive_tests',
    'hpivtested':'hpiv_tests',
    'hpivtest':'hpiv_tests',
	# calculate by summing the numbers

    'flutested':'flu_tests',
    'flutest':'flu_tests',

    'flua_positive_positive_tests':'flua_positive_tests',
    'fluapos_positive_tests':'flua_positive_tests',
    'flub_positive_positive_tests':'flub_positive_tests',
    'flubpos_positive_tests':'flub_positive_tests',
    'flu_a_positive_tests':'flua_positive_tests',
    'flu_b_positive_tests':'flub_positive_tests',
    'flu_a_pct_positive':'flua_pct_positive',
    'flu_b_pct_positive':'flub_pct_positive'
	}

LOC_CORRECTION = {
    'ca':'nation',
    'on':'province',
    'qc':'province',
    'ns':'province',
    'nb':'province',
    'mb':'province',
    'bc':'province',
    'pe':'province',
    'sk':'province',
    'ab':'province',
    'nl':'province',
    'nt':'territory',
    'yt':'territory',
    'nu':'territory',
    'atlantic':'region',
    'prairies':'region',
    'territories':'region'

}


COLUMNS_TARGET = ['time_value','geo_type','geo_value','flu_pct_positive','rsv_pct_positive','sarscov2_pct_positive']

# Regions are groups of provinces that are geographically close together. Some single provinces are reported as their own region (e.g. Québec, Ontario).
REGIONS = ['atlantic','atl','at','province of québec','québec','qc','province of ontario','ontario','on',
            'prairies', 'pr', "british columbia",'bc',"territories",'terr',]
NATION = ["canada","can",'ca',]


DASHBOARD_BASE_URL = "https://health-infobase.canada.ca/src/data/respiratory-virus-detections/"
DASHBOARD_W_DATE_URL = DASHBOARD_BASE_URL + "archive/{date}/"
DASHBOARD_UPDATE_DATE_FILE = "RVD_UpdateDate.csv"
DASHBOARD_DATA_FILE = "RVD_WeeklyData.csv"
SEASON_BASE_URL = "https://www.canada.ca"
ALTERNATIVE_SEASON_BASE_URL = "www.phac-aspc.gc.ca/bid-bmi/dsd-dsm/rvdi-divr/"
HISTORIC_SEASON_REPORTS_URL = SEASON_BASE_URL+"/en/public-health/services/surveillance/respiratory-virus-detections-canada/{year_range}.html"

HISTORIC_SEASON_URL = (HISTORIC_SEASON_REPORTS_URL.format(year_range = year_range) for year_range in
    (
        "2013-2014",
        "2014-2015",
        "2015-2016",
        "2016-2017",
        "2017-2018",
        "2018-2019",
        "2019-2020",
        "2020-2021",
        "2021-2022",
        "2022-2023",
        "2023-2024",
        "2024-2025"
        )
)

HISTORIC_SEASON_URL_CHECKPOINT = []


RESP_COUNTS_OUTPUT_FILE = "respiratory_detections.csv"
POSITIVE_TESTS_OUTPUT_FILE = "positive_tests.csv"

LAST_WEEK_OF_YEAR = 35


def abbreviate_virus(full_name):
    lowercase=full_name.lower()
    keys = (re.escape(k) for k in VIRUSES.keys())
    pattern = re.compile(r'\b(' + '|'.join(keys) + r')\b')
    result = pattern.sub(lambda x: VIRUSES[x.group()], lowercase)
    return(result)

def abbreviate_geo(full_name):
    lowercase=full_name.lower()
    lowercase = re.sub("province of ","",lowercase)
    lowercase=re.sub("\.|\*","",lowercase)
    lowercase=re.sub("/territoires","",lowercase)
    lowercase=re.sub("^cana$","can",lowercase)

    keys = (re.escape(k) for k in GEOS.keys())
    pattern = re.compile(r'^\b(' + '|'.join(keys) + r')\b$')

    result = pattern.sub(lambda x: GEOS[x.group()], lowercase)
    return(result)

def create_geo_types(geo,default_geo):
    if geo in NATION:
        geo_type="nation"
    elif geo in REGIONS:
        geo_type="region"
    else:
        geo_type = default_geo
    return(geo_type)

def check_date_format(date_string):
    if not re.search("[0-9]{4}-[0-9]{2}-[0-9]{2}",date_string):
        if re.search(r"/",date_string):
            new_date = re.sub(r"/","-",date_string)
            new_date = datetime.strptime(new_date,"%d-%m-%Y").strftime("%Y-%m-%d")
        elif re.search("[0-9]{2}-[0-9]{2}-[0-9]{4}",date_string):
            new_date = datetime.strptime(date_string,"%d-%m-%Y").strftime("%Y-%m-%d")
        else:
            raise AssertionError("Unrecognised date format")
    else:
        new_date=date_string

    return(new_date)

def get_revised_data(base_url):
    headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    }

    # Get update date
    update_date_url =  base_url + DASHBOARD_UPDATE_DATE_FILE
    update_date_url_response = fetch_url(update_date_url, headers=headers)
    update_date = datetime.strptime(update_date_url_response.text, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")

    #update_date = datetime.strptime(update_date_url_response.text,"%m/%d/%Y %H:%M:%S").strftime("%Y-%m-%d") #"%m/%d/%Y %H:%M:%S"

    # Get update data
    url = base_url+DASHBOARD_DATA_FILE

    url_response = fetch_url(url, headers=headers)
    df = pd.read_csv(io.StringIO(url_response.text))

    df['virus'] = [abbreviate_virus(v) for v in df['virus']]
    epiw =  df.apply(lambda x: Week(x['year'],x['week']),axis=1)
    df.insert(0,"epiweek",[int(str(w)) for w in epiw])
    df['epiweek'] = [int(str(w)) for w in df['epiweek']]
    df['province'] = [abbreviate_geo(g) for g in df['province']]
    df=df.rename(columns={'province':"geo_value",'date':'time_value',"detections":"positivetests"})
    df['time_value'] = [check_date_format(d) for d in df['time_value']]
    df['geo_type'] = [create_geo_types(g,"province") for g in df['geo_value']]
    df.insert(1,"issue",update_date)

    df=df.drop(["weekorder","region","year","week"],axis=1)

    df = df.pivot(index=['epiweek','time_value','issue','geo_type','geo_value'],
                  columns="virus",values=['tests','percentpositive','positivetests'])
    df.columns = ['_'.join(col).strip() for col in df.columns.values]
    df = df.rename(columns=lambda x: '_'.join(x.split('_')[1:]+x.split('_')[:1]))
    df.columns=[re.sub("positivetests", "positive_tests",col) for col in df.columns]
    df.columns=[re.sub("percentpositive", "pct_positive",col) for col in df.columns]
    df.columns=[re.sub(r' ','_',c) for c in df.columns]

    for k in range(len(df.columns)):
        if "pct_positive" in df.columns[k]:
            assert all([0 <= val <= 100 or math.isnan(val) for val in  df[df.columns[k]]]), "Percentage not from 0-100"

    return(df)

def get_weekly_data(base_url,start_year):
    headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    }

    # Get update date
    update_date_url =  base_url + "RVD_UpdateDate.csv"
    update_date_url_response = fetch_url(update_date_url, headers=headers)
    update_date = datetime.strptime(update_date_url_response.text,"%m/%d/%Y %H:%M:%S").strftime("%Y-%m-%d")

    # Get current week and year
    summary_url =  base_url + "RVD_SummaryText.csv"
    summary_url_response = fetch_url(summary_url, headers=headers)
    summary_df = pd.read_csv(io.StringIO(summary_url_response.text))

    week_df = summary_df[(summary_df['Section'] == "summary") & (summary_df['Type']=="title")]
    week_string = week_df.iloc[0]['Text'].lower()
    current_week = int(re.search("week (.+?) ", week_string).group(1))

    if current_week < LAST_WEEK_OF_YEAR:
        current_year = start_year+1
    else:
        current_year = start_year

    current_epiweek= Week(current_year,current_week)

    # Get weekly data
    weekly_url = base_url + "RVD_CurrentWeekTable.csv"
    weekly_url_response = fetch_url(weekly_url, headers=headers)
    weekly_url_response.encoding='UTF-8'
    df_weekly = pd.read_csv(io.StringIO(weekly_url_response.text))

    df_weekly = df_weekly.rename(columns=lambda x: '_'.join(x.split('_')[1:]+x.split('_')[:1]))
    df_weekly.insert(0,"epiweek",int(str(current_epiweek)))
    df_weekly.insert(1,"time_value",str(current_epiweek.enddate()))
    df_weekly.insert(2,"issue",update_date)
    df_weekly.columns=[abbreviate_virus(c) for c in df_weekly.columns]
    df_weekly.columns=[re.sub(r'test\b','tests',c) for c in df_weekly.columns]
    df_weekly.columns=[re.sub(r'pos\b','positive_tests',c) for c in df_weekly.columns]
    df_weekly.columns=[re.sub(r'flua_','flu_a',c) for c in df_weekly.columns]
    df_weekly.columns=[re.sub(r'flub_','flu_b',c) for c in df_weekly.columns]
    df_weekly.columns=[re.sub(r'bpositive','b_positive',c) for c in df_weekly.columns]
    df_weekly.columns=[re.sub(r'apositive','a_positive',c) for c in df_weekly.columns]
    df_weekly.columns=[re.sub(r'flu_ah1_','flu_ah1pdm09_',c) for c in df_weekly.columns]
    df_weekly.columns=[re.sub(r' ','_',c) for c in df_weekly.columns]
    df_weekly=df_weekly.rename(columns={'reportinglaboratory':"geo_value"})
    df_weekly['geo_value'] = [abbreviate_geo(g) for g in df_weekly['geo_value']]
    df_weekly['geo_type'] = [create_geo_types(g,"lab") for g in df_weekly['geo_value']]

    #if df_weekly.columns.isin(["weekorder","date","week"]).all():
    df_weekly=df_weekly.drop(["weekorder","date","week"],axis=1)

    return(df_weekly)

def get_report_season_years(soup):
    """Get the start year of the season and the year the season ends """
    # Find the url in the page html and get the years included in the season
    canonical_url = str(soup.find_all('link',rel="canonical"))
    # The season range is in YYYY-YYYY format
    matches = re.search("20[0-9]{2}-20[0-9]{2}",canonical_url)
    #print(matches)
    if matches:
        season = matches.group(0)
    years=season.split("-")
    return(years)

def add_https_prefix(urls):
    """ Add https to urls, and changes any http to https"""
    for i in range(len(urls)):
        temp_url = urls[i]

        http_present = re.search("http:",temp_url)
        if not http_present:
            urls[i]=SEASON_BASE_URL+temp_url
        else:
            urls[i]=re.sub("http:","https:",temp_url)
    return(urls)

def construct_weekly_report_urls(soup):
    """ Construct links for each week in a season"""
    year= "-".join(get_report_season_years(soup))
    links=soup.find_all('a')
    alternative_url = ALTERNATIVE_SEASON_BASE_URL+year

    urls = [link.get("href") for link in links if "ending" in str(link) or
            alternative_url in str(link)]

    report_links = add_https_prefix(urls)
    return(report_links)

def report_weeks(soup):
    """ Get a list of all the weeks in a season"""
    links=soup.find_all('a')
    full_weeks = [link.text for link in links if "Week" in str(link)]
    weeks= [int(re.search('Week (.+?) ', week).group(1)) for week in full_weeks]
    return(weeks)

def get_report_date(week,start_year,epi=False):
    """
    Get the end date of the current reporting/epiweek

    week - the epidemiological week number
    start_year - the year the season starts in
    epi - if True, return the date in cdc format (yearweek)

    """
    if week < LAST_WEEK_OF_YEAR:
        year=int(start_year)+1
    else:
        year=int(start_year)

    epi_week =  Week(year, week)

    if not epi:
        report_date = str(epi_week.enddate())
    else:
        report_date =  str(epi_week)

    return(report_date)

def extract_captions_of_interest(soup):
    """
    finds all the table captions for the current week so tables can be identified

    The captions from the 'summary' tag require less parsing, but sometimes they
    are missing. In that case, use the figure captions
    """
    captions = soup.findAll('summary')

    table_identifiers = ["respiratory","number","positive","abbreviation"]

    # For every caption, check if all of the table identifiers are missing. If they are,
    # this means the caption is noninformative (i.e just says Figure 1). If any of the captions are
    # noninformative, use the figure captions as captions
    if sum([all(name not in cap.text.lower() for name in table_identifiers) for cap in captions]) != 0:
        figcaptions = soup.findAll('figcaption')
        captions = captions + figcaptions

    remove_list=[]
    for i in range(len(captions)):
        caption = captions[i]

        matches = ["period","abbreviation","cumulative", "compared"] #skip historic comparisons and cumulative tables
        # remove any captions with a class or that are uninformative
        if any(x in caption.text.lower() for x in matches) or caption.has_attr('class') or all(name not in caption.text.lower() for name in table_identifiers):
            remove_list.append(caption)

    new_captions = [cap for cap in captions if cap not in remove_list]
    new_captions = list(set(new_captions))

    return(new_captions)

def get_modified_dates(soup,week_end_date):
    """
    Get the date the report page was modfified

    Reports include both posted dates and modified dates. Fairly often on
    historical data reports, posted date falls before the end of the week
    being reported on. Then the page is modified later, presumably with
    updated full-week data. Therefore, we use the modified date as the issue
    date for a given report.
    """
    meta_tags=soup.find_all("meta",title="W3CDTF")
    for tag in meta_tags:
        if tag.get("name", None) == "dcterms.modified" or tag.get("property", None) == "dcterms.modified":
            modified_date = tag.get("content", None)

    mod_date = datetime.strptime(modified_date, "%Y-%m-%d")
    week_date = datetime.strptime(week_end_date, "%Y-%m-%d")

    diff_days = (mod_date-week_date).days

    # Manually create a new modified date if the existing one is too long after the week.
    # Historically, we commonly see data reports being modified ~5 days after
    # the end of the week being reported on. In some cases, though, the
    # modified date falls a long time (up to a year) after the end of the
    # week being reported on. We expect that any changes made to the report
    # at that point were primarily wording, and not data, changes. So if the
    # modified date is NOT within 0-14 days after the end of the week, set
    # the issue date to be 5 days after the end of the week.
    if diff_days > 0 and diff_days < 14:
        new_modified_date = mod_date
    else:
        new_lag = timedelta(days=5)
        new_modified_date = week_date + new_lag

    new_modified_date_string = new_modified_date.strftime("%Y-%m-%d")

    return(new_modified_date_string)

def deduplicate_rows(table):
    """
    Sometimes tables have more than one row for the same week
    In that case, keep the row that has the highest canada tests
    (i.e drop the rows with the lower counts)
    """
    if table['week'].duplicated().any():
       duplicated_rows = table[table.duplicated('week',keep=False)]
       grouped = duplicated_rows.groupby("week")
       duplicates_drop = []

       for name, group in grouped:
           duplicates_drop.append(group['can tests'].idxmin())

       new_table = table.drop(duplicates_drop).reset_index(drop=True)

    else:
        new_table=table
    return(new_table)

def add_flu_prefix(flu_subtype):
    """ Add the prefix `flu` when only the subtype is reported """

    pat1 =r"^ah3"
    pat2= r"^auns"
    pat3= r"^ah1pdm09"
    pat4= r"^ah1n1pdm09"
    combined_pat = '|'.join((pat1, pat2,pat3,pat4))

    full_fluname = re.sub(combined_pat, r"flu\g<0>",flu_subtype)
    return(full_fluname)

def make_signal_type_spelling_consistent(signal):
    """
    Make the signal type (i.e. percent positive, number tests, total tests) have consistent spelling
    Also remove total from signal names
    """

    pat1 = "positive"
    pat2 = 'pos'
    combined_pat = '|'.join((pat1, pat2))

    pat3 = r"test\b"
    pat4 = 'tested'
    combined_pat2 = '|'.join((pat3, pat4))

    new_signal = re.sub(combined_pat, "positive_tests",signal)
    new_signal = re.sub(combined_pat2, "positive_tests",signal)
    new_signal = re.sub("total ", "",signal)
    return(new_signal)

def preprocess_table_columns(table):
    """
    Remove characters like . or * from columns
    Abbreviate the viruses in columns
    Change some naming of signals in columns (i.e order of hpiv and other)
    Change some naming of locations in columns (i.e at instead of atl)
    """
    table.columns = [re.sub("\xa0"," ", col) for col in table.columns] # \xa0 to space
    table.columns = [re.sub("(.*?)(\.\d+)", "\\1", c) for c in table.columns] # remove .# for duplicated columns
    table.columns =[re.sub("\.", "", s)for s in table.columns] #remove periods
    table.columns =[re.sub(r"\((all)\)", "", s)for s in table.columns] # remove (all)
    table.columns =[re.sub(r"\s*\(|\)", "", s)for s in table.columns]
    table.columns = [re.sub(' +', ' ', col) for col in table.columns] # Make any muliple spaces into one space
    table.columns = [re.sub(r'\(|\)', '', col) for col in table.columns] # replace () for _
    table.columns = [re.sub(r'/', '_', col) for col in table.columns] # replace / with _

    table.columns = [re.sub(r"^at\b","atl ",t) for t in table.columns]
    table.columns = [re.sub("canada","can",t) for t in table.columns]

    table.columns =[re.sub(r"h1n1 2009 |h1n12009", "ah1n1pdm09", s)for s in table.columns]
    table.columns =[abbreviate_virus(col) for col in table.columns] # abbreviate viruses
    table.columns = [re.sub(r"flu a","flua",t) for t in table.columns]
    table.columns = [re.sub(r"flu b","flub",t) for t in table.columns]
    table.columns = [re.sub("flutest","flu test", col) for col in table.columns]
    table.columns = [re.sub(r"other hpiv","hpivother",t) for t in table.columns]

    return(table)

def create_detections_table(table,modified_date,week_number,week_end_date,start_year):
    lab_columns =[col for col in table.columns if 'reporting' in col][0]
    table=table.rename(columns={lab_columns:"geo_value"})
    table['geo_value']=table['geo_value'].str.lower()

    if start_year==2016 and week_number==3:
        table["geo_value"]=[re.sub("^province of$","alberta",c) for c in table["geo_value"]]

    # make naming consistent
    table.columns=[make_signal_type_spelling_consistent(col) for col in table.columns]
    table.columns=[add_flu_prefix(col) for col in table.columns]
    matches=['test','geo_value']

    new_names = []
    for i in range(len(table.columns)):
        if not any(x in table.columns[i] for x in matches):
            new_names.append(table.columns[i]+ " positive_tests")
        else:
            new_names.append(table.columns[i])

    table.columns=new_names

    # remove any underscores or spaces from virus names
    table.columns=[re.sub(" positive","_positive",t) for t in table.columns]
    table.columns=[re.sub(" tests","_tests",t) for t in table.columns]
    table.columns=[re.sub(" ","",t) for t in table.columns]

    table['geo_value'] = [abbreviate_geo(g) for g in table['geo_value']]
    geo_types = [create_geo_types(g,"lab") for g in table['geo_value']]

    table = table.assign(**{'epiweek': get_report_date(week_number, start_year,epi=True),
                    'time_value': week_end_date,
                    'issue': modified_date,
                    'geo_type':geo_types})

    table.columns =[re.sub(" ","_",col) for col in table.columns]
    return(table)

def create_number_detections_table(table,modified_date,start_year):
    week_columns = table.columns.get_indexer(table.columns[~table.columns.str.contains('week')])

    for index in week_columns:
        new_name = abbreviate_virus(table.columns[index]) + " positive_tests"
        table.rename(columns={table.columns[index]: new_name}, inplace=True)

    if "week end" not in table.columns:
        week_ends = [get_report_date(week,start_year) for week in table["week"]]
        table.insert(1,"week end",week_ends)

    table = table.assign(**{'issue': modified_date,
                    'geo_type': "nation",
                    'geo_value': "ca"})

    table=table.rename(columns={'week end':"time_value"})
    table.columns =[re.sub(" ","_",col) for col in table.columns]
    table['time_value'] = [check_date_format(d) for d in table['time_value']]

    table=table.rename(columns={'week':"epiweek"})
    table['epiweek'] = [get_report_date(week, start_year,epi=True) for week in table['epiweek']]
    return(table)

def create_pct_positive_col(df, viruses):
    """
    This function creates '_pct_positive' columns in the DataFrame for each virus 
    based on the corresponding '_positive_tests' and '_tests' columns.
    
    Parameters:
    df (pd.DataFrame): The DataFrame to modify.
    viruses (list): List of virus names to create the percentage columns for.
    
    Returns:
    pd.DataFrame: The modified DataFrame with new '_pct_positive' columns.
    """
    for virus in viruses:
        positive_column = f"{virus}_positive_tests"
        tests_column = f"{virus}_tests"
        pct_column = f"{virus}_pct_positive"

        # Ensure both positive tests and total tests columns exist
        if positive_column in df.columns and tests_column in df.columns:
             df[positive_column] = pd.to_numeric(df[positive_column], errors='coerce')
             df[tests_column] = pd.to_numeric(df[tests_column], errors='coerce')
            # Calculate the percentage and handle division by zero
             df[pct_column] = df.apply(
                lambda row: (row[positive_column] / row[tests_column] * 100) if row[tests_column] != 0 else 0,
                axis=1
            )
    
    return df

def create_percent_positive_detection_table(table,modified_date,start_year, flu=False,overwrite_weeks=False):
    table = deduplicate_rows(table)
    table.columns=[re.sub(" *%", "_pct_positive",col) for col in table.columns]
    table.columns = [re.sub(' +', ' ',col) for col in table.columns]
    table.insert(2,"issue",modified_date)
    table=table.rename(columns={'week end':"time_value"})
    table['time_value'] = [check_date_format(d) for d in table['time_value']]

    # get the name of the virus for the table to append to column names
    virus_prefix=[]
    if flu:
        virus_prefix=['flua_pct_positive','flub_pct_positive']
        virus="flu"
        table.columns=[re.sub("a_pct","flua_pct",c) for c in table.columns]
        table.columns=[re.sub("b_pct","flub_pct",c) for c in table.columns]
    else:
        names=[]
        for j in range(len(table.columns)):
            old_name = table.columns[j]
            if "pct_positive" in table.columns[j]:
                virus_prefix=[table.columns[j]]
                virus=re.match("(.*?)_pct_positive",old_name).group(1)
                geo = table.columns[j-1].split(" ")[0]
                new_name = geo + " " + old_name
            else:
                new_name=old_name
            names.append(new_name)
        table.columns=names

    # Remake the weeks column from dates
    if overwrite_weeks:
        week_ends = [datetime.strptime(date_string, "%Y-%m-%d") for date_string in table['time_value']]
        table["week"] = [Week.fromdate(d).week for d in week_ends]

    # Change order of column names so tthey start with stubbnames
    table  = table.rename(columns=lambda x: ' '.join(x.split(' ')[::-1])) #
    stubnames= virus_prefix+['tests']
    table= pd.wide_to_long(table, stubnames, i=['week','time_value','issue'],
                           j='geo_value', sep=" ", suffix=r'\w+').reset_index()

    table.columns=[re.sub("tests",virus+"_tests",c) for c in table.columns]
    table.columns =[re.sub(" ","_",col) for col in table.columns]

    table=table.rename(columns={'week':"epiweek"})
    table['epiweek'] = [get_report_date(week, start_year,epi=True) for week in table['epiweek']]

    table['geo_value']= [abbreviate_geo(g) for g in table['geo_value']]
    geo_types = [create_geo_types(g,"lab") for g in table['geo_value']]
    table.insert(3,"geo_type",geo_types)

    # Calculate number of positive tests based on pct_positive and total tests
    if flu:
        table["flua_positive_tests"] = (table["flua_pct_positive"]/100)*table["flu_tests"]
        table["flub_positive_tests"] = (table["flub_pct_positive"]/100)*table["flu_tests"]

        table["flu_positive_tests"] =  table["flua_positive_tests"] +  table["flub_positive_tests"]
        table["flu_pct_positive"] =   (table["flu_positive_tests"]/table["flu_tests"])*100
    else:
        table[virus+"_positive_tests"] = (table[virus+"_pct_positive"]/100) *table[virus+"_tests"]

    table = table.set_index(['epiweek', 'time_value', 'issue', 'geo_type', 'geo_value'])

    return(table)

def create_hpiv_positive_tests(df):
    """
    This function creates the 'hpiv_positive_tests' column by summing all columns 
    that represent HPIV (Human Parainfluenza Virus) positive tests. It uses regex 
    to identify columns related to HPIV positive tests.
    
    Parameters:
    df (pd.DataFrame): The DataFrame to modify.

    Returns:
    pd.DataFrame: The modified DataFrame with the new 'hpiv_positive_tests' column.
    """
    # Regular expression pattern to identify columns related to hpiv positive tests
    hpiv_pattern = re.compile(r'hpiv\d*.*positive_tests', re.IGNORECASE)
    
    # Find all columns that match the hpiv pattern
    hpiv_columns = [col for col in df.columns if hpiv_pattern.search(col)]
    
    if hpiv_columns:
        # Sum the relevant hpiv columns to create the 'hpiv_positive_tests' column
        df['hpiv_positive_tests'] = df[hpiv_columns].sum(axis=1)
        
        # Optionally, drop the original columns if desired
        df = df.drop(columns=hpiv_columns)
    
    return df

def rename_and_merge_duplicate_columns(df):
    """
    Detect and rename duplicated columns in the DataFrame by appending '_dup' 
    or '_dup2', '_dup3', etc., then merge the columns by keeping non-null values.
    
    Parameters:
    df (pd.DataFrame): The DataFrame with possible duplicated columns.
    
    Returns:
    pd.DataFrame: The DataFrame with renamed and merged columns.
    """
    # Track how many times a column name has appeared
    cols_seen = {}

    # Step 1: Rename duplicated columns with suffixes like '_dup', '_dup2', etc.
    new_columns = []
    for col in df.columns:
        if col in cols_seen:
            # If the column name is duplicated, append a suffix
            cols_seen[col] += 1
            new_col_name = f"{col}_dup{cols_seen[col]}"
        else:
            cols_seen[col] = 0
            new_col_name = col
        new_columns.append(new_col_name)

    # Rename the columns in the DataFrame
    df.columns = new_columns

    # Step 2: Merge columns with the same base name
    base_columns = set([col.split('_dup')[0] for col in new_columns])

    for base_col in base_columns:
        # Find all columns that share the same base name (e.g., 'flu_tests', 'flu_tests_dup')
        matching_cols = [col for col in df.columns if col.startswith(base_col)]
        
        # Merge by keeping the first non-null value across matching columns
        if len(matching_cols) > 1:
            df[base_col] = df[matching_cols].bfill(axis=1).iloc[:, 0]
            
            # Drop the extra columns after merging
            df.drop(columns=matching_cols[1:], inplace=True)

    return df

def process_tables(all_respiratory_detection_table, all_positive_tables, COL_MAPPERS, viruses):
    # Step 1: Rename columns in both tables using COL_MAPPERS
    all_respiratory_detection_table = all_respiratory_detection_table.rename(columns=COL_MAPPERS)
    all_positive_tables = all_positive_tables.rename(columns=COL_MAPPERS)

    # Drop 'flu_a_tests' and 'flu_b_tests' columns if they exist
    all_respiratory_detection_table = all_respiratory_detection_table.drop(columns=['flu_a_tests', 'flu_b_tests'], errors='ignore')
    all_positive_tables = all_positive_tables.drop(columns=['flu_a_tests', 'flu_b_tests'], errors='ignore')

    # Step 2: Create hpiv_positive_tests by summing relevant columns
    all_respiratory_detection_table = create_hpiv_positive_tests(all_respiratory_detection_table)

    # Step 3: Drop columns that contain the substrings 'fluah1', 'fluah3', or 'fluauns'
    all_respiratory_detection_table = all_respiratory_detection_table.drop(
        columns=all_respiratory_detection_table.filter(regex=r'fluah1|fluah3|fluauns').columns
    )

    all_positive_tables = all_positive_tables.drop(
        columns=all_positive_tables.filter(regex=r'fluah1|fluah3|fluauns').columns
    )
    all_respiratory_detection_table = all_respiratory_detection_table.drop(
        columns=all_respiratory_detection_table.filter(regex=r'flu_ah1|flu_ah3|flu_auns').columns
    )

    all_positive_tables = all_positive_tables.drop(
        columns=all_positive_tables.filter(regex=r'flu_ah1|flu_ah3|flu_auns').columns
    )
    # Step 4: Rename and merge duplicate columns in both tables
    all_respiratory_detection_table = rename_and_merge_duplicate_columns(all_respiratory_detection_table)
    all_positive_tables = rename_and_merge_duplicate_columns(all_positive_tables)

    # Step 5: Convert 'flu_tests' to numeric
    all_respiratory_detection_table['flu_tests'] = pd.to_numeric(all_respiratory_detection_table['flu_tests'], errors='coerce')

    # Step 6: Sum 'flua_positive_tests' and 'flub_positive_tests' to create 'flu_positive_tests'
    all_respiratory_detection_table['flu_positive_tests'] = (
        all_respiratory_detection_table['flua_positive_tests'] + all_respiratory_detection_table['flub_positive_tests']
    )

    # Step 7: Create percentage columns for various viruses
    all_respiratory_detection_table = create_pct_positive_col(all_respiratory_detection_table, viruses)

    # Step 8: Ensure 'flua_positive_tests' and 'flub_positive_tests' are numeric
    all_respiratory_detection_table['flua_positive_tests'] = pd.to_numeric(all_respiratory_detection_table['flua_positive_tests'], errors='coerce')
    all_respiratory_detection_table['flub_positive_tests'] = pd.to_numeric(all_respiratory_detection_table['flub_positive_tests'], errors='coerce')

    # Step 9: Create 'flua_pct_positive' as (flua_positive_tests / flu_tests) * 100
    all_respiratory_detection_table['flua_pct_positive'] = all_respiratory_detection_table.apply(
        lambda row: (row['flua_positive_tests'] / row['flu_tests'] * 100) if row['flu_tests'] != 0 else 0, axis=1
    )

    # Step 10: Create 'flub_pct_positive' as (flub_positive_tests / flu_tests) * 100
    all_respiratory_detection_table['flub_pct_positive'] = all_respiratory_detection_table.apply(
        lambda row: (row['flub_positive_tests'] / row['flu_tests'] * 100) if row['flu_tests'] != 0 else 0, axis=1
    )

    return all_respiratory_detection_table, all_positive_tables

def get_season_reports(url):
    # From the url, go to the main landing page for a season
    # which contains all the links to each week in the season
    page=fetch_url(url)
    soup=BeautifulSoup(page.text,'html.parser')

    # get season, week numbers, urls and week ends
    season = get_report_season_years(soup)
    urls=construct_weekly_report_urls(soup)
    weeks= report_weeks(soup)
    end_dates = [get_report_date(week, season[0]) for week in weeks]

    # create tables to hold all the data for the season
    all_positive_tables=pd.DataFrame()
    all_number_tables=pd.DataFrame()
    all_respiratory_detection_table=pd.DataFrame()

    for week_num in range(len(urls)):
        current_week = weeks[week_num]
        current_week_end = end_dates[week_num]

        # In the 2019=2020 season, the webpages for weeks 5 and 47 only have
        # the abbreviations table and the headers for the respiratory detections
        # table, so they are effectively empty, and skipped
        if season[0] == '2019':
            if current_week == 5 or current_week == 47:
                continue

        # Get page for the current week
        temp_url=urls[week_num]
        temp_page=fetch_url(temp_url)
        new_soup = BeautifulSoup(temp_page.text, 'html.parser')
        captions = extract_captions_of_interest(new_soup)
        modified_date = get_modified_dates(new_soup,current_week_end)

        positive_tables=[]
        number_table_exists = False
        for i in range(len(captions)):
            caption=captions[i]
            tab = caption.find_next('table')

            # Remove footers from tables so the text isn't read in as a table row
            if tab.find('tfoot'):
                tab.tfoot.decompose()

            # In the positive adenovirus table in week 35 of the 2019-2020 season
            # The week number has been duplicated, which makes all the entries in the table
            # are one column to the right of where they should be. To fix this the
            # entry in the table (which is the first "td" element in the html) is deleted
            if season[0] == '2019' and current_week == 35:
                if "Positive Adenovirus" in caption.text:
                    tab.select_one('td').decompose()

            # Replace commas with periods
            # Some "number of detections" tables have number with commas (i.e 1,000)
            # In this case the commas must be deleted, otherwise turn into periods
            # because some tables have commas instead of decimal points
            if "number" not in caption.text.lower():
                tab = re.sub(",",r".",str(tab))
            else:
                tab = re.sub(",","",str(tab))

            # Read table, coding all the abbreviations for missing data into NA
            # Also use dropna because removing footers causes the html to have an empty row
            na_values = ['N.A.','N.A', 'N.C.','N.R.','Not Available','Not Tested',"N.D.","-"]
            table =  pd.read_html(tab,na_values=na_values)[0].dropna(how="all")

            # Check for multiline headers
            # If there are any, combine them into a single line header
            if isinstance(table.columns, pd.MultiIndex):
                table.columns = [c[0] + " " + c[1] if c[0] != c[1] else c[0] for c in table.columns]

            # Make column names lowercase
            table.columns=table.columns.str.lower()

            # One-off edge cases where tables need to be manually adjusted because
            # they will cause errors otherwise
            if season[0] == '2017':
                if current_week == 35 and "entero" in caption.text.lower():
                    # The positive enterovirus table in week 35 of the 2017-2018 season has french
                    # in the headers,so the french needs to be removed
                    table.columns = ['week', 'week end', 'canada tests', 'entero/rhino%', 'at tests',
                       'entero/rhino%.1', 'qc tests', 'entero/rhino%.2', 'on tests',
                       'entero/rhino%.3', 'pr tests', 'entero/rhino%.4', 'bc tests',
                       'entero/rhino%.5']
                elif current_week == 35 and "adeno" in caption.text.lower():
                    # In week 35 of the 2017-2018, the positive adenovirus table has ">week end"
                    # instead of "week end", so remove > from the column
                    table = table.rename(columns={'>week end':"week end"})
                elif current_week == 47 and "rsv" in caption.text.lower():
                    #  In week 47 of the 2017-2018 season, a date is written as 201-11-25,
                    #  instead of 2017-11-25
                    table.loc[table['week'] == 47, 'week end'] = "2017-11-25"
            elif season[0] == '2015' and current_week == 41:
                # In week 41 of the 2015-2016 season, a date written in m-d-y format not d-m-y
                table=table.replace("10-17-2015","17-10-2015",regex=True)
            elif season[0] == '2022' and current_week == 11 and "hmpv" in caption.text.lower():
                #  In week 11 of the 2022-2023 season, in the positive hmpv table,
                # a date is written as 022-09-03, instead of 2022-09-03
                 table.loc[table['week'] == 35, 'week end'] = "2022-09-03"

            # Rename columns
            table= preprocess_table_columns(table)

            # If "reporting laboratory" is one of the columns of the table, the table must be
            # the "Respiratory virus detections " table for a given week
            # this is the lab level table that has weekly positive tests for each virus, with no revisions
            # and each row represents a lab

            # If "number" is in the table caption, the table must be the
            # "Number of positive respiratory detections" table, for a given week
            # this is a national level table, reporting the number of detections for each virus,
            # this table has revisions, so each row is a week in the season, with weeks going from the
            # start of the season up to and including the current week

            # If "positive" is in the table caption, the table must be one of the
            # "Positive [virus] Tests (%)" table, for a given week
            # This is a region level table, reporting the total tests and percent positive tests  for each virus,
            # this table has revisions, so each row is a week in the season, with weeks going from the
            # start of the season up to and including the current week
            # The columns have the region information (i.e Pr tests, meaning this columns has the tests for the prairies)

            if "reporting laboratory" in str(table.columns):
               respiratory_detection_table = create_detections_table(table,modified_date,current_week,current_week_end,season[0])
               respiratory_detection_table = respiratory_detection_table.set_index(['epiweek', 'time_value', 'issue', 'geo_type', 'geo_value'])
            elif "number" in caption.text.lower():
               number_table_exists = True
               number_detections_table = create_number_detections_table(table,modified_date,season[0])
               number_detections_table = number_detections_table.set_index(['epiweek', 'time_value', 'issue', 'geo_type', 'geo_value'])
            elif "positive" in caption.text.lower():
               flu = " influenza" in caption.text.lower()

               # tables are missing week 53
               # In the 2014-2015 season the year ends at week 53 before starting at week 1 again.
               # weeks 53,2 and 3 skip week 53 in the positive detection tables, going from 52 to 1,
               # this means the week numbers following 52 are 1 larger then they should be
               # fix this by overwriting the week number columns

               missing_week_53 = [53,2,3]
               if season[0]=="2014" and current_week in missing_week_53:
                   overwrite_weeks=True
               else:
                   overwrite_weeks=False

               pos_table = create_percent_positive_detection_table(table,modified_date,season[0],flu,overwrite_weeks)

               # Check for percentages >100
               # One in 2014-2015 week 39, left in
               if season[0] != '2014' and current_week != 39:
                   for k in range(len(pos_table.columns)):
                       if "pct_positive" in pos_table.columns[k]:
                           assert all([0 <= val <= 100 or math.isnan(val) for val in  pos_table[pos_table.columns[k]]]), "Percentage not from 0-100"

               positive_tables.append(pos_table)

        # combine all the positive tables
        combined_positive_tables=pd.concat(positive_tables,axis=1)

        # Check if the indices are already in the season table
        # If not, add the weeks tables into the season table
        if not respiratory_detection_table.index.isin(all_respiratory_detection_table.index).any():
            all_respiratory_detection_table= pd.concat([all_respiratory_detection_table,respiratory_detection_table])

        if not combined_positive_tables.index.isin(all_positive_tables.index).any():
            all_positive_tables=pd.concat([all_positive_tables,combined_positive_tables])

        if number_table_exists:
            if not number_detections_table.index.isin(all_number_tables.index).any():
                all_number_tables=pd.concat([all_number_tables,number_detections_table])

    viruses = ['hcov', 'hmpv', 'sarscov2', 'rsv', 'hpiv', 'flu', 'adv', 'ev_rv']
    all_respiratory_detection_table, all_positive_tables = process_tables( all_respiratory_detection_table, all_positive_tables, 
                                                                          COL_MAPPERS, viruses)


    # write files to csvs
            # create path to save files
    if season[0] != 2025:
        path = "./auxiliary-data/target-data-archive/season_" + season[0]+"_"+season[1]
        path_aux  = path
    else:
        path = "./target-data/season_" + season[0]+"_"+season[1]
        path_aux = "./auxiliary-data/season_" + season[0]+"_"+season[1]
        if not os.path.exists(path_aux):
            os.makedirs(path_aux)
        

    if not os.path.exists(path):
        os.makedirs(path)

    all_respiratory_detection_table.to_csv(path_aux+"/" + RESP_COUNTS_OUTPUT_FILE, index=True)
    all_positive_tables.to_csv(path_aux+"/" + POSITIVE_TESTS_OUTPUT_FILE, index=True)

	# Merge repiratory_detection and positive_test files
    concatenated_table = pd.concat([all_respiratory_detection_table, all_positive_tables], axis=0)
    concatenated_table = concatenated_table.reset_index()
	
    concatenated_table = concatenated_table[concatenated_table['geo_value'].isin(LOC_CORRECTION.keys())]
    concatenated_table['geo_type'] = concatenated_table['geo_value'].map(LOC_CORRECTION)

    concatenated_table['issue'] = pd.to_datetime(concatenated_table['issue'])
    concatenated_table = concatenated_table.groupby(['time_value', 'geo_type', 'geo_value']).apply(lambda x: x.bfill()).sort_values(by='issue', ascending=False)
    concatenated_table = concatenated_table.drop_duplicates(subset=['time_value', 'geo_type', 'geo_value'], keep='first')

    concatenated_table = concatenated_table.drop(columns=['issue'], errors='ignore')
    concatenated_table = concatenated_table.drop(columns=['epiweek'], errors='ignore')

    #concatenated_table = concatenated_table.drop(columns=[col for col in concatenated_table.columns if 'pct_positive' in col])
    #concatenated_table.to_csv(path+"/" + 'raw.csv', index=False)
    
    for col in concatenated_table.columns:   
        if col not in COLUMNS_TARGET:
            concatenated_table = concatenated_table.drop(columns=[col])
        elif 'pct_positive' in col:
            # Round percentage columns to 2 decimal places
            concatenated_table[col] = concatenated_table[col].round(2)

    concatenated_table.to_csv(path+"/" + 'target_rvdss_data.csv', index=False)

    HISTORIC_SEASON_URL_CHECKPOINT.append(url)

def main():
    max_retries=3
    retries = 0
    while retries < max_retries:
        try:
            # Suppress all warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=FutureWarning)
                warnings.simplefilter("ignore", category=DeprecationWarning)
                # Check if previous seasons' lab data exists
                if os.path.exists('./auxiliary-data/target-data-archive/season_2024_2025/target_rvdss_data.csv')==False:
                    [get_season_reports(url) for url in HISTORIC_SEASON_URL if url not in HISTORIC_SEASON_URL_CHECKPOINT]
            break
        except requests.exceptions.RequestException as e:
            # Handle specific connection errors
            print(f"Connection error while accessing url: {e}")
            
            retries += 1
            if retries < max_retries:
                print(f"Retrying... (Attempt {retries}/{max_retries})")
            else:
                print(f"Max retries reached.")
                raise


	# Check if the directory exists, and if not, create it
    directory = './target-data/season_2025_2026/'
    if not os.path.exists(directory):
        os.makedirs(directory)


    def get_weekly_data2(base_url,start_year):
        headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        }

        # Get update date
        update_date_url =  base_url + "RVD_UpdateDate.csv"
        update_date_url_response = fetch_url(update_date_url, headers=headers)
        #print(update_date_url_response.text)
        update_date = datetime.strptime(update_date_url_response.text, "%Y-%m-%d %H:%M:%S")

        #update_date = datetime.strptime(update_date_url_response.text,"%m/%d/%Y %H:%M:%S").strftime("%Y-%m-%d")

        # Get current week and year
        summary_url =  base_url + "RVD_SummaryText.csv"
        summary_url_response = fetch_url(summary_url, headers=headers)
        summary_df = pd.read_csv(io.StringIO(summary_url_response.text))

        week_df = summary_df[(summary_df['Section'] == "summary") & (summary_df['Type']=="title")]
        week_string = week_df.iloc[0]['Text'].lower()
        current_week = int(re.search("week (.+?) ", week_string).group(1))

        if current_week < LAST_WEEK_OF_YEAR:
            current_year = start_year+1
        else:
            current_year = start_year

        current_epiweek= Week(current_year,current_week)

        # Get weekly data
        weekly_url = base_url + "RVD_CurrentWeekTable.csv"
        weekly_url_response = fetch_url(weekly_url, headers=headers)
        weekly_url_response.encoding='UTF-8'
        df_weekly = pd.read_csv(io.StringIO(weekly_url_response.text))

        df_weekly = df_weekly.rename(columns=lambda x: '_'.join(x.split('_')[1:]+x.split('_')[:1]))
        df_weekly.insert(0,"epiweek",int(str(current_epiweek)))
        df_weekly.insert(1,"time_value",str(current_epiweek.enddate()))
        df_weekly.insert(2,"issue",update_date)
        df_weekly.columns=[abbreviate_virus(c) for c in df_weekly.columns]
        df_weekly.columns=[re.sub(r'test\b','tests',c) for c in df_weekly.columns]
        df_weekly.columns=[re.sub(r'pos\b','positive_tests',c) for c in df_weekly.columns]
        df_weekly.columns=[re.sub(r'flua_','flu_a',c) for c in df_weekly.columns]
        df_weekly.columns=[re.sub(r'flub_','flu_b',c) for c in df_weekly.columns]
        df_weekly.columns=[re.sub(r'bpositive','b_positive',c) for c in df_weekly.columns]
        df_weekly.columns=[re.sub(r'apositive','a_positive',c) for c in df_weekly.columns]
        df_weekly.columns=[re.sub(r'flu_ah1_','flu_ah1pdm09_',c) for c in df_weekly.columns]
        df_weekly.columns=[re.sub(r' ','_',c) for c in df_weekly.columns]
        df_weekly=df_weekly.rename(columns={'reportinglaboratory':"geo_value"})
        df_weekly['geo_value'] = [abbreviate_geo(g) for g in df_weekly['geo_value']]
        df_weekly['geo_type'] = [create_geo_types(g,"lab") for g in df_weekly['geo_value']]

        df_weekly = df_weekly.drop(columns=['time_value','epiweek'])
        df_weekly = df_weekly.rename(columns={'date':'time_value','week':'epiweek'})
        #print(df_weekly.columns)
        df_weekly['epiweek'] = df_weekly['epiweek'].astype(str)
        df_weekly['epiweek'] = '2025' + df_weekly['epiweek']

        if df_weekly.columns.isin(["weekorder","date","week"]).all():
            df_weekly=df_weekly.drop(["weekorder","date","week"],axis=1)

        return(df_weekly)


    weekly_data = get_weekly_data2(DASHBOARD_BASE_URL,2025).set_index(['epiweek', 'time_value', 'issue', 'geo_type', 'geo_value'])
    positive_data = get_revised_data(DASHBOARD_BASE_URL)
    # print('weekly_data cols:', weekly_data.columns)
    # print('positive_data cols:', positive_data.columns)

    viruses = ['hcov', 'hmpv', 'sarscov2', 'rsv', 'hpiv', 'flu', 'adv', 'ev_rv']
    weekly_data, positive_data = process_tables(weekly_data, positive_data, COL_MAPPERS, viruses)


    path1 = './auxiliary-data/season_2025_2026_raw_files/respiratory_detections.csv'
    path2 = './auxiliary-data/season_2025_2026_raw_files/positive_tests.csv'


    if os.path.exists('./auxiliary-data/season_2025_2026_raw_files/')==False:
        os.makedirs('./auxiliary-data/season_2025_2026_raw_files/')

    if os.path.exists(path1)==False:
        weekly_data.to_csv(path1,index=True)
        old_detection_data = weekly_data
    else:
        old_detection_data = pd.read_csv(path1).set_index(['epiweek', 'time_value', 'issue', 'geo_type', 'geo_value'])
        if weekly_data.index.isin(old_detection_data.index).any() == False:
            old_detection_data= pd.concat([old_detection_data,weekly_data],axis=0)
            old_detection_data.to_csv(path1,index=True)

    if os.path.exists(path2)==False:
        positive_data.to_csv(path2,index=True)
        old_positive_data = positive_data
    else:
        old_positive_data = pd.read_csv(path2).set_index(['epiweek', 'time_value', 'issue', 'geo_type', 'geo_value'])
        if positive_data.index.isin(old_positive_data.index).any() == False:
            old_positive_data= pd.concat([old_positive_data,positive_data],axis=0)
            old_positive_data.to_csv(path2,index=True)

    if os.path.exists(path2) and os.path.exists(path1) ==True:
        concatenated_table = pd.concat([old_detection_data, old_positive_data], axis=0)
    else:
        concatenated_table = pd.concat([weekly_data, positive_data], axis=0)

    
    concatenated_table = concatenated_table.reset_index()
    #print(concatenated_table['issue'])
    concatenated_table['issue'] = pd.to_datetime(concatenated_table['issue'], format='mixed', errors='raise')


    # Update the geo_type based on LOC_CORRECTION values
    concatenated_table = concatenated_table[concatenated_table['geo_value'].isin(LOC_CORRECTION.keys())]
    concatenated_table['geo_type'] = concatenated_table['geo_value'].map(LOC_CORRECTION)

    concatenated_table = concatenated_table.groupby(['time_value', 'geo_type', 'geo_value']).apply(lambda x: x.bfill()).sort_values(by='issue', ascending=False)
    concatenated_table = concatenated_table.drop_duplicates(subset=['time_value', 'geo_type', 'geo_value'], keep='first')

    concatenated_table = concatenated_table.drop(columns=['issue'], errors='ignore') 
    concatenated_table = concatenated_table.drop(columns=['epiweek','week','date','weekorder'], errors='ignore')
    
    #concatenated_table.to_csv('./auxiliary-data/season_2024_2025_raw_files/raw.csv', index=False)
    
    for col in concatenated_table.columns:   
        if col not in COLUMNS_TARGET:
            concatenated_table = concatenated_table.drop(columns=[col])
        elif 'pct_positive' in col:
            # Round percentage columns to 2 decimal places
            concatenated_table[col] = concatenated_table[col].round(2)
	
    concatenated_table = concatenated_table.reset_index(drop=True)
    #print(concatenated_table)
    concatenated_table = concatenated_table.sort_values('time_value', ascending=False)

    concatenated_table.to_csv('./target-data/season_2025_2026/target_rvdss_data.csv', index=False)
   
if __name__ == '__main__':
    main()
