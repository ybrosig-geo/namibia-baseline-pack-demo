"""Sentinel-2 seasonal composites (Cloud Score+ masking), spectral indices and terrain."""
import ee

S2_BANDS = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"]
CS_THRESHOLD = 0.60  # Cloud Score+ 'cs_cdf': keep pixels >= this


def season_dates(year, months):
    """Season dates, named after the year it ends in. [12, 3] + 2025 -> 1 Dec 2024 to 1 Apr 2025."""
    start_year = year - 1 if months[0] > months[1] else year
    start = ee.Date.fromYMD(start_year, months[0], 1)
    end = ee.Date.fromYMD(year, months[1], 1).advance(1, "month")
    return start, end


def s2_clear_collection(region, year, months, cs_threshold=CS_THRESHOLD, max_scene_cloud=80):
    """Sentinel-2 SR scenes for one season, cloud-masked with Cloud Score+, reflectance 0-1."""
    start, end = season_dates(year, months)
    s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
          .filterBounds(region).filterDate(start, end)
          .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_scene_cloud)))
    cs = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")

    def mask(img):
        clear = img.select("cs_cdf").gte(cs_threshold)
        out = img.select(S2_BANDS).updateMask(clear).divide(10000)
        return ee.Image(out.copyProperties(img, ["system:time_start"]))

    return s2.linkCollection(cs, ["cs_cdf"]).map(mask)


def add_indices(img):
    """NDVI (greenness), NDMI (moisture), MNDWI (water), BSI (bare soil)."""
    ndvi = img.normalizedDifference(["B8", "B4"]).rename("NDVI")
    ndmi = img.normalizedDifference(["B8", "B11"]).rename("NDMI")
    mndwi = img.normalizedDifference(["B3", "B11"]).rename("MNDWI")
    bsi = img.expression("((S + R) - (N + B)) / ((S + R) + (N + B))",
                         {"S": img.select("B11"), "R": img.select("B4"),
                          "N": img.select("B8"), "B": img.select("B2")}).rename("BSI")
    return img.addBands([ndvi, ndmi, mndwi, bsi])


def seasonal_composite(region, year, months, label, **kwargs):
    """Median composite + indices, band names prefixed (e.g. 'dry_NDVI').
    Returns (composite, clear_obs_count_image, number_of_scenes)."""
    col = s2_clear_collection(region, year, months, **kwargs)
    comp = add_indices(col.median())
    comp = comp.rename(comp.bandNames().map(lambda b: ee.String(label + "_").cat(b)))
    count = col.select("B4").count().rename(label + "_clear_obs")
    return comp.clip(region), count.clip(region), col.size()


def terrain(region):
    """Copernicus DEM GLO-30 elevation (m) and slope (degrees)."""
    col = ee.ImageCollection("COPERNICUS/DEM/GLO30_2024_1").filterBounds(region).select("DEM")
    dem = col.mosaic().setDefaultProjection(col.first().projection()).rename("elevation")
    return dem.addBands(ee.Terrain.slope(dem).rename("slope")).clip(region)


def count_summary(count_img, region, scale=20):
    """Min / mean / max clear observations per pixel over the region."""
    reducer = ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True)
    return count_img.reduceRegion(reducer, region, scale, maxPixels=1e9).getInfo()
