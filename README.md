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
- `roads.json`: pohjakarttaa täydentävät käsin valitut tieosuudet. Toistettava
  tuontityönkulku on kuvattu tiedostossa `scripts/roads/README.md`.
- `saaristo.json`: laiturit, nimet ja muut karttakohteet. Tiedoston juuri on
  historiallisista syistä GeoJSON-tyylinen mutta ei täydellinen
  `FeatureCollection`.
- `timetables_jpg/`: sovelluksessa näytettävät paikalliset aikataulukuvat.
- `scripts/audit_ferry_data.py`: nykyisen `data.json`-aineiston rakenteen ja
  aikataulujen voimassaolon tarkistus.
- `docs/data-audit-2026-10-08.md`: vuoden 2026 lähde- ja sisältöauditoinnin
  tulokset.
- `docs/aland-ferry-pricing-2026.md`: Ålandstrafikenin vuoden 2026
  hinnoittelun lähdemuistio.
- `future/structured-routing/structured-timetables.json`: koneellisesti muodostettu rakenteellisen
  aikataulun luonnos. Tietueen `review.status` kertoo tarkistustilan.
- `future/structured-routing/structured-timetables.schema.json`: rakenteellisen aikataulun JSON Schema.
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

## Rakenteellisen aikataulun luonnos

Generoi rakenteellinen luonnos hyväksytyistä, paikallisesti tallennetuista
lähteistä:

```sh
python3 future/structured-routing/scripts/build_structured_timetables.py
```

Tarkista, että versionhallinnassa oleva tulos vastaa lähteitä:

```sh
python3 future/structured-routing/scripts/build_structured_timetables.py --check
```

Muunnin lukee lähdeluettelon `timetable-checks.json`:sta ja alkuperäiset
tiedostot Gitin ulkopuolisesta `.timetable-checker/originals/`-hakemistosta.
Ensimmäinen versio muuntaa Finferriesin HTML-aikataulujen lähtöajat,
voimassaolot, viikonpäivät, ajosuunnat, tauot ja huomautukset. Kellonaika
`24:00` tallennetaan arvona `00:00`, `dayOffset: 1`, mutta alkuperäinen arvo
säilyy kentässä `sourceTime`.

Jokaisella yksittäisellä lähdöllä on viikonpäivät lentoaikatauluista tutussa
`operatingDays`-muodossa. Seitsemän merkkiä tarkoittavat järjestyksessä
maanantaita–sunnuntaita, numero tarkoittaa ajopäivää ja alaviiva ettei vuoroa
ajeta, esimerkiksi `12_4567`. Aikataulun tekstissä annetut poikkeukset pitää
purkaa tähän lopulliseen ajopäiväjoukkoon. Säilytä lisäksi alkuperäinen merkintä
`noteRefs`-kentässä ja rakenteinen tulkinta `conditions`-kentässä, jotta tulkinta
voidaan jäljittää ja tarkistaa. Pelkkä tekstihuomautus ei riitä matkahakuun.
`noteInterpretationStatus` on `resolved` vasta, kun merkinnän vaikutus on purettu
rakenteeksi. Arvo `unresolved` estää keskeneräisen merkinnän sekoittamisen
valmiiseen reititysdataan. Merkinnättömän lähdön arvo on `not_applicable`.

Tietomallin ylin aikataulutaso on reitti, ei operaattorin lähdesivu. Esimerkiksi
Högsåralla on yksi `hogsara`-tietue, vaikka Finferries julkaisee arjen,
lauantain ja sunnuntain eri HTML-sivuilla. Saman suunnan ja kellonajan lähtö on
yksi `departures`-tietue. Sen `operations`-lista kertoo eri voimassaolojaksot,
ajopäivät, pyhäpäiväsäännöt ja poikkeusehdot. Operaattorin sivujen tunnisteet
säilytetään ainoastaan `sourceId`-provenienssina.

Kahden laiturin lähtöaikatauluissa `departures[].from` tarkoittaa aina
lähtölaituria. Älä käytä epämääräistä `direction`-kenttää. Kohdelaituri voidaan
johtaa kaksipäisen reitin toisesta laiturista; monen pysähdyksen
yhteysalusvuoroissa kulkusuunta määräytyy järjestetystä `calls`-listasta.

PDF-taulukoiden käsin tarkistetut litteroinnit säilytetään
`future/structured-routing/structured-timetable-transcriptions/`-hakemistossa. Monen pysähdyksen
yhteysalusvuorot kuvataan `trips`-listana ja niiden satamakäynnit järjestettynä
`calls`-listana. Generaattori yhdistää litteroinnit samaan reittikohtaiseen
aineistoon HTML-lähteiden kanssa.

Loppujen PDF:ien häviötön välivaiheen poiminta tehdään komennolla
`/Users/kranto/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 future/structured-routing/scripts/extract_remaining_pdf_timetables.py`.
Se tallentaa taulukot `sourceTables`-kenttään ja sivujen tekstin
`sourcePageText`-kenttään. Välivaihe poistaa PDF-taiton riippuvuuden ja säilyttää
kaikki solut, mutta `review.routingReady: false` tarkoittaa, ettei aineistoa saa
vielä käyttää matkahakuun. Vuorojen rajat, ajopäivät ja huomautusmerkit on ensin
purettava `trips`/`calls`-rakenteeksi ja tarkistettava lähdekuvaa vasten.
Pelkkä tekstipoiminta ei riitä, jos PDF käyttää väriä semantiikkaan. Esimerkiksi
Houtskarin ja Iniön lisäreitin sininen merkintä ilmaisee virallisen
vaihtoyhteyden. Säilytä ja tarkista tällaiset värikoodit lähdekuvasta.

Jos saman virallisen aikataulun kieliversiot ovat keskenään ristiriidassa,
säilytä kaikki lähdearvot ja ristiriidan kuvaus rakenteessa. Käytä oletuksena
Manner-Suomen aikatauluissa suomenkielistä ja Ahvenanmaan aikatauluissa
ruotsinkielistä tietoa. Kirjaa valittu arvo ja valintaperuste erikseen, jotta
ratkaisu voidaan myöhemmin tarkistaa tai vaihtaa.

Ålandstrafikenin vuosiaikataulu muodostuu tavallisesti viidestä kaudesta mutta
kolmesta varsinaisesta aikataulupohjasta: alkuvuosi vastaa loppuvuotta, kevään
välikausi syksyn välikauden aikataulua ja kesäkausi muodostaa kolmannen pohjan.
Vuodenvaihteessa julkaistaan uusi vuosikerta, jota voidaan vielä päivittää
vuoden aikana. Päivitetyssä loppuvuoden PDF:ssä näkyvät alkuvuoden tai kevään
poikkeukset ovat historiallisia viitteitä; merkitse ne pois aktiivisesta
reitityksestä, elleivät ne kuulu tarkasteltavaan voimassaolokauteen.

Ahvenanmaan vaijerilossien yleissivun taukoja ei kopioida reitille, jolla on
oma kellonaikataulu: tauko näkyy jo aikataulun lähtöjen aukosta ja olisi
redundantti. Yleissivulta yhdistetään tällaiselle reitille vain muualta
puuttuvat poikkeukset, kuten joulun liikenne. Embarsund on poikkeus syys–
joulukuussa: kesäaikataulun päätyttyä se liikennöi tarvittaessa ilman
kellonaikataulua, joten yleissivu toimii silloin aktiivisena lähteenä.

Ålandstrafikenillä varaus on käyttäjän kannalta normaali toimintatapa. Reititin
voi käsitellä vuoron mahdollisena, jos käyttäjä pystyy varaamaan sen. Esimerkiksi
polttoainekuljetuksia koskevat merkinnät säilytetään tarvittaessa vähäisinä
lähdeannotaatioina, mutta niitä ei nosteta käyttäjän matkahaun ehdoiksi.
Liitä polttoainekuljetuksen vaikutus kyseisen vuoron vähäiseen
`userNotices`-huomioon. Kerro vain lähteen vahvistama käytännön vaikutus:
Brändö–Kumlinge-aikataulussa se on enintään 20 matkustajaa. Älä väitä
ajoneuvokapasiteetin pienenevän, koska lähde ei sitä sano.
Poikkeuksellisia, maakuntahallitukselta viikkoja etukäteen anottavia yövuoroja
ei sisällytetä tämän palvelun käyttäjille tarjottaviin reittivaihtoehtoihin.

Finferriesin terminologiassa `yhteysalus` tarkoittaa monisatamaista
yhteysaluspalvelua, ei point-to-point-liikennettä hoitavaa maantielauttaa.
Finferriesin yhteysalusmatka varataan aina yhteisestä varauspalvelusta
`https://booking.finferries.fi/`. Tämä matkan varaus on eri asia kuin vanhoista
taulukoista säilynyt `y`: `y` määrää, että kyseisessä laiturissa poiketaan vain
ennakkoon tehdystä tilauksesta. `x` tarkoittaa tarvittaessa tehtävää
laiturikäyntiä, jota ei tarvitse tilata erikseen. Älä päättele `y`:n
puuttumisesta, ettei yhteysalusmatkaa tarvitsisi varata.
Käytännön hypoteesi on, että `y` kuuluu jokaiselle tilattavalle välikäynnille.
Päätelaiturin kellonajasta merkintä voi puuttua, koska se ei antaisi kaikkien
matkojen yleisen varausvelvollisuuden lisäksi uutta tietoa. Säilytä silti
lähteen solumerkintä sellaisenaan äläkä lisää puuttuvaa `y`:tä lähdedataan.
Luokittele reitti ensisijaisesti kartta-aineiston yhteystyypistä:
`saaristo.json`-aineistossa yhteysalukset ovat `conn4` ja Iniö–Kustavi sekä
Kasnäs–Hiittinen `conn2`. Kahden laiturin rakenne tukee jälkimmäisten
`road_ferry`-luokitusta, mutta laiturimäärä ei yksin ratkaise tyyppiä.

Yhteysalustaulukon sama päätelaituri vuoron alussa ja lopussa kuvaa aluksen
kierroksen operatiivista kehystä, ei matkustajalle tarjottavaa päätelaituri–
päätelaituri-matkaa. Kierros ajetaan, kun vähintään yksi matka päätelaiturista
saareen, saaresta päätelaituriin tai poikkeuksellisesti saarten välillä on
varattu. Ilman varauksia alus ei aja tyhjää kierrosta. Lähtöaika voi olla tarkka
ja paluuaika likimääräinen, koska paluu riippuu tilatuista laiturikäynneistä ja
olosuhteista. Matkahaku ei saa muodostaa esimerkiksi Kirjais–Kirjais-yhteyttä.

Sulkeisiin merkitty välilaiturin aika tulkitaan arvioajaksi. Paraisten reitillä
Pensar on kierroksen kauimmaisin piste, joten sen arvioaika on käyttäjälle
hyödyllinen kiintopiste ja voi tavallisesti olla melko vakaa myös Pensarin
jälkeisiltä laitureilta lähteville. Sitä ei kuitenkaan esitetä minuutilleen
taattuna aikana, sillä tilatut käynnit ja olosuhteet voivat siirtää sitä.

Erota aina koko matkan varausvelvollisuus yksittäisen laituripoikkeaman
tilaamisesta. Paraisten reitillä kaikki matkustajan matkat varataan.
Granholmen käsitellään rakenteessa omana varattavana laituririvinään ennen tai
jälkeen jokaista Heisala-käyntiä kulkusuunnan mukaan. Granvik–Heisala on lähes
heiluriliikennettä ja Granholmen vain pieni poikkeama reitiltä, joten lähde on
jättänyt toistuvat Granholmen-rivit painamatta. Klo 7.45 ja 14.00 Granvikista
lähtevät kierrokset muodostavat poikkeuksen: alus ajaa vain
Granvik–Heisala–Granvik eikä käy Granholmenissa lainkaan. Niillä ei siis voi
tilata Granvik–Granholmen- eikä Granholmen–Granvik-matkaa. Kaikilla muilla
vuoroilla matkan voi tilata kumpaankin suuntaan.

Ramsholm on Heisalan saaren toisessa päässä sijaitseva oma laituri, vaikka se ei
ole normaali aikataulupysähdys. Se säilytetään erillisenä haettavana lähtö- ja
määräpaikkana erikoismerkinnällä `varattavissa vain olosuhteiden niin
vaatiessa`. Käyttäjälle ei esitetä arvailuja siitä, mitä nämä olosuhteet ovat.
Granvikista tultaessa reittijärjestys on
Björkholm–Ramsholm–Stenholm–Aspholm; Ramsholm ja Stenholm on jätetty painetusta
aikataulutaulukosta pois.
Stenholmiin ja Stenholmista voi varata matkan kumpaankin suuntaan jokaisella
Pensariin ulottuvalla kierroksella. Lyhyemmillä kierroksilla Stenholm-käynti ei
ole tarjolla.

Paraisten reitin varausohjeen `aamuvuoro` tulkitaan vain päivän ensimmäiseksi,
Granvikista klo 6.00 lähteväksi vuoroksi. Se varataan edellisenä päivänä klo 17
mennessä; muiden vuorojen määräaika on vähintään 10 minuuttia ennen lähtöä.
Sanamuoto ei määrittele aamuvuoroa täsmällisesti, joten tulkinnan varmuustaso on
rakenteessa keskitaso.

Iniö–Kustavin aikataulun harmaa taustaväri on semanttinen merkintä. Tiistain ja
torstain Heponiemen klo 7.00 sekä Kannvikin klo 9.30 lähdöt ovat vaarallisten
aineiden kuljetuksia, joilla matkustajamäärä on rajoitettu. Tieto tallennetaan
yksittäisten lähtöjen huomautukseksi eikä koko reitin ominaisuudeksi.
Kasnäs–Hiittinen-reitillä sama harmaa merkintä koskee kaikkia maanantaista
perjantaihin Kasnäsistä klo 6.30 ja Långnäsistä klo 8.30 lähteviä vuoroja:
viittä lähtöä kumpaankin suuntaan eli yhteensä kymmentä lähtöä viikossa.

Utön reitin `(tx)`-merkinnät muodostavat yhden yön yli jatkuvan kierron, eivät
joukkoa toisistaan riippumattomia lähtöjä. Henkilökuljetus lähtee reitin
päälaiturista Pärnäisistä sunnuntaina klo 17.05, saapuu Utön kylälaituriin klo
19.30, yöpyy Utössä ja palaa maanantaina klo 6.00–8.15 Pärnäisiin. Molemmat
osuudet tilataan viimeistään edeltävänä lauantaina klo 15. Vuoro ajetaan
Myrskylinnulla tai Berghamnilla, eikä sillä kuljeteta ajoneuvoja; koululaiset ja
paikalliset asukkaat ovat ensisijaisia matkustajia. Vuoro näytetään silti
kaikille matkahakijoille mahdollisena yhteytenä, jos varaus hyväksytään;
ensisijaisuus esitetään huomautuksena eikä käyttörajauksena.
Utön perjantain aamukierroksella Utö 5.30–Pärnäinen 10.00 Berghamnin `z`-käynti
on varattavissa edellisenä päivänä klo 17 mennessä vain parittomilla
ISO-viikoilla. Parillisilla viikoilla Berghamnia ei tarjota tällä kierroksella
lainkaan.
Utön pääsiäispoikkeus 25.3.2027 `perjantain aikataulu klo 18.00 →` tarkoittaa,
ettei ennen klo 18 ole lainkaan liikennettä. Vasta klo 18 alkaen käytetään
perjantain aikataulua; sitä ei yhdistetä torstain päivävuoroihin. Utön matka
kestää noin viisi tuntia, joten alus ei ehtisi ajaa kahta tällaista kierrosta.
Pääsiäisen 2027 `(tx)`-yökierto siirtyy päivällä: sunnuntaiaikataulun mukainen
Pärnäinen 17.05–Utö 19.30 ajetaan maanantaina 29.3. ja siihen kuuluva
maanantaiaikataulun Utö 6.00–Pärnäinen 8.15 tiistaina 30.3. Tiistaina ei ole
muita normaaleja vuoroja. Normaali keskiviikkoliikenne jatkuu 31.3. Siirretty
kierto varataan edeltävänä lauantaina 27.3. klo 15 mennessä.
Maanantain `(tx)`-paluu saapuu Pärnäisiin klo 8.15 ja varsinainen M/S Utö lähtee
klo 8.30. Vaihto on fyysisesti mahdollinen, mutta sitä ei ehdoteta yhteytenä:
`(tx)` on jo käynyt samoissa välisaarissa, joihin M/S Utö on lähdössä takaisin.
Reitityksen pitää karsia tällaiset teknisesti mahdolliset mutta hyödyttömät
takaisinpäin vaihdot.
Östra Tallholm poistetaan nykyisestä Paraisten reitistä ja kartan
laiturikohteista. Se esiintyi ainakin vuoden 2019 aikataulussa, mutta ei
tarkistetuissa vuoden 2025 kesäaikatauluissa eikä nykyisessä talviaikataulussa.
Rakenteinen data kuvaa nykyisiä matkustusmahdollisuuksia, ei historiallista
laituriluetteloa.

Jos painettu aikataulu yhdistää kaksi lähekkäistä saarta samalle riville tilan
säästämiseksi, säilytä lähderivi mutta pura se reitityksessä kahdeksi erilliseksi
kohteeksi. Esimerkiksi Nauvon eteläisen reitin `Gloskär / Trunsö` tarkoittaa
kahta erillistä `y`-käyntiä. Kummankin voi varata erikseen ja samalla vuorolla
voidaan käydä molemmissa.
Yleisemmin kauttaviivalla samalla rivillä luetellut laiturit ovat matkustajalle
erillisiä kohteita, joille rivin `y`, `x` tai muu ehto periytyy erikseen.
Yhdistetty rivi tulkitaan painetun taulukon tilansäästöksi, ellei lähde tai
reittikohtainen tieto nimenomaisesti osoita muuta.
Kauttaviiva voi kuitenkin erottaa myös saman paikan kieliversiot. Esimerkiksi
`Själö/Seili`, `Nagu/Nauvo` ja `Pärnäs/Pärnäinen` normalisoidaan kukin yhdeksi
laituriksi kielikohtaisine nimineen, ei kahdeksi kohteeksi.

Nauvon pohjoisen reitin sunnuntain `y**` yhdistää kaksi merkittyä vuoroa
jaksoilla 11.8.–13.9. ja 9.–31.5. Erillisten Nauvo–Seili–Nauvo- ja
Nauvo–…–Ahvensaari-vuorojen sijasta ajetaan yksi kierros klo 17.50:
Nauvo–Seili–Nauvo–Innamo–Järvsor–Maskinnamo–Ahvensaari. Korvatut vuorot eivät
jää samalle päivälle erillisiksi lähdöiksi.

Nauvon eteläisen reitin viikonloppuliikenne muodostaa Borstön yökierron.
Päälaituri on Kirjais ja kaukaisin kohde Borstö. Alus lähtee lauantaina
Kirjaisista klo 10, saapuu Borstöön noin klo 13.25 ja palaa sunnuntaina klo
12–noin 18 Kirjaisiin. Sunnuntain paluuvuoron `y+` tarkoittaa, että koko matka
tilataan edellisenä päivänä klo 12 mennessä, vaikka plusmerkkiä ei ole toistettu
jokaiseen soluun. Klo 18 alkava Kirjais–Peno–Pensar–Kirjais on erillinen lyhyt
`y`-kierros, jonka määräaika on edellisenä päivänä klo 18. Taulukon vahva
poikkiviiva ei yhdistä näitä vuoroja.
Sunnuntain Borstö–Kirjais-paluun `y*+` tulkitaan toistaiseksi keskitason
varmuudella näin: sama M/S Falkö jatkaa Kopparholmin jälkeen ilman aluksenvaihtoa,
ohittaa varmasti Knivskärin ja ajaa sijainnin mukaisessa järjestyksessä
poikittaisen reitin Berghamn–Ängsö–Lånholm–Hummelholm,
minkä jälkeen se palaa eteläiselle reitille Brännskärissä ja jatkaa
Grötö–Stenskär–Gullkrona–Kirjais. Kopparholm kuuluu eteläiseen reittiin.
Plus- ja tähtimerkinnän voidaan ajatella koskevan koko Borstö–Kopparholm-osuutta,
vaikka ne on painettu vain Kopparholmin soluun; tulkinta ei ole täysin varma.

Brännskär, Grötö, Stenskär ja Gullkrona kuuluvat sekä Nauvon poikittaiseen että
eteläiseen reittiin. Grötö sekä aikataulussa lisäksi mainittu Triören ovat
poikittaisella reitillä tilauksesta poikettavia laitureita. Triören puuttui
vanhasta reitti- ja laituridatasta kokonaan. Se lisätään Gullkronan
pohjoispuolelle alustavasti kaakkoisrannan laituriin, ja reittiviiva kulkee
Gullkronasta Furuskärin ja Mottonskärin itäpuolitse. Laiturin tarkka koordinaatti
varmistetaan myöhemmin historiallisen livedatan avulla.

Tiistaisin M/S Falkö siirtyy eteläiseltä reitiltä ajamaan poikittaisen reitin
kierroksen Kirjaisista noin klo 9.30 ja palaa Kirjaisiin klo 12. Poikittaisen
taulukon mukainen järjestys on
Kirjais–Byskär–Brännskär–Ängsö–Lånholm–Hummelholm–Berghamn–Kirjais.
Kyse ei ole erillisestä eteläisen reitin matkustajakierroksesta. Eteläisen
reitin klo 16 lähtö on myöhempi erillinen vuoro.

Poikittaisen taulukon sunnuntain `Borstö → *` ei aloita uutta vuoroa. Se jatkaa
samaa M/S Falkön Borstöstä klo 12 lähtenyttä eteläisen reitin paluuvuoroa
poikittaisen reitin osuudella Berghamn–Ängsö–Lånholm–Hummelholm ja edelleen
Brännskär–Grötö–Stenskär–Gullkrona–Kirjaisiin noin klo 18. Viimeiset yhteiset
laiturit on jätetty poikittaisesta taulukosta pois, jotta yhtä sunnuntaivuoroa
varten ei tarvita omia rivejä. Taulukoiden yhteinen oranssi pohjaväri on semanttinen
jatkuvuusmerkintä. Rakenteessa kyse on yhdestä lähdöstä, vaikka vuoro kuvataan
kahdessa reittitaulukossa.

Nauvon eteläisen reitin arkipäivien ensimmäinen Kirjaisin lähtö on
lähtöaikaikkuna 6.15–6.50, ei yksittäinen arvioaika. Tarkka lähtö määräytyy
varausten perusteella ja vahvistuu matkustajalle varauksen yhteydessä.
Brännskärin klo 7.20 ja Kirjaisiin paluun klo 7.45 ajat säilytetään julkaistuina
kiintopisteinä.

Käyttöliittymä näyttää nimen ensisijaisesti käyttäjän valitsemalla kielellä.
Kun kieliversiot poikkeavat niin paljon, ettei samaa paikkaa voi helposti
tunnistaa, näytä lisäksi toinen kotimainen nimi. Suositeltuja muotoja ovat
esimerkiksi `Seili / Själö`, `Själö / Seili` ja englanniksi `Seili / Själö`.
Yhteinen pysyvä laituritunniste estää rinnakkaisnimien muuttumisen erillisiksi
reittisolmuiksi.
Samannimisiä mutta eri paikkoja ei tarvitse tarkentaa saman reitin tavallisessa
näkymässä tai kartalla, koska ne eivät esiinny samalla reitillä. Lisää reitti-
tai kuntatarkenne vasta hakutulokseen, jossa eri reittien samannimiset kohteet
voivat sekoittua. Berghamn on tärkeä testitapaus: eri yhteysalusreittien varrella
on useita eri Berghamn-kohteita.
Sulkeissa oleva paikannimi voi olla pelkkä sijaintikonteksti eikä osa laiturin
nimeä. Nauvon pohjoisen reitin `Lavarn (Houtsala)` normalisoidaan laituriksi
`Lavarn`: Houtsala on ympäröivä saari tai alue. Koska muuta Lavarnia ei ole,
Houtsala-tarkennetta ei näytetä normaalissa käyttöliittymässä.
Rymättylän reitin `Korvenmaa/Wihuri/Pyytti` puretaan vastaavasti kolmeksi
erilliseksi käynniksi. Korvenmaa ja Pyytti ovat eri saaria; Wihuri on erillinen
laituri Korvenmaan saaressa.
Nauvon poikittaisen reitin `Ängsö / Lånholm` tarkoittaa kahta itsenäistä
laituria saman suuren saaren eri puolilla, yli kahden kilometrin päässä
toisistaan. Solun merkintä periytyy kummallekin erikseen.
Velkuan reitin Munninmaa, Kettumaa, Liettinen ja Tammisluoto ovat eri saaria.
Niiden vaihtelevat kauttaviivayhdistelmät puretaan aina luetelluiksi erillisiksi
laiturikäynneiksi.

Rymättylän reitin sulkeissa olevat kellonajat ovat laskennallisia väliaikoja,
eivät sitovia lähtö- tai saapumisaikoja. Esimerkiksi Ruotsalainen `(10.35)x` ja
Pakinainen `(10.55)x` ilmaisevat noin 20 ja 40 minuuttia Haapalan klo 10.15
lähdöstä. `x`-käynti tehdään tarvittaessa ja on käytännössä tavallinen, mutta ei
varma. Muille laitureille ei pidä keksiä aikaa. Haapalan painettu paluuaika on
kierroksen kehysaika; todellinen paluu voi aikaistua, jos valinnaisia käyntejä
jää pois.
Sunnuntain Pakinainen `(16.40/17.05)x` on ehdollinen aika: noin klo 16.40, jos
Pähkinäisessä ei käydä ensin, ja noin klo 17.05, jos Pähkinäisen käynti tehdään.
Älä muodosta niistä kahta erillistä lähtöä.

Houtskarin reitin talvi-PDF:n ensimmäisestä otsikkorivistä puuttuu pystyviiva
maanantain ja tiistain välistä. Se on taittovirhe, ei yhdistetty päiväotsikko.
Aamun klo 5.50 kierroksen ajat ovat tiistain ja keskiviikon sarakkeissa
(`_23____`), eivät maanantaina.
Sunnuntain Själö `(~13.20)` – Torsholma 13.55/14.10 – Själö `(~14.50)` on yksi
edestakainen kierros. Själön ajat ovat likimääräisiä väliaikoja mennessä ja
palatessa; Torsholman ajat ovat saapuminen ja paluulähtö.
Houtskarin aikataulun mainitsema yhteys Iniön lisäreitiltä Houtskarin reitille
on suunniteltu, vain tähän suuntaan toimiva vaihto Själössä. Älä päättele
odottamistakuuta ilman erillistä lähdettä. Esimerkiksi perjantaina Åselholm
13.10 – Själö 13.40 jatkuu M/S Finnön Torsholmasta klo 14.30 alkavalla
kierroksella Själöstä Roslaxiin klo 17.40. Själön tarkka noutoaika puuttuu ja
on historiadata-arvion ehdokas; normaali odotus on yli tunti.
Maanantaina, keskiviikkona ja sunnuntaina Iniön lisäreitin ja Houtskarin reitin
alukset ovat iltapäivällä yhtä aikaa Själössä. Näinä päivinä aikataulu tarjoaa
virallisen vaihtoyhteyden kumpaankin suuntaan. Yhteys on merkitty PDF:ssä
sinisellä; väri on tässä rakenteellista tietoa eikä koriste. Merkitse yhteys
viralliseksi, mutta älä päättele odottamistakuuta ilman erillistä lupausta.

Korppoon reittialueen sunnuntain `#`-merkityt Österskär-ajat tulkitaan omaksi
klo 10.00 Korppoosta lähteväksi kierrokseksi. Lähteen Österskär klo 12.00
säilytetään julkaistuna arvona, mutta noin 90 minuutin tyypillinen matka-aika ja
paluu ennen klo 13.00 alkavaa seuraavaa kierrosta tarkennetaan historiadatasta.
Korppoo 13.00 – Berghamn 14.00 – Korppoo 15.30 on erillinen kierros.
Österskärin kierroksen `Brunskär/Kälö` puretaan kahdeksi erilliseksi
varattavaksi laituriksi. PDF:n harmaa värialue ja `#`-huomautus keskeyttävät
koko kierroksen 2.11.2026–30.4.2027, joten talvella ei käydä Brunskärissä,
Kälössä eikä Österskärissä tämän vuoron osana.

### Historiadataan perustuvat laituriaika-arviot

Rakenteessa julkaistu aikatauluaika ja myöhemmin laskettava historiapohjainen
arvio ovat eri asioita. Säilytä julkaistu aika kentissä `time`, `timeRange` tai
`timeAlternatives`. Mahdollinen arvio kuuluu satamakäynnin erilliseen
`historicalEstimate`-kenttään eikä se saa korvata lähteen ilmoittamaa aikaa.

Arviossa on vaihteluväli (`range.earliest`–`range.latest`) ja mahdollinen
tyypillinen aika (`typical`). Tallenna myös otoskoko, havaintojen aikaväli,
arvion laskenta-aika, malliversio ja mahdollinen luottamusarvo. Arvio on aina
luonteeltaan neuvova. `disclosureRequired` on pakollisesti `true`, ja
käyttöliittymän pitää kertoa `disclosureKey`-tekstillä, että aika perustuu vain
historiadataan eikä ole operaattorin julkaisema aikataulu tai taattu yhteys.

Historiapohjainen arvio sopii erityisesti PDF:ssä ilman kellonaikaa oleville
tilattaville välikäynneille. Älä lisää arviota ennen kuin käytettävissä on
riittävä havaintoaineisto; siihen asti `time: null` on oikea esitys.

Generoitu tietue on aina aluksi `generated_unreviewed`. Älä käytä sitä
matkahakuun varmennettuna tietona ennen kuin lähtöajat, poikkeukset ja
huomautusviitteet on verrattu alkuperäiseen aikatauluun. PDF-lähteet ja
HTML-sivut, joissa ei ole aktiivisia lähtöjä, luetellaan toistaiseksi
`unconvertedSources`-kentässä. Näin aineiston kattavuusvajetta ei voi tulkita
vahingossa liikennöinnin puuttumiseksi.

Rakenteellinen aikataulu sisältää vain tarkistushetkellä voimassa olevat ja
tulevat kaudet sekä päivämääräpoikkeukset. Päättynyt `validTo` ja mennyt
poikkeuspäivä poistetaan sekä litteroinnista että generoidusta aineistosta.
Avoimena jatkuvaa aikataulua ei poisteta vain siksi, että sen `validFrom` on
menneisyydessä. Lähdetarkistuksen historiatiedot voivat säilyä erillisessä
`timetable-checks.json`-tiedostossa, mutta niitä ei viedä reititysdataan.
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

### Lähdeaikataulujen muutosten tarkistus

`scripts/check_timetables.py` vertaa Finferriesin HTML-aikatauluja sekä
Finferriesin, Ålandstrafikenin ja Saaristolinjojen PDF:iä hyväksyttyyn
vertailutilaan.
Versionhallintaan kuuluva `timetable-checks.json` sisältää lähdeosoitteet ja
niiden viimeksi hyväksytyt tunnisteet. Alkuperäiset PDF:t ja HTML-tiedostot
tallennetaan `.timetable-checker/originals/`-hakemistoon. Koko
`.timetable-checker/` on jätetty Gitin ulkopuolelle.

Tee tavallinen, esimerkiksi viikoittainen tarkistus näin:

```sh
python3 scripts/check_timetables.py check
```

Tarkistus ei muuta hyväksyttyä vertailutilaa. Se tallentaa uusimmat ladatut
tiedostot `.timetable-checker/candidates/`-hakemistoon ja koneellisesti
luettavan raportin tiedostoon `.timetable-checker/last-report.json`.
Tulosteessa käytetään seuraavia tiloja:

- `UNCHANGED`: sisältö vastaa vertailutilaa. HTTP 304 tarkoittaa, että palvelin
  vahvisti tämän ETag-tunnisteella lataamatta tiedostoa uudelleen.
- `METADATA`: tiedoston tavut muuttuivat, mutta HTML:n normalisoitu sisältö tai
  PDF:n kaikki renderöidyt sivut säilyivät samoina.
- `CHANGED`: aikataulun sisältö muuttui. PDF:n kohdalla raportti luettelee
  muuttuneet sivut.
- `ERROR`: lähdettä ei voitu tarkistaa. Tämä ei tarkoita, että lähde olisi
  ennallaan.

Paluuarvo on 0, kun kaikki on ennallaan, 2 kun muutoksia löytyi ja 1 kun
vähintään yksi tarkistus epäonnistui. Virhe saa etusijan muutokseen nähden.
Ålandstrafiken suojaa sivunsa JavaScriptillä suoritettavalla
proof-of-work-tarkistuksella. Skripti käyttää siksi näihin lähteisiin paikallista
Google Chromea ja säilyttää sen istunnon `.timetable-checker/chrome-profile/`-
hakemistossa. Chromen tarkan polun voi tarvittaessa antaa
`TIMETABLE_CHROME`-ympäristömuuttujassa. Jos selainkaan ei läpäise tarkistusta,
skripti ilmoittaa `ERROR` eikä kuittaa tiedostoa tarkistetuksi. Lataa PDF:t
siinä tapauksessa selaimella paikalliseen hakemistoon ja vertaa niitä
tiedostonimiin perustuen samalla PDF-tarkistuksella:

```sh
python3 scripts/check_timetables.py check-local /polku/ladattuihin/pdf-tiedostoihin
```

Hakemistossa ei tarvitse olla kaikkia lähteitä; komento tarkistaa ne tiedostot,
joiden nimi vastaa jonkin `sources`-rivin `seedFile`-kenttää. Myös tämä komento
tallentaa raportin ja ehdokkaat, mutta ei hyväksy niitä automaattisesti.

Skripti sulkee oman Chromensa hallitusti. Jos aikaisempi ajo on keskeytynyt,
se poistaa käynnistyksessä vain tarkistusprofiilin vanhentuneet
`SingletonLock`-, `SingletonSocket`- ja `SingletonCookie`-linkit. Käynnissä
olevan prosessin lukkoa ei poisteta. Chromen käynnistysloki tallennetaan
tarvittaessa tiedostoon `.timetable-checker/chrome-startup.log`, ja sama
käynnistysvirhe raportoidaan ajon aikana vain alkuperäisen syyn perusteella
uudelleen yrittämättä Chromea jokaiselle PDF:lle erikseen.

Kun raportti ilmoittaa muutoksesta:

1. Säilytä `.timetable-checker/candidates/` tarkastuksen ajan. Vertaa muuttuneet
   sivut ja päivitä sovelluksen aikataulukuvat sekä `data.js` normaalin
   työjärjestyksen mukaan.
2. Lisää kokonaan uudet kausilinkit `timetable-checks.json`:n `sources`-listaan.
   Finferriesin tarkistus käy aikatauluhakemiston reittisivut läpi ja
   Ålandstrafikenin sekä Saaristolinjojen tarkistukset lukevat niiden
   aikataulusivut. Ne kertovat uusista PDF- tai HTML-aikataululinkeistä, mutta
   eivät lisää niitä automaattisesti. `acceptedUrls` sisältää lähdesivulla
   edelleen näkyvät historialliset tiedostot, joita ei tarvitse tarkistaa
   sisältölähteinä mutta joita ei myöskään pidä ilmoittaa uutena joka ajolla.
3. Kun uusi aikataulu on käsitelty ja tarkistettu, hyväksy ladatut lähteet:

   ```sh
   python3 scripts/check_timetables.py accept
   ```

4. Tarkista ja kommitoi muuttunut `timetable-checks.json` aikataulupäivityksen
   mukana. Älä lisää `.timetable-checker/`-hakemiston alkuperäistiedostoja
   versionhallintaan.

Vertailutila voidaan rakentaa uudelleen jo ladatuista alkuperäistiedostoista.
Jokaiselle `sources`-rivin `seedFile`-nimelle on löydyttävä tiedosto jostakin
annetusta hakemistosta:

```sh
python3 scripts/check_timetables.py seed /polku/finferries /polku/alandstrafiken
```

PDF:stä tallennetaan tavuhajautuksen lisäksi jokaisen 150 dpi:n PNG-renderöidyn
sivun SHA-256. Siksi PDF:n metatietojen muuttuminen voidaan erottaa näkyvästä
aikataulumuutoksesta myös niissä Ålandstrafikenin PDF:issä, joista tekstiä ei
voi luotettavasti poimia. Renderöintitarkistus edellyttää Popplerin
`pdftoppm`-komentoa. macOSissa sen voi asentaa komennolla `brew install
poppler`. Vaihtoehtoisesti komennon tarkan polun voi antaa ympäristömuuttujassa
`TIMETABLE_PDFTOPPM`. Skripti etsii myös Homebrewin tavalliset asennuspolut ja
Codexin mukana toimitetun version. Jos renderöintitarkkuutta muutetaan, vanha
vertailutila on alustettava uudelleen samalla tarkkuudella.

Finferriesin HTML-lähteiden normalisoitu hajautus jättää
`finferriesFerryBulletins`-liikennetiedotteet huomiotta. Lyhyen huoltoseisakin
tai muun tilapäisen tiedotteen lisääminen tai poistuminen ei siten näyttäydy
aikataulumuutoksena. Raakatiedoston SHA-256 muuttuu silti, joten tapaus näkyy
`METADATA`-tilana ja voidaan tarvittaessa tarkastaa raportista.

## Sovelluksen tarkistus

Datamuutoksen jälkeen rakenna sovellus Node.js 24:llä:

```sh
cd ../saaristolautat
PATH=/Users/kranto/.nvm/versions/node/v24.21.0/bin:$PATH npm run build
```
