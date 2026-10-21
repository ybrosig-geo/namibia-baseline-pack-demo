"""Dry-season NDVI time series (Landsat 8/9 C2 L2), CHIRPS rain-year totals, trend statistics."""
import ee
import numpy as np
import pandas as pd
from scipy import stats
from baseline_pack.composites import season_dates

LANDSAT = ["LANDSAT/LC08/C02/T1_L2", "LANDSAT/LC09/C02/T1_L2"]


def _landsat_ndvi(img):
    """Mask clouds/shadows/saturation, scale to reflectance, compute NDVI."""
    qa = img.select("QA_PIXEL")
    bad = (qa.bitwiseAnd(1 << 1).neq(0)      # dilated cloud
           .Or(qa.bitwiseAnd(1 << 2).neq(0))  # cirrus
           .Or(qa.bitwiseAnd(1 << 3).neq(0))  # cloud
           .Or(qa.bitwiseAnd(1 << 4).neq(0)))  # cloud shadow
    ok = bad.Not().And(img.select("QA_RADSAT").eq(0))
    sr = img.select(["SR_B4", "SR_B5"]).multiply(0.0000275).add(-0.2)
    ndvi = sr.normalizedDifference(["SR_B5", "SR_B4"]).rename("NDVI").updateMask(ok)
    return ee.Image(ndvi.copyProperties(img, ["system:time_start"]))


def landsat_ndvi(region, start, end):
    col = ee.ImageCollection(LANDSAT[0]).merge(ee.ImageCollection(LANDSAT[1]))
    return col.filterBounds(region).filterDate(start, end).map(_landsat_ndvi)


def annual_season_ndvi(region, years, months):
    """One image per year: median NDVI of the season, clear-obs count, and a 'year' band."""
    imgs = []
    for y in years:
        start, end = season_dates(y, months)
        col = landsat_ndvi(region, start, end)
        med = col.median().rename("NDVI")
        n = col.count().rename("n_obs")
        year_band = ee.Image.constant(y).float().rename("year").updateMask(med.mask())
        imgs.append(year_band.addBands(med).addBands(n).clip(region)
                    .set("year", y, "system:time_start", ee.Date.fromYMD(y, months[0], 1).millis()))
    return ee.ImageCollection.fromImages(imgs)


def sens_slope_image(annual):
    """Per-pixel Sen's slope (NDVI per year) and offset."""
    return annual.select(["year", "NDVI"]).reduce(ee.Reducer.sensSlope())


def region_ndvi_table(annual, region, scale=30):
    """AOI mean NDVI and minimum clear observations per year -> DataFrame."""
    def f(img):
        mean = img.select("NDVI").reduceRegion(ee.Reducer.mean(), region, scale, maxPixels=1e9)
        nmin = img.select("n_obs").reduceRegion(ee.Reducer.min(), region, scale, maxPixels=1e9)
        return ee.Feature(None, {"year": img.get("year"), "ndvi_mean": mean.get("NDVI"),
                                 "min_obs": nmin.get("n_obs")})
    feats = ee.FeatureCollection(annual.map(f)).getInfo()["features"]
    return pd.DataFrame([x["properties"] for x in feats]).sort_values("year").set_index("year")


def rain_year_totals(region, years, start_month=7, scale=5566):
    """CHIRPS total rain (mm) for rain year Jul(Y-1)-Jun(Y), AOI mean -> Series."""
    chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").select("precipitation")
    out = {}
    for y in years:
        start = ee.Date.fromYMD(y - 1, start_month, 1)
        total = chirps.filterDate(start, start.advance(1, "year")).sum()
        out[str(y)] = total.reduceRegion(ee.Reducer.mean(), region, scale).get("precipitation")
    d = ee.Dictionary(out).getInfo()
    return pd.Series({int(k): v for k, v in d.items()}, name="rain_mm").sort_index()


def trend_stats(x, y):
    """Sen's slope + Mann-Kendall (Kendall's tau vs time) for a short series."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    slope, intercept, lo, hi = stats.theilslopes(y, x)
    tau, p = stats.kendalltau(x, y)
    return {"sen_slope_per_yr": slope, "slope_95ci_low": lo, "slope_95ci_high": hi,
            "kendall_tau": tau, "p_value": p}


def restrend(df, ndvi_col="ndvi_mean", rain_col="rain_mm"):
    """Rain-adjusted trend: regress NDVI on rain, then test the residuals for a trend over time."""
    fit = stats.linregress(df[rain_col], df[ndvi_col])
    resid = df[ndvi_col] - (fit.intercept + fit.slope * df[rain_col])
    return {"ndvi_vs_rain_r2": fit.rvalue ** 2, "ndvi_vs_rain_p": fit.pvalue,
            **{f"residual_{k}": v for k, v in trend_stats(df.index, resid).items()}}, resid
