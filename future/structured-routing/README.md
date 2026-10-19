# Rakenteellinen aikataulu ja reititys

Tämä hakemisto sisältää tulevaa rakenteellista aikataulua, sen generointia ja
sen avulla tehtävää reititystä koskevan kokeellisen työn. Hakemiston aineisto ei
ole tuotannossa eikä sitä julkaista nykyisen Saaristolautat-datan mukana.

Keskeiset tiedostot:

- `structured-timetables.json`: generoitu rakenteellisen aikataulun luonnos.
- `commercial-ferry-timetables.json`: virallisista operaattorilähteistä
  litteroidut Turun, Naantalin ja Helsingin sekä Ahvenanmaan väliset Tallinkin,
  Viking Linen ja Finnlinesin reittivuorot, poikkeukset, varauslinkit ja
  lähtöselvitysehdot. Hinnat ovat dynaamisia eikä niitä tallenneta numeroina.
- `structured-connection-timetables.json`: yhteysalusreittien ja reitityksessä
  tarvittavien Ahvenanmaan aluslinjojen säännölliset viikkoaikataulut matkoiksi
  normalisoiva kokeellinen aineisto.
- `connection-trip-normalization-report.json`: normalisoinnin reittikohtainen
  kattavuus ja vielä normalisoimattomien pyhäpäiväpoikkeusten tila.
- `structured-timetables.schema.json`: luonnoksen JSON Schema.
- `ais-arrival-estimates.json`: AIS-historiasta laskettu, sovelluskäyttöön
  rajattu neuvoa-antava ajoaikamalli.
- `ais-arrival-estimates.schema.json`: AIS-ajoaikamallin JSON Schema.
- `ais-arrival-estimates-flexible.json`: aikataulusta riippumaton kokeellinen
  malli, jossa perusyksikkö on suunnattu laituriväli.
- `ais-directional-call-estimates.json`: lineaaristen meno–paluu-reittien
  suuntakohtainen kokeellinen laituriaikamalli.
- `ais-call-role-model.json`: sekamuotoisten reittien kokeellinen
  käyntiroolimalli; ei sisällä vielä lopullisia ajoaika-arvioita.
- `ais-role-aware-arrival-estimates.json`: käyntiroolin, päätepisteparin ja
  täsmällisen välilaituriketjun erottava kokeellinen ajoaikamalli.
- `ais-anchor-path-estimates.json`: myös muun tunnetun lähtölaiturin kuin
  analyysin päälaiturin hyväksyvä täsmällisten AIS-ketjujen malli. Mallissa on
  erikseen liikkeessäoloajat välilaitureille ja koko matkan seinäkelloajat
  julkaistun päättymisajan historialliseen vertailuun.
- `ais-anchor-path-backtest.json`: ankkurimallin viimeisten 90 päivän ajallinen
  takautuva testi.
- `ais-aland-detour-validation.json`: Husön ja Kyrkogårdsön poikkeamien
  kasautumista koskeva AIS-tarkistus ja analyysissä käytettävä 10 + 20 minuutin
  sääntö.
- `structured-timetables-with-ais.json`: rakenteellisen aikataulun ja
  yhteensopivien AIS-arvioiden generoitu yhdistelmä.
- `structured-connection-timetables-with-ais.json`: normalisoitujen
  yhteysalusmatkojen sekä rooli- ja ketjutietoisten AIS-arvioiden yhdistelmä.
- `connection-ais-estimate-link-report.json`: uuden liitoksen kattavuus ja syyt
  niihin käynteihin, joille arviota ei vielä voitu antaa.
- `connection-arrival-prediction-catalog.json`: sovelluksesta riippumaton,
  vuoro- ja käyntikohtainen hakuluettelo julkaistuista ajoista ja lähtöhetkeen
  lisättävistä AIS-aikaväleistä.
- `connection-arrival-prediction-catalog-report.json`: hakuluettelon kattavuus.
- `ais-arrival-estimate-link-report.json`: liitoksen osumat ja turvallisuussyistä
  hylätyt vuorot.
- `ais-estimate-link-overrides.json`: tarkistetut reitti- ja laiturinimien
  vastaavuudet kahden aineiston välillä.
- `structured-timetable-transcriptions/`: PDF-lähteiden litteroinnit.
- `scripts/`: aineiston poiminta- ja generointityökalut.
- `road-components.json`: ylläpidetty laiturien ryhmittely yhtenäisiin,
  lautattomiin tiealueisiin sekä tarkistetut auditoinnin poissulut.
- `road-network.json`: OpenStreetMap/Valhalla-reitityksellä validoidut suunnatut
  laiturivälit, etäisyydet sekä auton ja polkupyörän ajoajat.
- `road-network-audit.json`: lähimpien muiden laiturien tarkistus mahdollisten
  puuttuvien tiealuejäsenyyksien löytämiseksi.
- `road-network-review.md`: ihmiselle tarkoitettu tarkistuslista tiealueista ja
  kaikista laituriväleistä.
- `external-routing-stop-index.json`: kaikkien tunnettujen vesiliikenteen
  pysähdyspaikkojen koordinaatit ja niistä johdetut lautattomat tiealueet.
  Ylläpidetyn monen pysähdyspaikan tiealueen ulkopuoliset paikat muodostavat
  yhden pysähdyspaikan tiealueen. Varsinainen pysähdyspaikan koordinaatti
  säilytetään lauttojen tunnistamista varten, mutta tarvittaessa sillä voi olla
  erillinen `routingCoordinates`-piste maantieverkon puolella. Lautattomissa
  tiehauissa Valhallaa estetään lisäksi ankkuroimasta päätepistettä
  lauttageometriaan.
- `external-routing-stop-index.schema.json`: ulkoisen reitityksen
  pysähdyspaikkahakemiston JSON Schema.
- `routing-stop-overrides.json`: reitityksessä käytettävät laiturinimien
  vastaavuudet sekä useita mahdollisia laiturikäyntejä sisältävien
  aikataulusolujen rakenteinen tulkinta.
- `routing-graph.json`: tieverkon, aikataulutetut ja jatkuvat lauttayhteydet
  sekä yhteysalusvuorot yhdistävä ajasta riippuva reititysgraafi.
- `routing-graph-report.json`: graafin kattavuus ja vielä puuttuvat
  normalisoidut reitit.
- `routing-graph.schema.json`: reititysgraafin JSON Schema.
- `scripts/query_direct_services.py`: yhden suoran aikataulutetun yhteyden
  päiväkohtainen tarkistustyökalu.
- `scripts/route_itinerary.py`: kokeellinen ajasta riippuva reitinhaku, joka
  yhdistää lautattomat tieosuudet, aikataulutetut lauttavuorot ja tunnetun
  ylitysajan sisältävät jatkuvat lossiyhteydet. Vaihtoriski ilmoitetaan
  yhteysvälikohtaisesti.

Lossien `crossingMinutes` on reititysaika rannasta rantaan. Kentän
`crossingTimeBasis` kertoo, perustuuko se viranomaisen liikenneanalyysiin,
muuhun lähdetietoon vai reitin pituudesta tehtyyn vertailuarvioon. Jälkimmäistä
ei pidä esittää julkaistuna aikatauluaikana.
- `scripts/route_itineraries.py`: saman haun useita eri lauttavuoroketjuja
  säilyttävä versio. Se voi rajata saapumisen samalle päivälle ja siirtää
  matkan alun tieosuudet juuri ennen ensimmäistä lauttaa. Haku yhdistää
  rajatun monivaihtoehtohaun lähtöaikapyyhkäisyyn: jokaisesta pyyhkäisyn
  lähtöhetkestä säilytetään aikaisin toteuttamiskelpoinen reitti, minkä jälkeen
  vain aidosti dominoidut vaihtoehdot poistetaan. Näin myöhempi riskialtis
  yhteys säilyy käyttäjän valittavana, mutta aiemmin lähtevä, myöhemmin saapuva
  ja vähintään yhtä riskialtis odotuskierto putoaa pois.
- `scripts/query_routes.py`: sovellukselle tarkoitettu versio
  monivaihtoehtohausta. Se palauttaa versionoidun JSON-vastauksen ilman
  sisäistä diagnostiikkaa, ellei diagnostiikkaa pyydetä erikseen.
- `route-query-response.schema.json`: sovellukselle tarkoitetun
  reititysvastauksen JSON Schema.
- `scripts/query_address_routes.py`: osoitteet geokoodaava ja ulkoiset
  lautattomat tieosuudet saariston aikataulureititykseen yhdistävä kokeellinen
  ovelta ovelle -haku.
- `address-route-query-response.schema.json`: osoitehaun vastauksen JSON
  Schema. Varsinaiset matkavaihtoehdot käyttävät samaa rakennetta kuin
  laiturista laituriin tehtävä haku.
- `scripts/external_routing.py`: vaihdettavat Nominatim- ja Valhalla-sovittimet.
  Julkiset palvelimet sopivat kehityskokeisiin; tuotannossa niiden tilalla on
  käytettävä sovelluksen omia tai erikseen sovittuja palveluja.
- `scripts/build_external_routing_stop_index.py`: koostaa yleisen
  reitityspalvelun lauttaan nousukoordinaattien tunnistamiseen käytettävän
  pysähdyspaikka- ja tiealuehakemiston. Vanhan sovellusdatan `pier`-tyyppiä ei
  muuteta, mutta uusi aineisto käyttää yleistermiä `stop`.
- `scripts/classify_external_route.py`: lukee ajo-ohjeet sisältävän Valhalla-
  vastauksen, purkaa reittigeometrian ja palauttaa ensimmäisen lauttaan
  nousupaikan, jonka lähin tunnettu pysähdyspaikka on enintään 500 metrin
  päässä. Aiemmat tuntemattomat lautat ohitetaan eikä vastarannan
  tunnistamista vaadita tiealueen päättelemiseksi. Jos reitillä ei ole
  lauttaa, kysytty piste saa tunnetun ankkuripisteen tiealueen.
- `route-query-timing-audit.json`: reiteittäin ja laitureittain ryhmitelty
  auditointi niistä matkan sisäisistä käynneistä, joille ei vielä ole
  julkaistua eikä historiallista aikaa.

Ensimmäiseen aikataulutettuun alukseen johtavalla lautattomalla tieosuudella
operaattorin ilmoittama lastausvalmiusaika on ehdoton: reittiä ei tarjota, jos
laituriin saavutaan sen jälkeen. Kun matkalla on jo käytetty lauttaa,
seuraavan aluksen lastausvalmiusaika ei karsi vaihtoehtoa. Se näkyy kyseisen
vaihdon riskiluokituksessa, jotta käyttäjä voi itse valita tiukan yhteyden.
Reitti edellyttää silti, että käytetty saapumisaika ei ole seuraavan aluksen
lähtöajan jälkeen.

Laiturikohtaiset kausirajoitukset käsitellään reitittimen sisällä. Suljetun
kauden laituria ei voi käyttää lähtö- tai määräpaikkana, ja se poistetaan myös
vuoron palautettavista välipysähdyksistä. Kausirajoituksen lähdemetadataa tai
kohteen kuvailevaa luokitusta ei palauteta käyttöliittymän suodatettavaksi.

Aikataulun lähdemerkkejä, kuten `x` ja `y`, ei palauteta reittivastauksessa.
Reititin ratkaisee niiden perusteella matkakohtaisen varausvaatimuksen ja
palauttaa `booking.deadline`-kentässä täydellisen paikallisen päivämäärän ja
kellonajan. `previous_operating_day` lasketaan reitin vuorokalenterista ja
poikkeuspäivistä eikä jätetä käyttöliittymän tulkittavaksi.

Jokainen lauttalegi sisältää `intermediateStops`-listan. Välilaiturista
palautetaan tunniste, tulkittu `mandatory`-arvo ja `timing`: julkaistu aika tai
historiallinen AIS-arvio täydellisinä päivämäärä-kellonaikoina sekä mahdollinen
vaihteluväli. Pakollisuudessa huomioidaan sekä aikataulusolun merkintä että
laituriin kohdistuva reittitason ehto. Jos välilaiturin aikaa ei tunneta,
`timing` on `null`.
- `ROUTING_PLAN.md`: reitityksen suunnitelma ja perustelut.
- `STRUCTURED_TIMETABLE_UNCERTAINTIES.md`: tarkistettavat tulkinnat.

Generointi ajetaan repositorion juuresta:

```sh
python3 future/structured-routing/scripts/build_structured_timetables.py
python3 future/structured-routing/scripts/build_structured_timetables.py --check

python3 future/structured-routing/scripts/link_ais_arrival_estimates.py \
  future/structured-routing/structured-timetables.json \
  future/structured-routing/ais-arrival-estimates.json \
  future/structured-routing/structured-timetables-with-ais.json \
  future/structured-routing/ais-arrival-estimate-link-report.json \
  --overrides future/structured-routing/ais-estimate-link-overrides.json

python3 future/structured-routing/scripts/build_connection_trip_draft.py \
  future/structured-routing/structured-timetables.json \
  future/structured-routing/structured-connection-timetables.json \
  future/structured-routing/connection-trip-normalization-report.json

python3 future/structured-routing/scripts/link_role_aware_trip_estimates.py \
  future/structured-routing/structured-connection-timetables.json \
  future/structured-routing/ais-role-aware-arrival-estimates.json \
  future/structured-routing/ais-arrival-estimates-flexible.json \
  future/structured-routing/ais-anchor-path-estimates.json \
  future/structured-routing/structured-connection-timetables-with-ais.json \
  future/structured-routing/connection-ais-estimate-link-report.json

python3 future/structured-routing/scripts/build_connection_prediction_catalog.py \
  future/structured-routing/structured-connection-timetables-with-ais.json \
  future/structured-routing/connection-arrival-prediction-catalog.json \
  future/structured-routing/connection-arrival-prediction-catalog-report.json

python3 future/structured-routing/scripts/build_road_network.py
python3 future/structured-routing/scripts/audit_road_components.py
python3 future/structured-routing/scripts/build_road_network_review.py
python3 future/structured-routing/scripts/build_external_routing_stop_index.py
python3 future/structured-routing/scripts/build_external_routing_stop_index.py --check
python3 future/structured-routing/scripts/build_routing_graph.py

python3 future/structured-routing/scripts/classify_external_route.py \
  valhalla-route-response.json --anchor-road-area mainland_finland

python3 future/structured-routing/scripts/query_direct_services.py \
  Roslax Bockholm 2026-11-02 --mode car

python3 future/structured-routing/scripts/route_itinerary.py \
  Verkan Storpensor 2026-10-30 12:00 --mode car

python3 future/structured-routing/scripts/route_itineraries.py \
  Turku Storpensor 2026-10-30 --mode car --same-day

python3 future/structured-routing/scripts/query_routes.py \
  Turku Wihuri 2026-11-01 --mode car --same-day

python3 future/structured-routing/scripts/query_address_routes.py \
  "Hallituskatu 13, Tampere" "Norra Finbyvägen 8, Sund" \
  2026-11-03 --mode car --same-day

python3 future/structured-routing/scripts/audit_route_timing_coverage.py

python3 -m unittest discover \
  -s future/structured-routing/tests -v
```

Osoitehaussa geokoodatusta pisteestä etsitään lähin tunnettu ankkurilaituri ja
pyydetään yleiseltä reitityspalvelulta reitti sinne lautat sallittuina. Jos
reitillä ei ole lauttaa, piste kuuluu ankkurin tiealueeseen. Muussa tapauksessa
ensimmäinen enintään 500 metrin päästä tunnistettu lauttaan nousupaikka ratkaisee
tiealueen; tätä edeltävät tuntemattomat lautat ohitetaan.

Tiealueen tunnistamisen jälkeen lähtöosoite liitetään lautattomilla tieosuuksilla
alueen kaikkiin reititysgraafin laitureihin ja määränpää vastaavasti oman
tiealueensa laitureihin. Sisäinen ajasta riippuva reititin valitsee niiden
väliltä käyttökelpoiset lautta- ja yhteysalusketjut. Ensimmäisen aluksen
lastausvalmiusaika siirtää myös osoitteesta lähdön oikeaan ajankohtaan.

Valhallan julkisen demopalvelimen matriisihaku on rajattu lyhyemmäksi kuin sen
tavallinen reittihaku. Jos matriisi ei siksi tuota yhtään tieosuutta, kokeilu
hakee tavallisella reittihaulla enintään kahdeksan maantieteellisesti lähintä
laituria. Tuotantopalvelussa tulee käyttää riittävän suuren matriisirajan
Valhalla-instanssia, jolloin kaikki saman tiealueen laiturit voidaan vertailla
yhdellä pyynnöllä. Yli 150 kilometrin pyöräosuuksia ei hyväksytä.

Yhteysalusaikataulun kauttaviivasolu, esimerkiksi `Gloskär/Trunsö` tai
`Vänö/Tunnhamn`, tarkoittaa kahta itsenäisesti ehdollista laiturikäyntiä:
vuoro voi käydä kummassa tahansa tai molemmissa. Graafi laajentaa solun
erillisiksi laitureiksi ja tuottaa saman vuoron sisäiset ohitussärmät, joten
kumpaakaan käyntiä ei tulkita pakolliseksi. Sen sijaan `Nagu / Nauvo` on
kaksikielinen nimi ja vastaa yhtä Nauvon laituria.

Skriptit lukevat edelleen repositorion juuressa olevia nykyisiä lähdetietoja
sekä Gitin ulkopuolisen `.timetable-checker/originals/`-hakemiston tiedostoja.

Ensimmäisen AIS-ajoaikamallin tuottaa
`future/structured-routing/ais-analysis/build_arrival_prediction_model.py`.
Malli sisältää vain
vähintään viisi kertaa samassa viikonpäivä- ja lähtöaikaryhmässä havaitut
välilaituriketjut. Ajat ovat laiturivälien ajoaikojen summia; välilaitureissa
vietetty odotusaika ei sisälly arvioon. Tiedosto on luonnos eikä korvaa
operaattorin julkaisemaa aikataulua.

`future/structured-routing/ais-analysis/build_flexible_arrival_model.py` tuottaa uuden
aikataulusta riippumattoman luonnoksen. Se yhdistää laiturivälien ajoajat
kaikista luotettavista havainnoista eikä vaadi saman viikonpäivän tai lähtöajan
löytymistä historiasta. Täsmälleen havaittu välilaituriketju voidaan käyttää
sellaisenaan, uusi ketju voidaan arvioida laiturivälien summana ja tuntemattoman
ketjun varalle on kaikkien toistuvien historiallisten vaihtoehtojen haarukka.
Kalenteriluokat kuvaavat eri käyntiketjujen yleisyyttä ja antavat
välilaitureiltaan tuntemattomalle vuorolle kohdekohtaisen ensisijaisen
varahaarukan. Jos sellaista ei ole, käytetään kaikkien luotettavien
historiallisten ketjujen konservatiivista haarukkaa. Tätä v2-luonnosta ei ole
vielä liitetty rakenteiseen aikatauluun.

Paraisten reitin yleisiä `destinationFallbacks`-arvoja ei saa käyttää ilman
suuntaerottelua, koska ne yhdistävät menomatkan jättökäynnit ja paluumatkan
noutokäynnit. `ais-directional-call-estimates.json` korvaa nämä arviot
Paraisten reitillä. Se käyttää tunnettua ulospäin kulkevaa laiturijärjestystä ja
erottelee käynnit `outbound`- ja `inbound`-vaiheisiin.

`ais-call-role-model.json` erottaa Rymättylän, Velkuan sekä Nauvon pohjoisen ja
eteläisen reitin sekä Hiittisten, Houtskarin, Korppoon, Utön ja Ahvenanmaan
linjojen historialliset käynnit rakenteen mukaan. Mallissa ovat
reittien analyysipäätepisteet, havaittujen matkarakenteiden määrät ja
laiturikohtaiset roolimäärät. `single_loop_call` tarkoittaa vain, että laituri
havaittiin kerran suljetulla matkalla; sitä ei pidä yksin tulkita varmaksi
rengasreitiksi. Tiedosto ei ole sovelluksen käytössä.

`ais-role-aware-arrival-estimates.json` käyttää varsinaisena tyypillisenä
arviona vain vähintään viisi kertaa havaittua täsmällistä käyntiketjua. Väljä
reitti–laituri–rooliryhmä on mukana ainoastaan konservatiivisena mahdollisena
min–max-haarukkana. Ahvenanmaan linjoilla julkaistu aikataulu on määräävä ja AIS
toimii toteutuneiden ajoaikojen tarkistuksena. Eteläisellä linjalla Husön 10 ja
Kyrkogårdsön 20 minuutin poikkeamat lasketaan yhteen, jos molemmat toteutuvat.

Liitos käyttää ensisijaisesti täsmälleen vastaavaa viikonpäivä- ja
lähtöaikaryhmää. Jos aikataulukausi on vaihtunut, se voi käyttää vähintään
viiteen havaintoon perustuvaa reitti- ja välilaituriketjukohtaista arviota.
Varmistus hylkää koko vuoron arviot, jos arvioitu välipysähdys olisi myöhempi
kuin vuoron myöhempi julkaistu aika. Pooled-arvion luottamus on rajattu enintään
0,75:een ja käyttöliittymän on aina näytettävä historiadataa koskeva ilmoitus.

Kaikilla 19 tarkastellulla yhteysalus- ja Ahvenanmaan alusreitillä on nyt
säännöllisen viikkoaikataulun `trips`-rakenne: yhteensä 462 matkamallia ja
1 976 käyntiä. Viimeksi lisätyt reitit ovat Åva–Jurmo, Enklinge–Kumlinge,
Föglön linja, Iniön lisäreitti, Vuosnainen–Åva ja Velkua–Taivassalo.
Kymmenen reitin lähteissä olevat pyhäpäiväsäännöt on lisäksi normalisoitu
päiväkohtaisiksi korvaaviksi matkoiksi tai liikenteettömiksi päiviksi.
Päiväkohtaiset matkat ovat mukana myös varsinaisessa reititysgraafissa;
poikkeuspäivänä säännöllinen viikkopohja ei jää niiden rinnalle vahingossa
voimaan. Korppoon ja Utön aiemmat kahden matkan käsin tehdyt osaluonnokset on
korvattu lähdetaulukoista poimituilla koko viikkoaikatauluilla.

Puuttuva julkaistu kellonaika löytyi 646 matkan sisäiseltä käynniltä. Niistä
461:lle voitiin liittää vähintään viisi kertaa havaitun, aikataulun
pysähdysjärjestykseen sopivan AIS-ketjun tyypillinen aika ja vaihteluväli.
Lisäksi 90 käynnille liitettiin vain konservatiivinen havaittu min–max-haarukka;
väljän rooliryhmän mediaania ei käytetä ennusteena. Näin jokin historiallinen
ajoaikatieto kattaa 85,3 % kellonajattomista käynneistä ja 96,2 % niistä,
joilla on tunnettu lähtöaika ja käytettävissä AIS-lähde. Nauvon poikittaisen 58
käyntiä jäävät tarkoituksella ilman AIS-arviota, koska reitin alus ei lähetä
AIS-dataa. Ahvenanmaan pohjoisella ja eteläisellä linjalla kaikki tämän
luonnoksen käynnit saavat ajan julkaistusta aikataulusta, joka on siellä aina
määräävä. Lopetettu reitti on Ahvenanmaan poikittainen, ei Nauvon poikittainen.
Pyhäpäivämatkoihin kopioitiin 139 vastaavan viikkopohjan välilaituriarviota ja
26 päättymisarviota, yhteensä 165 historiallista ajoitustietoa.

Hakuluettelo sisältää 462 säännöllistä matkamallia, 456 päiväkohtaista
pyhäpäivämatkaa ja 17 liikenteetöntä poikkeuspäivää. Sisäisissä käynneissä on
1 332 julkaistua kellonaikaa, 577 täsmällistä historiallista arviota, 113
konservatiivista historiallista haarukkaa ja 495 käyntiä ilman aikaa. Arvioiden
ydin on kellonajan sijasta lähtöhetkeen lisättävä minuuttimäärä, joten samaa
mallia voidaan käyttää myös toteutuneen lähtöajan siirtyessä.

Laiturin asema reitin päätepisteenä ei tarkoita, että se sopii automatkan
lähtöpisteeksi. Reittikohtainen `pierAccess` erottaa alueelliseen tie- ja
maantielauttaverkkoon liittyvät laiturit saarilaitureista. Kun käyttäjä ei anna
lähtöpaikkaa, ehdotukseen saa ottaa vain laiturin, jonka
`suggestForUnspecifiedOrigin` on `true`. Esimerkiksi Pärnäs, Kasnäs, Dalsbruk,
Roslax ja Torsholma ovat tällaisia lähtöpisteitä; Utö, Borstö ja Själö eivät
ole, vaikka ne voivat olla aikataulumatkan päätepisteitä tai aluksen
yöpymispaikkoja.

Överöllä on tieyhteys Föglön sisällä, mutta sitä ei ehdoteta lähtöpisteeksi
käyttäjälle, joka ei ole jo Föglössä. Havträsk ja Lavarn sen sijaan ovat
käytännöllisiä automatkan lähtölaitureita ilmaisen maantielauttayhteyden takana.
`TorsholmaI` ei tarkoita Iniötä vaan Brändössä sijaitsevaa Torsholman itäistä
laituria. Se ja suurempi Torsholman satama ovat samalla saarella ja tieyhteyden
päässä toisistaan. Pohjoinen linja käyttää tätä nykyisin väliaikaisesti.

Ålandstrafikenin aluslinjat luokitellaan omaksi
`alandstrafiken_archipelago_ferry`-ryhmäkseen riippumatta siitä, onko linjalla
kaksi vai useampia laitureita. Ne eivät ole manner-Suomen yhteysalusreittejä.
Ålandstrafikenin vaijerilossit kuuluvat erilliseen `cable_ferry`-luokkaan.

Reititysgraafissa on 184 laiturisolmua, 9 942 yhteyttä ja 2 542 matkamallia.
Kaikilla 45 varsinaisella liikennöintireitillä on vähintään yksi graafiyhteys;
ainoa 46. reittitietue on Ahvenanmaan vaijerilossien yhteinen lähde- ja
metatietosäiliö. Graafissa ei ole koordinaatittomia solmuja eikä ratkaisemattomia
laituritunnisteita. Reitittimen regressiotestit kattavat muun muassa
Turku–Storpensarin, Turku–Wihurin, Nauvo–Degerbyn sekä uudet Åva–Jurmon,
Vuosnainen–Åvan ja Iniön lisäreitin yhteydet, Enklingen varausehdon ja Föglön
jouluaaton tilausvuoron.

Maantielautat ja lossit esitetään reititykselle yhtenäisinä kahden laiturin
verkon kaarina. `routingService.terminals` nimeää päät, `model` erottaa
aikataulutetut lähdöt jatkuvasta tai kutsusta toimivasta liikenteestä, ja
`trips` sisältää aikataulutetut suunnatut ylitykset kalenteri- ja
poikkeusehtoineen. Jatkuvan liikenteen `continuousServices` säilyttää
liikennöinti-ikkunat ja tauot. Arvioitu ylitysaika annetaan vain, jos se löytyy
ylläpidetystä reittidatasta; tuntematonta aikaa ei arvata.

Finferriesin 19 aktiivista maantielautta- ja lossireittiä sekä
Ålandstrafikenin kuusi vaijerilossireittiä käyttävät nyt samaa mallia. Niille
syntyy yhteensä 1 540 kalenteriehtoineen yksilöityä vuoroa sekä 14 jatkuvan tai
kutsuliikenteen palvelujaksoa. Iniö–Kustavin HTML-lähteen `inio` ja muun datan
`iniokustavi` on yhdistetty samaksi reitiksi.

Ålandstrafikenin PDF:t tarkistettiin myös visuaalisesti, koska värit määräävät
viikonloppuna ja pyhäpäivinä pois jäävät vuorot. Seglinge-, Simskäla- ja
Töftö-linjoilla julkaistaan aika vain toiselta rannalta. Malli muodostaa myös
paluusuunnan: Seglingessä ja Simskälässä paluulähtö on lähteen mukaan noin
seitsemän minuuttia julkaistua aikaa myöhemmin, Töftössä 5–7 minuuttia
myöhemmin. Yöliikenne, viikonlopun kutsuliikenne, tauot, ennakkotilausajat,
poikkeuspäivät ja lähteen liikennöintihuomautukset säilytetään erillisinä
ehtoina. Björkö-, Embarsund- ja Ängösund-linjat ovat jatkuvan tai kutsusta
toimivan liikenteen verkkokaaria.

Tieosuudet ja maantielautat muodostavat yhden reititysverkon. Siksi tuleva
tiegraafi tarvitsee laiturien välisille tiekaarille vain etäisyyden sekä auton
ja polkupyörän suuntaa-antavat ajoajat; erillistä tietoa siitä, sisältääkö
yhteys tie- tai maantielautan, ei tarvita. Maantielauttojen ja lossien kaikki
laiturit oletetaan autolla saavutettaviksi. Yhteysaluksen kykyä lastata auto
yksittäisessä saarilaiturissa ei mallinneta, vaan matkan ajoneuvokelpoisuuden
lopullinen tarkistus jää varausjärjestelmälle.

Lautattomassa tiegraafissa on nyt 23 tiealuetta ja 85 laituria. Niistä syntyy
606 suunnattua laituriväliä ja 1 210 auton tai polkupyörän reititystulosta.
Jokaisen tuloksen reitti on hyväksytty vain, jos Valhalla ei ilmoita sillä
lauttaosuutta. `hasFerry`- ja `hasToll`-kenttiä ei kirjoiteta tuloksiin, koska
lauttomuus on hyväksymisehto eikä Suomen aineistossa tarvita tiemaksutietoa.
Öröllä muodostetaan vain pyöräreitit. Julkisen reitittimen 150 kilometrin
pyörärajaa pidemmät Helsinki-yhteydet koostetaan kahdesta hyväksytystä
osareitistä Salo-välipisteen kautta; sovellus voi myöhemmin jättää näin pitkät
pyöräsiirtymät kokonaan ehdottamatta.

Laiturin karttakoordinaatti ja tiereitityksen ankkuri voidaan pitää erillään.
Eckerön Berghamnissa reititys alkaa satama-alueen liittymästä Eckerövägenillä,
koska varsinaisen laituripisteen yksisuuntainen palvelutieverkko tuotti
keinotekoisen 9–11 minuutin suuntaeron. Kartalla käytetään edelleen oikeaa
laiturikoordinaattia.

Auditointi vertaa ylläpidettyjä tiealueita lähimpiin muihin laitureihin. Se
ottaa huomioon rakenteiseen aikatauluun mallinnetut maantielautta- ja
lossiyhteydet eikä ehdota niiden vastarantojen yhdistämistä samaksi
tiealueeksi. Lisäksi se torjuu epäuskottavan lyhyet ja pitkät reitit sekä
käyttäjän erillisiksi saariksi vahvistamat Aspholm–Ramsholm- ja
Rauhala–Talosmeri-parit. Viimeisin ajo ei löytänyt yhtään tarkistamatonta,
todennäköistä puuttuvaa tieyhteyttä. Söderlångvik kuuluu manner-Suomen
tiealueeseen ja Ramsholm sekä Heisala omaan yhteiseen tiealueeseensa.

Hakutuloksen on näytettävä kaikki valittuun matkaan soveltuva lähdeaikataulun
matkustajainformaatio. `travelerInformation` säilyttää muun muassa
varausvelvollisuuden ja -määräajat, lastausvalmiusajan, mahdollisen aikaisen
lähdön säännön, ajoneuvorajoitukset sekä yhteyksiä ja poikkeuksia koskevat
huomautukset. Näitä ei saa tiivistää pois. Esimerkiksi Houtskarin ja Rymättylän
reiteillä sekä matkustajien että ajoneuvojen on oltava lastausvalmiina 10
minuuttia ennen lähtöä.

Julkaistu matkan päättymisaika säilyy aina varsinaisena aikatauluna. Sen
rinnalle on liitetty 206 matkamalliin erillinen historiallinen
päättymisarvio: 170:ssä on tyypillinen aika ja havaittu vaihteluväli, 36:ssa
vain konservatiivinen vaihteluväli. Päättymisajan laskenta sisältää normaalit
lyhyet välilaiturikäynnit mutta katkaisee ketjun yli 30 minuutin taukoon.
Tulos sisältää sekä kellonaikavälin että poikkeaman julkaistusta
päättymisajasta; se ei korvaa julkaistua aikaa.

Ankkurimallin 90 päivän ajallisessa takautuvassa testissä syntyi 36 629
ennustetta. Mediaanivirhe oli 1,12 minuuttia, p90-virhe 5,83 minuuttia ja 96,4 %
ennusteista oli enintään kymmenen minuutin päässä toteumasta. P10–p90-haarukka
sisälsi toteuman 80,1 %:ssa tapauksista.

## Reitityspalvelu

`service/app.py` julkaisee osoitteesta osoitteeseen -reitityksen FastAPI-
palveluna. Ensimmäisessä versiossa on kaksi rajapintaa:

- `GET /health` palauttaa palvelun tilan ja version
- `POST /route` ottaa vastaan `route-request.schema.json`-muotoisen pyynnön ja
  palauttaa `address-route-query-response.schema.json`-muotoisen vastauksen

Esimerkkipyyntö:

```sh
curl http://127.0.0.1:8082/route \
  -H 'Content-Type: application/json' \
  -d '{
    "origin": "Hallituskatu 13, Tampere",
    "destination": "Norra Finbyvägen 8, Sund",
    "date": "2026-11-03",
    "mode": "car",
    "sameDay": true
  }'
```

Palvelu geokoodaa osoitteet Nominatimilla, tunnistaa tiealueet Valhallan
avulla ja käyttää niiden välissä omaa saariston reititysgraafia. Vain valittujen
reittivaihtoehtojen ulkoisille tieosuuksille haetaan lopuksi karttageometria.
Nominatimin ja Valhallan onnistuneet JSON-vastaukset tallennetaan pysyvään
SQLite-välimuistiin. Välimuistin oletuskesto on 30 päivää ja polku kontissa
`/var/cache/saaristolautat/routes.sqlite3`. Myös täysin saman pyynnön valmis
reititysvastaus tallennetaan samaan välimuistiin. Avaimessa on mukana
reititysgraafin ja laiturihakemiston sisältötiiviste, joten uusi data ei käytä
vanhan aineiston tuloksia.

Käynnistys palvelimella:

```sh
docker compose up -d --build
```

`compose.yml` kuuntelee vain palvelimen omassa osoitteessa
`127.0.0.1:8082`. Sama compose käynnistää Suomen aineistoa käyttävän Valhallan
osoitteeseen `127.0.0.1:18083`; reititys-API käyttää sitä compose-verkon sisällä
osoitteella `http://valhalla:8002`. Valhallan aineisto säilytetään nimetyllä
levyllä `saaristolautat-valhalla-finland`, joten kontin uudelleenluonti ei
rakennuta noin kymmenen gigatavun aineistoa uudelleen. Ensimmäinen käynnistys
uudella palvelimella lataa ja rakentaa aineiston ennen API:n käynnistymistä.
`deploy/nginx-location.conf` sisältää nginxin käänteisen välityksen mallin.
FastAPIn koneellisesti muodostama rajapintakuvaus löytyy palvelun käydessä
osoitteesta `/docs`.

Kontti käyttää aluksi yhtä palvelinprosessia. Näin Nominatimin vähintään yhden
sekunnin kutsuväli ja SQLite-välimuistin kirjoitukset pysyvät yhden prosessin
hallinnassa. Hitaat ulkoiset haut suoritetaan säikeissä, joten ne eivät estä
palvelinta vastaanottamasta muita HTTP-yhteyksiä.

Sisäinen hakukone esilaskee kyselyn aikavälin toteutuvat vuorot ja niiden
poikkeuspäivät `ScheduledInstanceIndex`-indeksiin. Samaa kalenteriehtoa ei näin
tulkita uudelleen jokaiselle hakutilalle. Hakutilat karsitaan lisäksi
saapumisajan, mahdollisimman myöhäisen lähtöajan ja yhteysriskin muodostamalla
Pareto-rintamalla. Lokakuun 2026 paikallisessa vertailussa Turku–Wihuri-haun
kesto putosi noin 20 sekunnista noin yhteen sekuntiin. Muut yhden päivän
esimerkit valmistuivat noin 1–2,4 sekunnissa ja kylmä osoitehaku paikallisella
Valhallalla noin 4,4 sekunnissa. Nämä ovat kehityskoneen suuntaa-antavia
lukuja, eivät rajapinnan suorituskykytakuu.

Hakugraafista lasketaan lisäksi jokaiselle solmulle vähimmäislegimäärä
määränpäähän. Haara katkaistaan heti, jos jäljellä oleva 12 legin raja ei voi
enää riittää. Tämä pudotti kolmen päivän Turku–Storpensor-testin noin 7,8
sekunnista noin 4,8 sekuntiin muuttamatta palautettuja vaihtoehtoja.

Eri lähtöhetkiä ei käydä enää läpi kiinteällä 30 minuutin askelluksella.
Reititin siirtyy suoraan hetkeen, jolloin ensimmäinen saavutettavissa oleva
aikatauluvuoro menetetään tai yhteysriskin luokka vaihtuu. Näin harvoin
liikennöidyllä reitillä ei lasketa kymmeniä keskenään samanlaisia hakuja, ja
riskiluokan raja löytyy minuutin tarkkuudella askelvälistä riippumatta.

Kun `sameDay` on `false`, reititin etsii enintään kolmen päivän aikajänteeltä
ensimmäisen päivän, jona määränpäähän voidaan saapua, ja palauttaa kyseisen
saapumispäivän hyödylliset vaihtoehdot. Myöhempien päivien samanlaisia vuoroja
ei lasketa turhaan eikä palauteta ensimmäisten käyttökelpoisten yhteyksien
jälkeen.

Tuotannossa on asetettava tunnistettava, yhteystiedon sisältävä
`ROUTING_USER_AGENT`. Valhallalle suositellaan omaa instanssia tai palvelua,
jonka matriisirajat kattavat Suomen ja Ahvenanmaan laituriehdokkaat. Jos
matriisihaku ei onnistu, reititin tarkistaa kaikki tiealueen laiturit
yksittäisinä hakuina. Se ei enää rajaa ehdokkaita kahdeksaan lähimpään, joten
oikea reitti ei jää tämän optimoinnin vuoksi löytymättä; pysyvä välimuisti
estää samojen hakujen toistumisen.

Oman reitittimen, paikallisen Valhallan ja Google Mapsin lokakuussa 2026 tehty
vertailu sekä sen rajaukset on dokumentoitu tiedostossa
[`ROUTING_ENGINE_COMPARISON.md`](ROUTING_ENGINE_COMPARISON.md). Vertailu
vahvistaa, että yleistä reitityspalvelua käytetään vain saaristoreitin alku- ja
loppupään tieosuuksiin; se ei korvaa aikataulutettua sisäistä graafia.

Paikallinen kehitys:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn service.app:app --reload
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```
