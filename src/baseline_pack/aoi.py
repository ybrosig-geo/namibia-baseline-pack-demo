"""AOI helpers: build square study areas in UTM and convert to Earth Engine."""
import json
import ee
import geopandas as gpd
from shapely.geometry import Point

EPSG = 32733  # WGS 84 / UTM zone 33S


def square_aoi(lon, lat, half_size_m=10_000, epsg=EPSG, shift_e_m=0, shift_n_m=0):
    """Square AOI (side = 2*half_size_m) centred on lon/lat, optionally shifted in metres."""
    pt = gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(epsg)
    sq = pt.buffer(half_size_m, cap_style=3).translate(shift_e_m, shift_n_m)
    return gpd.GeoDataFrame(geometry=sq, crs=epsg)


def buffer_aoi(aoi_gdf, buffer_m=2000):
    """Buffer that keeps square corners (join_style=2 = mitre)."""
    return gpd.GeoDataFrame(geometry=aoi_gdf.buffer(buffer_m, join_style=2), crs=aoi_gdf.crs)


def gdf_to_ee(gdf):
    """GeoDataFrame -> ee.FeatureCollection (via WGS84 GeoJSON)."""
    return ee.FeatureCollection(json.loads(gdf.to_crs(4326).to_json()))
