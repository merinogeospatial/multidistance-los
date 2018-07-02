"""
Multiple Distance, Experience Based LOS
06/25/18
RM
"""

### Import dependencies ###

import sys
import arcpy
from arcpy import env

################# Start Defining Subroutines ###############################################

# Join closest distance to block
def route_data(route, block):
    arcpy.AddMessage("Joining clostest routes to blocks...")

    new_tbl = str(block)[:-4] + "_" + str(route)[:-4]
    arcpy.CopyRows_management(route, new_tbl)
    route_tbl = str(new_tbl) + "_tvw"
    arcpy.MakeTableView_management(new_tbl, route_tbl)

    arcpy.AddField_management(route_tbl, "GEOID10", "TEXT", "", "", 15, "GEOID10")
    arcpy.AddField_management(route_tbl, "SITE", "TEXT", "", "", 75, "SITE")

    arcpy.CalculateField_management(route_tbl, "GEOID10", "(!Name![0:15])", "PYTHON_9.3")
    arcpy.CalculateField_management(route_tbl, "SITE", "(!Name![18:])", "PYTHON_9.3")
    arcpy.CalculateField_management(route_tbl, "SITE", "(!SITE![:-6])", "PYTHON_9.3")

    arcpy.AddJoin_management(block, "GEOID10", route_tbl, "GEOID10")
    field_name = str(route_tbl)[:-4]
    arcpy.CalculateField_management(block, "DIST", "(!" + field_name + ".Total_Length!)", "PYTHON_9.3")
    arcpy.CalculateField_management(block, "DIST", "(!DIST!/5280)", "PYTHON_9.3")
    arcpy.RemoveJoin_management(block)
    arcpy.AddMessage("...completed!")
    return


# Generate acreage, number of parks, and experience counts
def route_data_mile(route, park, block):
    arcpy.AddMessage("Counting and joining subscores. This could take a hot minute...")

    # Make intermediate table view for routes
    new_tbl = str(block)[:-4] + "_" + str(route)[:-4]
    arcpy.CopyRows_management(route, new_tbl)
    route_tbl = str(new_tbl) + "_tvw"
    arcpy.MakeTableView_management(new_tbl, route_tbl)

    arcpy.AddField_management(route_tbl, "GEOID10", "TEXT", "", "", 15, "GEOID10")
    arcpy.AddField_management(route_tbl, "SITE", "TEXT", "", "", 75, "SITE")
    arcpy.AddField_management(route_tbl, "ACRES", "DOUBLE", "", "", "", "ACRES")
    arcpy.AddField_management(route_tbl, "POP", "LONG", "", "", "", "POP")
    arcpy.AddField_management(route_tbl, "ACRE_COUNT", "DOUBLE", "", "", "", "ACRE_COUNT")
    arcpy.AddField_management(route_tbl, "PARK_COUNT", "DOUBLE", "", "", "", "PARK_COUNT")
    arcpy.AddField_management(route_tbl, "EXP_COUNT", "SHORT", "", "", "", "EXP_COUNT")

    arcpy.CalculateField_management(route_tbl, "GEOID10", "(!Name![0:15])", "PYTHON_9.3")
    arcpy.CalculateField_management(route_tbl, "SITE", "(!Name![18:])", "PYTHON_9.3")
    arcpy.CalculateField_management(route_tbl, "SITE", "(!SITE![:-6])", "PYTHON_9.3")

    arcpy.AddJoin_management(route_tbl, "SITE", park, "NAME")
    field_name_1 = str(park)[:-4]
    calc_acres = "(" + "!" + field_name_1 + ".MAP_ACRES!" + ")"
    arcpy.CalculateField_management(route_tbl, "ACRES", calc_acres, "PYTHON_9.3")
    count_experiences = "(" + "!" + field_name_1 + ".TOTAL_COUNT!" + ")"
    arcpy.CalculateField_management(route_tbl, "EXP_COUNT", count_experiences, "PYTHON_9.3")
    arcpy.RemoveJoin_management(route_tbl)

    arcpy.AddJoin_management(route_tbl, "GEOID10", block, "GEOID10")
    field_name_2 = str(block)[:-4]
    calc_pop = "(" + "!" + field_name_2 + ".POP!" + ")"
    arcpy.CalculateField_management(route_tbl, "POP", calc_pop, "PYTHON_9.3")
    arcpy.RemoveJoin_management(route_tbl)

    # Deletes rows where GEOID10 AND SITE are duplicates just in case
    arcpy.DeleteIdentical_management(route_tbl, ["GEOID10", "SITE"])

    # Summarize SITE by ACRES & POP
    site_tbl = str(route_tbl) + "_stats"
    arcpy.Statistics_analysis(route_tbl, site_tbl, [["ACRES", "MEAN"], ["POP", "SUM"]], "SITE")

    # Calculate acres & number of parks
    arcpy.AddField_management(site_tbl, "ACRE_COUNT", "DOUBLE", "", "", "", "ACRE_COUNT")
    arcpy.AddField_management(site_tbl, "PARK_COUNT", "DOUBLE", "", "", "", "PARK_COUNT")
    arcpy.AddField_management(site_tbl, "EXP_COUNT", "SHORT", "", "", "", "EXP_COUNT")
    get_acres = "(!MEAN_ACRES!/1)" # This is a mean since it is counting acres by access point - this normalizes acreage since getting the mean = (acreage sum of all access points)/(number of access points)
    get_parks = "(1)" # Value is 1 for count per park
    
    arcpy.CalculateField_management(site_tbl, "ACRE_COUNT", get_acres, "PYTHON_9.3")
    arcpy.CalculateField_management(site_tbl, "PARK_COUNT", get_parks, "PYTHON_9.3")

    arcpy.AddJoin_management(route_tbl, "SITE", site_tbl, "SITE")
    count_acres = "(!" + site_tbl + ".ACRE_COUNT!)"
    count_parks = "(!" + site_tbl + ".PARK_COUNT!)"
    arcpy.CalculateField_management(route_tbl, "ACRE_COUNT", count_acres, "PYTHON_9.3")
    arcpy.CalculateField_management(route_tbl, "PARK_COUNT", count_parks, "PYTHON_9.3")
    arcpy.RemoveJoin_management(route_tbl)

    # Summarize route layer by GEOID
    geoid_tbl = str(route_tbl) + "_geoidStats"
    arcpy.Statistics_analysis(route_tbl, geoid_tbl, [["ACRE_COUNT", "SUM"], ["PARK_COUNT", "SUM"], ["EXP_COUNT", "SUM"]], "GEOID10")

    # Join back to block and calculate fields
    arcpy.AddJoin_management(block, "GEOID10", geoid_tbl, "GEOID10")
    join_sum_acres = "(!" + geoid_tbl + ".SUM_ACRE_COUNT!)"
    join_sum_parks = "(!" + geoid_tbl + ".SUM_PARK_COUNT!)"
    join_sum_exp = "(!" + geoid_tbl + ".SUM_EXP_COUNT!)"
    arcpy.CalculateField_management(block, "ACRE_COUNT", join_sum_acres, "PYTHON_9.3")
    arcpy.CalculateField_management(block, "PARK_COUNT", join_sum_parks, "PYTHON_9.3")
    arcpy.CalculateField_management(block, "EXP_COUNT", join_sum_exp, "PYTHON_9.3")
    arcpy.RemoveJoin_management(block)
    arcpy.AddMessage("... completed!")

    # Replace null values with 0's in table
    arcpy.AddMessage("Cleaning up null values...")
    with arcpy.da.UpdateCursor(block, ["ACRE_COUNT", "PARK_COUNT", "EXP_COUNT"]) as cursor:
        for row in cursor:
            if row[0] is None:
                row[0] = 0
            if row[1] is None:
                row[1] = 0
            if row[2] is None:
                row[2] = 0    
            cursor.updateRow(row)
            del row
    del cursor
    arcpy.AddMessage("Null values have been set to zero.")
    return

# Adds fields for weights and calculates weighted values
def calculate_weights(block):
    arcpy.AddMessage("Adding weighted fields...")

    arcpy.AddField_management(block, "ACRE_WGT", "DOUBLE", "", "", "", "ACRE_WGT")
    arcpy.AddField_management(block, "PARK_WGT", "DOUBLE", "", "", "", "PARK_WGT")
    arcpy.AddField_management(block, "EXP_WGT", "DOUBLE", "", "", "", "EXP_WGT")

    arcpy.AddMessage("...calculating weighted fields...")
    weight_acres = "(!ACRE_COUNT! *" + weight_multiplier + ")"
    weight_parks = "(!PARK_COUNT! *" + weight_multiplier + ")"
    weight_exp = "(!EXP_COUNT! *" + weight_multiplier + ")"
    arcpy.CalculateField_management(block, "ACRE_WGT", weight_acres, "PYTHON_9.3")
    arcpy.CalculateField_management(block, "PARK_WGT", weight_parks, "PYTHON_9.3")
    arcpy.CalculateField_management(block, "EXP_WGT", weight_exp, "PYTHON_9.3")

################# End Subroutine Definition #############################################################


################# Start Arcpy Configuration & Layer Setup ###############################################
arcpy.AddMessage("Starting up...")

# Ask user to define workspace
arcpy.env.workspace = arcpy.GetParameterAsText(0)
env.overwriteOutput = True 
run_bg = "YES"

# Ask user to assign layers/feature classes
blocks = arcpy.GetParameterAsText(1)
parks = arcpy.GetParameterAsText(2)
mile_routes = arcpy.GetParameterAsText(3)
closest_routes = arcpy.GetParameterAsText(4)
weight_multiplier = arcpy.GetParameterAsText(5)

# Ask user to name and specify output
out_location = arcpy.GetParameterAsText(6)
ouput = arcpy.GetParameterAsText(7)

# layers
blocks_lyr = blocks + "_lyr"
parks_lyr = parks + "_lyr"
mile_routes_lyr = mile_routes + "_lyr"
closest_routes_lyr = closest_routes + "_lyr"

# Create layers
arcpy.MakeFeatureLayer_management(blocks, blocks_lyr)
arcpy.MakeFeatureLayer_management(parks, parks_lyr)
arcpy.MakeFeatureLayer_management(mile_routes, mile_routes_lyr)
arcpy.MakeFeatureLayer_management(closest_routes, closest_routes_lyr)

arcpy.AddMessage("Input paramters set...")
################# End Configuration & Setup ##############################################################


##### Check to see if parks have been joined with experience counts, and make sure that the counts field name is correct #####
lstFields = arcpy.ListFields(parks)
field_names = [f.name.upper() for f in lstFields]  
  
if "TOTAL_COUNT" in field_names:  
    arcpy.AddMessage("Your parks input looks like it has experiences joined. Nice! Let's continue...")
else:  
    arcpy.AddError("{0} does not have the field name 'TOTAL_COUNT'... Please join your experience count table and ensure the total counts field is named 'TOTAL_COUNT'!".format(parks))
    sys.exit()

##### Call Functions #####
route_data(closest_routes_lyr, blocks_lyr)
route_data_mile(mile_routes_lyr, parks_lyr, blocks_lyr)
calculate_weights(blocks_lyr)

arcpy.CopyFeatures_management(blocks_lyr, out_location + "/" + ouput)

arcpy.AddMessage("Completed! Check your block's attribute table.")



