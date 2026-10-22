# Land-cover class key (reference year 2025)

Woody canopy cover = share of ground covered by tree and shrub crowns seen from above,
judged visually on high-resolution imagery. Height is not distinguished.

| ID | Class | Definition |
|---|---|---|
| 1 | Closed woody vegetation | Woody canopy >= 70%; crowns nearly continuous, little or no ground visible. Thickets, hill slopes, drainage lines; often includes taller trees. |
| 2 | Bush savanna | Woody canopy 10-70%; distinct shrubs/trees with ground or grass visible between them. Most encroached rangeland. |
| 3 | Grassland / open | Woody canopy < 10% and ground mostly covered by herbaceous vegetation in the wet season (red in the wet 2025 false colour). Includes cleared blocks where grass has re-established. |
| 4 | Bare / disturbed ground | Woody canopy < 10% and mostly exposed soil or rock even in the wet season (grey/beige/white in the wet 2025 false colour): quarries, construction, fresh clearing, wide gravel areas, pan floors. |
| 5 | Built-up | Buildings, paved surfaces and yards. |

## Decision rules for edge cases
- Scattered tall trees in grass: count their crowns; if total canopy < 10% -> Grassland / open.
- Cleared block with resprouting shrubs: judge the canopy as it is now (2025), not before clearing.
- Grass vs bare is decided on the wet-season (Dec 2024-Mar 2025) image, never on the dry season alone.
- Pans: grass-covered in the wet season -> Grassland / open; otherwise -> Bare.
- Paved roads in town -> Built-up; gravel tracks narrower than ~10 m are not mapped as a class.
- Mixed areas: assign the class covering the majority of the area being judged.

## Excluded on purpose
- Water: pans are seasonal and dry most of the year; surface water is mapped separately as occurrence (pack item 4).
- Cropland / irrigated land: none present in the AOI in 2025.
- Woodland (tall trees) as its own class: not reliably separable from dense bush at 10 m.

## Change log
- 2026-10-22: Class 1 threshold raised from 40% to 70% (closed woody vegetation) and class 2 widened to 10-70%, to match how training areas were actually interpreted.

## Change log
- 2026-10-22: Class 1 threshold raised from 40% to 70% (closed woody vegetation) and class 2 widened to 10-70%, to match how training areas were actually interpreted.
- 2026-10-22: Grassland vs bare redefined by wet-season vegetation cover; classes 3 and 4 re-digitised.
