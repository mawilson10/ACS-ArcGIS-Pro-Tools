import arcpy as ap
import pandas as pd
import tempfile
from collections import OrderedDict
import os
import requests
import json
import re

# Developed by the Tennessee Department of Transportation, Long Range Planning Division
# 
# Note: This tool previously relied on the CensusData Python module, which is no longer supported. However, 
#       the module's source code was free to use and modify. Several elements of this script are modified 
#       code from the CensusData module, including the class censusgeo, and functions geographies, _download, 
#       download, and acs_search. More information and a download link for the CensusData module can be found
#       here: https://pypi.org/project/CensusData/


Year = ap.GetParameterAsText(0) # Year (string) # All available years since 2011.
State = ap.GetParameterAsText(1) # Select state of interest (name)
Counties = ap.GetParameterAsText(2) # Semicolon-delimited string containing either counties of interest, or 'All counties'
Geography = ap.GetParameterAsText(3) # Census geography: county, tract, or block group

ACS_Table = ap.GetParameterAsText(6) # Input Table ID, used if entire table is exported ('All fields')
Output_Table = ap.GetParameterAsText(7) # Output feature class containing select population estimates for the designated geography
Select_Fields = ap.GetParameterAsText(8) # Indicates whether all fields from ACS_Table will be exported, or selected fields from one or more tables

Output_Fields = ap.GetParameterAsText(10) # Semicolon-delimited string containing pairs of field IDs and aliases for each selected output field
Margin_of_Error = ap.GetParameterAsText(11) # Checkbox indicating whether or not to include margins of error in the output table

if Counties != "'All counties'":
    Counties = Counties.split(";")

ACS_Table = ACS_Table.split(" ")[0]
Output_Fields = Output_Fields.split(";")


class censusgeo:
    """Class for representing Census geographies.

    Args:
        geo (tuple of 2-tuples of strings): Tuple of 2-tuples of the form (geographic component, identifier), where geographic component is a string (e.g., 'state') and
            identifier is either a numeric code (e.g., '01') or a wildcard ('*'). These identify the geography in question.
        name (str, optional): Name of geography (e.g., 'Alabama').

    """

    #: dict: Census summary level codes for different types of geography
    sumleveldict = {
        'state': '040',
        'state> county': '050',
        'state> county> tract': '140',
        'state> county> tract> block group': '150'
    }

    def __init__(self, geo, name=''):
        self.geo = tuple(geo)
        self.name = name


    def __str__(self):
        if self.name == '':
            return 'Summary level: ' + self.sumlevel() + ', ' + '> '.join([geo[0]+':'+geo[1] for geo in self.geo])
        else:
            return self.name + ': Summary level: ' + self.sumlevel() + ', ' + '> '.join([geo[0]+':'+geo[1] for geo in self.geo])

    def hierarchy(self):
        """Geography hierarchy for the geographic level of this object.

        Returns:
            str: String representing the geography hierarchy (e.g., 'state> county')."""
        return '> '.join([geo[0] for geo in self.geo])

    def sumlevel(self):
        """Summary level code for the geographic level of this object.

        Returns:
            str: String representing the summary level code for this object's geographic level, e.g., '050' for 'state> county'."""
        return self.sumleveldict.get(self.hierarchy(), 'unknown')

    def request(self):
        """Generate geographic parameters for Census API request.

        Returns:
            dict: Dictionary with appropriate 'for' and, if needed, 'in' parameters for Census API request."""
        nospacegeo = [(geo[0].replace(' ', '+'), geo[1]) for geo in self.geo]
        if len(nospacegeo) > 1:
            result = {'for': ':'.join(nospacegeo[-1]),
            'in': '+'.join([':'.join(geo) for geo in nospacegeo[:-1]])}
        else:
            result = {'for': ':'.join(nospacegeo[0])}
        return result


def geographies(within, year, key=None):
    """List geographies within a given geography, e.g., counties within a state.

    Args:
        within (censusgeo): Geography within which to list geographies.
        src (str): Census data source: 'acs1' for ACS 1-year estimates, 'acs5' for ACS 5-year estimates, 'acs3' for
            ACS 3-year estimates, 'acsse' for ACS 1-year supplemental estimates, 'sf1' for SF1 data.
        year (int): Year of data.
        key (str, optional): Census API key.
        endpt (str, optional): Allows override of whether old or new API endpoint is used. Specify
            'old' for old, 'new' for new, '' to use default. This option generally shouldn't
            need to be specified but can be helpful if download problems are encountered.

    Returns:
        dict: Dictionary with names as keys and `censusgeo` objects as values.

    Examples::

        # Pull data on all state geographies from the ACS 2011-2015 5-year estimates.
        censusdata.geographies(censusdata.censusgeo([('state', '*')]), 'acs5', 2015)
    """
    georequest = within.request()
    params = {'get': 'NAME'}
    params.update(georequest)
    if key is not None: params.update({'key': key})
    geo = _download(year, params)
    name = geo['NAME']
    del geo['NAME']
    return {name[i]: censusgeo([(key, geo[key][i]) for key in geo]) for i in range(len(name))}

def _download(year, params, baseurl = 'https://api.census.gov/data/'):

    """Request data from Census API. Returns data in ordered dictionary. Called by `geographies()` and `download()`.

	Args:

		year (int): Year of data.
		params (dict): Download parameters.
		baseurl (str, optional): Base URL for download.

    """

    url = baseurl + str(year) + '/acs/acs5?' + '&'.join('='.join(param) for param in params.items())
    r = requests.get(url)

    try:
        data = r.json()
    except:
        raise ValueError('Unexpected response (URL: {0.url}): {0.text} '.format(r))
    rdata = OrderedDict()
    for j in range(len(data[0])):
        rdata[data[0][j]] = [data[i][j] for i in range(1, len(data))]
    return rdata

def download(year, geo, var, key=None):
    """Download data from Census API.

	Args:

		year (int): Year of data.
		geo (censusgeo): Geographies for which to download data.
		var (list of str): Census variables to download.
		key (str, optional): Census API key.


	Returns:
		pandas.DataFrame: Data frame with columns corresponding to designated variables, and row index of censusgeo objects representing Census geographies.


    """
	

    georequest = geo.request()
    data = OrderedDict()
    chunk_size = 49

    for var_chunk in [var[i:(i+chunk_size)] for i in range(0, len(var), chunk_size)]:
        params = {'get': ','.join(['NAME']+var_chunk)}
        params.update(georequest)
        if key is not None: params.update({'key': key})
        
        data.update(_download(year, params))

    geodata = data.copy()
    for key in list(geodata.keys()):

        if key in var:
            del geodata[key]
            try:
                data[key] = [int(d) if d is not None else None for d in data[key]]
            except ValueError:
                try:
                    data[key] = [float(d) if d is not None else None for d in data[key]]
                except ValueError:
                    data[key] = [d for d in data[key]]
        else:
            del data[key]

    geoindex = [censusgeo([(key, geodata[key][i]) for key in geodata if key != 'NAME'], geodata['NAME'][i]) for i in range(len(geodata['NAME']))]
    return pd.DataFrame(data, geoindex)

def acs_search(year, field, criterion, tabletype='detail'):
    """Search Census variables.

    Args:
            ACS 3-year estimates, 'acsse' for ACS 1-year supplemental estimates, 'sf1' for SF1 data.
        year (int): Year of data.
        field (str): Field in which to search.
        criterion (str or function): Search criterion. Either string to search for, or a function which will be passed the value of field and return
            True if a match and False otherwise.
        tabletype (str, optional): Type of table from which variables are drawn (only applicable to ACS data). Options are 'detail' (detail tables),
            'subject' (subject tables), 'profile' (data profile tables), 'cprofile' (comparison profile tables).

    Returns:
        list: List of 3-tuples containing variable names, concepts, and labels matching the search criterion.

    """

    if hasattr(criterion, '__call__'): match = criterion
    else: match = lambda value: re.search(criterion, value, re.IGNORECASE)

    try:
        assert tabletype == 'detail' or tabletype == 'subject' or tabletype == 'profile' or tabletype == 'cprofile'
    except AssertionError:
        raise ValueError(u'Unknown table type {0}!'.format(tabletype))


    json_url = 'https://api.census.gov/data/' + str(year) + '/acs/acs5/variables.json'

    js = requests.get(json_url)

    allvars = js.text

    allvars = json.loads(allvars)['variables']

    return [(k, allvars[k].get('concept'), allvars[k].get('label')) for k in sorted(allvars.keys()) if match(allvars[k].get(field, ''))]



def listToString(s):  
    
    str1 = ""  

    for ele in s:  
        str1 += ele   

    return str1 

def GetStateNum(state_name):
    """Returns a state FIPS code for an input state name"""
    stategeo = geographies(censusgeo([('state', "*")]), int(Year))

    statenum = str(stategeo[state_name]).split(":")[-1]

    return statenum


def GetCountyNums(state_name, counties):
    """Returns a list of county FIPS codes for a list of counties in a particular state"""

    state_num = GetStateNum(state_name)
        
    countygeo = geographies(censusgeo([('state', state_num), ("County", '*')]), int(Year))
    
    county_list = [str(countygeo[c.strip("'") + ", " + state_name]).split(":")[-1] for c in counties]
    
    return county_list


def unique(list1):


    """Returns a list of only unique values from a list with multiple of the same values
    
    Args: 
        list1 (list): input list of values"""

    unique_list = []

    for x in list1:

        if x not in unique_list:

            unique_list.append(x)

    return unique_list

def DownloadTable(year, state_num, fields, counties, geo="County"):

    """Returns a pandas dataframe containing population estimates from a list of fields, for a certain year and geography
    
    Args:
        year (int): input year
        state_num (str): state FIPS number
        fields (list): list of field IDs for ACS data
        counties (list or str): either a list containing either a list of county FIPS numbers or 'All fields'
        geo (str): Geography: County, Tract, or Block group"""
        


    def GetGeoArgs(geo):
        """generates the general portion of the arguments for each geograpy level"""
        if geo == "County":
            geo_arg = []

        elif geo == "Tract":
            geo_arg = [("tract", "*")]

        elif geo == "Block group":
            geo_arg = [("block group", "*")]
        
        return geo_arg

    if counties == "'All counties'":

        acs_df = download(year,
        censusgeo([("state", state_num), ("county", "*")] + GetGeoArgs(geo)), ["GEO_ID"] + fields)

    else:

        acs_df = pd.DataFrame(columns=["GEO_ID"] + fields)
        for county in counties:
            county = str(county).zfill(3)

            county_df = download(
                year,
                censusgeo([("state", state_num), ("county", county)] + GetGeoArgs(geo)), ["GEO_ID"] + fields)
            acs_df = acs_df.append(county_df)
    
    acs_df["Geography"] = acs_df.index.to_series()

    acs_df.rename(columns={"GEO_ID": "GEOID"}, inplace=True)
    acs_df = acs_df.set_index("GEOID")
    acs_df.columns = [c + "_" + str(year) for c in acs_df.columns if c not in ["Geography"]] + ["Geography"]
    out_cols = ["Geography"] + [c for c in acs_df.columns if c not in ["Geography"]]
    acs_df = acs_df[out_cols]
    return acs_df
    

def GetFieldList(table, year):
    
    """
    Returns a list of all fields for a particular table ID
    
    Args:
        table (str): Table ID
        year (int): ACS year"""

    table = str(table).upper()

    cl = acs_search(year, 'concept', table)
    gl = acs_search(year, 'group', table)

    fl = cl + gl

    fields = [f for f in fl if f[0].split("_")[0] == table and f[0][-1] == 'E']

    field_list = ["{0} {1}".format(f[0], f[2]) for f in fields]

    return field_list


def GetFieldMappings(in_table, field_list):

    """Returns a field mappings object from an input data table, which can be used to control the order and selection of output data fields
    
    Parameters:
        in_table (string): input table, can either be a spatial data table or standalone
        field_list (list): list containing paired sets of field names and aliases"""
        

    fms = ap.FieldMappings()

    for field in field_list:

        fmap = ap.FieldMap()
        fmap.addInputField(in_table, field[0])
        out_f = fmap.outputField
        out_f.name = field[0]
        out_f.aliasName = field[1]
        fmap.outputField = out_f
        fms.addFieldMap(fmap)
    
    return fms


def GetOutputTable(acs_table, select_fields, output_fields, year, state, counties, geo, out_table, margin_of_error):
    
    """Uses parameter text inputs to download selected tables and columns, and output as either a table or spatial file.
        Final output is saved as the file specified in the Output Data parameter"""
    
    statenum = GetStateNum(State)


    if select_fields == "All fields":

        param_fields = [[f.split(" ")[0], "".join(f.split(" ")[1:])] for f in GetFieldList(acs_table, year)]

        if Margin_of_Error == "true":

            field_list = []

            for field in param_fields:    
                field_list.append([field[0], field[1]])
                field_list.append([field[0].replace("E", "M"), "MOE_" + field[1].lstrip("Estimate!!")])    

        else:
            field_list = param_fields

        out_fields = [f[0] for f in field_list]

        field_list = [[f[0] + "_" + str(year), f[1]] for f in field_list]

        out_df = DownloadTable(year, statenum, out_fields, counties, geo)

        out_df.columns = ["Geography"] + [f + "_" + str(year) for f in out_fields]

    else:

        year_list = [f.split(" ")[1] for f in output_fields]

        years = [y.lstrip("(").rstrip(")'") for y in unique(year_list)]

        if len(years) > 1:

            df_list = []
            field_list = []
            for year in years:

                param_fields = [[f.split(" ")[0].lstrip("'"), f.split("' ")[-1].strip("'")] for f in output_fields if year in f.split(" ")[1]]

                if Margin_of_Error == "true":

                    year_fields = []

                    for field in param_fields:

                        year_fields.append([field[0], field[1]])
                        year_fields.append([field[0].replace("E", "M"), "MOE_" + field[1].lstrip("Estimate!!")])

                else:

                    year_fields = param_fields

                field_list = field_list + [[y[0] + "_" + str(year), y[1]] for y in year_fields]
                year_fields = [y[0] for y in year_fields]
                year_df = DownloadTable(int(year), statenum, year_fields, counties, geo)
                year_df.columns = ["Geography"] + [f + "_" + str(year) for f in year_fields]

                df_list.append([year, year_df])

            join_df = df_list[0][1]

            for df in df_list[1:]:

                join_df = join_df.join(df[1].drop("Geography", axis=1), how="outer")
            out_df = join_df

        else:

            year = int(years[0])

            param_fields = [[f.split(" ")[0].lstrip("'"), listToString(f.split(" ")[1:]).split("'")[1]] for f in output_fields if str(year) in f.split(" ")[1]]

            if Margin_of_Error == "true":

                field_list = []

                for field in param_fields:

                    field_list.append([field[0], field[1]])
                    field_list.append([field[0].replace("E", "M"), "MOE_" + field[1].lstrip("Estimate!!")])
            
            else: 
                
                field_list = param_fields

            out_fields = [f[0] for f in field_list]

            field_list = [[f[0] + "_" + str(year), f[1]] for f in field_list]

            out_df = DownloadTable(year, statenum, out_fields, counties, geo)

            out_df.columns = ["Geography"] + [f + "_" + str(year) for f in out_fields]


    if out_table.endswith(".csv"):

        out_df.to_csv(out_table)

    else:

        temp = tempfile.TemporaryDirectory()

        tpath = os.path.dirname(temp.name)

        out_name = os.path.basename(out_table)

        temp_table = os.path.join(tpath, out_name + ".csv")

        out_df.to_csv(temp_table)

        fmappings = GetFieldMappings(temp_table, [["GEOID", "GEOID"], ["Geography", "Geography"]] + field_list)

        ap.TableToTable_conversion(temp_table, os.path.dirname(out_table), out_name, "", fmappings)

        ap.CalculateField_management(out_table, "GEOID", "!GEOID!.split('S')[1]", "PYTHON")

        os.remove(temp_table)

if Counties == "'All counties'":

    county_list = Counties
else:
    county_list = GetCountyNums(State, Counties)


GetOutputTable(ACS_Table, Select_Fields, Output_Fields, int(Year), State, county_list, Geography, Output_Table, Margin_of_Error)
