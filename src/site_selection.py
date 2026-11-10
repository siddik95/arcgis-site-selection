# -*- coding: utf-8 -*-
"""
Site Selection — Fort Collins, CO
=================================

Cleaned-up, parameterized version of the ArcGIS Pro ModelBuilder model
"SiteSelection" (original export: modelbuilder/SiteSelection_export.py).

Finds vacant parcels that are:
  * within 1 mile of the city limits,
  * within 300 ft of a river,
  * outside the flood plain,
  * more than 300 ft from residential parcels and parks,
  * larger than a minimum area (default 50,000 in the output's area units).

Requires ArcGIS Pro (arcpy).

Usage — from the ArcGIS Pro Python window:
    import site_selection
    site_selection.site_selection(
        river="Hydro", city_limits="City Limits", parks="Parks",
        residential="Residential Parcels", flood_plain="Flood Plain",
        vacant_parcels="Vacant Parcels", out_gdb=r"C:\\data\\FtCollins.gdb")

Usage — from the command line (ArcGIS Pro's Python, e.g. propy.bat):
    propy site_selection.py C:\\data\\FtCollins.gdb --overwrite
"""
import argparse
import os

import arcpy


def site_selection(
    river,
    city_limits,
    parks,
    residential,
    flood_plain,
    vacant_parcels,
    out_gdb,
    river_dist="300 Feet",
    city_dist="1 Miles",
    residential_dist="300 Feet",
    parks_dist="300 Feet",
    min_area=50000,
    overwrite=False,
):
    """Run the site-selection workflow and return the path to the candidate parcels."""
    arcpy.env.overwriteOutput = overwrite

    def out(name):
        return os.path.join(out_gdb, name)

    # 1. Areas to avoid: buffers around residential parcels and parks
    res_buf = out("ResBuf")
    arcpy.analysis.Buffer(residential, res_buf, residential_dist, dissolve_option="ALL")

    parks_buf = out("ParksBuf")
    arcpy.analysis.Buffer(parks, parks_buf, parks_dist, dissolve_option="ALL")

    # 2. Combine everything unsuitable (flood plain + both buffers) into one layer
    #    (the model did this with Create Feature Class + Append)
    unsuitable = out("Unsuitable")
    arcpy.management.Merge([flood_plain, res_buf, parks_buf], unsuitable)

    # 3. Areas that are required: near the city AND near the river
    city_buf = out("CityBuf")
    arcpy.analysis.Buffer(city_limits, city_buf, city_dist, dissolve_option="ALL")

    river_buf = out("RiverBuf")
    arcpy.analysis.Buffer(river, river_buf, river_dist, dissolve_option="ALL")

    must_be_in = out("MustBeIn")
    arcpy.analysis.Clip(city_buf, river_buf, must_be_in)

    # 4. Suitable areas = required areas minus unsuitable areas
    suitable = out("SuitableAreas")
    arcpy.analysis.Erase(must_be_in, unsuitable, suitable)

    # 5. Vacant parcels (portions) that fall inside suitable areas
    vacant_suitable = out("VacantSuitable")
    arcpy.analysis.Clip(vacant_parcels, suitable, vacant_suitable)

    # 6. Keep only those large enough
    candidates = out("Candidates")
    arcpy.analysis.Select(vacant_suitable, candidates, f"Shape_Area > {min_area}")

    count = int(arcpy.management.GetCount(candidates)[0])
    arcpy.AddMessage(f"{count} candidate parcel(s) written to {candidates}")
    return candidates


def main():
    p = argparse.ArgumentParser(description="ArcGIS Pro site-selection workflow")
    p.add_argument("out_gdb", help="File geodatabase holding inputs and receiving outputs")
    p.add_argument("--river", default="Hydro")
    p.add_argument("--city-limits", default="City Limits")
    p.add_argument("--parks", default="Parks")
    p.add_argument("--residential", default="Residential Parcels")
    p.add_argument("--flood-plain", default="Flood Plain")
    p.add_argument("--vacant-parcels", default="Vacant Parcels")
    p.add_argument("--min-area", type=float, default=50000)
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs")
    a = p.parse_args()

    with arcpy.EnvManager(workspace=a.out_gdb, scratchWorkspace=a.out_gdb):
        site_selection(
            a.river, a.city_limits, a.parks, a.residential, a.flood_plain,
            a.vacant_parcels, a.out_gdb, min_area=a.min_area, overwrite=a.overwrite,
        )


if __name__ == "__main__":
    main()
