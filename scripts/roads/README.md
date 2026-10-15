# Teiden lisääminen `roads.json`-tiedostoon

`roads.json` täydentää pohjakarttaa tieosuuksilla, joiden pitää näkyä aikaisemmin
kuin OpenFreeMap tai OpenStreetMap ne näyttää. Tiedosto sijaitsee tämän
`saaristodata`-projektin juuressa. Sovellus lukee sen `public/data`-symlinkin kautta.

Työnkulku on tarkoitettu muutamasta tieosuudesta muutamaan kymmeneen. Reitin
geometriaa ei tarvitse enää kopioida tai muuntaa käsin.

## Zoom-arvot

Manifestissa käytetään vanhan 256 px tiilikartan zoom-arvoja, aivan kuten nykyisessä
`roads.json`:issa:

- `minZ`: ensimmäinen zoom, jolla tie piirretään
- `maxZ`: viimeinen zoom, jolla oma tie piirretään

MapLibre-koodi tekee automaattisesti muunnoksen `MapLibre = vanha zoom - 1`.
Esimerkiksi `minZ: 8, maxZ: 10` vastaa MapLibren näkyvyysaluetta alkaen
zoomista 7 ja päättyen ennen zoomia 10. Yläraja on käyttäjän kannalta vanhan
kartan tapaan inklusiivinen.

Kun tarkoitus on vain paikata pohjakartan liian myöhään ilmestyvä tie, valitse
`maxZ` niin, että oma viiva poistuu juuri pohjakartan tien tullessa näkyviin.

## 1. Täydennä manifestia

Lisää tiet versionhallittuun tiedostoon
`scripts/roads/road-imports.json`. Laajempi mallipohja löytyy tiedostosta
`scripts/roads/road-imports.example.json`. Ladattu OSRM-välimuisti ja paikallinen
esikatselu on jätetty Gitin ulkopuolelle. Varsinainen lopputulos tallennetaan
projektin juuren `roads.json`:iin.

Jokaisella tieosuudella on pysyvä ja yksilöllinen `id`. Sama skripti voidaan ajaa
uudelleen: aiemmin samalla `id`:llä tuotu osuus korvataan eikä monistu.

## 2A. Helpoin tapa: reitti koordinaateista

Lisää manifestiin reitti:

```json
{
  "id": "nauvo-kirjainen",
  "name": "Nauvo - Kirjainen",
  "minZ": 8,
  "maxZ": 10,
  "source": {
    "type": "osrm",
    "via": [
      [21.9081, 60.1934],
      [21.8750, 60.1640],
      [21.8260, 60.1230]
    ]
  }
}
```

Koordinaatit voi kirjoittaa kummassa järjestyksessä tahansa: sekä `[lon, lat]`
että `[lat, lon]` hyväksytään. Skripti tulkitsee alle 40 olevan luvun
pituusasteeksi ja yli 40 olevan luvun leveysasteeksi. Esimerkiksi nämä tarkoittavat
samaa paikkaa:

```json
[19.781503, 60.193575]
[60.193575, 19.781503]
```

Jos molemmat luvut ovat samalla puolella arvoa 40, skripti pysähtyy virheeseen
eikä arvaa järjestystä. Ota alku- ja loppupiste sekä tarvittaessa välietappeja
kartalta. Välietapit pakottavat reitin halutulle tielle. Lisää piste ennen
jokaista risteystä, jossa reititin voisi valita väärän tien.

Skripti käyttää oletuksena julkista OSRM-reitityspalvelua ja pitää yhden sekunnin
tauon hakujen välissä. Välimuistin ansiosta samaa geometriaa ei haeta uudelleen,
ellei käytetä `--refresh`-valintaa.

Jos macOS:n Python-asennuksesta puuttuu CA-varmenneketju ja `urllib` antaa
`CERTIFICATE_VERIFY_FAILED`-virheen, skripti yrittää pyynnön automaattisesti
järjestelmän `curl`-komennolla. TLS-varmennusta ei poisteta käytöstä kummassakaan
vaiheessa.

Tarkista aina esikatselusta, ettei autoprofiili ole oikaissut lossin, lauttareitin
tai muun ei-toivotun yhteyden kautta. Tee eri saarilla olevista teistä erilliset
manifestikohdat.

## 2B. Vaihtoehto: valmis GeoJSON- tai GPX-reitti

Jos tie on helpompi piirtää tai reitittää toisessa palvelussa, vie se GeoJSON- tai
GPX-tiedostoksi hakemistoon `scripts/roads/imports/` ja käytä tiedostolähdettä.
Nämä lähdetiedostot kannattaa lisätä Gitiin yhdessä manifestin kanssa, jotta
tuonti voidaan myöhemmin toistaa:

```json
{
  "id": "kemiön-erikoisosuus",
  "name": "Kemiön erikoisosuus",
  "minZ": 9,
  "maxZ": 12,
  "source": {
    "type": "file",
    "path": "imports/kemion-erikoisosuus.gpx"
  }
}
```

GeoJSONista hyväksytään `LineString`, `MultiLineString`, `Feature` ja
`FeatureCollection`. GPX:stä luetaan ensisijaisesti track-pisteet ja niiden
puuttuessa route-pisteet. Korkeustieto poistetaan automaattisesti.

## 3. Tee esikatselu

```sh
python3 scripts/roads/update_roads.py \
  scripts/roads/road-imports.json \
  --output scripts/roads/roads.preview.json
```

Skripti:

1. validoi nimet, zoom-arvot ja koordinaatit
2. hakee tai lukee geometriat
3. poistaa peräkkäiset kaksoispisteet ja korkeustiedot
4. muodostaa vakaan GeoJSON-kohteen
5. korvaa saman `roadImportId`:n aiemman version
6. jättää vanhat käsin tehdyt tieosuudet koskematta

Yhden osuuden voi käsitellä erikseen:

```sh
python3 scripts/roads/update_roads.py scripts/roads/road-imports.json \
  --only nauvo-kirjainen \
  --output scripts/roads/roads.preview.json
```

Pakota uuden geometrian haku:

```sh
python3 scripts/roads/update_roads.py scripts/roads/road-imports.json \
  --refresh \
  --output scripts/roads/roads.preview.json
```

## 4. Päivitä `roads.json`

Kun esikatselu on tarkistettu:

```sh
python3 scripts/roads/update_roads.py \
  scripts/roads/road-imports.json \
  --write
```

Oletuskohde on projektin juuren `roads.json`. Toisen tiedoston voi antaa
`--roads`-valinnalla. Kirjoitus tehdään atomisesti väliaikaisen tiedoston kautta.
Tarkista muutos ennen commitointia:

```sh
git diff --stat -- roads.json
git diff -- roads.json
```

Käynnissä oleva Vite-palvelin lukee päivitetyn datan tavallisesti sivun
uudelleenlatauksella. Lopuksi tarkista ainakin `minZ`, `maxZ` ja reitin muoto
kartalla sekä aja sovelluksen build:

```sh
cd ../saaristolautat
PATH=/Users/kranto/.nvm/versions/node/v24.21.0/bin:$PATH npm run build
```

## Huomioita

- Julkinen OSRM-palvelu sopii tähän pieneen, satunnaiseen ylläpitotyöhön. Älä aja
  suuria automaattisia eriä tai poista välimuistia turhaan.
- `roadImportId` on ylläpitotunniste. Sovellus jättää sen huomiotta.
- Ensimmäinen tuonti muotoilee koko `roads.json`:in kahden välilyönnin JSONiksi.
  Sisältö säilyy, mutta ensimmäinen diff voi siksi olla suuri.
- Jos tie koostuu useasta irrallisesta osasta, tee niistä eri manifestikohteet.
