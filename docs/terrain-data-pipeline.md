# Maastoaineistojen käsittely- ja julkaisuohje

Tämä on KMTK-maanpeitteen, Syke-metsätäytön, korkeuskäyrien ja
rinnevarjostuksen kanoninen päästä päähän -ohje. Lähteiden, alueen ja
luokkamuunnosten koneellisesti luettava totuus on tiedostossa
`data-sources/landcover.yml`. Skriptit ovat hakemistoissa
`scripts/landcover/` ja `scripts/terrain/`.

## Lopputulos ja piirtojärjestys

OpenFreeMap-maastokartassa aineistot muodostavat seuraavan kokonaisuuden:

1. OpenFreeMap on varsinainen pohjakartta.
2. Syken metsäpolygoni täydentää puuttuvaa yhtenäistä metsäpeitettä.
3. KMTK:n tarkemmat luokat piirretään Syken päälle.
4. Pienillä zoomeilla KMTK ja Syke korvataan niistä etukäteen sommitellulla
   rasterilla, jotta selain ei lataa ja käsittele raskaita vektoritiiliä.
5. Rinnevarjostus ja korkeuskäyrät ovat erillisiä, käyttäjän valittavia
   maastokartan tasoja.

KMTK:ssa ei ole yhtenäistä metsäpolygonia. Siksi Syke toimii alimpana
täyttöaineistona; se ei korvaa KMTK:n avokallioita, peltoja, soita tai muita
tarkempia kohteita. Oletuskartta käyttää lisäksi erillistä, kevyttä KMTK:n
`urban_area`-aineistoa. Pienten zoomien maastorasteri ei sisällä tätä
oletuskartan urban-arkistoa.

### Julkaistavat tiedostot

| Tiedosto | Sisältö | Sijainti repossa |
|---|---|---|
| `terrain-landcover-overview-r1.pmtiles` | KMTK + Syke valmiina WebP-rasterina | `tiles/` |
| `terrain-landcover-r1.pmtiles` | KMTK:n maastoluokat vektoreina | `tiles/` |
| `terrain-landcover-fill-r1.pmtiles` | rantaan maskattu ja pehmennetty Syke-metsä | `tiles/` |
| `terrain-landcover-detail-r1.pmtiles` | oletuskartan KMTK-urban | `tiles/` |
| `terrain-contour-5m-r1.pmtiles` | kaikki viidellä metrillä jaolliset käyrät | `raw/landcover/terrain-test/` |
| `terrain-contour-10m-r1.pmtiles` | 10 metrillä jaollisten käyrien osajoukko | `raw/landcover/terrain-test/` |
| `terrain-hillshade-r1.pmtiles` | rantaan maskattu MML Rinnevarjoste 8 m | `raw/landcover/terrain-test/` |

Suuret raakadata-, välituote- ja PMTiles-tiedostot on tarkoituksella ohitettu
Gitissä. Gitissä säilytetään skriptit, konfiguraatio, käsittelyraportit ja
tarkisteet. Paikallinen `raw/` on säilytettävä: ladattujen lähtöaineistojen
uudelleenkäyttö tekee myöhemmistä tyylin, pakkauksen, maskin tai zoomrajan
muutoksista nopeita eikä ulkoisia rajapintoja tarvitse rasittaa uudelleen.

## Aluerajaus

Nykyinen alue on manifestin `pilot-archipelago-sea`. Historiallinen `pilot`-
nimi on säilytetty toistettavuuden vuoksi, vaikka kyse on koko julkaistavasta
alueesta.

- latausvaippa: W 19.00, S 59.70, E 23.58061, N 60.75826
- pääalue: W 19.00, S 59.70, E 23.00, N 60.75826
- itälaajennus: W 22.62179, S 59.71622, E 23.58061, N 60.53005
- poistettava koillisalue: W 22.23415, S 60.55430, E 24.69488, N 61.45784
- ehdoton pohjoisraja: N 60.75826

`area_clip_geometry()` muodostaa include-suorakaiteiden unionin, leikkaa sen
pohjoisrajaan ja vähentää exclude-alueet. Samaa geometriaa käyttävät KMTK,
Syke, käyrät, rinnevarjostus ja rantamaski, joten kaikkien aineistojen pitäisi
päättyä samaan rajaan kaikilla zoomeilla. Aluetta muutettaessa päivitetään vain
`data-sources/landcover.yml` ja rakennetaan kaikki johdannaiset uudelleen.

## Zoomit: rasteri vai vektori

Sovelluksen lopullinen vaihtoraja on MapLibre-zoom 12:

| MapLibre-kartan zoom | Maanpeite |
|---|---|
| alle 8 | vain OpenFreeMap |
| 8.00–8.99 | rasterilähteen z9 |
| 9.00–9.99 | rasterilähteen z10 |
| 10.00–10.99 | rasterilähteen z11 |
| 11.00–11.99 | rasterilähteen z12 |
| 12.00–12.99 | vektorilähteen z12 |
| 13.00–13.99 | vektorilähteen z13, jne. |

Numeroero johtuu siitä, että rasterilähde ilmoitetaan MapLibrelle 256 px:n
tiilinä ja MapLibren vektoritiilet käyttävät 512 px:n zoomkonventiota.
Rasterilähteen tiilizoom on siksi karttazoom + 1. Vektorilähteen tiilizoom on
sama kuin karttazoom. Rasteriarkistossa on myös z8, vaikka nykyisen kerroksen
`minzoom: 8` tarkoittaa, ettei sitä tavallisesti piirretä näkyviin.

MapLibre `maxzoom` on poissulkeva: rasterikerroksen `maxzoom: 12` tarkoittaa,
että rasteri näkyy alle z12:n ja vektori alkaa täsmälleen z12:sta.

## Sovelluksen kytkentä ja nykyinen kartografinen tyyli

Integraatio on `saaristolautat`-repon tiedostossa
`src/components/MapLibreMap.jsx`. Arkistojen julkiset nimet on määritelty sen
alun vakioissa. Maanpeiterasterin lähteellä täytyy säilyttää `tileSize: 256`;
vektorilähteelle ei saa asettaa 256 px:n tiilikokoa, koska MapLibre edellyttää
vektoritiililtä 512 px:n konventiota. Vaihtorajan vakio on
`LANDCOVER_VECTOR_ZOOM_START`.

Rasterin värit ja peittävyydet ovat `build_overview_raster.py`-skriptin
`CLASS_STYLES`-taulukossa, ja niiden on vastattava sovelluksen
`LANDCOVER_TUNING_DEFAULTS`-arvoja. Nykyiset tärkeimmät oletukset ovat metsä
45 %, pelto 80 % ja pienten zoomien rasterille yhteinen peittävyyskerroin
0,825. Jos värejä tai peittävyyksiä muutetaan pysyvästi, päivitä sekä sovellus
että rasterigeneraattori ja rakenna rasteri uudelleen.

Korkeuskäyrien nykyiset oletukset ovat:

- väri `#a27339`;
- tavallisten käyrien peittävyys 30 % ja leveys 1,00 px;
- 20 m:n indeksikäyrien peittävyys 45 % ja leveys 1,30 px;
- 10 m:n käyrät saavuttavat täyden peittävyyden z11:ssä;
- 5 m:n lisäkäyrät saavuttavat täyden peittävyyden z13:ssa;
- peittävyys kasvaa nollasta valittuun arvoon zoomin `n-1` ja `n` välillä;
- 10 ja 20 m:n viivat kasvavat 0,25-kertaisesta leveydestä täyteen leveyteen
  zoomin `n-1` ja `n+1` välillä.

Rinnevarjostuksen oletuspeittävyys on 20 %. Se alkaa alfalla 0 z7:ssä ja
saavuttaa täyden oletuspeittävyyden z8:ssa. Käyrät ja rinnevarjostus ovat
käyttäjän asetuksissa oletuksena pois päältä; valinta tallennetaan selaimen
localStorageen. Localhostissa näkyvät lisäksi kehityspaneelit värien,
leveyksien, peittävyyksien ja zoomrajojen kokeiluun. Tuotantoon viedään aina
koodiin lukittu yhdistelmä, ei kehityspaneelin paikallista tilaa.

## Työkalut ja ympäristö

Tarvitaan Python 3, `tippecanoe`, `pmtiles`, `curl` sekä pinned Python-
riippuvuudet. Luo ympäristö repositorion ulkopuolelle:

```sh
cd /Users/kranto/personal/saaristodata
python3 -m venv /tmp/saaristolautat-landcover-venv
/tmp/saaristolautat-landcover-venv/bin/pip install \
  -r scripts/landcover/requirements.txt
/tmp/saaristolautat-landcover-venv/bin/pip install \
  pillow==12.0.0 pyshp==2.3.1
```

MML-avain luetaan ensisijaisesti ympäristömuuttujasta `MML_API_KEY` tai
repositorion Gitistä ohitetusta `.env`-tiedostosta. KMTK-lataajalle voidaan
antaa myös `--api-key-file`. Avainta ei saa kommitoida. KMTK-lataaja syöttää
avaimen curlille stdin-konfiguraationa, joten se ei näy prosessilistassa.

## Täysi uudelleenrakennus

Järjestys on tärkeä: pienten zoomien rasteri rakennetaan vasta lopuksi niistä
vektoriarkistoista, jotka oikeasti julkaistaan.

### Välimuistien käyttö

Tavallisessa väri-, peittävyys-, pakkaus- tai zoommuutoksessa säilytä ja käytä
uudelleen ladatut KMTK-GeoJSONit, Syke-GeoTIFF, rinnevarjostuksen karttalehdet,
MML:n meripolygoni ja yhdistetty rinnevarjostus-GeoTIFF. Aja vain muutoksen
jälkeiset vaiheet.

Jos kohdealue, lähdeversio tai lähdeaineiston sisältö muuttuu, vanhoja
rajaukseen sidottuja välimuisteja ei saa käyttää hiljaisesti. Arkistoi vanha
`raw/landcover/` ensin erilliseen nimettyyn hakemistoon ja lataa tai muodosta
uudelleen ainakin:

- KMTK:n alue-GeoJSON (`download_kmtk.py --force`);
- Syken alue-GeoTIFF (`download_syke.py --force`);
- `terrain-test/cache/hillshade-8m-merged-region-v2.tif`;
- `shore-mask/mml-sea.geojson`.

Yksittäiset MML:n rinnevarjostuskarttalehdet voi säilyttää: lataaja hakee vain
uudelta alueelta puuttuvat lehdet. Älä poista ainoaa raakadatakopiota; siirrä
vanha versio arkistoon ennen uudelleenrakennusta.

### 1. KMTK:n lataus ja normalisointi

```sh
/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/download_kmtk.py \
  --area pilot-archipelago-sea \
  --api-key-file /polku/mml-api-avaimeen

/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_kmtk_geojson.py \
  --area pilot-archipelago-sea
```

Jos nykyinen, oikean alueen raakadata on jo tallessa, ohita latauskomento ja
aloita normalisoinnista. Käytä lataajan `--force`-valitsinta vain, kun haluat
tietoisesti korvata olemassa olevan raakadataversion.

Lataaja käy läpi manifestin KMTK-kokoelmat. Jos vastaus osuu 10 000 kohteen
rajaan, bbox pilkotaan rekursiivisesti. Erityisen raskas `rock_area` pilkotaan
jo ennakolta. Päällekkäiset vastaukset deduplikoidaan `kmtk_id`:llä ja lopuksi
kohteet leikataan yhteiseen kohdealueeseen. Luokkamuunnokset ja luokkakohtaiset
minimipinta-alat ovat manifestissa.

Rakenna maastokartan KMTK-vektori:

```sh
/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_tiles.py \
  --area pilot-archipelago-sea \
  --source mml-kmtk-beta \
  --variant kmtk \
  --output tiles/terrain-landcover-r1.pmtiles \
  --force
```

Rakenna samasta raakadatasta oletuskartan urban-variantti:

```sh
/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_kmtk_geojson.py \
  --area pilot-archipelago-sea \
  --include-collection urban_area \
  --variant kmtk-urban

/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_tiles.py \
  --area pilot-archipelago-sea \
  --source mml-kmtk-beta \
  --variant kmtk-urban \
  --output tiles/terrain-landcover-detail-r1.pmtiles \
  --force
```

Vektoritiilet tehdään kahdessa vaiheessa. z8–9 käyttää voimakkaampaa
yleistystä ja vain piirrossa tarvittavaa `class`-kenttää; z10–14 säilyttää
yksityiskohdat. Tippecanoen MBTiles-välituotteet ovat `work/landcover/`-
hakemistossa ja lopputulos muunnetaan PMTilesiksi.

### 2. Syke-metsä

Syken Maanpeite 2 m 2022 ladataan WCS:stä 20 metrin työresoluutiolla. Tässä
käytetään vain metsäluokkaa 220:

```sh
/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/download_syke.py \
  --area pilot-archipelago-sea \
  --variant syke-forest \
  --output-resolution-metres 20

/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_geojson.py \
  --area pilot-archipelago-sea \
  --variant syke-forest-smoothed \
  --include-class forest \
  --input raw/landcover/syke-maanpeite-2022/pilot-archipelago-sea-syke-forest.tif \
  --clip-to-area \
  --smooth-factor 4 \
  --smooth-radius-pixels 2
```

Pehmennys suurentaa 20 m maskin 5 m työruudukkoon, käyttää 10 m:n
laatikkosuodatinsädettä ja vektoroi 50 %:n rajan. Se tekee reunasta
kartografisesti siistimmän, mutta ei lisää aineiston todellista tarkkuutta.
Käsittely tehdään limittäisissä paloissa muistin käytön rajaamiseksi.

Älä julkaise tätä vielä sellaisenaan: metsä leikataan rantaan kohdassa 4.

### 3. Korkeuskäyrät ja rinnevarjostuksen raakadata

```sh
/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/terrain/build_test_terrain.py
```

Skripti tekee seuraavaa:

- hakee MML:n karttalehtijaon ja valitsee 1:25 000 -lehdet, jotka leikkaavat
  latausvaippaa;
- lataa valmiit `Rinnevarjoste 8 m` GeoTIFFit enintään 100 lehden erissä;
- yhdistää GeoTIFFit yhdeksi 8 m:n välimosaiikiksi;
- hakee `korkeuskayra`-kokoelman 0,25 asteen paloissa, pilkkoo 10 000 kohteen
  rajaan osuvat haut ja deduplikoi `mtk_id`:llä;
- leikkaa käyrät tarkkaan kohdealueeseen;
- kirjoittaa 5 m:n arkistoon kaikki 5 000 millimetrillä jaolliset käyrät ja
  10 m:n arkistoon niiden 10 000 millimetrillä jaollisen osajoukon;
- tekee käyräarkistot z7–14 ja ensimmäisen rinnevarjostusarkiston z7–12.

MML:n rinnevarjosteessa neutraali harmaa 181 muutetaan läpinäkyväksi.
Poikkeama neutraalista määrää alfakanavan, hyvin pienet alfa-arvot nollataan,
harmaasävyt kvantisoidaan 64 tasoon ja tiilet pakataan läpinäkyväksi WebP:ksi
laadulla 80. z12:n jälkeen samaa viimeistä rasteritasoa ylisuurennetaan, jotta
mobiili ei lataa ja pura jatkuvasti uusia rasteritasoja.

### 4. Rantamaski Syke-metsälle ja rinnevarjostukselle

```sh
/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/terrain/build_shore_mask.py
```

Maskin rantaviiva tulee MML:n `meri`-kokoelmasta, koska se vastaa MML:n
rinnevarjostusta ja käyriä paremmin kuin OpenStreetMapin rantaviiva. Ladattu
merigeometria tallennetaan `raw/landcover/shore-mask/mml-sea.geojson` ja
käytetään seuraavilla ajoilla uudelleen.

- Syke-metsästä vähennetään meripolygoni geometrisesti ennen Tippecanoeta.
- Rinnevarjostuksessa vesipeitto rasteroidaan nelinkertaisella resoluutiolla.
  Jokaisen lopullisen pikselin alfa kerrotaan sen maaosuudella. Tämä antaa
  antialiasoidun rantareunan: hehku ei leviä veteen, mutta pienet luodot ja
  rantatörmien varjot eivät katoa kovaan yhden pikselin leikkaukseen.
- Molemmat leikataan lisäksi samaan include/exclude-kohdealueeseen.

Skripti korvaa julkaistavan `tiles/terrain-landcover-fill-r1.pmtiles`-arkiston
ja `raw/landcover/terrain-test/terrain-hillshade-r1.pmtiles`-arkiston.
`--pilot` tekee vain alkuperäisen pienen vertailualueen. `--hillshade-only`
käyttää jo luotua maskattua metsäsekvenssiä ja rakentaa vain varjostuksen.

### 5. Rinnevarjostuksen pienten zoomien optimointi

```sh
/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/terrain/optimize_hillshade.py \
  raw/landcover/terrain-test/terrain-hillshade-r1.pmtiles
```

Optimointi käsittelee saman arkiston sisällä vain z7–9:n:

| Tiilizoom | sisäinen renderöinti | WebP-laatu | rantamaskin alfa |
|---|---:|---:|---|
| z7 | 32 px | 35 | yksinkertaistetaan kuvan mukana |
| z8 | 64 px | 45 | yksinkertaistetaan kuvan mukana |
| z9 | 128 px | 60 | säilytetään tarkkana |
| z10–12 | 256 px | 80 | kopioidaan muuttamatta |

Työkalu tarkistaa, ettei kattavuus muutu eikä tiilistä tule tyhjiä, yhdistää
optimoidut z7–9-tiilet muuttamattomiin z10–12-tiiliin ja ajaa `pmtiles verify`.

### 6. Pienten zoomien maanpeiterasteri

Tämä tehdään viimeiseksi, koska lähteinä ovat valmiit KMTK- ja maskattu
Syke-vektori:

```sh
/tmp/saaristolautat-landcover-venv/bin/python \
  scripts/landcover/build_overview_raster.py
```

Rasteriarkisto sisältää z8–12. z8–9:n kuvat ovat 256 px ja WebP-laadut 70/75;
z10–12 säilyttävät 512 px:n renderöinnin ja käyttävät laatua 85. Geometria
rasteroidaan kaksinkertaisella supersamplingilla. Alfa-arvoihin käytetään
kerrointa 0,825, joka vastaa sovelluksen pienen zoomin peittävyysrajaa.
Tuloksena syntyvät arkisto ja `tiles/landcover-overview-raster.json`, jossa ovat
tiilimäärät, tavumäärät, asetukset ja SHA-256.

## Tarkistukset

Aja vähintään:

```sh
/tmp/saaristolautat-landcover-venv/bin/python -m unittest discover \
  -s scripts/landcover/tests -v

pmtiles verify tiles/terrain-landcover-overview-r1.pmtiles
pmtiles verify tiles/terrain-landcover-r1.pmtiles
pmtiles verify tiles/terrain-landcover-detail-r1.pmtiles
pmtiles verify tiles/terrain-landcover-fill-r1.pmtiles
pmtiles verify raw/landcover/terrain-test/terrain-contour-5m-r1.pmtiles
pmtiles verify raw/landcover/terrain-test/terrain-contour-10m-r1.pmtiles
pmtiles verify raw/landcover/terrain-test/terrain-hillshade-r1.pmtiles
```

Vertaa neljän maanpeitearkiston kokoja ja SHA-256-arvoja tiedostoon
`tiles/published-landcover.json`. Tarkista lisäksi `git diff`, etteivät raportit
sisällä odottamattomia alueraja-, luokka- tai tiilimäärämuutoksia. Sovelluksen
repossa ajetaan Node 24:llä `npm run build` ja kartta tarkistetaan sekä
läppärillä että puhelimella erityisesti rasteri–vektori-rajan molemmin puolin.

## Julkaiseminen palvelimelle

Skriptit ja raportit kommitoidaan `saaristodata`-repoon, mutta ohitetut
PMTiles-binäärit siirretään erikseen. Testi ja tuotanto käyttävät samaa
`/home/islanti/services/saaristodata`-hakemistoa bind mountilla, joten yksi
datasiirto päivittää molempien aineiston. Sovelluskoodin muutos vaatii lisäksi
web-konttien uudelleenrakennuksen.

### 1. Commit ja push

```sh
git status --short
git add data-sources scripts reports tiles/*.json docs
git commit -m "Kuvaava aineistomuutos"
git push origin master
```

Älä lisää Gitistä ohitettuja raakadata- tai PMTiles-tiedostoja väkisin.

### 2. Siirrä PMTiles ensin väliaikaisella nimellä

Esimerkki maanpeiterasterista:

```sh
scp tiles/terrain-landcover-overview-r1.pmtiles \
  islanti@het1:/home/islanti/services/saaristodata/tiles/terrain-landcover-overview-r1.pmtiles.new

shasum -a 256 tiles/terrain-landcover-overview-r1.pmtiles
ssh islanti@het1 \
  'sha256sum /home/islanti/services/saaristodata/tiles/terrain-landcover-overview-r1.pmtiles.new'
```

Kun tarkisteet täsmäävät, vaihda tiedosto atomisesti:

```sh
ssh islanti@het1 \
  'mv /home/islanti/services/saaristodata/tiles/terrain-landcover-overview-r1.pmtiles.new /home/islanti/services/saaristodata/tiles/terrain-landcover-overview-r1.pmtiles'
```

Käytä samaa `.new` → tarkiste → `mv` -menettelyä muille arkistoille. Käyrien
ja rinnevarjostuksen etäkohde on
`/home/islanti/services/saaristodata/raw/landcover/terrain-test/`.

Kun julkinen tiedostonimi muuttuu, päivitä samalla `MapLibreMap.jsx`, mahdolliset
julkaisumanifestit ja palvelimen tiedosto. Poista vanha julkinen nimi vasta,
kun uusi sovellusversio ja uusi tiedosto on tarkistettu sekä testissä että
tuotannossa.

### 3. Päivitä checkout

```sh
ssh islanti@het1
cd /home/islanti/services/saaristodata
git status --short
git pull --ff-only
```

Jos GitHubin SSH-yhteys epäonnistuu satunnaisesti, yritä samaa SSH-pullia
ensin uudelleen. Älä päättele yhdestä virheestä, että SSH-autentikointi tai
host key -asetus olisi rikki, äläkä vaihda HTTPS:ään ennen uusintayritystä.

### 4. Tarkista molemmat julkiset osoitteet

Dataa välimuistitetaan viisi minuuttia. Ohita välimuisti kyselyparametrilla:

```sh
curl --fail --head \
  "https://test.saaristolautat.fi/data/tiles/terrain-landcover-overview-r1.pmtiles?v=$(date +%s)"
curl --fail --head \
  "https://saaristolautat.fi/data/tiles/terrain-landcover-overview-r1.pmtiles?v=$(date +%s)"
```

Varmista `Content-Length`, `Accept-Ranges: bytes` ja palvelimen SHA-256. Jos
vain data vaihtui, kontteja ei tarvitse käynnistää uudelleen. Jos samalla
muuttui `saaristolautat`-sovellus, vedä sen commit ja rakenna ensin `test`,
tarkista kartta ja rakenna sitten `production`.

## Palautus ja vianhaku

- Säilytä edellinen PMTiles paikallisesti, kunnes uusi versio on tarkistettu.
- Palautus tehdään samalla atomisella siirtomenettelyllä vanhasta arkistosta.
- Tyhjä alue rasteri–vektori-rajalla viittaa yleensä siihen, että sovelluksen
  zoomraja ja palvelimen rasteriarkiston `maxzoom` eivät vastaa toisiaan tai
  vanha arkiston otsake on vielä välimuistissa.
- Veden päälle leviävä harmaa hehku tarkoittaa, että käytössä on maskaamaton
  rinnevarjostus. Veden päälle ulottuva vihreä tarkoittaa maskaamatonta Syke-
  metsää.
- Pohjoiseen tai itään jatkuva yksittäinen aineisto tarkoittaa yleensä, ettei
  se ole käyttänyt manifestin yhteistä `area_clip_geometry()`-rajausta.
- PMTilesia ei ladata kokonaan selaimeen. Selain tekee Range-pyyntöjä
  hakemistoon ja näkyviin tiileihin; siksi `Accept-Ranges` on pakollinen.

