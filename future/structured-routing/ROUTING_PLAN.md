# Suunnitelma rakenteiselle reittikalenterille ja yhdistelmäreititykselle

## Tavoite

Palveluun rakennetaan aikataulukuvien rinnalle rakenteinen reittikalenteri,
josta voidaan hakea tietyn päivän vuorot ja muodostaa usean lautta-,
yhteysalus- ja tieosuuden matkaketjuja.

Palvelun tehtävä ei ole taata matkan toteutumista tai alukseen mahtumista. Sen
tehtävä on kertoa julkaistujen aikataulujen perusteella mahdolliset yhteydet,
niiden ehdot ja käytännölliset vaihtoehdot niin, ettei käyttäjän tarvitse itse
tulkita useita PDF:iä tai aikataulukuvia.

Esimerkkikysymyksiä:

- Miten pääsen Äpplöön 30.11., jos voin lähteä Roslaxista tai Kannvikista?
- Miten pääsen 23.12. Kustavista Sottungaan autolla?
- Miten pääsen pyörällä Turusta Iniöön, jos ajan keskimäärin 18 km/h ja vältän
  vilkasliikenteisiä teitä?
- Kuinka aikaisin minun kannattaa lähteä, jos haluan varmasti ehtiä päivän
  viimeiselle jatkoyhteydelle?

## Miksi rakenteinen kalenteri on mahdollinen

Nykyisistä aikatauluista voidaan poimia riittävän luotettavasti:

- voimassaolojaksot ja liikennöintipäivät
- normaalit sekä pyhä- ja poikkeusaikataulut
- lähdöt, saapumiset ja välilaiturit
- ajosuunnat ja viikonpäiväkohtaiset erot
- tilausvuorot ja tarvittaessa käytävät laiturit
- tilauksen määräajat ja yhteystiedot
- ajoneuvoja, varauksia ja maksuja koskevat ehdot
- voiko mukaan ottaa polkupyörän, moottoripyörän tai auton
- aikatauluun merkityt jatkoyhteydet
- lähdeasiakirja ja sen tarkistusajankohta

PDF:n tai HTML-taulukon koneellinen tulkinta voi tuottaa ensimmäisen luonnoksen,
mutta rakenteinen data hyväksytään vasta vertaamalla se alkuperäiseen
aikatauluun. Nykyinen lähteiden muutostarkistin kertoo myöhemmin, mitkä
aikataulut pitää käsitellä uudelleen.

## Kaksi eri liikennetyyppiä

Reitityksessä on erotettava kaksi käytännössä hyvin erilaista tapausta.

### Harvoin kulkevat yhteysalukset ja tilattavat vuorot

Tilausvuoro tai tarvittaessa käytävä laituri ei ole epävarma tai huonompi
reittivaihtoehto. Aikataulua hakee juuri käyttäjä, joka haluaa päästä kyseiselle
vuorolle ja voi tehdä tarvittavan tilauksen.

Nämä yhteydet kulkevat yleensä niin harvoin, että matka suunnitellaan tietyn,
ennalta valitun vuoron ympärille. Jos vuoro pitää tilata tai autopaikka varata,
reititin näyttää sen normaalina yhteytenä ja antaa käyttäjälle selkeän
toimintaohjeen:

- mitä pitää tilata tai varata
- mihin määräaikaan mennessä
- puhelinnumero tai varauslinkki
- koskeeko ehto koko vuoroa, tiettyä laituria vai vain ajoneuvoa
- onko osuus maksullinen

Reitittimen ei pidä korvata tällaista vuoroa epämääräisellä aikaikkunalla tai
piilottaa sitä epävarmana. Tavoitteena on saapua ajoissa juuri varatulle
vuorolle. Sitä edeltäville osuuksille lisätään käyttäjän valitsema tai
reittikohtaisesti suositeltu varmuusväli.

### Lyhyet lossit ja jatkuva sukkulaliikenne

Lyhyillä lossiyhteyksillä käyttäjällä on yleensä vaihtoehtoja. Esimerkiksi
Parainen–Nauvo voi ruuhkassa olla täynnä tai jäädä julkaistusta aikataulusta,
vaikka kaksi alusta liikennöi käytännössä jatkuvasti edestakaisin.

Tällainen yhteys mallinnetaan jatkuvana tai tiheänä sukkulaliikenteenä, ei
ehdottoman tarkkana yksittäisenä lähtönä. Reititin huomioi:

- arvioidun vuorovälin ja ylitysajan
- mahdollisen ajoneuvojonon
- sen, ettei ensimmäiseen alukseen välttämättä mahdu
- mahdollisuuden ottaa seuraava vuoro
- seuraavan aikataulusidonnaisen yhteyden tärkeyden

Jatkuvana tai tarvittaessa liikennöivälle lautalle ajettaessa lisätään nyt
aina viiden minuutin yleinen varoaika ajoajan päälle. Tämä ei vielä kuvaa
lossin todellista odotus- tai matka-aikaa. Malliin pitää myöhemmin lisätä
reittikohtainen realistinen kutsu- ja odotusviive, koska alus voi olla
vastarannalla tai vasta reagoimassa kutsuun. Viive pidetään erillään
aikataulun varsinaisista tauoista ja käyttäjälle varattavasta varmuusajasta.

Lyhyen lossin kohdalla voidaan siten tarjota useita lähtövaihtoehtoja tai
lisätä aikaa yhden tai useamman vuoron menettämiselle. Tätä varmuuslogiikkaa ei
pidä soveltaa samalla tavalla harvoin kulkevaan varattuun yhteysalukseen, jonka
käyttäjä on nimenomaan valinnut matkansa kiintopisteeksi.

## Käyttäjän riskiprofiili

Käyttäjä voi valita, kuinka paljon varmuutta hän haluaa. Profiili vaikuttaa
erityisesti lyhyisiin losseihin ja varattua yhteyttä edeltäviin vaihtoihin.

### Tiukka

- lyhin mahdollinen kokonaismatka-aika
- pienet vaihtomarginaalit
- olettaa pääsyn ensimmäiseen tarjolla olevaan lyhyeen lossiyhteyteen
- sopii käyttäjälle, joka hyväksyy jatkoyhteyden menettämisen riskin

### Tavallinen

- lisää tavanomaisen odotus- ja vaihtovaran
- huomioi tunnetut ruuhkautuvat yhteydet
- sallii yhden tiheän lossivuoron menettämisen, jos seuraava vuoro tulee pian
- suositeltava oletus useimmille käyttäjille

### Varma

- pyrkii suojaamaan harvoin kulkevan tai varatun jatkoyhteyden
- sallii yhden tai useamman lyhyen lossivuoron menettämisen
- käyttää suurempaa puskuria päivän viimeisten yhteyksien edellä
- voi ehdottaa selvästi aikaisempaa lähtöä, vaikka perilläoloaika ei muuttuisi

Marginaalit eivät voi olla kaikkialla samoja. Niihin vaikuttavat ainakin:

- matkustetaanko autolla vai ilman autoa
- yhteyden vuoroväli ja kapasiteetti
- viikonpäivä, kellonaika ja sesonki
- tunnetut pullonkaulat
- seuraavan yhteyden vuoroväli
- pitääkö seuraava osuus tilata tai varata
- onko kyseessä päivän viimeinen toimiva matkaketju

## Kulkutavat ja ajoneuvokelpoisuus

Jalankulkija, pyöräilijä, moottoripyöräilijä ja autoilija eivät muodosta yhtä
yleistä ajoneuvoluokkaa. Jokaisella lautta- tai yhteysalusosuudella pitää olla
erikseen tieto siitä, mitkä kulkutavat hyväksytään ja millä ehdoilla.

Vähimmäisluokitus on:

- jalankulkija
- polkupyörä
- moottoripyörä
- henkilöauto
- ajoneuvoyhdistelmä
- raskas ajoneuvo

Useimpiin saaristolauttoihin ja yhteysaluksiin voi ottaa polkupyörän, mutta sitä
ei pidä päätellä pelkästään siitä, että matkustajat otetaan kyytiin. Mahdollinen
maksu, varausvelvollisuus, kapasiteettirajoitus tai pyörän kuljetustapa
tallennetaan lähteen perusteella.

Moottoripyörä käsitellään autosta erillään. Esimerkiksi Teersalo–Hakkenpää-
yhteyttä voidaan käyttää moottoripyörällä mutta ei autolla. Reititin saa siis
tarjota sen moottoripyöräilijälle, pyöräilijälle tai jalankulkijalle, mutta sen
on suljettava yhteys pois henkilöautolla tehtävästä hausta.

Ajoneuvokelpoisuus kuuluu yksittäiselle reittiosuudelle tai vuorolle. Saman
reitin eri alus, kausi tai poikkeusvuoro voi muuttaa sallittuja ajoneuvoja.
Puuttuva tieto tarkoittaa tarkistamatonta ominaisuutta, ei automaattisesti
sallittua tai kiellettyä kulkutapaa.

## Pyöräilyprofiili

Pyöräilijät muodostavat tärkeän ja sisäisesti hyvin erilaisen käyttäjäryhmän.
Pelkkä vakionopeudella laskettu lyhin tie ei tuota kaikille käyttökelpoista
reittiä. Käyttäjän profiiliin tarvitaan ainakin:

- oma arvio matkanopeudesta tasaisella tiellä
- haluttu varmuusmarginaali lautoille ehtimiseen
- suositaanko lyhintä, nopeinta, rauhallisinta vai maisemallisinta reittiä
- vältetäänkö vilkasliikenteisiä teitä
- hyväksytäänkö soratiet ja muut päällystämättömät osuudet
- huomioidaanko mäkisyys voimakkaasti vai vähän
- hyväksytäänkö pyörän taluttaminen lyhyellä osuudella
- sähköpyörä ja käytettävissä oleva toimintamatka
- matkatavaroiden vaikutus nopeuteen

Reititin laskee tieosuuden ajan käyttäjän nopeusprofiilista, reitin pinnasta,
mäkisyydestä ja mahdollisista turvallisuusrangaistuksista. Ensimmäinen versio
voi käyttää käyttäjän ilmoittamaa keskinopeutta ja yksinkertaista
pintaluokitusta. Myöhemmin nopeusarviota voidaan tarkentaa korkeuserojen ja
tieympäristön perusteella.

Pyörä kulkee matkaketjussa käyttäjän mukana. Lauttaosuus ei katkaise
pyöräreittiä, jos kyseinen yhteys sallii polkupyörän. Hakutuloksessa kerrotaan:

- sallitaanko pyörä
- pitääkö pyörä tai matkustaja varata
- peritäänkö pyörästä maksu
- onko pyöräpaikkojen määrä rajallinen
- pitääkö pyörä taluttaa, lastata itse tai jättää tiettyyn paikkaan

Pyöräilijän vaihtomarginaalissa huomioidaan myös laiturille saapuminen,
mahdollinen lipunosto ja lastaus. Lyhyen lossin menettäminen on usein pieni
haitta, mutta harvoin kulkevalle yhteysalukselle pyöräilijänkin pitää ehtiä
ajoissa juuri valitulle vuorolle.

## Rakenteisen datan luonnos

Tietomalli voidaan rakentaa GTFS:n perusajatusten mukaisesti, mutta saariston
tilausvuorot, ehdolliset laiturikäynnit, jatkuva lossiliikenne ja epävarmat ajat
tarvitsevat omia lisäkenttiä.

### Reitin voimassaolokausi

```json
{
  "route": "korporutt",
  "validFrom": "2026-09-01",
  "validTo": "2027-06-01",
  "weekdays": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
  "excludedDates": [],
  "addedDates": [],
  "source": "saaristolinjat-aikataulu-2026-09-01.pdf"
}
```

### Aikataulutettu pysähdys

```json
{
  "stop": "Äpplö",
  "arrival": "14:20",
  "departure": "14:25",
  "call": "on_request",
  "booking": {
    "required": true,
    "deadline": "previous_day 15:00",
    "phone": "+358..."
  }
}
```

`call` voi olla esimerkiksi:

- `scheduled`: normaali aikataulutettu käynti
- `on_request`: laituriin poiketaan matkustajan tilauksesta
- `conditional`: käynti riippuu aikataulussa kuvatusta ehdosta
- `pass_through`: paikka on reitillä, mutta siitä ei oteta matkustajia

### Lyhyt lossiyhteys

```json
{
  "route": "pargasnagu",
  "serviceMode": "continuous_shuttle",
  "publishedHeadwayMinutes": 15,
  "crossingMinutes": 8,
  "capacityGuaranteed": false,
  "vehicleQueuePossible": true,
  "recommendedBufferMinutes": {
    "tight": 0,
    "normal": 20,
    "safe": 45
  }
}
```

Todelliset marginaalit ylläpidetään reitti-, suunta-, ajankohta- ja
ajoneuvokohtaisesti. Esimerkkilukuja ei pidä käyttää tuotannossa ilman
perusteltua lähdettä tai käytännön kokemukseen perustuvaa ylläpitopäätöstä.

### Varaus, maksu ja ajoneuvot

Vuoroon tai osaväliin voidaan liittää:

```json
{
  "reservation": {
    "requiredForVehicle": true,
    "url": "https://example.invalid/booking",
    "deadline": "previous_day 15:00"
  },
  "fare": {
    "required": true,
    "detailsUrl": "https://example.invalid/prices"
  },
  "vehicles": ["passenger", "bicycle", "car"]
}
```

Ajoneuvot voidaan kuvata tarkemmin sallittujen ja ehdollisten kulkutapojen
avulla:

```json
{
  "mobility": {
    "foot": { "allowed": true },
    "bicycle": { "allowed": true, "reservationRequired": false },
    "motorcycle": { "allowed": true },
    "car": { "allowed": false }
  }
}
```

## Maantie- ja kävelyosuudet

Yhdistelmäreititys tarvitsee lauttayhteyksien lisäksi laiturien väliset
maantie- ja kävelyosuudet. Ne voidaan laskea OpenStreetMap-pohjaisella
reitityksellä tai tallentaa yleisimmille vaihtoväleille valmiiksi.

Jokaisesta osuudesta tarvitaan vähintään:

- lähtö- ja määräpaikka
- kulkutapa
- matka ja arvioitu ajoaika
- mahdollinen lossiyhteys tieosuuden sisällä
- pysäköintiä, lähtöselvitystä tai jonotusta varten tarvittava lisäaika

Autolla tai moottoripyörällä tehtävä haku saa käyttää vain yhteyksiä, jotka
kuljettavat kyseisen ajoneuvon. Jalan ja pyörällä tehtävät haut voivat tuottaa
keskenään ja moottoriajoneuvoihin verrattuna erilaiset matkaketjut. Pyöräreitin
tieosuudet lasketaan pyöräilyyn soveltuvasta verkosta eikä auton ajo-ohjeista.

## Hakutulos

Tuloksessa näytetään useita käyttökelpoisia vaihtoehtoja eikä vain yhtä
matemaattisesti nopeinta reittiä.

```text
Reittiehdotus 1 – suositeltu

Lähtö klo 10.23
Kustavi – Kivimaa: auto 3 km, noin 3 min
Kivimaa – Vartsala: lautta 10.40–10.45
Vartsala – Vuosnainen: auto 6 km, noin 6 min
Vuosnainen – Åva: lautta 11.30–12.35
  Maksullinen. Autopaikka varattava. [Varauslinkki]
Åva – Torsholma: auto ja lossiyhteys 12.40–13.25

Perillä noin klo 17.10
Kokonaiskesto 6 h 47 min
Kaksi ennakkovarausta ja yksi tilattava laiturikäynti
```

Vaihtoehdot voidaan nimetä esimerkiksi:

- nopein mahdollinen
- suositeltu
- varma
- vähiten vaihtoja
- vähiten ajamista
- vähiten varauksia

### Viimeinen toimiva yhteys ja hätävaravaihtoehto

Matkaketju suunnitellaan normaalisti viimeisen aikataulun ja vaadittujen
lastausmääräaikojen mukaan varmasti toimivan syöttöyhteyden varaan. Sen rinnalla
näytetään saman lyhyen lauttayhteyden edellinen ja seuraava vuoro, jotta käyttäjä
näkee pelivaran ja sen, mitä yhden vuoron menettäminen tarkoittaa.

Seuraavaa vuoroa ei kuitenkaan piiloteta vain siksi, ettei se enää täytä
normaalia vaihtomarginaalia. Jos sillä voi fyysisesti ehtiä jatkoyhteydelle vain
operaattorin joustolla, se näytetään erillisenä hätävaravaihtoehtona:

- yhteys ei ole aikataulun mukaan varma eikä sitä käytetä ensisijaisen matkan
  suunnitteluun
- jäljelle jäävä aika ja rikottu lastaus- tai vaihtomarginaali näytetään
  minuuteissa
- käyttäjälle kerrotaan, että hänen pitää soittaa jatkavalle alukselle heti
- puhelinnumero näytetään suoraan vaihtoehdon yhteydessä
- operaattorin odottamista tai kyytiin pääsyä ei luvata

Esimerkiksi Galtbyn klo 9.30 lähdölle ajoneuvon pitää olla lastausvalmiina klo
9.15. Pärnäinen–Retainen klo 8.50–8.55 on viimeinen normaalisti toimiva yhteys.
Seuraava klo 9.10–9.15 johtaa Galtbyhyn noin klo 9.25: määräaika on jo mennyt,
mutta matkustaja voi hätätilanteessa yrittää yhteyttä soittamalla alukselle.
Molemmat tiedot ovat matkustajalle hyödyllisiä, mutta ne esitetään eri
luotettavuusluokissa.

Lyhyen lossiyhteyden jälkeen voidaan näyttää myös varasuunnitelma:

> Jos et mahdu ensimmäiseen lossivuoroon, seuraava arvioitu ylitys on noin klo
> 11.00. Ehdit sillä edelleen jatkoyhteydelle. Jos menetät myös sen, seuraava
> toimiva matkaketju lähtee klo 12.15.

Tilaus- ja varausehdot näytetään sekä niiden osuudella että koko matkan
yhteenvedossa. Käyttäjän ei pidä joutua etsimään toimintaohjetta erillisestä
PDF:stä.

## Aikojen tarkkuus

Tietomallissa erotetaan:

- tarkka julkaistu aika
- arvioitu aika
- julkaistu aikaikkuna
- edellisen pysähdyksen jälkeen tapahtuva käynti ilman ilmoitettua aikaa
- nimettyä yhteyttä odottava jatkoyhteys

Arvioituja aikoja voidaan käyttää reittiehdotuksen muodostamiseen, kun niiden
luonne näytetään käyttäjälle. Kahden epävarman ajan välille ei muodosteta
tiukkaa vaihtoa ilman virallista jatkoyhteysmerkintää tai riittävää
vaihtomarginaalia.

Myöhemmin laiturikäynnille voidaan laskea historiadatasta tyypillinen aika ja
vaihteluväli. Tämä tallennetaan erillisenä `historicalEstimate`-tietona eikä
julkaistun aikatauluajan tilalle. Arvion mukana säilytetään vähintään otoskoko,
havaintojakso, malliversio ja laskenta-aika. Käyttöliittymä kertoo aina, että
arvio perustuu vain historiadataan eikä ole operaattorin julkaisema aika tai
taattu yhteys. Reititin käyttää vaihteluväliä ja käyttäjän riskiprofiilia
vaihtomarginaalin valintaan.

## Tietojen tuottaminen ja tarkistus

1. PDF tai HTML-aikataulu muunnetaan rakenteiseksi luonnokseksi.
2. Kaikki symbolit, alaviitteet ja poikkeusehdot kohdistetaan vuoroon,
   pysähdykseen tai ajoneuvotyyppiin.
3. Rakenteisesta datasta generoidaan ihmisen tarkistettava näkymä.
4. Näkymää verrataan alkuperäiseen aikatauluun.
5. Automaattiset tarkistukset varmistavat ainakin, että:
   - voimassaolojaksot eivät mene väärin päällekkäin
   - pyhäpoikkeukset korvaavat oikean normaaliliikenteen
   - ajat ja pysähdysjärjestys ovat mahdollisia
   - kaikki viitatut laiturit, reitit ja alukset tunnetaan
   - tilaus- ja varausehdoilla on toimintaohje
   - jokaisella tiedolla on lähde ja tarkistusajankohta
6. Lähteiden muutostarkistin ilmoittaa myöhemmin päivitettävät aikataulut.

OCR tai kielimalli voi nopeuttaa luonnoksen muodostamista, mutta sitä ei käytetä
ainoana totuuslähteenä. Ensimmäinen tuonti ja jokainen merkittävä lähdemuutos
hyväksytään vertaamalla rakenteinen tulos alkuperäiseen aikatauluun.

## Toteutusvaiheet

### 1. Rakenteinen reittikalenteri

- määritellään JSON-skeema
- muunnetaan yksi monipuolinen pilottireitti, ensisijaisesti Korppoon
  reittialue
- toteutetaan päivämääräkohtainen vuorohaku
- näytetään tilaukset, varaukset, maksut ja poikkeukset
- generoidaan tarkistusnäkymä alkuperäisen aikataulun rinnalle

### 2. Yhden operaattorin reititys

- haetaan yhteyksiä saman reittialueen laiturien välillä
- käsitellään ehdolliset laiturikäynnit täysivaltaisina vaihtoehtoina
- lisätään vaihtoehtoiset lähtölaiturit
- suodatetaan yhteydet erikseen jalankulkijalle, pyörälle, moottoripyörälle ja
  autolle
- muodostetaan nopeat, suositellut ja varmat vaihtoehdot

### 3. Yhdistelmäreititys

- lisätään erilliset maantie-, moottoripyörä-, pyöräily- ja kävelyosuudet
- yhdistetään eri operaattorien vuorot
- mallinnetaan lyhyiden lossien vuoroväli-, jono- ja kapasiteettiriski
- suojataan harvoin kulkevat varatut yhteydet käyttäjän riskiprofiilin mukaan
- huomioidaan pyöräilijän nopeus, reittimieltymykset ja pyörän kuljetusehdot
- tuotetaan vaihtoehtoiset matkaketjut ja varasuunnitelmat

Ensimmäinen laaja testitapaus on Kustavi–Sottunga autolla. Se pakottaa
käsittelemään maantieosuudet, lyhyet lossit, maksulliset ja varattavat lautat,
eri operaattorit, poikkeuspäivät sekä käyttäjäkohtaisen varmuusvälin.

Sen rinnalle tarvitaan pyöräilyn testitapaus, jossa vaihtoehtoiset nopeudet ja
tieprofiilit tuottavat aidosti erilaisia yhteyksiä. Teersalo–Hakkenpää toimii
ajoneuvoluokituksen regressiotestinä: yhteys saa löytyä moottoripyörälle mutta
ei henkilöautolle.

## Prototyypistä tuotantoon

Koko reititysjärjestelmää ei kirjoiteta tuotantovaiheessa uudelleen puhtaalta
pöydältä. Nykyisestä toteutuksesta säilytetään ja sitä kehitetään edelleen
ainakin seuraavilta osin:

- rakenteinen aikataulu- ja AIS-aineisto
- reititysgraafi ja reititysalgoritmit
- Valhalla-integraatio, geokoodaus ja välimuisti
- FastAPI-palvelu ja sen JSON-rajapinta
- reittikohtaiset erityissäännöt sekä regressiotestit

Näihin on kertynyt suuri määrä vaikeasti uudelleen löydettävää saaristoliikenteen
toimialatietoa. Kokonaan uusi toteutus lisäisi tarpeettomasti riskiä siitä, että
jo ratkaistut virheet ja erikoistapaukset palaisivat.

Kokeellinen `service/route-preview.html` on sen sijaan toiminnallinen
käyttöliittymäprototyyppi ja myöhemmän tuotantokäyttöliittymän referenssi. Sen
tehtävänä on löytää oikea tapa näyttää matkaketjut, vaihtoehtoiset lauttavuorot,
lastausvalmius, vaihtomarginaalit ja käyttäjän lukitsemat valinnat. Sitä ei ole
tarkoitus kasvattaa sellaisenaan lopulliseksi käyttöliittymäksi. Kun
toimintamalli on riittävän vakaa, sama näkymä toteutetaan komponenttipohjaisesti
varsinaiseen Saaristolautat-sovellukseen.

Ennen tuotantokäyttöliittymän toteuttamista:

1. viimeistellään prototyypissä näytettävät reittivaihtoehdot ja
   lauttavuorojen valintatapa
2. tallennetaan noin 15–30 edustavaa esimerkkimatkaa regressiotesteiksi
3. vakautetaan käyttöliittymän tarvitsema JSON-rajapinta
4. varmistetaan, että rajapinta kertoo suoraan ainakin klikattavat vuorot,
   automaattiset ja lukitut valinnat, lastausvalmiuden, ylimääräisen ajan,
   operaattorin, maksullisuuden ja matkustajaohjeet
5. rakennetaan tuotantonäkymä komponentteina nykyiseen sovellukseen käyttäen
   prototyyppiä toiminnallisena määrittelynä

Taustajärjestelmää tuotantokuntoon vietäessä tehdään hallittuja refaktorointeja
uudelleenkirjoituksen sijasta. Esimerkiksi palvelun käyttämä varsinainen
ohjelmakoodi siirretään vähitellen `scripts`-hakemistosta asennettavaksi
Python-paketiksi. Rajapinnan käyttäytyminen ja regressioreittien tulokset
pidetään refaktorointien aikana ennallaan.

## Onnistumisen rajaus

Palvelu lupaa:

> Näin matka on julkaistujen aikataulujen perusteella mahdollinen. Tässä ovat
> kaikki tiedossa olevat varaukset, tilaukset, maksut, aikamarginaalit ja muut
> ehdot, joista matkustajan pitää huolehtia.

Palvelu ei lupaa vapaata autopaikkaa, liikenteen toteutumista poikkeusoloissa
tai sitä, että ruuhkautuvaan lossiin mahtuu ensimmäisellä yrityksellä. Näitä ei
piiloteta yleiseksi epävarmuudeksi, vaan ne muutetaan käyttäjälle näkyviksi
valinnoiksi, varmuusväleiksi ja vaihtoehtoisiksi matkaketjuiksi.
