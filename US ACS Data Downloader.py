import arcpy as ap
import censusdata as cd
import pandas as pd
import tempfile
import os

def alt_search_year(year):
    if int(year) == 2019:
        search_year = 2018
    else:
        search_year = int(year)
    return search_year

Year = ap.GetParameterAsText(0)
State = ap.GetParameterAsText(1)
Counties = ap.GetParameterAsText(2)
Geography = ap.GetParameterAsText(3)

ACS_Table = ap.GetParameterAsText(6)
Output_Table = ap.GetParameterAsText(7)
Select_Fields = ap.GetParameterAsText(8)

Output_Fields = ap.GetParameterAsText(10)
Margin_of_Error = ap.GetParameterAsText(11)

if Counties != "'All counties'":
    Counties = Counties.split(";")

ACS_Table = ACS_Table.split(" ")[0]

Output_Fields = Output_Fields.split(";")


def GetStateNum(state_name, year):

    stategeo = cd.geographies(cd.censusgeo([('state', "*")]), 'acs5', int(year))
    
    statenum = str(stategeo[state_name]).split(":")[-1]
    
    return statenum


def GetCountyNums(state_name, counties, year):

    state_num = GetStateNum(state_name, year)
        
    countygeo = cd.geographies(cd.censusgeo([('state', state_num), ("county", '*')]), 'acs5', int(year))
    
    county_list = [str(countygeo[c.strip("'") + ", " + state_name]).split(":")[-1] for c in counties]
    
    return county_list

def GetAllCounties(state_name, year):

    state_num = GetStateNum(state_name, year)

    countygeo = cd.geographies(cd.censusgeo([('state', state_num), ('county', '*')]), 'acs5', int(year))

    county_names = countygeo.keys()

    county_list = [str(countygeo[c]).split(":")[-1].strip("'") for c in county_names]
    return county_list


def unique(list1):

    unique_list = []

    for x in list1:

        if x not in unique_list:

            unique_list.append(x)

    return unique_list

def DownloadTable(year, state_name, state_num, fields, counties, geo="County", margin_of_error="false"):


    if margin_of_error == "true":

        field_list = []

        for field in fields:

            field_list.append(field)
            field_list.append(field.replace("E", "M"))
        fields = field_list


    geo_arg = []

    if geo == "Tract":

        geo_arg = [("Tract", "*")]
    
    elif geo == "Block group":

        table_list = []

        if counties == "'All counties'" and geo == "Block group":

            for county in sorted(GetAllCounties(state_name, year)):
                
                ctable = cd.download("acs5", year,
                cd.censusgeo([("state", state_num), ("county", county), ("block group", "*")]), ["GEO_ID"] + fields)
                table_list.append(ctable)

            acs_df = table_list[0]

            for ctable in table_list:

                acs_df = acs_df.append(ctable)

        else:
            geo_arg = [("Block group", "*")]


    if counties == "'All counties'" and geo != "Block group":

        acs_df = cd.download(
            "acs5", year,
            cd.censusgeo([("state", state_num), ("county", "*")] + geo_arg), ["GEO_ID"] + fields)

    elif counties != "'All counties'":
        acs_df = pd.DataFrame(columns=["GEO_ID"] + fields)
        for county in counties:
            county = str(county).zfill(3)
            county_df = cd.download(
                "acs5", year,
                cd.censusgeo([("state", state_num), ("county", county)] + geo_arg), ["GEO_ID"] + fields)
            acs_df = acs_df.append(county_df)

    
    acs_df["County"] = acs_df.index.to_series()
    acs_df.rename(columns={"GEO_ID": "GEOID"}, inplace=True)
    acs_df = acs_df.set_index("GEOID")
    acs_df.columns = [c + "_" + str(year) for c in acs_df.columns if c not in ["County"]] + ["County"]
    out_cols = ["County"] + [c for c in acs_df.columns if c not in ["County"]]
    acs_df = acs_df[out_cols]
    return acs_df
    

def GetFieldList(table, year):
    year = alt_search_year(year)
    table = str(table).upper()

    cl = cd.search('acs5', year, 'concept', table)
    gl = cd.search('acs5', year, 'group', table)

    fl = cl + gl

    fields = [f for f in fl if f[0].split("_")[0] == table and f[0][-1] == 'E']

    field_list = ["{0} {1}".format(f[0], f[2]) for f in fields]

    return field_list

def listToString(s):  
    
    str1 = ""  

    for ele in s:  
        str1 += ele   

    return str1

def GetFieldMappings(in_table, field_list):

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


def GetOutputTable(acs_table, year, state, counties, geo, out_table, margin_of_error):

    statenum = GetStateNum(State, Year)


    if Select_Fields == "All fields":

        field_list = [[f.split(" ")[0], listToString(f.split(" ")[1:])] for f in GetFieldList(acs_table, year)]

        out_fields = [f[0] for f in field_list]

        field_list = [[f[0] + "_" + str(year), f[1]] for f in field_list]
        ap.AddMessage(out_fields)
        out_df = DownloadTable(year, state, statenum, out_fields, counties, geo, margin_of_error)

    else:

        year_list = [f.split(" ")[1] for f in Output_Fields]

        years = [y.lstrip("(").rstrip(")'") for y in unique(year_list)]

        if len(years) > 1:

            df_list = []
            field_list = []
            for year in years:

                year_fields = [[f.split(" ")[0].lstrip("'"), listToString(f.split(" ")[1:]).split("'")[1]] for f in Output_Fields if year in f.split(" ")[1]]

                field_list = field_list + [[y[0] + "_" + str(year), y[1]] for y in year_fields]
                year_fields = [y[0] for y in year_fields]
                year_df = DownloadTable(int(year), state, statenum, year_fields, counties, geo, margin_of_error)
                df_list.append([year, year_df])

            join_df = df_list[0][1]
            for df in df_list[1:]:
                
                new_join = df[1].drop("County", axis=1)

                join_df = join_df.join(new_join, how="outer")
            out_df = join_df

        else:

            year = int(years[0])

            field_list = [[f.split(" ")[0].lstrip("'"), listToString(f.split(" ")[1:]).split("'")[1]] for f in Output_Fields if str(year) in f.split(" ")[1]]

            out_fields = [f[0] for f in field_list]

            field_list = [[f[0] + "_" + str(year), f[1]] for f in field_list]

            out_df = DownloadTable(year, state, statenum, out_fields, counties, geo, margin_of_error)

    if margin_of_error == "true":
        all_fields = []
        for field in field_list:
            all_fields.append([field[0], field[1]])
            all_fields.append([field[0].replace("E", "M"), "MOE_" + field[1].lstrip("Estimate!!")])
        field_list = all_fields

    if out_table.endswith(".csv"):

        out_df.to_csv(out_table)

    else:

        temp = tempfile.TemporaryDirectory()

        tpath = os.path.dirname(temp.name)

        out_name = os.path.basename(out_table)

        temp_table = os.path.join(tpath, out_name + ".csv")

        out_df.to_csv(temp_table)

        fmappings = GetFieldMappings(temp_table, [["GEOID", "GEOID"], ["County", "County"]] + field_list)

        ap.TableToTable_conversion(temp_table, os.path.dirname(out_table), out_name, "", fmappings)

        ap.CalculateField_management(out_table, "GEOID", "!GEOID!.split('S')[1]", "PYTHON")

        os.remove(temp_table)

if Counties == "'All counties'":

    county_list = Counties
else:
    county_list = GetCountyNums(State, Counties, Year)


GetOutputTable(ACS_Table, int(Year), State, county_list, Geography, Output_Table, Margin_of_Error)






