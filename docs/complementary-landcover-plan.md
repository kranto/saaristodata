# Täydentävän maanpeiteaineiston suunnitelma

## Tavoite

OpenStreetMapin maanpeite on Suomen saaristossa epätasainen. Monet saaret
näkyvät OpenFreeMap-pohjakartassa yhtenäisen vaaleina, koska niiltä puuttuvat
muun muassa metsää, peltoja, kosteikkoja ja avokalliota kuvaavat alueet.

Tavoitteena on tuottaa Saaristolautat-sovellukselle erillinen täydentävä
maanpeittotaso. Sen pitää parantaa saarten hahmottamista lähizoomilla ilman,
että kartan tärkeimmät kohteet -- meri, saaret, tiet ja lauttareitit --
menettävät luettavuuttaan.

Täydentävää aineistoa ei ole tarkoitus tuoda OpenStreetMapiin. Se pidetään
Saaristolauttojen omana, lähteistettynä karttatasona.

## 1. Ladattavat aineistot

Ensimmäiseen versioon otetaan vain lauttakartan lukemista parantavat
maanpeittoluokat:

| Oma luokka | Sisältö |
| --- | --- |
| `forest` | Metsä ja puustoinen alue |
| `farmland` | Pellot ja muu viljelymaa |
| `open` | Niityt, avoin metsämaa, nummet ja muu avoin maa |
| `wetland` | Suot, kosteikot ja ruovikot |
| `rock` | Avokalliot ja laajat kivikot |
| `sand` | Hiekka-alueet ja rannat |
| `urban` | Laajat rakennetut alueet, jos lähteen luokitus on käyttökelpoinen |

Ensimmäiseen versioon ei oteta rakennuksia, teitä, polkuja, korkeuskäyriä,
kiinteistörajoja eikä pieniä yksittäisiä maastokohteita. Myöskään rantaviivaa
ja vesistöjä ei korvata, vaan ne tulevat edelleen OpenFreeMapista.

## 2. Aineistolähteet

### Manner-Suomi ja Turun saaristo

Ensisijainen kokeilulähde on Maanmittauslaitoksen Kansallinen
maastotietokanta (KMTK). BETA-vaiheessa aineisto ladataan rajatusti MML:n OGC
API Features -rajapinnasta vain testi- ja kehityskäyttöön. Tuotantokäyttö
edellyttää KMTK:n tuotantoversion, skeeman ja käyttöehtojen uutta tarkistusta.

Koko Suomen GeoPackagea ei ladata. Lataus rajataan Saaristolauttojen
toiminta-alueeseen ja vain tarvittaviin teemoihin.

Lähteet:

- [Maastotietokannan tuotekuvaus](https://www.maanmittauslaitos.fi/kartat-ja-paikkatieto/aineistot-ja-rajapinnat/tuotekuvaukset/maastotietokanta)
- [Maastotietokannan GeoPackage-versio](https://www.maanmittauslaitos.fi/geopackage)

Maastotietokanta on CC BY 4.0 -lisensoitu. Aineistolähde, aineiston nimi ja
luovutusajankohta merkitään sekä tuotantotiedoston metatietoihin että kartan
tekijätietoihin.

KMTK:n aluekohteista saadaan muun muassa avokallio, viljelysmaa, suo, niitty,
harvapuustoinen alue, hiekka ja taajama. Jatkuvaa metsäpolygonia ei ole.
Ensimmäinen KMTK-versio jätetään tarkoituksella ilman Syke-täyttöä, jotta
KMTK:n todellinen kattavuus voidaan arvioida. Syken Maanpeite 2 m 2022 otetaan
mukaan vasta, jos luokittelemattomien alueiden täydentämisestä on kartalle
selvää hyötyä.

### Ahvenanmaa

Ensin tarkistetaan, sisältääkö MML:n Maastotietokanta Ahvenanmaalta samat
tarvittavat kohdeluokat ja riittävän kattavuuden kuin Manner-Suomesta.

Jos kattavuus ei riitä, vaihtoehtoinen lähde on Ahvenanmaan maakuntahallituksen
[kartor.ax](https://kartor.regeringen.ax/)-palvelu. Sopivat tasot ladataan sen
WFS-rajapinnoista. Jokaisen tason sisältö, lisenssi, päivityspäivä ja kattavuus
tarkistetaan erikseen ennen käyttöä.

- [Kartor.ax:n WMS/WFS-ohje](https://kartor.regeringen.ax/dokument/bilagor/anslutWMS_WFSLR.pdf)

### OpenStreetMap

OpenStreetMapia käytetään puutteiden ja lopputuloksen vertailuun, mutta sen
geometrioita ei yhdistetä täydentävään aineistoon. Näin ODbL-aineistoa ja
viranomaisaineistoja ei sekoiteta samaan johdannaiseen tiedostoon.

## 3. Aineistojen käsittely

Käsittely toteutetaan toistettavana komentoriviputkena:

1. Ladataan rajattu GeoPackage- tai WFS-aineisto.
2. Tarkistetaan lähteen skeema, lisenssi, päiväys ja koordinaattijärjestelmä.
3. Muunnetaan käsittelykoordinaatistoksi ETRS-TM35FIN (EPSG:3067).
4. Valitaan vain sovitut kohdeluokat.
5. Muunnetaan lähteiden luokat yhteiseen Saaristolautat-luokitukseen.
6. Korjataan virheelliset geometriat.
7. Yhdistetään vierekkäiset saman luokan polygonit.
8. Poistetaan zoomitasolla merkityksettömät pienet kuviot.
9. Yksinkertaistetaan geometria zoomitasokohtaisesti topologia säilyttäen.
10. Rajataan aineisto määriteltyyn toiminta-alueeseen.
11. Tuotetaan vektoritiilet ja pakataan ne PMTiles-arkistoksi.
12. Ajetaan laatutarkistukset ja muodostetaan käsittelyraportti.

Ensisijaiset työkalut ovat GDAL/OGR ja Tippecanoe. Käsittelyskriptit ja
luokkamuunnokset sijoitetaan hakemistoon:

```text
scripts/landcover/
```

Lähdekohtaiset luokkamuunnokset pidetään erillisessä versionhallittavassa
asetustiedostossa. Putki ei saa perustua käsin tehtäviin QGIS-muokkauksiin,
vaikka QGISiä käytetään tuloksen tutkimiseen ja laadunvarmistukseen.

## 4. Käsitellyn aineiston muoto

### Normalisoitu välituote

Välituote on GeoPackage, jossa on yksi polygonitaso. Sen vähimmäiskentät ovat:

| Kenttä | Sisältö |
| --- | --- |
| `class` | Saaristolauttojen yhtenäinen maanpeittoluokka |
| `source` | Esimerkiksi `mml` tai `aland` |
| `source_date` | Lähdeaineiston päiväys |

Esimerkkitiedosto:

```text
landcover-normalized.gpkg
```

### Sovelluksen lopputuote

Sovellukselle tuotetaan versionoitu PMTiles-tiedosto:

```text
landcover-2026-11.pmtiles
```

Arkistossa on yksi vektoritaso, `landcover`. Mukana ei säilytetä sovellukselle
tarpeettomia lähdekenttiä.

Alustavat kokobudjetit ovat:

- pilottialueen PMTiles alle 25 Mt
- koko toiminta-alueen PMTiles mielellään alle 250 Mt
- yhden lähizoomin karttanäkymän verkkoliikenne mielellään alle 1--2 Mt

Nämä ovat hyväksymistavoitteita, eivät arvioita aineiston lopullisesta koosta.
Niitä tarkennetaan pilotin mittausten perusteella.

## 5. Tallennus

Ehdotettu hakemistorakenne:

```text
saaristodata/
  data-sources/landcover.yml
  scripts/landcover/
  raw/landcover/2026-11/          # ei versionhallintaan
  work/landcover/                 # väliaikainen, ei versionhallintaan
  tiles/landcover-2026-11.pmtiles # julkaistava tiedosto
  tiles/landcover.json            # aktiivisen version metatiedot
  reports/landcover-2026-11.html
```

Gitissä säilytetään:

- lataus- ja käsittelyskriptit
- lähdemanifesti ja lisenssitiedot
- luokkamuunnokset
- toiminta-alueen rajaus
- testit ja hyväksymisrajat
- käsittelyraportit tai niiden tiivistelmät

Raaka-aineistoja, välituotteita ja suuria PMTiles-tiedostoja ei lähtökohtaisesti
tallenneta Gitiin. Palvelimella säilytetään aktiivinen ja vähintään yksi
edellinen PMTiles-versio palautusta varten.

## 6. Tarjoilu

Saaristolautat-sovelluksen nginx tarjoaa jo `saaristodata`-hakemiston
osoitteesta `/data/`. Valmis arkisto tarjoillaan samasta originista esimerkiksi
osoitteella:

```text
/data/tiles/landcover-2026-11.pmtiles
```

Nginxin staattinen tiedostotarjoilu tukee PMTilesin käyttämiä HTTP Range
-pyyntöjä. Erillistä tietokantaa tai tiilipalvelinta ei tarvita.

Julkaisu tehdään versionoidulla tiedostonimellä:

1. Uusi PMTiles kopioidaan palvelimelle.
2. Tiedoston tarkistussumma ja luettavuus tarkistetaan.
3. Aktiivinen versio vaihdetaan manifestissa tai sovelluksen asetuksessa.
4. Edellinen versio säilytetään nopeaa palautusta varten.

PMTiles-tiedostolle annetaan pitkä välimuistiaika, koska sen nimi on
versionoitu. Pienen `landcover.json`-manifestin välimuisti pidetään lyhyenä.
Selaimen ei tarvitse ottaa yhteyttä MML:n tai kartor.ax:n palveluihin.

## 7. Näyttäminen Saaristolautat-sovelluksessa

Sovellukseen lisätään `pmtiles`-kirjasto ja PMTiles-protokolla rekisteröidään
MapLibrelle. Karttaan lisätään yksi vektorilähde ja maanpeittoluokkien
fill-tasot.

Tasojärjestys on:

```text
OpenFreeMapin pohjamaa
-> täydentävä maanpeite
-> OpenFreeMapin tiet ja rakennukset
-> Saaristolauttojen tiet ja lauttareitit
-> nimet, kyltit ja muut merkinnät
```

Täydentävä taso näytetään vain lähizoomilla, alustavasti MapLibre-zoomilta 9
tai 10 alkaen. Lopullinen raja päätetään visuaalisessa testissä.

Kehitysvaiheessa tasolle tehdään päälle/pois-kytkin, jotta OpenFreeMapin
alkuperäistä näkymää ja täydentävää aineistoa voidaan verrata. MML:n ja
mahdollisen Ahvenanmaan aineiston tekijätiedot lisätään MapLibren
tekijätietokenttään.

## 8. Ylläpito

Aineisto päivitetään aluksi käsin kerran vuodessa. Tiheämpää päivitystä ei
lähtökohtaisesti tarvita, koska maanpeite muuttuu hitaasti ja MML:n muiden
maastokohteiden päivityssykli on tyypillisesti useita vuosia.

Päivitysprosessi:

1. Tarkistetaan lähteiden skeemat, kattavuus ja lisenssit.
2. Ladataan uudet lähdeversiot.
3. Ajetaan sama käsittelyputki alusta loppuun.
4. Verrataan pinta-aloja edelliseen versioon luokittain.
5. Tarkistetaan geometriavirheet ja poikkeuksellisen suuret muutokset.
6. Luodaan kuvakaappaukset vakioiduista testipaikoista.
7. Julkaistaan uusi versio ensin testiympäristöön.
8. Hyväksynnän jälkeen vaihdetaan tuotannon aktiivinen versio.

Lähdemanifestiin tallennetaan vähintään lähdeosoite, latauspäivä,
aineistoversio, lisenssi ja tarkistussumma. Lataus voidaan automatisoida, kun
rajapinnat ja käsittely ovat osoittautuneet vakaiksi. Tuotantoon vienti pysyy
silti erikseen hyväksyttävänä vaiheena.

## 9. Toteutusvaiheet

### Vaihe 0: aineistokartoitus

- Selvitetään MML:n tarkat kohdeluokat ja niiden geometriat.
- Tarkistetaan Ahvenanmaan kattavuus.
- Inventoidaan tarvittaessa kartor.ax:n soveltuvat WFS-tasot ja lisenssit.
- Päätetään lopullinen luokkamuunnos.
- Tallennetaan lähdemanifesti ja pieni näyteaineisto.

Tässä vaiheessa ei muuteta tuotantosovellusta.

### Vaihe 1: Kustavi--Iniö--Velkua-pilotti

- Ladataan vain pilottialueen aineisto.
- Tuotetaan sovitut maanpeittoluokat.
- Mitataan raaka-aineiston, välituotteen ja PMTilesin koot.
- Tarkastetaan luokitus, saaret, rantaviivat ja geometriavirheet.
- Verrataan tulosta OpenStreetMapin nykyiseen maanpeitteeseen.

Tuloksena ovat ensimmäinen PMTiles-tiedosto ja käsittelyraportti.

### Vaihe 2: testinäyttö sovelluksessa

- Lisätään PMTiles-tuki Saaristolautat-sovellukseen.
- Näytetään taso vain testiympäristössä ja lähizoomilla.
- Lisätään kehityskäyttöön päälle/pois-kytkin.
- Varmistetaan, etteivät lauttareitit, tiet, nimet ja kyltit huku aineistoon.
- Mitataan tiilien latausmäärä ja piirron suorituskyky mobiilissa.

### Vaihe 3: Ahvenanmaan pilotti

- Testataan sama prosessi esimerkiksi Jomalassa.
- Käytetään ensisijaisesti MML:n aineistoa.
- Otetaan kartor.ax käyttöön vain, jos sille on osoitettu sisällöllinen tarve
  ja käyttöoikeus on varmistettu.
- Tarkistetaan mahdollinen sauma kahden lähdeaineiston välillä.

### Vaihe 4: koko toiminta-alue

- Laajennetaan rajaus kaikille Saaristolauttojen lauttareiteille.
- Optimoidaan zoomitasot, vähimmäispinta-alat ja geometrioiden tarkkuus.
- Tarkistetaan koko- ja verkkoliikennebudjetit.
- Testataan mobiililaitteella ja hitaalla verkkoyhteydellä.

### Vaihe 5: tuotanto ja ylläpito

- Dokumentoidaan toistettava päivitys- ja julkaisuprosessi.
- Lisätään automaattiset skeema-, geometria- ja kokotarkistukset.
- Julkaistaan ensin testiin ja hyväksynnän jälkeen tuotantoon.
- Varmistetaan palautus edelliseen PMTiles-versioon.

## 10. Riskit ja niiden hallinta

| Riski | Hallinta |
| --- | --- |
| Ahvenanmaan aineisto poikkeaa MML:n aineistosta | Tehdään Ahvenanmaasta erillinen pilotti ennen koko alueen käsittelyä. |
| Lähteiden luokat eivät tarkoita samaa asiaa | Käytetään pientä omaa luokitusta ja dokumentoituja lähdekohtaisia muunnoksia. |
| Aineisto antaa vanhentuneen tai liian tarkan vaikutelman | Vältetään tarpeetonta hienojakoisuutta ja kirjataan aineiston päiväys. |
| Geometriat tekevät arkistosta tai tiilistä liian suuria | Yhdistetään alueita, asetetaan vähimmäispinta-alat ja yksinkertaistetaan zoomikohtaisesti. |
| Viranomaisaineiston ja OSM-rantaviivan väliin syntyy rakoja tai ylityksiä | Tarkastetaan rannat pilotissa ja säädetään luokkia, peittävyyttä tai rantarajausta. |
| Kahden lähteen rajalle syntyy näkyvä sauma | Normalisoidaan luokat ja sijoitetaan lähderaja mahdollisuuksien mukaan merelle. |
| Kartasta tulee liian levoton | Taso näytetään vain lähizoomilla ja lauttareitit sekä merkinnät piirretään sen päällä. |
| WFS- tai latauspalvelun skeema muuttuu | Lähdeskeema validoidaan, raaka-aineisto arkistoidaan ja muunnokset pidetään erillisinä. |
| Lisenssin ehdot tai tekijätiedot unohtuvat | Lisenssitiedot ovat pakollinen osa manifestia, raporttia ja kartan tekijätietoja. |
| Suuri tiedosto vaihtuu käyttäjän latauksen aikana | Käytetään versionoituja tiedostonimiä ja atomista aktiivisen version vaihtoa. |
| Selain tai välipalvelin ei käsittele Range-pyyntöjä odotetusti | Lisätään testi Range-vastaukselle ja kokeillaan tuotannon nginx-ketjun läpi ennen julkaisua. |
| Ylläpidosta muodostuu kohtuuton työmäärä | Rajataan sisältö olennaisiin luokkiin, päivitetään korkeintaan vuosittain ja automatisoidaan vasta vakaa prosessi. |

## Pilotin hyväksymiskriteerit

Pilotti on onnistunut, jos:

- yksiväriset saaret saavat silmämääräisesti hyödyllistä rakennetta
- luokitus ei johda selvästi harhaan valituissa tarkistuspisteissä
- lauttareitit, tiet, nimet ja kyltit säilyvät ensisijaisina
- rantaviivoilla ei ole häiritseviä rakoja tai mereen ulottuvia alueita
- aineisto pysyy asetetuissa koko- ja verkkoliikennebudjeteissa
- sama lopputulos voidaan tuottaa uudelleen yhdellä dokumentoidulla komennolla
- lähteet, lisenssit ja aineistoversiot voidaan jäljittää manifestista

