# Saaristolautat-data

Tämä repositorio sisältää Saaristolautat-sovelluksen reitti-, alus-,
aikataulu- ja karttadatan. Sovellus lukee aineiston `index.json`-tiedoston
kautta.

Palvelun kaksi ydintehtävää ovat saariston reitistön kattava esittäminen
kartalla ja aikataulujen tekeminen helposti löydettäviksi. Aikataulunäkymä on
tarkoitettu matkan suunnitteluun eri päiville ja kausille, ei vain seuraavan
lähdön näyttämiseen.

## Tietojen ylläpito

Reittien, lauttojen, aikataulujen, operaattorien ja yhteystietojen
ensisijainen lähdetiedosto on `data.js`. Älä muokkaa generoituvaa
`data.json`-tiedostoa suoraan.

Tyypillinen päivitys:

1. Muokkaa `data.js`-tiedostoa.
2. Generoi JSON uudelleen repositorion juuressa:

   ```sh
   node data.js > data.json
   ```

3. Tarkista, että tulos on kelvollista JSON-dataa:

   ```sh
   jq empty data.json
   ```

4. Päivitä `index.json`:n muutettua aineistoa vastaava versionumero.
5. Tarkista muutokset ennen julkaisua:

   ```sh
   git diff --check
   git diff -- data.js data.json index.json
   ```

`data.js` ja siitä generoitu `data.json` kuuluvat aina samaan muutokseen.

## `index.json` ja välimuistin ohitus

`index.json` kertoo sovellukselle ladattavat tiedostot. Kyselyparametrin
versionumero on päivitettävä aina, kun vastaavan tiedoston sisältö muuttuu.
Muuten selaimet tai välipalvelimet voivat jatkaa vanhan datan käyttämistä.

Esimerkiksi:

```json
{
  "data": "data.json?v=134",
  "geojson": ["roads.json?v=2", "routes.json?v=1", "saaristo.json?v=27"]
}
```

- Kun `data.js` ja `data.json` muuttuvat, kasvata `data.json?v=...`-arvoa.
- Kun `roads.json` muuttuu, kasvata sen `v`-arvoa.
- Kun `routes.json` muuttuu, kasvata sen `v`-arvoa.
- Kun `saaristo.json` muuttuu, kasvata sen `v`-arvoa.
- Älä kasvata muuttumattomien tiedostojen versioita ilman erityistä syytä.

Versionumeron tarvitsee olla yksilöllinen aiempaan julkaisuun nähden.
Nykyinen käytäntö on kasvattaa kokonaislukua yhdellä.

## Tiedostojen roolit

- `data.js`: reittien ja niihin liittyvien tietojen ylläpidettävä lähde.
- `data.json`: `data.js`:stä generoitu sovelluksen käyttämä tiedosto.
- `routes.json`: kartan reittiviivat.
- `roads.json`: pohjakarttaa täydentävät käsin valitut tieosuudet.
- `saaristo.json`: laiturit, nimet ja muut karttakohteet. Tiedoston juuri on
  historiallisista syistä GeoJSON-tyylinen mutta ei täydellinen
  `FeatureCollection`.
- `timetables_jpg/`: sovelluksessa näytettävät paikalliset aikataulukuvat.
- `index.json`: ladattavien tiedostojen nimet ja välimuistiversiot.

## Reittien elinkaari

Päättynyttä reittiä ei tarvitse poistaa historiasta. Merkitse se lähdedatassa:

```js
obsolete: true,
```

Vanhentuneiksi merkittyjä reittejä ei näytetä normaalina aktiivisena
liikenteenä eikä niitä pidä laskea aktiivisten reittien puutteiksi.

Alusrekisteri on historiallinen ja kumulatiivinen. Älä poista aiemmin käytössä
ollutta alusta `ferries`-rekisteristä, vaikka se poistuisi nykyiseltä reitiltä:
alus voi palata myöhemmin saman tai toisen operaattorin käyttöön. Lisää uusi
alus aina uutena tietueena. Reitin `vessels`-luettelo voidaan sen sijaan
päivittää kuvaamaan vahvistettua nykyistä käyttöä.

Alusvaihdos voi olla tilapäinen. Päivitä reitin alusluettelo vain, kun muutos
voidaan vahvistaa liikenteen tilaajan tai operaattorin omasta lähteestä.

## Aikataulut ja lähteet

- Käytä tietojen lähteenä ensisijaisesti liikenteen tilaajan tai operaattorin
  virallista aikataulua.
- Arvioi esitystapa reittikohtaisesti. Ulkoinen linkki voi olla hyvä ja pysyvä
  ratkaisu, jos se vie suoraan vakaaseen, ajantasaiseen, koko suunnittelujakson
  kattavaan ja mobiilissa helposti selattavaan aikatauluun.
- Muissa tapauksissa tuo aktiivisen reitin voimassa oleva aikataulu tähän
  palveluun kuvana tai muussa helposti lähestyttävässä muodossa. Tämä on
  useimpien reittien oletusratkaisu.
- Säilytä virallisen alkuperäisaikataulun linkki lähteenä ja tarkistamista
  varten myös silloin, kun aikataulu esitetään paikallisesti.
- Anna jokaiselle aikataululle `validFrom` ja mahdollisuuksien mukaan
  `validTo` ISO-muodossa `YYYY-MM-DD`.
- Älä jatka vanhan aikataulun voimassaoloa ilman lähdettä.
- Paikallisen voimassa olevan aikataulun puuttuminen käynnistää
  reittikohtaisen tarkistuksen. Jos ulkoinen palvelu täyttää yllä mainitut
  vaatimukset, linkki voidaan hyväksyä lopulliseksi ratkaisuksi. Muuten puute
  korjataan paikallisella esityksellä. Vanhaa kuvaa ei saa näyttää
  ajantasaisena kummassakaan tapauksessa.
- Muunna vaikeasti selattavat PDF-aikataulut mobiiliin sopiviksi kuviksi tai
  muuksi selkeäksi esitykseksi. Rajaa suuret valkoiset marginaalit pois, mutta
  älä muuta aikataulun sisältöä, merkintöjä tai ehtoja.
- Kun aikataulu koostetaan verkkosivun taulukosta, tee ensisijaisesti erilliset
  kuvat suomeksi, ruotsiksi ja englanniksi. Lokalisoitavia tietoja ovat myös
  viikonpäivät, voimassaoloaika, huomautukset ja kuvan lähdetiedot. Käytä
  `images_fi`, `images_sv` ja `images_en` -kenttiä sekä parasta yhteistä
  varavaihtoehtoa `images`-kentässä.
- Merkitse lähtötaulukon otsikkoon myös suunta nuolella, esimerkiksi
  `Parainen → Nauvo` ja `Nauvo → Parainen`. Pelkkä lähtölaiturin nimi ei aina
  kerro käyttäjälle riittävän selvästi, mihin suuntaan ajat ovat.
- Suosi puhelimelle sopivaa kapeaa asettelua. Laita vastakkaisten suuntien
  taulukot allekkain ja jaa eri viikonpäiväryhmät tarvittaessa omiksi kuvikseen.
- Säilytä kaikki suunnittelun kannalta tarpeelliset vuorot ja voimassaolojaksot.
  Pelkkä seuraavan lähdön tieto ei korvaa koko aikataulua.
- Tarkista samalla reitti, alus, operaattori ja yhteystiedot.

### PDF-aikataulun päivittäminen

1. Etsi aikataulu liikenteen tilaajan tai operaattorin viralliselta
   reittisivulta. Tallenna `link`, `link_sv` ja `link_en` osoittamaan
   vastaaville reittisivuille, ei hakutulokseen tai tilapäiseen latausosoitteeseen.
2. Valitse käyttäjälle näytettävä PDF kielittäin seuraavassa järjestyksessä:

   - suomi: `fi`, `sv`, `en`
   - ruotsi: `sv`, `fi`, `en`
   - englanti: `en`, `sv`, `fi`

   Jos aikataulu on vain yhdellä kielellä, tallenna kuvasarja yhteiseen
   `images`-kenttään. Jos eri kieliversiot ovat saatavilla, käytä kenttiä
   `images_fi`, `images_sv` ja `images_en` ja pidä `images` parhaana yhteisenä
   varavaihtoehtona. Sovelluksen on toteutettava yllä kuvattu kielikohtainen
   varajärjestys; datassa oleviin vanhoihin, tästä poikkeaviin kenttävalintoihin
   ei pidä ottaa mallia.
3. Muunna PDF:n jokainen aikataulun ymmärtämiseen tarvittava sivu omaksi
   JPEG-kuvakseen. Käytä riittävää tarkkuutta, jotta pienikin teksti säilyy
   luettavana puhelimella zoomattaessa. Rajaa pois suuret valkoiset reunukset,
   mutta säilytä otsikot, selitteet, alaviitteet, yhteystiedot ja muut
   aikataulun tulkintaan vaikuttavat merkinnät.
4. Nimeä kuvat alkuperäisen PDF:n ja sivunumeron mukaan, esimerkiksi:

   ```text
   nauvon-pohjoinen-reitti-talvi-11.8.2026-30.5.2027-1.jpg
   nauvon-pohjoinen-reitti-talvi-11.8.2026-30.5.2027-2.jpg
   ```

   Tallenna kuvat `timetables_jpg/`-hakemistoon. Älä korvaa erinimistä vanhaa
   kuvaa uudella sisällöllä.
5. Tarkista jokainen valmis kuva silmämääräisesti täydessä koossa. Varmista,
   ettei rajaus leikkaa tekstiä ja että kaikki PDF:n aikataulusivut ovat mukana
   oikeassa järjestyksessä.
6. Korvaa päivitettävän reitin vanhentuneet `tables`-rivit `data.js`:ssä
   uusilla voimassaolojaksoilla. Samassa PDF:ssä voi olla kaksi erillistä
   kautta; tee niille erilliset rivit, vaikka ne käyttäisivät samoja kuvia:

   ```js
   tables: [
     {
       validFrom: "2026-01-01",
       validTo: "2026-05-07",
       images: ["inio-kustavi-talvi-1.1.-7.5.2026-ja-14.9.-31.12.2026-1.jpg"],
     },
     {
       validFrom: "2026-09-14",
       validTo: "2026-12-31",
       images: ["inio-kustavi-talvi-1.1.-7.5.2026-ja-14.9.-31.12.2026-1.jpg"],
     },
   ],
   ```

   Poista vain kyseisen reitin vanhentuneet `tables`-rivit. Vanhoja
   kuvatiedostoja ei tarvitse poistaa tämän päivityksen yhteydessä, eikä
   aluksia poisteta `ferries`-rekisteristä.
7. Generoi `data.json` uudelleen ja tarkista, että kaikki viitatut kuvat ovat
   olemassa. Päivitä `index.json`:n dataversio vasta, kun muutos kommitoidaan
   julkaistavaksi; keskeneräisen aikataulutyön aikana versiota ei nosteta.
8. Avaa aikataulu sovelluksessa kaikilla tuetuilla kielillä ja tarkista
   voimassaolojaksojen rajat, kielten varajärjestys, sivujärjestys ja kuvan
   luettavuus sekä puhelin- että työpöytäkoossa.

### Päivityksissä opittuja käytäntöjä

- Älä päättele PDF:n voimassaoloa pelkästä tiedostonimestä tai verkkosivun
  linkkitekstistä. Tarkista jokaisen sivun otsikko: yksi PDF voi sisältää
  useita kausia, eri suuntien taulukoita sekä erillisiä selite- ja
  poikkeussivuja.
- Ryhmittele samaan `tables`-riviin kaikki sivut, joita kyseisen jakson
  aikataulun tulkitseminen vaatii. Esimerkiksi ensimmäinen sivu voi sisältää
  menovuorot ja seuraava paluuvuorot tai varaus- ja poikkeusehdot.
- Tee toisistaan erillään oleville voimassaolojaksoille omat rivit, vaikka ne
  käyttäisivät samoja kuvia. Älä venytä yhtä jaksoa sen välissä olevan kesä-,
  talvi- tai poikkeuskauden yli.
- Pätki pyhä- ja poikkeusliikenne niin, etteivät perusaikataulun ja
  erikoisaikataulun voimassaolojaksot mene päällekkäin. Lisää perusaikataulu
  tarvittaessa uudelleen poikkeusjakson jälkeen. Näin käyttäjälle ei näytetä
  samalle päivälle kahta keskenään ristiriitaista tabia.
- Yhteinen liite voi olla osa usean reitin aikataulua. Esimerkiksi
  vaijerilossien yleinen tauko- ja poikkeussivu lisätään reittikohtaisen kuvan
  lisäksi tai yksinään niille kausille, joille ei ole erillistä aikataulua.
- Älä oleta, että kaikille vanhoille reiteille julkaistaan edelleen oma
  aikataulu. Jos reitti puuttuu operaattorin nykyiseltä aikataulusivulta, älä
  jatka vanhan aikataulun voimassaoloa. Selvitä reitin tila erikseen.
- Tarkista kohdetiedoston nimi ennen kuvan kirjoittamista. Jos nimi on jo
  käytössä, lisää nimeen vuosi tai tarkempi voimassaolojakso. Vanhaa kuvaa ei
  saa korvata uuden kauden sisällöllä.
- Käytä aikataulun `link`-kentässä vakaata reitti- tai aikatauluhakemiston
  sivua. PDF:n suora osoite voi vaihtua korjauksen yhteydessä, vaikka kauden
  nimi pysyisi samana.
- Tarkista PDF:stä löytyvät alusnumerot, sähköpostiosoitteet ja varausehdot
  samalla kertaa. Vertaa niitä operaattorin yhteystietosivuun ja päivitä
  alus- tai operaattoritietue vain virallisen lähteen perusteella.
- Tarkista lopuksi, että kaikki `data.js`:ssä viitatut kuvat ovat olemassa,
  `data.json` vastaa täsmälleen `node data.js` -komennon tulosta ja sovellus
  näyttää sekä nykyiset että tulevat jaksot oikeassa järjestyksessä.

### Finferriesin verkkotaulukoista koostettavat aikataulut

Finferriesin reittisivun aikataulu voi olla selaimessa näkyvä HTML-taulukko
PDF:n sijaan. Pääsivun tekstiversio tai hakukoneen tallenne voi näyttää
`Aikataulut`-osion tyhjänä, koska taulukot ladataan sivulle erikseen. Tarkista
aina selaimessa näkyvä sisältö ja kaikki reittisivun lataamat nykyiset
aikataulutaulukot ennen kuin päätät, ettei reitillä ole aikataulua.

- Tee jokaisesta päiväryhmästä oma kuva: esimerkiksi maanantai–perjantai,
  lauantai sekä sunnuntai ja pyhät. Jos sama aikataulu on voimassa viikon
  jokaisena päivänä, käytä otsikoita `Päivittäin`, `Dagligen` ja `Daily`.
- Tee yhden päivän erikoisaikataulusta oma kuva ja oma `tables`-jakso, jonka
  `validFrom` ja `validTo` ovat sama päivä. Katkaise perusaikataulu ennen
  erikoispäivää ja aloita se tarvittaessa uudelleen seuraavana päivänä, jotta
  tabit eivät mene päällekkäin.
- Pitkillä lauttareiteillä voi olla samalla kaudella erilliset arki- ja
  viikonloppukuvat. Yksi `tables`-jakso voi viitata molempiin, jos niiden
  voimassaolo alkaa ja päättyy samana päivänä.
- Lue ajat suoraan taulukosta ja säilytä jokainen aikaan liittyvä tunnus,
  kuten `*`, `T`, `A`, `S`, numeroitu alaviite tai tilausmerkintä. Älä irrota
  tunnusta lähtöajasta tai normalisoi sitä pois.
- Kopioi tai tiivistä kuvaan kaikki aikataulun tulkintaan vaikuttavat tiedot:
  tauot, välittömän paluun ehdot, yö- ja tilausliikenne, tilauksen määräaika ja
  puhelinnumero, tekstiviestitilaus, vaarallisten aineiden vuorot,
  koulukuljetukset, ajoneuvojen lastausjärjestys, käytettävän aluksen tunnus
  sekä joulu- ja muiden pyhäpäivien viimeiset lähdöt.
- Ole tarkka ehtolauseissa. Esimerkiksi ”paluu heti” ja ”paluu heti, jos
  rannalla on matkustajia” eivät tarkoita samaa asiaa. Vertaa jokaisen
  kielikuvan tekstiä virallisen taulukon kyseiseen kieliversioon.
- Erottele pysyvä aikataulusisältö lyhytaikaisesta liikennetiedotteesta.
  Päiväkohtainen aikataulumuutos kuuluu voimassaolojaksoon ja kuvaan;
  kalustonvaihdosta tai liikennekatkoa koskevaa tiedotetta ei pidä muuttaa
  pysyväksi aikataulutiedoksi.
- Käytä kuvassa kielikohtaisia paikannimiä silloin, kun niille on vakiintunut
  muoto, ja nimeä molemmat suunnat selvästi nuolella. Älä jätä käyttäjän
  pääteltäväksi, onko taulukon paikka lähtö- vai määräpaikka.
- Renderöi teksti lopullista kuvaa suuremmalla tarkkuudella ja pienennä kuva
  laadukkaalla suodatuksella. Nykyinen toimiva mobiilileveys on noin 620 px;
  JPEG-tallennuksessa tekstin luettavuus vaatii korkean laadun ja vähäisen
  värialinäytteistyksen. Tarkista lopputulos aina silmämääräisesti.
- Varmista ohjelmallisesti, että jokaisella `images`, `images_fi`, `images_sv`
  ja `images_en` -viittauksella on tiedosto, aikataulujaksot eivät mene
  päällekkäin ja jokainen lähdetaulukko tuotti vähintään yhden ajan.
- Älä rajaa verkkotaulukoiden käsittelyä vain lyhyisiin losseihin.
  Nauvo–Korppoo, Korppoo–Norrskata ja Korppoo–Houtskari käyttävät samaa
  lähderakennetta, vaikka reitit ovat pidempiä ja aikataulut monimutkaisempia.

## Sovelluksen tarkistus

Datamuutoksen jälkeen rakenna sovellus Node.js 24:llä:

```sh
cd ../saaristolautat
PATH=/Users/kranto/.nvm/versions/node/v24.21.0/bin:$PATH npm run build
```
