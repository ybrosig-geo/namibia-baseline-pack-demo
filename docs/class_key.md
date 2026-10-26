# Land-cover class key (reference year 2025)

Woody canopy cover = share of ground covered by tree and shrub crowns seen from above,
judged visually on high-resolution imagery and 2025 Sentinel-2 false colour. Height is not distinguished.

| ID | Class | Definition |
|---|---|---|
| 1 | Closed woody vegetation | Woody canopy >= 70%; crowns nearly continuous, little or no ground visible. Thickets, hill slopes, drainage lines; often includes taller trees. |
| 2 | Bush savanna | Woody canopy 10-70%; distinct shrubs/trees with ground or grass visible between them. Most encroached rangeland. |
| 3 | Open land (grass or bare) | Woody canopy < 10%: grassland, sparse grass, exposed soil or rock, cleared ground, pans, wide gravel areas. |
| 4 | Built-up | Buildings, paved surfaces and yards. |
| 5 | Water (permanent) | Open water in both the wet (Dec-Mar) and dry (Jun-Sep) 2025 composites (MNDWI > 0 and NDVI < 0 in both), at least 3 connected pixels. Assigned by rule after classification. |

## Decision rules
- Scattered trees in open land: count their crowns; total canopy < 10% -> Open land.
- Cleared blocks: judged as they are in 2025, not before clearing.
- Paved roads in town -> Built-up; gravel tracks narrower than ~10 m are not mapped separately.
- Mixed areas: the class covering the majority of the area being judged.

## Excluded on purpose
- Seasonal water (pans): classified as Open land; how often water appears is mapped separately (pack item 4).
- Cropland / irrigated land: none present in the AOI in 2025.
- Tall-tree woodland as its own class: not reliably separable from dense bush at 10 m.

## Change log
- 2026-10-22: Class 1 threshold raised from 40% to 70% and class 2 widened to 10-70%, to match how training areas were interpreted.
- 2026-10-22: Grassland and bare ground were digitised separately but merged into 'Open land'. Their wet-season NDVI overlapped strongly
  (grassland polygons 0.18-0.37, bare 0.08-0.24), so they were not reliably separable at 10 m. Original labels are kept in training.gpkg;
  clearing and bare-ground change is reported in the disturbance footprint instead.
- 2026-10-26: Final map from AlphaEarth embeddings (holdout 81% vs 68% spectral). Permanent water added as class 5 by a post-classification rule; seasonal pans stay Open land.
