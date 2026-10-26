"""Land-cover classification: features, training samples, Random Forest, area table."""
import ee
import numpy as np
import pandas as pd
from baseline_pack.aoi import gdf_to_ee

SEED = 42
PROJ = ee.Projection("EPSG:32733").atScale(10)


def feature_stack(dry, wet, topo, texture=True):
    """Both seasons, wet-minus-dry NDVI, terrain, and (optionally) dry-season NDVI texture:
    local standard deviation in 3x3 and 5x5 pixel windows (smooth = closed canopy, speckled = open bush)."""
    dndvi = wet.select("wet_NDVI").subtract(dry.select("dry_NDVI")).rename("dNDVI")
    stack = dry.addBands(wet).addBands(dndvi).addBands(topo)
    if texture:
        ndvi10 = dry.select("dry_NDVI").reproject(PROJ)      # fix the grid to 10 m UTM before the window
        sd3 = ndvi10.reduceNeighborhood(ee.Reducer.stdDev(), ee.Kernel.square(1)).rename("dry_NDVI_sd3")
        sd5 = ndvi10.reduceNeighborhood(ee.Reducer.stdDev(), ee.Kernel.square(2)).rename("dry_NDVI_sd5")
        stack = stack.addBands([sd3, sd5])
    return stack.float()

def prepare_training(gdf, inner_buffer_m=5, holdout_frac=0.3, seed=SEED):
    """Shrink polygons by half a pixel (only fully-interior pixels are sampled), then send whole
    polygons to 'test' until ~30% of each class's AREA is held out."""
    g = gdf[["class_id", "geometry"]].copy()
    g["geometry"] = g.buffer(-inner_buffer_m)
    g = g[g.geometry.notna() & ~g.geometry.is_empty].copy()
    g["class_id"] = g["class_id"].astype(int)
    g["poly_id"] = range(len(g))
    g["split"] = "train"
    rng = np.random.default_rng(seed)
    for _, grp in g.groupby("class_id"):
        order = rng.permutation(grp.index)
        target, held = holdout_frac * grp.area.sum(), 0.0
        for idx in order:
            if held >= target or len(order) - (g.loc[order, "split"] == "test").sum() <= 1:
                break
            g.loc[idx, "split"] = "test"
            held += grp.area[idx]
    return g


def sample_pixels(stack, train_gdf, max_per_class=300, max_per_polygon=40, seed=SEED):
    """All pixels inside the polygons (pts), and a balanced subset: at most max_per_polygon
    from any single polygon (so no field dominates), then at most max_per_class per class/split."""
    fc = gdf_to_ee(train_gdf[["class_id", "poly_id", "split", "geometry"]])
    pts = stack.sampleRegions(collection=fc, properties=["class_id", "poly_id", "split"],
                              projection=PROJ, tileScale=4).randomColumn("rnd", seed)
    per_poly = ee.FeatureCollection([
        pts.filter(ee.Filter.eq("poly_id", int(p))).sort("rnd").limit(max_per_polygon)
        for p in train_gdf["poly_id"]]).flatten()
    balanced = ee.FeatureCollection([])
    for c in sorted(train_gdf["class_id"].unique().tolist()):
        for split, n in (("train", max_per_class), ("test", max_per_class // 2)):
            sub = per_poly.filter(ee.Filter.And(ee.Filter.eq("class_id", c), ee.Filter.eq("split", split)))
            balanced = balanced.merge(sub.sort("rnd").limit(n))
    return pts, balanced


def pixel_counts(pts, classes):
    """How many usable pixels each class has, per split."""
    d = {f"{c}_{s}": pts.filter(ee.Filter.And(ee.Filter.eq("class_id", c), ee.Filter.eq("split", s))).size()
         for c in classes for s in ("train", "test")}
    r = ee.Dictionary(d).getInfo()
    return pd.DataFrame([{"class_id": c, "train_px": r[f"{c}_train"], "test_px": r[f"{c}_test"]}
                         for c in classes]).set_index("class_id")


def train_rf(samples, features, n_trees=300, seed=SEED):
    return ee.Classifier.smileRandomForest(numberOfTrees=n_trees, seed=seed).train(samples, "class_id", features)


def holdout_check(clf, test, classes, names):
    """Diagnostic confusion matrix on held-out polygons. Rows = true class, columns = predicted."""
    m = test.classify(clf).errorMatrix("class_id", "classification", classes)
    cm = pd.DataFrame(m.getInfo(), index=[names[c] for c in classes], columns=[names[c] for c in classes])
    per_class = pd.DataFrame({
        "producer_acc_%": (100 * np.diag(cm) / cm.sum(axis=1)).round(1),   # of the true X, how many found
        "user_acc_%": (100 * np.diag(cm) / cm.sum(axis=0)).round(1)})      # of pixels called X, how many right
    return cm, per_class, round(100 * np.trace(cm.values) / cm.values.sum(), 1)


def class_area_table(classified, region, names, scale=10):
    """Mapped area per class (pixel counting). NOT the final reported area (see Session 9)."""
    img = ee.Image.pixelArea().divide(1e4).addBands(classified)
    groups = img.reduceRegion(ee.Reducer.sum().group(groupField=1, groupName="class"), region,
                              scale=scale, crs="EPSG:32733", maxPixels=1e10).get("groups").getInfo()
    df = pd.DataFrame(groups).rename(columns={"sum": "area_ha"})
    df["class_name"] = df["class"].map(names)
    df["percent"] = (100 * df["area_ha"] / df["area_ha"].sum()).round(1)
    df["area_ha"] = df["area_ha"].round(1)
    return df.set_index("class")[["class_name", "area_ha", "percent"]]

def apply_water_rule(lc, dry, wet, min_pixels=3, water_class=5):
    """Permanent water = water-like in BOTH seasonal composites (MNDWI > 0 and NDVI < 0),
    at least min_pixels connected. Applied after classification; seasonal pans keep their RF class."""
    water = (dry.select("dry_MNDWI").gt(0).And(dry.select("dry_NDVI").lt(0))
             .And(wet.select("wet_MNDWI").gt(0)).And(wet.select("wet_NDVI").lt(0))).reproject(PROJ)
    big = water.selfMask().connectedPixelCount(100, True).gte(min_pixels).unmask(0)
    return lc.where(water.And(big), water_class).rename("class").toByte()