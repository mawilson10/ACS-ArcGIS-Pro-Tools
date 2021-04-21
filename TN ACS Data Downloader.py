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

# Define variables for incoming parameter values

Year = ap.GetParameterAsText(0) # Year (string): 2012-2018. Used if 'All fields' is selected in Select_Fields
Geography = ap.GetParameterAsText(1) # Census geography: county, tract, or block group
Counties = ap.GetParameterAsText(2) # Semicolon-delimited string containing either counties of interest, or 'All counties'

ACS_Table = ap.GetParameterAsText(5) # Input Table ID, used if entire table is exported ('All fields')
Output_Data = ap.GetParameterAsText(6) # Output feature class containing select population estimates for the designated geography
Select_Fields = ap.GetParameterAsText(7) # Indicates whether all fields from ACS_Table will be exported, or selected fields from one or more tables

Output_Fields = ap.GetParameterAsText(9) # Semicolon-delimited string containing pairs of field IDs and aliases for each selected output field
Margin_of_Error = ap.GetParameterAsText(10) # Checkbox indicating whether or not to include margins of error in the output table

Output_Fields = Output_Fields.split(";") # Converts Output_Fields from a string to a list

county_list = [[1, 'Anderson'], [3, 'Bedford'], [5, 'Benton'], [7, 'Bledsoe'], [9, 'Blount'], 
            [11, 'Bradley'], [13, 'Campbell'], [15, 'Cannon'], [17, 'Carroll'], [19, 'Carter'], 
            [21, 'Cheatham'], [23, 'Chester'], [25, 'Claiborne'], [27, 'Clay'], [29, 'Cocke'], 
            [31, 'Coffee'], [33, 'Crockett'], [35, 'Cumberland'], [37, 'Davidson'], [39, 'Decatur'], 
            [41, 'DeKalb'], [43, 'Dickson'], [45, 'Dyer'], [47, 'Fayette'], [49, 'Fentress'], 
            [51, 'Franklin'], [53, 'Gibson'], [55, 'Giles'], [57, 'Grainger'], [59, 'Greene'], 
            [61, 'Grundy'], [63, 'Hamblen'], [65, 'Hamilton'], [67, 'Hancock'], [69, 'Hardeman'],
            [71, 'Hardin'], [73, 'Hawkins'], [75, 'Haywood'], [77, 'Henderson'], [79, 'Henry'], 
            [81, 'Hickman'], [83, 'Houston'], [85, 'Humphreys'], [87, 'Jackson'], [89, 'Jefferson'], 
            [91, 'Johnson'], [93, 'Knox'], [95, 'Lake'], [97, 'Lauderdale'], [99, 'Lawrence'], 
            [101, 'Lewis'], [103, 'Lincoln'], [105, 'Loudon'], [107, 'McMinn'], [109, 'McNairy'], 
            [111, 'Macon'], [113, 'Madison'], [115, 'Marion'], [117, 'Marshall'], [119, 'Maury'], 
            [121, 'Meigs'], [123, 'Monroe'], [125, 'Montgomery'], [127, 'Moore'], [129, 'Morgan'], 
            [131, 'Obion'], [133, 'Overton'], [135, 'Perry'], [137, 'Pickett'], [139, 'Polk'], 
            [141, 'Putnam'], [143, 'Rhea'], [145, 'Roane'], [147, 'Robertson'], [149, 'Rutherford'], 
            [151, 'Scott'], [153, 'Sequatchie'], [155, 'Sevier'], [157, 'Shelby'], [159, 'Smith'], 
            [161, 'Stewart'], [163, 'Sullivan'], [165, 'Sumner'], [167, 'Tipton'], [169, 'Trousdale'], 
            [171, 'Unicoi'], [173, 'Union'], [175, 'Van Buren'], [177, 'Warren'], [179, 'Washington'], 
            [181, 'Wayne'], [183, 'Weakley'], [185, 'White'], [187, 'Williamson'], [189, 'Wilson']]


if Counties != "'All counties'": # Counties are converted to a list as well if specific counties are selected

    Counties = Counties.split(";")
    Counties = [c[0] for c in county_list if c[1] in Counties]

def sde_connections(name, sde="default"):

    """The path to an existing .sde file is verified as valid, and the full path is returned

    Args:
        name (str): name of .sde file being identified
        sde (str): String to path of sde connection. If not provided then this function will search for one.
    """
    if sde == "default":
        try:

            appdata = os.getenv('APPDATA')

            arcgisVersion = ap.GetInstallInfo()['Version']

            arcCatalogPath = os.path.join(programdata ,'ESRI', 'Desktop10.7', 'ArcCatalog')
            sdeConnections = []
            for file in os.listdir(arcCatalogPath):

                fileIsSdeConnection = file.lower().endswith(".sde")
                if fileIsSdeConnection:
                    sdeConnections.append(os.path.join(arcCatalogPath, file))

            for conn in sdeConnections:
                if name in conn:
                    return conn

        except:
            programdata = os.getenv('PROGRAMDATA')
            arcgisVersion = ap.GetInstallInfo()['Version']
            arcCatalogPath = os.path.join(programdata ,'ESRI', 'Desktop10.7', 'ArcCatalog')
            sdeConnections = []
            for file in os.listdir(arcCatalogPath):
                fileIsSdeConnection = file.lower().endswith(".sde")
                if fileIsSdeConnection:
                    sdeConnections.append(os.path.join(arcCatalogPath, file))

            for conn in sdeConnections:
                if name in conn:
                    return conn
    else:
        return sde
def unique(list1):

    """Returns a list of only unique values from a list with multiple of the same values
    
    Args: 
        list1 (list): input list of values"""

    unique_list = []

    for x in list1:

        if x not in unique_list:

            unique_list.append(x)

    return unique_list

def DownloadTable(year, fields, counties="'All counties'", geo="County"):

    """Returns a pandas dataframe containing population estimates from a list of fields, for a certain year and geography
    
    Parameters:
        year (int): input year
        fields (list): list of field IDs for ACS data
        counties (list or str): either a list containing either a list of county FIPS numbers or 'All fields'
        geo (str): Geography: County, Tract, or Block group"""
        

    def GetGeoArgs(geo):

        if geo == "County":
            geo_arg = []

        elif geo == "Tract":
            geo_arg = [("tract", "*")]

        elif geo == "Block group":
            geo_arg = [("block group", "*")]
        
        return geo_arg

    if counties == "'All counties'":

        acs_df = cd.download("acs5", year,
        cd.censusgeo([("state", "47"), ("county", "*")] + GetGeoArgs(geo)), ["GEO_ID"] + fields)

    else:

        acs_df = pd.DataFrame(columns=["GEO_ID"] + fields)
        for county in counties:
            county = str(county).zfill(3)

            county_df = cd.download(
                "acs5", year,
                cd.censusgeo([("state", "47"), ("county", county)] + GetGeoArgs(geo)), ["GEO_ID"] + fields)
            acs_df = acs_df.append(county_df)

    return acs_df
    
def GetFieldList(table, year):

    """
    Returns a list of all fields for a particular table ID
    
    Args:
        table (str): Table ID
        year (int): ACS year"""
        
    year = alt_search_year(year)
    table = str(table).upper().split(" ")[0]

    cl = cd.search('acs5', int(year), 'concept', table)
    gl = cd.search('acs5', int(year), 'group', table)

    fl = cl + gl

    fields = [f for f in fl if f[0].split("_")[0] == table and f[0][-1] == 'E']

    field_list = ["{0} {1}".format(f[0], f[2]) for f in fields]

    return field_list

def listToString(sl):  

    """
    Combines all items in a bracketed list in a single string
    
    Parameters:
        sl (list): List of strings to be converted"""
    
    str1 = ""  

    for ele in sl:  
        str1 += ele   

    return str1

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
        out_f.name = field[0].split(".")[-1]
        out_f.aliasName = field[1]
        fmap.outputField = out_f
        fms.addFieldMap(fmap)
    return fms


def GetOutputTable(acs_table, select_fields, output_fields, year, counties, geo, out_data):
    """"""

    if select_fields == "All fields":

        param_fields = [[f.split(" ")[0], listToString(f.split(" ")[1:])] for f in GetFieldList(acs_table, year)]
        
        if Margin_of_Error == "true":

            field_list = []

            for field in param_fields:    
                field_list.append([field[0], field[1]])
                field_list.append([field[0].replace("E", "M"), "MOE_" + field[1].lstrip("Estimate!!")])    

        else:
            field_list = param_fields

        out_fields = [f[0] for f in field_list]

        field_list = [[f[0] + "_" + str(year), f[1]] for f in field_list]

        out_df = DownloadTable(year, out_fields, counties, geo)

        out_df.columns = ["GEO_ID"] + [f + "_" + str(year) for f in out_fields]

        out_df = out_df.set_index("GEO_ID")    

    else:

        year_list = [f.split(" ")[1] for f in output_fields]

        years = [y.lstrip("(").rstrip(")'") for y in unique(year_list)]

        if len(years) > 1:

            df_list = []
            field_list = []
            for year in years:

                param_fields = [[f.split(" ")[0].lstrip("'"), listToString(f.split(" ")[1:]).split("'")[1]] for f in output_fields if year in f.split(" ")[1]]

                if Margin_of_Error == "true":

                    year_fields = []

                    for field in param_fields:

                        year_fields.append([field[0], field[1]])
                        year_fields.append([field[0].replace("E", "M"), "MOE_" + field[1].lstrip("Estimate!!")])

                else:

                    year_fields = param_fields

                field_list = field_list + [[y[0] + "_" + str(year), y[1]] for y in year_fields]
                year_fields = [y[0] for y in year_fields]
                year_df = DownloadTable(int(year), year_fields, counties, geo)
                year_df.columns = ["GEO_ID"] + [f + "_" + str(year) for f in year_fields]

                df_list.append([year, year_df])

            join_df = df_list[0][1].set_index("GEO_ID")

            for df in df_list[1:]:

                df[1] = df[1].set_index("GEO_ID")

                join_df = join_df.join(df[1], how="outer")

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

            out_df = DownloadTable(year, out_fields, counties, geo)

            out_df.columns = ["GEO_ID"] + [f + "_" + str(year) for f in out_fields]
            out_df = out_df.set_index("GEO_ID")

    temp = tempfile.TemporaryDirectory()

    tpath = os.path.dirname(temp.name)

    out_name = os.path.basename(out_data)

    temp_table = os.path.join(tpath, out_name + ".csv")

    out_df["GEOID"] = out_df.index.to_series()

    out_df = out_df.set_index("GEOID")

    out_df.to_csv(temp_table)

    out_table = out_name + "_table"

    field_list = [["GEOID", "GEOID"]] + field_list

    fmappings = GetFieldMappings(temp_table, field_list)
    
    ap.TableToTable_conversion(temp_table, os.path.dirname(out_data), out_table, "", fmappings)

    ap.CalculateField_management(out_table, "GEOID", "!GEOID!.split('S')[1]", "PYTHON")

    os.remove(temp_table)

    def JoinToGeometry(field_list):

        if geo == "Block group":

            fc = "TNMAP_DATA_LIBRARY.DBO.tl_2010_47_bg10_BlockGrp_"
            
            join_fields = ["GEOID10", "GEOID"]


        elif geo == "Tract":

            fc = "TNMAP_DATA_LIBRARY.DBO.tl_2010_47_tract10"

            join_fields = ["GEOID10", "GEOID"]

        elif geo == "County":

            fc = "TNMAP_DATA_LIBRARY.DBO.County_Administrative_Designations"

            join_fields = ["FIPS_CODE_3", "CNTY_FIPS"]

        sde = sde_connections("TNMap")

        join_fc = os.path.join(sde, fc)

        if geo == "County":
            ap.AddField_management(out_table, "CNTY_FIPS", "TEXT")
            ap.CalculateField_management(out_table, "CNTY_FIPS", "str(!GEOID![2:])", "PYTHON")


        ap.MakeFeatureLayer_management(join_fc, "join_lyr")

        ap.AddJoin_management("join_lyr", join_fields[0], out_table, join_fields[1], "KEEP_COMMON")

        field_list = [[out_table + "." + field[0], field[1]] for field in field_list]

        fmappings = GetFieldMappings("join_lyr", field_list)
        ap.FeatureClassToFeatureClass_conversion("join_lyr", os.path.dirname(out_data), out_name, "", fmappings)

    try:

        JoinToGeometry(field_list)

    except:

        ap.AddWarning("Unable to generate feature geometry. Output data table available: " + out_data + "_table")

        aprx = ap.mp.ArcGISProject("CURRENT")

        m = aprx.activeMap.name

        current_map = aprx.listMaps(m)[0]

        current_map.addDataFromPath(out_data + "_table")

GetOutputTable(ACS_Table, Select_Fields, Output_Fields, int(Year), Counties, Geography, Output_Data)






