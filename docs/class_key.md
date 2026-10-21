# Land-cover class key (reference year 2025)

Woody canopy cover = share of ground covered by tree and shrub crowns seen from above,
judged visually on high-resolution imagery. Height is not distinguished.

| ID | Class | Definition |
|---|---|---|
| 1 | Dense bush | Woody canopy >= 40%; crowns mostly touching. Includes scattered taller trees. |
| 2 | Open bush / shrub savanna | Woody canopy 10-40%; separate shrubs/trees with grass between. |
| 3 | Grassland / open | Woody canopy < 10%; includes cleared blocks now dominated by grass. |
| 4 | Bare / disturbed ground | Mostly exposed soil or rock: wide gravel tracks, quarries, fresh clearing, construction, dry pan floors. |
| 5 | Built-up | Buildings, paved surfaces and yards. |

## Decision rules for edge cases
- Scattered tall trees in grass: count their crowns; if total canopy < 10% -> Grassland / open.
- Cleared block with resprouting shrubs: judge the canopy as it is now (2025), not before clearing.
- Pans: bare floor in the 2025 dry season -> Bare; grass-covered -> Grassland / open.
- Paved roads in town -> Built-up; gravel tracks narrower than ~10 m are not mapped as a class.
- Mixed areas: assign the class covering the majority of the area being judged.

## Excluded on purpose
- Water: pans are seasonal and dry most of the year; surface water is mapped separately as occurrence (pack item 4).
- Cropland / irrigated land: none present in the AOI in 2025.
- Woodland (tall trees) as its own class: not reliably separable from dense bush at 10 m.
