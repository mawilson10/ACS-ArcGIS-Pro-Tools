import arcpy as ap
import censusdata as cd
import pandas as pd
import tempfile
import os

def alt_search_year(year):
    """Called as a workaround when the censusdata library is not fully updated"""

    if int(year) == 2019:
        search_year = 2018
    else:
        search_year = int(year)
    return search_year

Year = ap.GetParameterAsText(0) # Year (string): 2012-2018.
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

def GetStateNum(state_name):
    """Returns a state FIPS code for an input state name"""
    stategeo = cd.geographies(cd.censusgeo([('state', "*")]), 'acs5', 2019)
    
    statenum = str(stategeo[state_name]).split(":")[-1]
    
    return statenum


def GetCountyNums(state_name, counties):
    """Returns a list of county FIPS codes for a list of counties in a particular state"""

    state_num = GetStateNum(state_name)
        
    countygeo = cd.geographies(cd.censusgeo([('state', state_num), ("County", '*')]), 'acs5', 2019)
    
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

        acs_df = cd.download("acs5", year,
        cd.censusgeo([("state", state_num), ("county", "*")] + GetGeoArgs(geo)), ["GEO_ID"] + fields)

    else:

        acs_df = pd.DataFrame(columns=["GEO_ID"] + fields)
        for county in counties:
            county = str(county).zfill(3)

            county_df = cd.download(
                "acs5", year,
                cd.censusgeo([("state", state_num), ("county", county)] + GetGeoArgs(geo)), ["GEO_ID"] + fields)
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

    year = alt_search_year(year)
    table = str(table).upper()

    cl = cd.search('acs5', year, 'concept', table)
    gl = cd.search('acs5', year, 'group', table)

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
    
    """This function applies the above defined functions, using the input parameter 
        values from the tool as the input values for the function arguemnts"""
    
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







