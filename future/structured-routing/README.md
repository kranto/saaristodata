# Rakenteellinen aikataulu ja reititys

Tämä hakemisto sisältää tulevaa rakenteellista aikataulua, sen generointia ja
sen avulla tehtävää reititystä koskevan kokeellisen työn. Hakemiston aineisto ei
ole tuotannossa eikä sitä julkaista nykyisen Saaristolautat-datan mukana.

Keskeiset tiedostot:

- `structured-timetables.json`: generoitu rakenteellisen aikataulun luonnos.
- `structured-connection-timetables.json`: yhteysalusreittien säännölliset
  viikkoaikataulut matkoiksi normalisoiva kokeellinen aineisto.
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
```

Skriptit lukevat edelleen repositorion juuressa olevia nykyisiä lähdetietoja
sekä Gitin ulkopuolisen `.timetable-checker/originals/`-hakemiston tiedostoja.

Ensimmäisen AIS-ajoaikamallin tuottaa `saaristolautat`-repositorion
`scripts/ais_analysis/build_arrival_prediction_model.py`. Malli sisältää vain
vähintään viisi kertaa samassa viikonpäivä- ja lähtöaikaryhmässä havaitut
välilaituriketjut. Ajat ovat laiturivälien ajoaikojen summia; välilaitureissa
vietetty odotusaika ei sisälly arvioon. Tiedosto on luonnos eikä korvaa
operaattorin julkaisemaa aikataulua.

`scripts/ais_analysis/build_flexible_arrival_model.py` tuottaa uuden
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

Yhteysalusluonnoksessa kaikilla 13 tarkastellulla reitillä on nyt säännöllisen
viikkoaikataulun `trips`-rakenne: yhteensä 241 matkamallia ja 1 406 käyntiä.
Hiittisten Jurmon, Korppoon ja Utön lähteissä olevat pyhäpäiväsäännöt on lisäksi
normalisoitu päiväkohtaisiksi korvaaviksi matkoiksi tai liikenteettömiksi
päiviksi. Korppoon ja Utön aiemmat kahden matkan käsin tehdyt osaluonnokset on
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

Hakuluettelo sisältää 241 säännöllistä matkamallia, 60 päiväkohtaista
pyhäpäivämatkaa ja 13 liikenteetöntä poikkeuspäivää. Sisäisissä käynneissä on
627 julkaistua kellonaikaa, 575 täsmällistä historiallista arviota, 115
konservatiivista historiallista haarukkaa ja 113 käyntiä ilman aikaa. Arvioiden
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
