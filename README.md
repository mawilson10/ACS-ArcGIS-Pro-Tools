
Developed for and by the Tennessee Department of Transportation

## Introduction

An understanding of where people live, where they travel, and for what purpose is critical to transportation planning. The locations of population centers in relation to major employment and services hubs can be used to assess travel and traffic patterns, and allow for a better overall understanding of a region’s transportation needs. Social justice considerations can be made for vulnerable populations, identifying areas where transportation improvements could help those who are most in need. This makes access to accurate and authoritative population data a necessity for all agencies and organizations dedicated to building and improving transportation infrastructure. Furthermore, this data must be formatted so that it can be easily and intuitively incorporated into a GIS environment. This need was addressed in the Tennessee Department of Transportation’s Long Range Planning Division through the development of a Python script tool, which uses the publicly available Census Data API to import census population estimates directly into an ArcGIS-compatible format.

This tool was designed as an alternative to the United States Census website, which provides a search and download interface for various types of tables and sub-tables, including data from the decennial census as well as yearly American Community Survey population estimates. Although all these tables are readily available through the website, several pre-processing and formatting steps are necessary to prepare the data for use in GIS. This tool performs all the formatting itself, producing data which can be immediately incorporated into an ArcGIS workflow. There is also additional functionality, which allows the user to build their own tables, pulling select columns, and even combining data from various tables over multiple years in a single output. The purpose of this presentation is to describe the development of the tool and showcase its capabilities, with the goal of inspiring further interest and development of GIS-friendly population data tools.

The Census Data toolbox contains two ArcGIS Pro script tools. The US ACS Data Downloader is universally functional, and will output a table to an ESRI file geodatabase. The TN ACS Data Downloader is also provided. This tool is limited to Tennessee, as it utilizes feature data in a TDOT SDE database to output a feature class. The tool and its source code are provided, so that potential users with scripting experience can modify the county parameter and replace the TN geometry file path with data for their own state of interest.

## Installation Instructions (ArcGIS Pro)

This tool was designed to be used in ArcGIS Pro, in order for the tool to function, the CensusData Python library must be installed on your computer. This package must be reinstalled with each annual ACS data release, to account for updates to the data and source code. The package can be installed and updated using pip.

### First-time installation:

1.	Open the Start menu, and type “python”
2.	Open the Python Command Prompt
3.	In the prompt window, type “pip install censusdata --user”, then enter
4.	Wait for the installation to complete
5.	Download Census Data.tbx (provided above) to your local drive

### Update/re-installation:

1.	Open the Start menu, and type “python”
2.	Open the Python Command Prompt
3.	In the prompt window, type “pip uninstall censusdata”, then enter
4.	When prompted, type “y”, then enter
5.	Once the package has uninstalled, type “pip install censusdata –user”, then enter

Once the CensusData library has been installed, and the Census Data toolbox has been copied to your computer, the tool can be opened and used in ArcGIS Pro.

## Parameters

| Parameter | Description |
|-----------|-------------|
|Year       |Select year for ACS variables. Estimates are<br />available for all years since 2012.|
|State      |Select state for ACS Variables.
|Counties   |Select county or counties for chosen state.<br />Default value is 'All Counties'.|
|Geography  |Type of geographic unit for which estimates<br />are retrieved. Three choices are available:<br />county, tract, and block group.
|Search Key |Simple search function which will accept words<br />and exact phrases which match table names,<br />field names, and table IDs (e.g. 'age',  or 'B01001')<br />in all available tables for the selected year. Not<br />case sensitive.|
|Search Results|Selectable list of tables identified with the<br />search key.|
|ACS Table  |This parameter can be either populated from a<br />selection from the Search Results parameter,<br />or a manually entered table ID for a table of<br />interest (e.g. 'B01001')|
|Output Data|Output table. This must be saved to a<br />geodatabase|
|Select Fields|Indicates whether to export a whole table<br />('All fields') or a select field or series of fields<br />from a table or number of tables.|
|Field List |Selectable list of fields generated for the<br />table in the ACS Table parameter.|
|Output Fields|Selected fields from the Field List<br />parameter. This list can contain various fields from<br />different years and table IDs. Values in the Alias<br />column can be modified. Values in the Name field<br />should not be changed.| 
|Include Margin of Error|Includes a margin of error field for each<br />estimate field.|
