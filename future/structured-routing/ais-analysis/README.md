# AIS-aineiston analyysi

`prepare_ais.py` muodostaa lauttaliven raakakannasta rajatun ja tiivistetyn
SQLite-tietokannan. Lähdekantaan ei tehdä muutoksia.

Ohjelma:

- säilyttää alkuperäisen `rowid`-keräysjärjestyksen
- päättelee cronjobin keräyskierrokset siitä, että sama MMSI esiintyy yhdessä
  kierroksessa enintään kerran
- arvioi keräysajan kierroksen tuoreimpien AIS-aikaleimojen perusteella
- rajaa havainnot `analysis-area.geojson`-polygonilla
- yhdistää peräkkäiset täysin samat AIS-havainnot yhdeksi havainnoksi mutta
  säilyttää niiden keräyskierrosten määrän
- raportoi MMSI-kohtaisen ajallisen ja maantieteellisen kattavuuden

Esimerkki:

```sh
python3 future/structured-routing/ais-analysis/prepare_ais.py \
  /polku/lauttalive_20251023_20261011.db.gz \
  /tmp/ais-2025-2026.sqlite \
  --summary-csv /tmp/ais-vessels.csv \
  --summary-json /tmp/ais-summary.json
```

GeoJSON-rajaus on digitoitu likimäärin karttakuvasta. Sen pisteitä voidaan
tarkentaa muuttamatta analyysikoodia.

Laiturikäynnit ja kuukausittaiset reittikandidaatit muodostetaan valmistellusta
kannasta näin:

```sh
python3 future/structured-routing/ais-analysis/detect_route_candidates.py \
  /tmp/ais-2025-2026.sqlite \
  saaristo.json \
  data.json \
  /tmp/ais-route-candidates-60d \
  --vessel-summary /tmp/ais-vessels.csv \
  --minimum-active-days 60
```

Tulokset ovat `pier-calls.csv`, `route-candidates.csv`,
`unknown-stop-cells.csv` ja `summary.json`. Reittiehdotus annetaan
MMSI–kuukausi-tasolla, jotta pysyvät ja tilapäiset alusvaihdokset eivät sido
MMSI-tunnusta yhteen reittiin.

Laiturikohtaamiset luokitellaan havaintoperusteen mukaan:

- `slow_dwell`: vähintään 45 sekunnin viipymä ja SOG enintään 1,5 solmua
- `area_dwell`: vähintään kaksi havaintoa laiturialueella, mutta ei hidasta näytettä
- `close_proximity`: enintään 50 metriä laiturista ja SOG enintään 5 solmua
- `turnaround`: kolmen sijaintipisteen liikesuunta muuttuu vähintään 120 astetta
- `slow_sample`: yksittäinen hidas piste enintään 150 metriä laiturista
- `unconfirmed`: kohtaaminen ei täytä hyväksymiskriteerejä

Kääntymisessä käytetään koordinaateista laskettua liikesuuntaa, ei AIS-headingia.
Sekä saapuvan että lähtevän liikejakson on oltava vähintään 75 metriä pitkä,
jotta GPS-heilahtelu ei näytä käännökseltä.

Viikkokohtaiset reittiehdotukset, yhtenäiset liikennöintijaksot ja
katselmointi-GeoJSON muodostetaan näin:

```sh
python3 future/structured-routing/ais-analysis/build_route_review.py \
  /tmp/ais-route-candidates-60d/pier-calls.csv \
  /tmp/ais-route-candidates-60d/unknown-stop-cells.csv \
  /tmp/ais-2025-2026-vessels.csv \
  saaristo.json \
  data.json \
  /tmp/ais-route-review-60d \
  --minimum-active-days 60 \
  --livedata ../saaristolive/data/livedata.json \
  --route-ids future/structured-routing/ais-analysis/connection-routes.json \
  --vessel-names future/structured-routing/ais-analysis/vessel-names.json
```

Peräkkäiset saman laiturin käynnit yhdistetään, jos niiden väli on enintään 30
minuuttia. Reittipisteytys käyttää sekä havaittujen laiturien osuutta että
laiturien välisiä siirtymiä. Tuntemattomat 0,002 asteen pysähdyssolut
yhdistetään 300 metrin säteellä paikkaklustereiksi.
Alusten nimet liitetään MMSI-tunnuksiin `livedata.json`-aineistosta silloin,
kun nimi on siellä saatavilla.

`connection-routes.json` rajaa tämän analyysin monilaiturisiin
yhteysalusreitteihin. Maantielautat, lossit, kaksilaituriset sukkulareitit ja
matkailuliikenteen reitit eivät tällöin vaikuta alusluokitukseen tai
liikennöintijaksoihin. `vessel-names.json` täydentää historiasta tunnistettujen
MMSI-tunnusten nimiä silloin, kun alus ei juuri nyt esiinny livedatassa.

Tuntemattomat pysähdykset voidaan rajata OpenStreetMapin rantaviivan avulla:

```sh
curl --fail --silent --show-error \
  --data-urlencode 'data=[out:json][timeout:180];way["natural"="coastline"](59.55,19.75,60.85,23.30);out geom;' \
  -o /tmp/ais-coastline-overpass.json \
  https://overpass.kumi.systems/api/interpreter

python3 future/structured-routing/ais-analysis/prepare_coastline.py \
  /tmp/ais-coastline-overpass.json \
  /tmp/ais-route-review-60d/review.geojson \
  /tmp/ais-route-review-60d/coastline.json \
  /tmp/ais-route-review-60d/review-coastal.geojson \
  --max-offshore-metres 100
```

Ohjelma laskee klusterin lyhimmän etäisyyden rantaviivaan, poistaa yli 100
metrin päässä rannasta olevat tuntemattomat pysähdykset ja tuottaa karttaa
varten tiivistetyn, upotettavan rantaviiva-aineiston. Tunnettuja laitureita tai
reittiviivoja ei poisteta.

## Matkat ja käyntiketjut

Laiturien väliset matkat rakennetaan luotettavista viikkokohtaisista
reittipäätelmistä. Ensin toistuvien hitaiden käyntien sijainneista päätellään
laiturikohtainen AIS-kiinnittymiskeskus ja sen hajontaan perustuva ajoitussäde:

```sh
python3 future/structured-routing/ais-analysis/calibrate_pier_timing.py \
  /tmp/ais-2025-2026.sqlite \
  /tmp/ais-route-candidates-60d/pier-calls.csv \
  /tmp/ais-connection-review-60d/weekly-route-candidates.csv \
  data.json \
  saaristo.json \
  /tmp/ais-pier-calibration \
  --overrides future/structured-routing/ais-analysis/pier-timing-overrides.json
```

Kalibrointi käyttää vain luotettavan yhteysalusviikon `slow_dwell`-käyntejä.
Yhdestä käynnistä otetaan hitaiden näytteiden mediaanisijainti, minkä jälkeen
käyntipisteet klusteroidaan 50 metrin etäisyydellä. Monihuippuiset, hajanaiset,
vähäiset tai yli 150 metriä sovellusdatan laiturista poikkeavat tulokset
jätetään automaattisen kalibroinnin ulkopuolelle.
`pier-timing-overrides.json` voi hyväksyä käyttäjän vahvistaman monilaiturisen
kohteen erilliset klusterit. Kökarissa käytetään kahta noin 62 metrin päässä
toisistaan olevaa 20 metrin ydintä, jotta lähestymismutkan hetkellinen
hidastuminen ei sekoitu varsinaiseen laituripysähdykseen. Långnäsissä käytetään
kahta vahvaa 25 metrin yhteysalusydintä. Sovelluksen nykyinen Långnäs-piste on
niistä erillään ja lähempänä Ruotsin-laivojen kiinnittymispaikkaa.
Gloskärissä käytetään käyttäjän kartta- ja ilmakuvatulkinnalla vahvistettua
pohjoista 30 metrin ydintä; toinen vedessä oleva hitaiden näytteiden ryhmä
tulkitaan lähestymisen tai odottelun hidastumiseksi. Käynti voi olla lyhyt,
keula rantakalliota vasten tehtävä matkustajakäynti, joten usean minuutin
pysähdystä ei vaadita; läheisyys, hidastuminen ja paluusuunnan muutos tukevat
tunnistusta yhdessä.
Kopparholmissa käytetään 81 käynnin muodostamaa 25 metrin AIS-ydintä noin 244
metriä nykyisestä sovelluspisteestä itään. Varsinainen rantautumispaikka on
AIS-antennin ytimen eteläpuolella aluksen keulan kohdalla.
Penossa käytetään 115 käynnin muodostamaa pohjoista 35 metrin ydintä noin 183
metriä nykyisestä sovelluspisteestä. Kolme pääryhmästä irrallista tapahtumaa
jätetään ajoituksen ulkopuolelle.
Lempmossa käytetään 83 käynnin muodostamaa läntistä 25 metrin ydintä noin 209
metriä nykyisestä sovelluspisteestä. Viisi hajapistettä jätetään ajoituksen
ulkopuolelle.

Matka-aika ei käytä 250 metrin laiturintunnistusalueen reunoja. Ensisijainen
lähtöhetki on viimeinen hidas havainto lähtölaiturin kalibroidussa ytimessä ja
saapumishetki ensimmäinen hidas havainto määrälaiturin ytimessä. Jos hidasta
ydinhavaintoa ei ole, käytetään 50 metrin kehän ylitystä tai lopulta lähintä
havaintoa ja merkitään ajoitusmenetelmä tulokseen.

```sh
python3 future/structured-routing/ais-analysis/build_voyages.py \
  /tmp/ais-2025-2026.sqlite \
  /tmp/ais-route-candidates-60d/pier-calls.csv \
  /tmp/ais-connection-review-60d/weekly-route-candidates.csv \
  data.json \
  saaristo.json \
  /tmp/ais-connection-voyages.sqlite \
  --pier-calibration /tmp/ais-pier-calibration/pier-calibration.json

python3 future/structured-routing/ais-analysis/build_service_journeys.py \
  /tmp/ais-connection-voyages.sqlite \
  data.json \
  /tmp/ais-service-journeys \
  --route-overrides future/structured-routing/ais-analysis/journey-analysis-overrides.json

python3 future/structured-routing/ais-analysis/build_arrival_prediction_model.py \
  /tmp/ais-service-journeys/journeys.csv \
  /tmp/ais-service-journeys/journey-stops.csv \
  /tmp/ais-arrival-prediction-model \
  --compact-output \
  future/structured-routing/ais-arrival-estimates.json
```

Jälkimmäinen ohjelma muodostaa päälaiturista alkavat laiturikäyntiketjut,
toistuvien ketjujen yhteenvedot sekä kullekin ketjun alkuosalle saapumisajan
10., 50. ja 90. persentiilin. Näin saman kohdelaiturin ajat pysyvät erillään
sen mukaan, missä välilaitureissa alus kävi ennen sitä.
`leg-windows.csv` sisältää lisäksi suunnittaiset laiturivälien 10., 50. ja 90.
persentiilit; niihin hyväksytään vain matkat, joiden molemmissa päissä nähtiin
hidas ydinhavainto.

Käyntiketju ja kartan ajoura katkaistaan, jos peräkkäisten vastaanotettujen
AIS-havaintojen väli ylittää 90 sekuntia tai pisteparin laskennallinen nopeus
ylittää 20 solmua. Katkon yli ei piirretä suoraa viivaa eikä katkon sisältävää
laituriväliä käytetä luotettavaan saapumisaika-arvioon, koska mahdollisia
välilaiturikäyntejä ei silloin tunneta. Karttaa varten uraa yksinkertaistetaan
10 metrin geometrisella toleranssilla, joka säilyttää mutkat; tasavälistä
pisteiden harvennusta ei käytetä.

Ajanjakso hylätään aika-arvioista myös silloin, kun alus on laituriväliksi
tulkitun jakson sisällä yhtäjaksoisesti enintään 1,5 solmun nopeudessa yli
kolme minuuttia. Tämä poistaa esimerkiksi yön yli jatkuneen AIS-seurannan
muodostamat näennäiset suorat laiturivälit.

`journey-analysis-overrides.json` täydentää vain analyysin päälaitureita eikä
muuta sovellusdataa. Utön reitillä sekä Pärnäs että Utö käsitellään
päälaitureina, joten molempiin suuntiin lähtevät vuorot säilyvät aineistossa.

Ensimmäinen saapumisennustemalli ryhmittelee korkean luottamuksen matkat reitin,
päälaiturin, viikonpäivän ja 15 minuutin paikallisen lähtöaikakorin mukaan.
Se säilytetään tarkkojen historiallisten lähtöjen auditointia varten, mutta
sitä ei pidä käyttää nykyisen aikataulun ensisijaisena vastaavuusehtona:
aikataulut ja lähtöajat vaihtuvat kausittain.

Aikataulusta riippumaton malli muodostetaan näin:

```sh
python3 future/structured-routing/ais-analysis/build_flexible_arrival_model.py \
  /tmp/ais-service-journeys/journeys.csv \
  /tmp/ais-service-journeys/journey-stops.csv \
  /tmp/ais-arrival-prediction-flexible \
  --compact-output \
  future/structured-routing/ais-arrival-estimates-flexible.json
```

Tämän mallin ensisijainen ajoitusyksikkö on suunnattu laituriväli. Kaikki
luotettavat havainnot yhdistetään viikonpäivästä ja lähtöajasta riippumatta.
`leg-windows-flexible.csv` sisältää laiturivälien p10-, mediaani- ja p90-ajat.
Jos täsmälleen sama välilaituriketju on havaittu, käytetään ensisijaisesti sen
suoraan mitattua kokonaisaikaa (`path-windows-flexible.csv`). Uusi tai muuttunut
aikatauluketju voidaan arvioida summaamalla sen peräkkäisten laiturivälien ajat.
Pitkät laituriodotukset eivät sisälly kumpaankaan aikaan.

`destination-windows-flexible.csv` antaa lisäksi päälaiturin ja kohdelaiturin
välille kaikista vähintään viisi kertaa havaituista ketjuista lasketun yleisen
vaihteluvälin. Se toimii viimeisenä varavaihtoehtona silloin, kun tulevan vuoron
välilaitureita ei tunneta varmasti. Tyypillinen aika perustuu toistuviin
ketjuihin, mutta mahdollisen ajan ulkorajat käyttävät kaikkia korkean
luottamuksen historiallisia ketjuja. Näin harvinainen mutta mahdollinen pitkä
kierros ei katoa viiden havainnon otosrajan takia.

Viikonpäivää, vuodenaikaa ja kellonaikaa käytetään vain arvioimaan
välilaituriketjujen todennäköisyyttä. Luokat ovat ma, ti–to, pe, la ja su;
vuodenajat talvi, kevät–syksy ja kesä; päivän osat aamu, päivä, iltapäivä ja
ilta–yö. `service-pattern-contexts.csv` kuvaa näissä luokissa toistuneet
käyntiketjut. `contextual-leg-windows.csv` säilytetään diagnostista vertailua
varten, mutta kalenteriluokka ei rajaa laiturivälin ensisijaista ajoaikaa.
`contextual-destination-windows.csv` sisältää samoissa väljissä luokissa
päälaituri–kohdelaituri-ajoajat ja käyntitodennäköisyyden. Sitä käytetään
välilaitureiltaan tuntemattoman vuoron ensimmäisenä varatasona; kaikkien
lähtöjen yleinen haarukka on viimeinen varataso.

Vähintään kolme havaintoa säilytetään auditointituloksissa. Kompaktiin
kokeelliseen malliin hyväksytään vähintään viisi havaintoa. Täsmällistä
viikonpäivän ja kellonajan vastaavuutta ei vaadita.

Mallin ajallinen takautuva testi tehdään viimeisille 90 päivälle näin:

```sh
python3 future/structured-routing/ais-analysis/evaluate_flexible_arrival_model.py \
  /tmp/ais-service-journeys/journeys.csv \
  /tmp/ais-service-journeys/journey-stops.csv \
  /tmp/ais-arrival-prediction-backtest \
  --test-days 90
```

Testi opettaa mallin vain tätä edeltävästä aineistosta. Se raportoi erikseen
saman ketjun, laiturivälien summan, väljän kalenterikontekstin ja kaikkien
historiallisten ketjujen varahaarukan. Näin tulos ei mittaa saman havainnon
muistamista vaan myöhemmän ajanjakson ennustamista.

## Lineaaristen meno–paluu-reittien suunta

Paraisten reitin kaltaisella lähes lineaarisella tilausreitillä myöhäinen käynti
lähellä Granvikia ei ole vaihtoehtoinen menoreitti. Se on paluumatkan
noutokäynti: menomatkalla jätetään matkustajia ja paluumatkalla poimitaan heitä
kyytiin. Siksi meno- ja paluukäyntejä ei saa yhdistää samaan
päälaituri–kohdelaituri-haarukkaan.

Suuntaerottelu muodostetaan näin:

```sh
python3 future/structured-routing/ais-analysis/build_directional_call_model.py \
  /tmp/ais-service-journeys/journeys.csv \
  /tmp/ais-service-journeys/journey-stops.csv \
  future/structured-routing/ais-analysis/route-direction-overrides.json \
  /tmp/ais-directional-calls
```

`route-direction-overrides.json` sisältää reitin tunnetun ulospäin kulkevan
laiturijärjestyksen. Matkan kaukaisin saavutettu laituri tulkitaan
kääntöpisteeksi, jota edeltävät käynnit ovat menokäyntejä ja seuraavat
paluukäyntejä. Kääntöpisteen sama käynti palvelee kumpaakin suuntaa.
Tilaamattoman laiturin ohittaminen ei muuta muiden laiturien järjestystä.

Kaikkien reittien laiturikohtainen käyntimäärä analysoidaan erikseen:

```sh
python3 future/structured-routing/ais-analysis/analyze_call_multiplicity.py \
  /tmp/ais-service-journeys/journeys.csv \
  /tmp/ais-service-journeys/journey-stops.csv \
  /tmp/ais-call-multiplicity
```

`pier-call-multiplicity.csv` kertoo jokaiselle laiturille, kuinka monella
kokonaisella matkalla siinä käytiin kerran tai vähintään kahdesti. Lisäksi se
erottaa selvän kääntöpisteen (`A → B → A`) läpikulkevasta käynnistä.
`route-call-shapes.csv` kertoo reittitasolla, palataanko samaan päälaituriin,
toistetaanko välilaitureita ja ajetaanko sama havaittu laituriväli molempiin
suuntiin. Nämä ovat toisistaan riippumattomia ominaisuuksia: samalla reitillä
voi olla rengasosuuksia, edestakaisia haaroja ja päätepisteiden välisiä matkoja.

Neljän ensimmäisen sekamuotoisen reitin käyntiroolit muodostetaan näin:

```sh
python3 future/structured-routing/ais-analysis/build_call_role_model.py \
  /tmp/ais-service-journeys/journeys.csv \
  /tmp/ais-service-journeys/journey-stops.csv \
  future/structured-routing/ais-analysis/route-topology-overrides.json \
  /tmp/ais-call-roles \
  --compact-output \
  future/structured-routing/ais-call-role-model.json
```

`route-topology-overrides.json` määrittää vain analyysissä käytettävät
päätepisteet ja reitin tunnetun yleisrakenteen. Se ei muuta sovellusdataa.
`call-role-events.csv` luokittelee jokaisen käynnin seuraavasti:

- `terminal_to_terminal`: eri tunnettujen päätepisteiden välinen matka
- `turnaround`: täsmällisesti havaittu `A → B → A` -kääntö
- `outbound` ja `inbound`: saman laiturin ensimmäinen ja viimeinen käynti
  samalla suljetulla matkalla
- `single_loop_call`: laituri käytiin kerran suljetulla matkalla
- `journey_endpoint`: matkan päättävä paluu- tai päätepistekäynti

`single_loop_call` on tarkoituksella vain keskitason tulkinta. Yksi havaittu
käynti ei yksin todista rengasreittiä, sillä kyse voi olla myös haarasta tai
siitä, ettei samassa laiturissa ollut kysyntää molempiin suuntiin.
`pier-role-summary.csv` kokoaa roolit laitureittain ja
`journey-shape-summary.csv` matkarakenteet reiteittäin.

Roolitietoinen ajoaikamalli muodostetaan näin:

```sh
python3 future/structured-routing/ais-analysis/build_role_aware_arrival_model.py \
  /tmp/ais-call-roles/call-role-events.csv \
  future/structured-routing/ais-analysis/route-topology-overrides.json \
  /tmp/ais-role-aware-arrivals \
  --compact-output \
  future/structured-routing/ais-role-aware-arrival-estimates.json

python3 future/structured-routing/ais-analysis/evaluate_role_aware_arrival_model.py \
  /tmp/ais-call-roles/call-role-events.csv \
  /tmp/ais-role-aware-backtest \
  --test-days 90
```

`role-aware-path-windows.csv` sisältää vähintään viisi kertaa havaitun
täsmällisen käyntiketjun p10-, mediaani- ja p90-ajoajat. Malli pitää erillään
lähtö- ja päätepisteen, matkarakenteen sekä laiturin käyntiroolin. Väljä
`role-aware-destination-windows.csv` säilytetään auditointia varten, mutta sen
ryhmiä käytetään vain konservatiivisena havaittuna min–max-haarukkana. Niiden
mediaani ei ole riittävän luotettava ennuste, jos tarkka käyntiketju puuttuu.

Ahvenanmaan julkaistu aikataulu on aina AIS-mallia määräävämpi.
Eteläisen linjan poikkeamat tarkistetaan erikseen näin:

```sh
python3 future/structured-routing/ais-analysis/analyze_aland_detours.py \
  /tmp/ais-service-journeys/journeys.csv \
  /tmp/ais-aland-detours \
  --compact-output \
  future/structured-routing/ais-aland-detour-validation.json
```

Mallissa Husön noin 10 minuutin ja Kyrkogårdsön noin 20 minuutin julkaistut
viiveet summataan 30 minuutiksi, jos samalla vuorolla käydään molemmissa.
AIS-vertailu tukee vaikutusten kasautumista, mutta AIS:n puhdas ajoaika ja
aikataulun ilmoittama seuraavien satamien viive eivät ole sama suure.
