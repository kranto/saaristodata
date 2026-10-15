# AIS-reittikandidaatit ja liikennöintijaksot 2025–2026

Tämä vaihe jatkaa raportissa `ais-analysis-2025-2026.md` kuvattua
esikäsittelyä. Tarkoituksena on päätellä aluksen reitti sen toteutuneista
laiturikäynneistä eikä sitoa MMSI-tunnusta pysyvästi yhteen reittiin.

## Menetelmä

Enintään 30 minuutin välein havaitut peräkkäiset saman laiturin käynnit
yhdistetään yhdeksi käynniksi. Alle 60 aktiivisen päivän alukset on rajattu
pois ennen tätä vaihetta. Tämä vähensi jäljelle jääneiden operatiivisten
käyntien määrän 297 113:stä 295 536:een.

Käynnit ryhmitellään MMSI-tunnuksen ja ISO-viikon mukaan. Jokaiselle aktiiviselle
reitille lasketaan pisteet neljästä tiedosta:

- reitin laitureihin osuvien käyntien osuus, paino 45 %
- reitin sisäisten laituri–laituri-siirtymien osuus, paino 35 %
- havaittujen reittilaiturien osuus kaikista reitin laitureista, paino 20 %
- vähintään kahden eri reittilaiturin pitää esiintyä samalla viikolla

Viikon paras ehdotus luokitellaan korkeaksi, todennäköiseksi tai epävarmaksi
pistemäärän ja toiseksi parhaan ehdotuksen marginaalin perusteella. Peräkkäiset
saman reitin korkeat tai todennäköiset viikot yhdistetään liikennöintijaksoksi.

## Tulokset

- Viikkoja, joille löytyi reittiehdotus: 1 783
- Korkean luottamuksen viikkoja: 1 697
- Todennäköisiä viikkoja: 54
- Epävarmoja viikkoja: 32
- Yhtenäisiä MMSI–reitti-liikennöintijaksoja: 123
- Selvästi kiinnostavaan reittiliikenteeseen luokiteltuja MMSI-tunnuksia: 45
- Mahdollisia mutta vielä tarkistettavia MMSI-tunnuksia: 15
- Ilman tunnettua reittiosumaa jääneitä MMSI-tunnuksia: 8

Rajaus säilytti 68 alusta ja poisti 49 alle 60 aktiivisen päivän alusta.
Nykyisestä `livedata.json`-aineistosta löytyi nimi 56 säilytetylle alukselle;
12 näytetään edelleen MMSI-tunnuksella.

`unmatched` ei vielä tarkoita varmasti ulkopuolista alusta. Luokkaan jäävät myös
alukset, joiden käyttämä laituri puuttuu tunnetusta datasta tai joiden
laiturikäynnit eivät täytä tunnistuskriteerejä.

## Havaitut reitin vaihdokset

Menetelmä tunnistaa sekä tilapäisiä että pidempiä reitin vaihdoksia. Esimerkkejä:

- MMSI 230035990: Pieni rengastie 4.5.–7.9.2026 ja Pohjoinen linja
  14.–28.9.2026.
- MMSI 230129940: Seglingelinjen suurimman osan vuodesta, lyhyitä jaksoja
  Pohjoisella linjalla tammikuussa ja Åva–Jurmo-reitillä elo–syyskuussa.
- MMSI 230175040: Nauvon pohjoinen reitti pääjaksona, lisäksi Paraisten ja
  Rymättylän reittijaksot.
- MMSI 230938210: Korppoo–Norrskata talvikaudella ja Houtskari–Iniö
  kesäkaudella.
- MMSI 230940100: useita vuorottelevia jaksoja Töftö-, Seglinge- ja
  Simskälalinjoilla.

Nämä ovat algoritmin ehdotuksia. Erityisesti yhden tai kahden viikon jaksot
pitää tarkistaa kartalta ennen kuin niitä tulkitaan todellisiksi alusvaihdoiksi.

## Tuntemattomat pysähdyspaikat

Ensimmäisen vaiheen 268 pysähdyssolua yhdistettiin 300 metrin säteellä 64
paikkaklusteriksi. OpenStreetMapin rantaviivaan tehty 100 metrin etäisyysrajaus
poisti näistä 50 kauempana rannasta olevaa klusteria. Katselmointiin jäi 14
rannan tuntumassa olevaa klusteria. Suurimmat klusterit sijaitsevat muun muassa Turun ja
Paraisten satama-alueilla, joten suuri havaintomäärä ei yksin tarkoita puuttuvaa
yhteysaluslaituria. Jatkoluokittelussa erotetaan ainakin:

- mahdollinen puuttuva reittilaituri
- koti- tai yöpymissatama
- telakka tai huoltopaikka
- kaupallinen satama
- ankkuri- tai odotuspaikka

## Tuotetut katselmointiaineistot

Väliaikaisessa `/tmp/ais-route-review-60d`-hakemistossa ovat:

- `weekly-route-candidates.csv`
- `route-regimes.csv`
- `vessel-classification.csv`
- `unknown-stop-clusters.csv`
- `review.geojson`
- `review-coastal.geojson`
- `coastline.json`
- `summary.json`

Katselmointi-GeoJSON sisältää käytetyt tunnetut laiturit, tuntemattomat
pysähdysklusterit ja niiden reittien nykyiset viivat, joille löytyi vähintään
yksi todennäköinen viikkopäätelmä.
