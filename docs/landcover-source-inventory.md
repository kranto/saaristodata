# Complementary land-cover source inventory

Updated 2026-11-11.

## Recommended pilot source

Syke's **Maanpeite 2 m 2022** is the recommended base source for the first
pilot. It is a nationwide categorical raster with 2 m pixels, licensed under
CC BY 4.0. A WCS 2.0.1 service can return a bounded GeoTIFF without an API key.

Useful classes for the pilot are:

| Source value | Source class | Pilot class |
| ---: | --- | --- |
| 211 | field | `farmland` |
| 212 | other low vegetation | `open` |
| 220 | high vegetation | `forest` |
| 310 | bare rock | `rock` |
| 410 | bare land | `bare` |

The name `forest` is a cartographic simplification. Source class 220 means
high vegetation and can include vegetation that is not forest. The more
detailed canopy-height derivative does not have complete canopy-height input
on Åland, so the base product is used consistently on both sides of the
regional boundary.

Source metadata:

- https://luontotieto.syke.fi/en/aineisto/maanpeite-2-m-2022-ja-jatkojaloste-kasvillisuuden-korkeudella-2/
- WCS coverage: `Maanpeite2022Scalgo`
- CRS: EPSG:3067
- Required attribution: Syke, Maanpeite 2 m 2022

## Syke CORINE Land Cover 2024

CORINE 2024 is a second nationwide option. Its national raster has 20 m pixels
and was published in September 2026. It provides richer semantic land-cover
classes, including wetlands, but less spatial detail than Maanpeite 2 m 2022.
It is a candidate for adding wetland semantics or for comparison, not the
first pilot geometry source.

Source:

- https://www.syke.fi/fi/ymparistotieto/ladattavat-paikkatietoaineistot

## National Land Survey Topographic Database

The Topographic Database is useful as a supplemental vector source, not as the
sole land-cover source.

Polygon classes relevant to this work include:

| Purpose | Classes |
| --- | --- |
| Farmland and garden | 32611, 32612 |
| Meadow | 32800 |
| Thin peat / paludified ground | 35300 |
| Mires | 35411, 35412, 35421, 35422 |
| Open forest land and other open areas | 39110, 39120, 39130 |

The forest vegetation classes 32710, 32713, 32714, 32715 and 32719 are stored
as cartographic points. They describe dominant vegetation but do not delineate
continuous forest polygons. Consequently, the database cannot fill the map's
forest gaps by itself.

The open OGC API Features endpoint requires a user-specific API key. A manually
downloaded bounded GeoPackage remains another possible ingestion path.

Sources:

- https://www.maanmittauslaitos.fi/media/31472/download
- https://www.maanmittauslaitos.fi/maastotietokannan-kyselypalvelu

## New National Topographic Database (KMTK)

MML is replacing the old Topographic Database with KMTK. As of November 2026,
the nationwide GeoPackage and change feed are still marked as beta and must not
be used in production. MML also states that KMTK is intended for analysis and
data integration rather than direct cartographic products. The production
pipeline must therefore not depend on the beta schema.

Source:

- https://www.maanmittauslaitos.fi/kartat-ja-paikkatieto/aineistot-ja-rajapinnat/maastotiedot-ja-niiden-hankinta/maastotiedot

