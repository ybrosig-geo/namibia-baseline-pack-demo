"""Extract training pixels once (batch export, no time limit), then balance locally."""
import glob, shutil, time
import ee
import pandas as pd
from baseline_pack.aoi import gdf_to_ee

PROJ = ee.Projection("EPSG:32733").atScale(10)
DRIVE_EXPORT_DIR = "/content/drive/MyDrive/baseline_pack_exports"


def extract_pixels_to_csv(stack, train_gdf, out_csv, name):
    """One Earth Engine export of all pixels inside the polygons (with coordinates) -> CSV in the repo."""
    fc = gdf_to_ee(train_gdf[["class_id", "poly_id", "split", "geometry"]])
    pts = stack.sampleRegions(collection=fc, properties=["class_id", "poly_id", "split"],
                              projection=PROJ, tileScale=4, geometries=True)
    task = ee.batch.Export.table.toDrive(collection=pts, description=name, folder="baseline_pack_exports",
                                         fileNamePrefix=name, fileFormat="CSV")
    task.start()
    while task.active():
        print("Export running…", task.status()["state"]); time.sleep(30)
    if task.status()["state"] != "COMPLETED":
        raise RuntimeError(task.status())
    for _ in range(20):                       # Drive can take a minute to show the file
        hits = glob.glob(f"{DRIVE_EXPORT_DIR}/{name}*.csv")
        if hits:
            shutil.copy(hits[0], out_csv)
            return pd.read_csv(out_csv)
        time.sleep(15)
    raise FileNotFoundError("Export done but CSV not visible yet - wait a minute and rerun this cell.")


def balance(df, max_per_polygon=40, max_per_class=300, seed=42):
    """At most max_per_polygon pixels per polygon, then a per-class cap for train (test gets half).
    max_per_class: one number for all classes, or a dict {class_id: n} to weight dominant classes more."""
    df = df.sample(frac=1, random_state=seed).groupby("poly_id", group_keys=False).head(max_per_polygon)
    cap = (lambda c: max_per_class.get(c, 300)) if isinstance(max_per_class, dict) else (lambda c: max_per_class)
    parts = [g.head(cap(c) if s == "train" else cap(c) // 2)
             for (c, s), g in df.groupby(["class_id", "split"])]
    return pd.concat(parts).reset_index(drop=True)
    
def to_fc(df, features):
    """Upload a small sample table to Earth Engine (no geometry needed for training)."""
    recs = []
    for r in df[features + ["class_id", "poly_id", "split"]].to_dict("records"):
        props = {k: float(r[k]) for k in features}
        props.update(class_id=int(r["class_id"]), poly_id=int(r["poly_id"]), split=str(r["split"]))
        recs.append(ee.Feature(None, props))
    return ee.FeatureCollection(recs)
