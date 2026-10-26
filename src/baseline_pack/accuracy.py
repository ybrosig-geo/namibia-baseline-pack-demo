"""Accuracy assessment after Olofsson et al. (2014): 30 m assessment blocks,
stratified random sampling by map class; estimators follow in Session 9."""
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from rasterio.transform import Affine
from shapely.geometry import Point, box


def mode_aggregate(arr, factor=3, nodata=0):
    """Majority class per factor x factor block; ties -> centre pixel; nodata ignored."""
    h, w = (arr.shape[0] // factor) * factor, (arr.shape[1] // factor) * factor
    blocks = (arr[:h, :w].reshape(h // factor, factor, w // factor, factor)
              .swapaxes(1, 2).reshape(h // factor, w // factor, factor * factor))
    classes = range(1, int(arr.max()) + 1)
    counts = np.stack([(blocks == c).sum(axis=2) for c in classes], axis=-1)
    top = counts.max(axis=-1)
    tie = (counts == top[..., None]).sum(axis=-1) > 1
    out = np.where(tie, blocks[..., (factor * factor) // 2], counts.argmax(axis=-1) + 1)
    out[top == 0] = nodata
    return out.astype(np.uint8)


def assessment_map(tif, aoi_gdf, factor=3):
    """30 m block map, restricted to blocks whose centre lies inside the AOI."""
    with rasterio.open(tif) as src:
        arr, t, crs = src.read(1), src.transform, src.crs
    agg = mode_aggregate(arr, factor)
    t30 = t * Affine.scale(factor)
    inside = rasterize([(g, 1) for g in aoi_gdf.to_crs(crs).geometry], out_shape=agg.shape,
                       transform=t30, fill=0, all_touched=False)
    return np.where(inside == 1, agg, 0).astype(np.uint8), t30, crs


def allocate(counts, n_total, minimum):
    """Each class gets its minimum (capped by availability); the rest is shared in proportion to area."""
    N = pd.Series(counts, dtype=float); W = N / N.sum()
    n = pd.Series({c: min(minimum.get(c, 50), int(N[c])) for c in N.index}, dtype=float)
    rest = max(n_total - n.sum(), 0)
    n = (n + (rest * W).round()).clip(upper=N)
    return n.astype(int).to_dict()


def expected_se_overall(counts, n_h, expected_ua):
    """Expected standard error of overall accuracy (stratified estimator), from guessed user's accuracies."""
    N = pd.Series(counts, dtype=float); W = N / N.sum()
    var = sum(W[c] ** 2 * expected_ua[c] * (1 - expected_ua[c]) / max(n_h[c] - 1, 1) for c in N.index)
    return float(np.sqrt(var))


def draw_sample(agg, t30, crs, n_h, seed=42):
    """Random blocks per stratum; shuffled; returns centre points and 30 m block outlines."""
    rng = np.random.default_rng(seed)
    rows = []
    for c, n in n_h.items():
        r, k = np.nonzero(agg == c)
        for i in rng.choice(len(r), size=min(n, len(r)), replace=False):
            x, y = t30 * (k[i] + 0.5, r[i] + 0.5)
            rows.append({"stratum": int(c), "x": x, "y": y})
    df = pd.DataFrame(rows).sample(frac=1, random_state=seed).reset_index(drop=True)
    df.insert(0, "ref_id", range(1, len(df) + 1))
    half = abs(t30.a) / 2
    pts = gpd.GeoDataFrame(df, geometry=[Point(x, y) for x, y in zip(df.x, df.y)], crs=crs)
    cells = gpd.GeoDataFrame(df.copy(), crs=crs,
                             geometry=[box(x - half, y - half, x + half, y + half) for x, y in zip(df.x, df.y)])
    return pts, cells
