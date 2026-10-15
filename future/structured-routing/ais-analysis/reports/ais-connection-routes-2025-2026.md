# Yhteysalusreittien AIS-analyysi 2025–2026

Tässä vaiheessa aineistosta on poistettu maantielautat, lossit,
kaksilaituriset sukkulareitit, matkailuliikenteen reitit ja lopetettu
Ahvenanmaan poikittainen linja. Analyysiin jäi 12 määriteltyä
yhteysalusreittiä. Näistä 11:lle löytyi viimeisimmältä vuodelta luotettava
AIS-aineistoon perustuva reittiosuma. Nauvon poikittaiselta reitiltä ei saada
käyttökelpoista aineistoa, koska Cheri ei lähetä AIS-seurantaa.

## Reittijaksot ja matkat

- luotettavasti yhteysalusreitille luokiteltuja aluksia: 25
- yhtenäisiä alus–reitti-liikennöintijaksoja: 66
- enintään 90 sekunnin havaintokatkon, enintään 20 solmun laskennallisen
  pisteparinopeuden ja enintään kolmen minuutin yhtäjaksoisen hitaan jakson
  sisältäviä hyväksyttyjä laiturivälimatkoja: 56 224
- matkoja, joiden molemmat ajat perustuvat hitaaseen havaintoon kalibroidussa
  laituriytimessä: 51 187
- päälaiturista alkavia tunnistettuja käyntiketjuja: 21 582
- seuraavaan päälaituriin päättyviä kokonaisia ketjuja: 17 192
- kokonaisia ketjuja, joiden kaikilla osuuksilla on varma ydinajoitus: 16 381
- vähintään kolme kertaa havaittuja erillisiä käyntijärjestyksiä: 358
- vähintään kolmeen korkean luottamuksen havaintoon perustuvia kohdelaituri- ja
  käyntijärjestyskohtaisia saapumisaikahaarukoita: 804
- suunnittaisia laiturivälien aikahaarukoita: 597

Saapumisaika ryhmitellään reitin, lähtölaiturin, kohdelaiturin ja sitä edeltävän
laituriketjun mukaan. Esimerkiksi suora `A → C` ja kierros `A → B → C` eivät
päädy samaan jakaumaan. Lopullisessa ajoaikamallissa välilaiturissa käytetty
odotusaika poistetaan seuraavien laiturien ajoajasta.

## Ajoituksen luottamus

Laiturikäyntien löytämiseen käytetään edelleen 250 metrin aluetta. Ajoitusta
varten 61 846 luotettavan yhteysalusviikon hidasta käyntiä klusteroitiin
laitureittain. Kaikille aineistossa käytetyille 119 laiturille saatiin
hyväksytty ajoitusydin: 113 yksittäistä automaattista ydintä, kaksi vahvistettua
monilaiturista kohdetta ja neljä käyttäjän kartta- tai ilmakuvatulkinnalla
vahvistettua suurta koordinaattikorjausta.
Kökarissa hyväksyttiin käyttäjän ilmakuvasta vahvistamat kaksi erillistä
ajoluiskaa: 538 ja 495 käynnin klusterit ovat noin 62 metrin päässä toisistaan.
Niille käytetään erillisiä 20 metrin ytimiä, joten lähestymismutkan hetkellinen
hidastuminen ei kelpaa laituriajaksi.
Långnäsissä hyväksyttiin kaksi noin 65 metrin päässä toisistaan olevaa
yhteysalusten kiinnittymispaikkaa, joissa havaittiin 558 ja 236 käyntiä.
Molemmilla käyvät samat Eteläisen linjan alukset. Sovelluksen nykyinen
Långnäs-piste on lähempänä Ruotsin-laivojen kiinnittymispaikkaa eikä kumpaakaan
AIS-klusteria. Ajoituksessa yhteysaluspaikoille käytetään erillisiä 25 metrin
ytimiä.
Gloskärissä nykyinen sovelluspiste osoittautui vääräksi. Ajoitukseen hyväksytty
pohjoinen yhteysaluspaikka muodostuu 19 käynnistä ja sijaitsee noin 126 metriä
nykyisestä pisteestä. Lännempänä vedessä oleva 12 tapahtuman ryhmä koostuu
lähes aina vain yhdestä hitaasta näytteestä, joten se tulkitaan lähestymisen tai
odottelun hidastumiseksi eikä laituriksi.
Ilmakuvan ja käyntiradan perusteella pohjoinen paikka voi olla keula
rantakalliota vasten tehtävä lyhyt matkustajakäynti. Siksi Gloskärissä ei
edellytetä usean minuutin paikallaanoloa, vaan rantapisteen läheisyyttä,
hidastumista ja paluusuunnan muutosta arvioidaan yhdessä.
Kopparholmissa nykyisen sovelluspisteen kohdalla ei havaittu käyntejä.
Hyväksytty AIS-ydin muodostuu 81 käynnistä, sen 90. persentiilin hajonta on noin
10 metriä ja se sijaitsee noin 244 metriä nykyisestä pisteestä itään. Ydin
kuvaa aluksen antennin sijaintia; reittiviivojen osoittama varsinainen
rantautumispaikka on sen eteläpuolella aluksen keulan kohdalla.
Penossa hyväksyttiin käyttäjän reittiviivoista vahvistama pohjoisempi kääntö-
ja rantautumispaikka. AIS-ydin muodostuu 115/118 käynnistä, sen 90. persentiilin
hajonta on noin 22 metriä ja keskus sijaitsee noin 183 metriä nykyisestä
ilmakuvatulkintaan perustuneesta sovelluspisteestä.
Lempmossa hyväksyttiin käyttäjän reittiviivoista vahvistama läntisempi
rantautumispaikka. AIS-ydin muodostuu 83/88 käynnistä, sen 90. persentiilin
hajonta on noin 9 metriä ja keskus sijaitsee noin 209 metriä nykyisestä
ilmakuvatulkintaan perustuneesta sovelluspisteestä.
Ensisijainen lähtöhetki on viimeinen ja saapumishetki ensimmäinen enintään 1,5
solmun havainto kalibroidussa laituriytimessä. Kaikki suurten
koordinaattipoikkeamien kohteet on nyt tarkistettu käyttäjän kartta- ja
ilmakuvatulkinnan avulla.

Jos hidasta ydinhavaintoa ei nähdä, käytetään kehän interpoloitua ylitystä tai
viimeisenä vaihtoehtona lähintä havaintoa. Lähimpään havaintoon perustuvaa
matkaa ei käytetä korkean luottamuksen aikahaarukkaan. Lisäksi yli 90 sekunnin
AIS-katko, yli 20 solmun pisteparihyppy tai yli kolmen minuutin yhtäjaksoinen
hidas jakso matkan sisällä hylkää matkan aika-arviosta.

Yhteysalusviikkoihin ja kyseisen reitin laitureihin rajattuja hyväksyttyjä
laiturikäyntejä oli 64 918. Niistä:

- 61 296 eli 94,42 % perustui vähintään 45 sekunnin viipymään ja enintään 1,5
  solmun nopeuteen
- 3 566 eli 5,49 % perustui useaan laiturialueen pisteeseen ilman varmaa
  hidasta näytettä
- 34 eli 0,052 % perustui pelkkään sijaintiradan kääntymiseen
- 22 eli 0,034 % perustui 50 metrin läheisyyteen tai yksittäiseen hitaaseen
  pisteeseen

Yhteensä 5,58 % käynneistä tunnistettiin ilman varmaa pysähtymistä. Pelkkään
kolmen pisteen osoittamaan kääntymiseen perustui 0,052 % kaikista käynneistä.

## Päälaiturista kohteeseen laskettava ajoaika

Utön reitillä Pärnäs ja Utö käsitellään molemmat päälaitureina. Reitiltä löytyi
47 Pärnäsistä ja 105 Utöstä alkavaa korkean luottamuksen matkaa. Utön julkaistu
aikataulu on ensisijainen tieto; AIS:n tehtävä on kuvata toteutuneita
ajoaikoja.

Matka-aika lasketaan laiturivälien ajoaikojen summana. Välilaiturissa vietetty
aika jätetään pois, joten pitkä aikataulutauko ei venytä matkustajan
ajoaika-arviota. Normaali lyhyt tai pitkä laituriviipymä on silti nähtävissä
auditointia varten `intermediate_wait_seconds`-kentässä. Samassa matkassa
toistuvasti käytystä laiturista ennusteeseen otetaan vain ensimmäinen käynti.

Korkean luottamuksen matkoja oli 20 392. Ensimmäinen kokeilu ryhmitteli ne
viikonpäivän ja 15 minuutin lähtöaikakorin mukaan. Niistä 19 071 eli 93,52 %
sijoittui vähintään kolmen havainnon lähtöaikaryhmään. Ryhmiä oli 1 341 ja
niistä syntyi 3 870 kohdelaiturikohtaista aikahaarukkaa sekä 2 726 toistuvaa
välilaituriketjukohtaista aikahaarukkaa kaikille 11 AIS-reitille. Tämä malli on
hyödyllinen historiallisten lähtöjen tarkistamiseen, mutta liian tiukka uuden
aikataulukauden ennusteen ensisijaiseksi pohjaksi.

Joustavassa mallissa ajoaika irrotetaan lähtövuorosta. Ensisijainen yksikkö on
suunnattu laituriväli, jonka jakaumaan yhdistetään kaikki reitin luotettavat
havainnot viikonpäivästä, vuodenajasta ja kellonajasta riippumatta. Aineistossa
oli 41 946 tällaista laiturivälihavaintoa. Vähintään viisi kertaa toistuneet
430 suunnattua laituriväliä kattavat niistä 41 394 eli 98,68 %. Kaikki osuudet
saadaan näistä toistuvista väleistä 19 956 matkalle eli 97,86 %:lle korkean
luottamuksen matkoista.

Arviointijärjestys on:

1. Jos sama välilaituriketju on havaittu vähintään viisi kertaa, käytetään sen
   suoraan mitattua p10–mediaani–p90-ajoaikaa.
2. Jos aikatauluketju on uusi, sen ajoaika muodostetaan summaamalla peräkkäisten
   laiturivälien jakaumat.
3. Jos tulevan vuoron välilaitureita ei tunneta, käytetään päälaiturin ja
   kohdelaiturin kaikkien toistuvien historiallisten ketjujen muodostamaa
   mahdollista vaihteluväliä.

Täsmällistä vanhan lähtöajan tai aikataulukauden vastaavuutta ei vaadita.
Viikonpäivä, vuodenaika ja päivän osa vaikuttavat siihen, kuinka todennäköisiä
eri välilaituriketjut ovat, eivät yksittäisen laiturivälin perusajoaikaan.
Viikonpäiväluokat ovat ma, ti–to, pe, la ja su. Niitä tarkennetaan vuodenajan
(talvi, kevät–syksy, kesä) ja päivän osan (aamu, päivä, iltapäivä, ilta–yö)
mukaan silloin, kun havaintoja on riittävästi.

Joustava malli sisältää 509 vähintään kolmen havainnon laituriväliä
auditointiin, 430 vähintään viiden havainnon laituriväliä varsinaiseen malliin,
448 toistuvaa suoraan mitattua välilaituriketjua ja 142 yleistä
päälaituri–kohdelaituri-varahaarukkaa. Lisäksi aineistosta muodostui 650
kalenterikontekstia, joissa on vähintään yksi toistuva käyntiketju.

### Ajallinen takautuva testi

Malli testattiin opettamalla se vain ennen 13.7.2026 kerätystä aineistosta ja
ennustamalla viimeiset 90 päivää. Testijaksolla oli 5 917 matkaa ja 9 687
ensimmäistä kohdelaiturikäyntiä. Malli pystyi antamaan arvion 9 559 käynnille
eli 98,68 %:lle.

Valittu hierarkia käytti 8 862 kertaa samaa aiemmin havaittua ketjua, 375
kertaa laiturivälien summaa, 218 kertaa väljää kalenterikontekstia ja 104
kertaa kaikkien historiallisten ketjujen yleistä varahaarukkaa. Mediaanivirhe
oli 1,1 minuuttia, 90 % virheistä oli enintään 5,1 minuuttia, 96,42 % enintään
10 minuuttia ja 98,46 % enintään 20 minuuttia. P10–p90-haarukka sisälsi
toteutuneen ajan 81,25 %:ssa ennusteista, mikä vastaa hyvin nimellistä 80 %:n
haarukkaa.

Kun välilaituriketjua ei tunneta, väljän viikonpäivä–vuodenaika–päivänosa-
kontekstin mediaanivirhe oli 1,8 minuuttia ja haarukan mediaanileveys 11,1
minuuttia. Sen p10–p90-haarukka kattoi 80,96 % testihavainnoista. Kaikkien
historiallisten ketjujen konservatiivisen varahaarukan mediaanileveys oli 44,1
minuuttia ja se sisälsi toteuman 98,81 %:ssa tapauksista. Tyypillinen aika
perustuu edelleen toistuviin ketjuihin, mutta tämän viimeisen varatason
ulkorajoissa säilytetään myös yksittäiset korkean luottamuksen ketjut. Tämä
estää harvinaisen pitkän saaristokierroksen perusteettoman aliarvioinnin.

### Paraisten reitin meno- ja paluusuunta

Paraisten reitin ensimmäinen yleismalli yhdisti virheellisesti saman laiturin
meno- ja paluukäynnit. Reitti on lähes lineaarinen: Granvikista ulospäin
ajettaessa matkustajia jätetään saarille ja palatessa heitä poimitaan kyytiin.
Tilaamattomat laiturit ohitetaan, mutta varsinainen järjestys ei vaihtele
vapaasti. Esimerkiksi paluumatkan Björkholm-käynti voi olla vasta Pensarin tai
Kuggön jälkeen eikä kuvaa Granvikista Björkholmiin matkustavan saapumisaikaa.

Reitille lisättiin erillinen suuntamalli, jossa kaukaisin saavutettu laituri on
matkan kääntöpiste. Sitä edeltävät käynnit luokitellaan menoksi ja sitä seuraavat
paluuksi. Kaikki 2 611 korkean luottamuksen Paraisten matkaa voitiin luokitella
ilman suunnaltaan epäselvää matkaa.

Korjatussa mallissa Granvikista lähtevän menomatkan p10–mediaani–p90-ajat ovat:

| Laituri | Havaintoja | Ajoaika Granvikista |
| --- | ---: | ---: |
| Granholmen | 27 | 4,9–6,0–7,0 min |
| Heisala | 1 559 | 10,0–10,8–11,2 min |
| Björkholm | 544 | 10,1–18,0–22,0 min |
| Stenholm | 30 | 25,1–28,6–39,2 min |
| Aspholm | 137 | 26,0–27,9–33,5 min |
| Kuggö | 439 | 34,6–37,0–42,3 min |
| Pensar | 800 | 39,0–43,0–49,1 min |

Björkholmin kaksi tavallista menoaikaa syntyvät siitä, käydäänkö ensin
Heisalassa; 10–22 minuutin haarukka ei enää sisällä paluumatkan myöhäisiä
Björkholm-käyntejä. Paluusuunnan saarikohtainen aika lasketaan erikseen saman
Granvikista alkaneen kierroksen alusta. Nykyinen yleinen joustava malli on siis
Paraisten reitin kohdehaarukoiden osalta korvattava tällä suuntamallilla ennen
mahdollista sovelluskäyttöä.

### Käydäänkö laiturissa kerran vai mennen tullen?

Kaikista 16 383 täydellisestä korkean luottamuksen matkasta laskettiin
laiturikohtaisesti, käytiinkö samassa välilaiturissa kierroksen aikana kerran
vai vähintään kahdesti. Lisäksi tarkistettiin, palattiinko laiturista suoraan
edelliseen havaittuun laituriin (`A → B → A`) ja ajettiinko jokin havaittu
laituriväli saman matkan aikana molempiin suuntiin.

Tulokset eivät tue yhtä yhteistä mallia kaikille reiteille:

- **Paraisten reitti:** selvä meno–paluu-runko. Heisala käytiin kahdesti 95,
  Björkholm 31, Kuggö 46 ja Aspholm 11 täydellisellä kierroksella. Pensar on
  tavallinen kääntöpiste ja käydään samalla kierroksella vain kerran.
- **Rymättylän reitti:** vahva meno–paluu- ja haararakenne. Ruotsalainen käytiin
  kahdesti 75:llä niistä 112 kierroksesta, joilla siellä käytiin. Maisaari,
  Pakinainen ja Samsaari ovat usein kierroksen kääntöpisteitä ja niissä käytiin
  tavallisesti vain kerran.
- **Velkuan reitti:** sekamuoto. Rauhala käytiin kahdesti 268 kierroksella,
  Lailuoto 34 ja Talosmeri 36 kierroksella. Kettumaa, Tammisluoto ja Liettinen
  näkyvät tavallisesti kerran käytyinä haaroina tai kääntöpisteinä.
- **Nauvon pohjoinen reitti:** päätepisteiden välisen liikenteen ja lyhyiden
  edestakaisten vuorojen yhdistelmä. Maskinnamo käytiin kahdesti 32,
  Järvsor 10, Innamo 10 ja Seili 9 matkalla. Seili oli lisäksi 289 matkalla
  selvä `Nagu → Seili → Nagu` -kääntöpiste.
- **Nauvon eteläinen reitti:** useimmat laiturit käytiin vain kerran
  kierroksella. Lökholmissa oli kolme ja Kopparholmissa kolme kahden käynnin
  kierrosta; muissa saarissa toistuva käynti oli nolla tai yksi. Reitti sisältää
  sekä lyhyitä edestakaisia vuoroja että pidempiä rengas- tai haarakierroksia,
  joten sitä ei pidä käsitellä yhtenä lineaarisena reittinä.
- **Hiittisten reitti:** pääosin yksi käynti laituria ja matkaa kohti. Holma on
  poikkeus: kahdeksalla 36 Holmassa käyneestä matkasta siellä käytiin kahdesti.
  Örö, Örön yhteysaluslaituri ja Helsingholm näkyvät usein kääntöpisteinä.
- **Houtskarin reitti:** monen päätepisteen verkko, jossa laiturit käydään
  yleensä kerran. Åselholm käytiin kahdesti yhdeksällä matkalla. Kolko, Själö,
  Perkala ja PerkalaP toimivat usein lyhyen haaran kääntöpisteinä.
- **Korppoon reitti:** lähes kaikki välilaiturit käydään kerran. Aineistossa ei
  ole yhdellekään laiturille vähintään viittä kahden käynnin kierrosta. Useat
  laiturit toimivat vuorosta riippuen kääntöpisteinä.
- **Ahvenanmaan pohjoinen linja:** päätepisteiden välinen verkko. Enklingessä
  käytiin aina kerran ja se oli usein kääntöpiste. Lappo käytiin kahdesti 68 ja
  Asterholma 14 matkalla.
- **Ahvenanmaan eteläinen linja:** pääosin eri päätepisteiden välisiä matkoja.
  Kökar käytiin aina kerran ja usein kääntöpisteenä. Husö käytiin kahdesti 14 ja
  Kyrkogårdsö 18 matkalla, mutta yli 90 % niiden matkoista sisälsi vain yhden
  käynnin.
- **Utön reitti:** täydellisiä AIS-ketjuja oli tässä rajauksessa vain kaksi,
  joten rakennetta ei päätellä niistä. Julkaistu aikataulu vahvistaa
  pisteestä pisteeseen kulkevan järjestyksen Pärnäs–Nötö–Aspö–Jurmo–Utö ja
  erillisen paluuvuoron; välilaitureissa käydään kerran suuntaansa.

Tulos kertoo toteutuneesta liikenteestä, ei vain teoreettisesta
mahdollisuudesta. Esimerkiksi Paraisten reitin laituri voi rakenteellisesti olla
sekä meno- että paluukäynti, vaikka useimmilla kierroksilla kysyntää on vain
toiseen suuntaan ja laituri näkyy siksi vain kerran. Saapumisaikamallissa
laiturin suunta ratkaistaan reitti- ja laiturikohtaisesti, eikä pelkkä yhden
käynnin määrä riitä rengasreitin todisteeksi.

### Ensimmäinen käyntiroolimalli

Rymättylän, Velkuan sekä Nauvon pohjoisen ja eteläisen reitin 2 858 täydelle
korkean luottamuksen matkalle muodostettiin havaintokohtainen rakenneluokitus.
Se ei pakota koko reittiä yhteen tyyppiin, vaan erottaa päätepisteiden väliset
matkat, täsmälliset `A → B → A` -käännöt, samalla matkalla toistuvan laiturin
meno- ja paluukäynnit sekä vain kerran suljetulla matkalla havaitut käynnit.

| Reitti | Matkoja | Päätepisteestä toiseen | Yksinkertainen kääntö | Suljettu, toistuva laituri | Suljettu, vain yksittäisiä käyntejä |
| --- | ---: | ---: | ---: | ---: | ---: |
| Rymättylä | 271 | 0 | 138 (50,9 %) | 76 (28,0 %) | 57 (21,0 %) |
| Velkua | 1 739 | 379 (21,8 %) | 307 (17,7 %) | 305 (17,5 %) | 748 (43,0 %) |
| Nauvon pohjoinen | 729 | 391 (53,6 %) | 298 (40,9 %) | 17 (2,3 %) | 23 (3,2 %) |
| Nauvon eteläinen | 119 | 0 | 54 (45,4 %) | 6 (5,0 %) | 59 (49,6 %) |

Tulos tarkentaa reittien luonnetta olennaisesti:

- Rymättylällä puolet täydellisistä kierroksista oli yhden laiturin
  kääntövuoroja. Ruotsalainen sai 75 meno- ja 75 paluuroolia samalla
  kierroksella; Maisaari oli 93 ja Samsaari 32 kertaa selvä kääntöpaikka.
- Velkualla 379 matkaa kulki Teersalon ja Hakkenpään välillä. Suljetuilla
  kierroksilla Rauhala toistui 268, Talosmeri 36 ja Lailuoto 34 kertaa.
- Nauvon pohjoisella 391 matkaa oli Nauvon ja Lavarnin välisiä. Lisäksi 289
  matkaa oli täsmälleen `Nagu → Seili → Nagu`, joten Seiliä ei saa tulkita
  vain rengasreitin yksittäiseksi käynniksi.
- Nauvon eteläisellä 54 matkaa oli yhden laiturin kääntövuoroja ja 59 pidempiä
  suljettuja matkoja, joilla laiturit havaittiin kerran. Viimeksi mainittu
  tukee rengas- tai haarakierrosta mutta ei yksin todista kumpaa niistä ajettiin.

Luokitus on seuraavan ajoaikamallin syöte. Silloin päätepisteiden välisiä
matkoja ei sekoiteta suljettuihin kierroksiin, kääntövuoro saa oman haarukkansa
ja toistuvan laiturin meno- ja paluukäynnit erotetaan. Nykyinen sovellus ja sen
julkaistu data eivät käytä tätä kokeellista mallia.

Luokitus laajennettiin tämän jälkeen kaikille analyysissä mukana oleville
yhteysalusreiteille Paraisten erillistä lineaarista suuntamallia lukuun
ottamatta. Nauvon poikittainen reitti ei ole mukana AIS-mallissa, koska sen
alus Cheri ei lähetä AIS-seurantaa. Lopetettu reitti on Ahvenanmaan
poikittainen linja.

| Reitti | Täydellisiä matkoja | Päätepisteestä toiseen | Suljettuja matkoja |
| --- | ---: | ---: | ---: |
| Hiittinen | 329 | 222 | 107 |
| Houtskari | 762 | 512 | 250 |
| Korppoo | 486 | 258 | 228 |
| Ahvenanmaan pohjoinen | 6 466 | 4 089 | 2 377 |
| Ahvenanmaan eteläinen | 3 245 | 2 791 | 454 |
| Utö | 2 | 2 | 0 |

Ahvenanmaan linjoilla julkaistu aikataulu ratkaisee pysähdysjärjestyksen ja
ajat; AIS-aineistoa käytetään toteutuneiden ajoaikojen ja tilattujen poikkeamien
tarkistamiseen. Utön viimeisen vuoden täydellinen AIS-otos on liian pieni
rakenteen päättelemiseen, joten myös siellä kaksisuuntainen
Pärnäs–Nötö–Aspö–Jurmo–Utö-rakenne perustuu aikatauluun.

### Roolitietoiset ajoaikahaarukat

Rooli- ja päätepistejaon perusteella syntyi 517 vähintään viiden havainnon
täsmällistä käyntiketjuhaarukkaa ja 262 väljemmän tason auditointiryhmää.
Täsmällinen ryhmä pitää erillään lähtölaiturin, matkan päätepisteen,
matkarakenteen, laiturin roolin ja siihen asti toteutuneen pysähdysketjun.
Pitkiä laituritaukoja ei edelleenkään lasketa ajoaikaan.

Viimeisten 90 päivän ajallisessa takautuvassa testissä ennen testijaksoa
vähintään viisi kertaa nähty täsmällinen ketju antoi 7 168 ennustetta. Niiden
mediaanivirhe oli 1,1 minuuttia, p90-virhe 5,0 minuuttia ja 98,3 % ennusteista
oli enintään kymmenen minuutin päässä toteumasta. P10–p90-haarukka sisälsi
toteuman 80,4 %:ssa tapauksista, mikä vastaa hyvin haarukan nimellistä 80 %:n
kattavuutta.

Pelkkä sama reitti, päätepistepari, laituri ja käyntirooli ei riittänyt
tyypilliseksi ennusteeksi, jos täsmällistä ketjua ei ollut aiemmin nähty: sen
mediaanivirhe oli 18,6 minuuttia. Siksi väljä ryhmä säilytetään vain
konservatiivisena havaittuna min–max-haarukkana. Varsinainen arvio käyttää
täsmällistä ketjua tai aikaisemman joustavan mallin kalenterikontekstia.

### Husön ja Kyrkogårdsön yhteisvaikutus

Ahvenanmaan eteläisen linjan aikataulu ilmoittaa Husön poikkeaman viivästyttävän
seuraavia satamia noin 10 minuuttia ja Kyrkogårdsön noin 20 minuuttia. Mallissa
viiveet summataan: jos samalla vuorolla käydään molemmissa, myöhempien satamien
aikatauluun lisätään noin 30 minuuttia.

AIS-aineistosta löytyi vertailukelpoinen Sottunga–Kökar–Sottunga-aineisto:

| Poikkeamat | Matkoja | Ajoajan p10–mediaani–p90 | Mediaanin lisäys |
| --- | ---: | ---: | ---: |
| Ei kumpaakaan | 178 | 141,0–147,0–157,3 min | 0 min |
| Husö | 128 | 151,0–157,0–166,3 min | 10,0 min |
| Kyrkogårdsö | 96 | 154,5–159,0–172,0 min | 12,0 min |
| Molemmat | 50 | 165,1–169,5–180,2 min | 22,5 min |

Puhdas AIS-ajoaika ei ole sama suure kuin aikataulun ilmoittama myöhempien
satamien likimääräinen viive, mutta aineisto vahvistaa olennaisen asian:
molempien poikkeamien vaikutus kasautuu eikä toinen poikkeama korvaa toista.
Siksi aikataulun 10 + 20 minuutin summa on analyysin määräävä sääntö.

Kolmen havainnon auditointirajalla välilaituriketjun sisäisistä p10–p90-
haarukoista 93,3 % on enintään 10 minuuttia ja 99,6 % enintään 20 minuuttia.
Varsinaiseen sovellusmalliin hyväksytään vähintään viisi saman lähtövuoron ja
ketjun havaintoa. Näin saadaan 1 519 kohdekohtaista lähtövuoroarviota. Niistä
98,0 %:ssa kaikkien hyväksyttyjen ketjujen muodostama mahdollinen haarukka on
enintään 20 minuuttia ja 99,1 %:ssa enintään 30 minuuttia leveä.

2 351 harvemmin havaittua kohde–lähtövuoro-yhdistelmää säilytetään
auditointidatassa, mutta niitä ei viedä sovelluksen ensisijaiseen ennusteeseen.
Kolmen tai neljän havainnon ketju merkitään rajalliseksi aineistoksi eikä se
venytä luotettavampien ketjujen vaihteluväliä.

### Leveiden haarukoiden tarkistus

Vähintään viiden havainnon aineistoon jäi 13 yli 30 minuutin haarukkaa.
Kahdessatoista syy on selvä ja toistuva vaihtoehtoinen välilaituriketju:
esimerkiksi Sottunga–Husö kestää suoraan noin 29–32 minuuttia ja Kökarin kautta
119–123 minuuttia. Näitä eroja ei suodateta pois, koska juuri ne kuvaavat
tilattavien välilaiturien vaikutusta.

| Reitti | Lähtö | Kohde | Mahdollinen ajoaika | Tulkinta |
| --- | --- | --- | ---: | --- |
| Eteläinen linja | Sottunga to 10.30 | Husö | 29–123 min | suoraan tai Kökarin kautta |
| Eteläinen linja | Sottunga pe 13.15 | Kyrkogårdsö | 44–119 min | suoraan tai Kökarin kautta |
| Utön reitti | Pärnäs la 13.30 | Jurmo | 149–213 min | yksi poikkeava ajo saman ketjun sisällä |
| Velkuan reitti | Teersalo ke 13.30 | Lailuoto | 13–62 min | kolme eri välilaituriketjua |
| Nauvon pohjoinen | Nagu pe 18.45 | Innamo | 47–81 min | suoraan tai Seilin kautta |
| Houtskarin reitti | Kannvik ma 17.00 | Åselholm | 44–77 min | suoraan tai Kolkon kautta |
| Eteläinen linja | Galtby su 15.15 | Sottunga | 209–242 min | neljä eri välilaituriketjua |
| Nauvon pohjoinen | Lavarn ti 15.45 | Nagu | 88–120 min | kolme eri välilaituriketjua |
| Eteläinen linja | Sottunga su 10.30 | Galtby | 208–240 min | neljä eri välilaituriketjua |
| Nauvon pohjoinen | Lavarn pe 15.45 | Maskinnamo | 20–51 min | suoraan tai Åvensorin kautta |
| Nauvon pohjoinen | Lavarn to 07.45 | Maskinnamo | 19–50 min | suoraan tai Åvensorin kautta |
| Nauvon pohjoinen | Nagu pe 12.45 | Maskinnamo | 84–115 min | Seilin kautta tai ilman Seiliä |
| Nauvon pohjoinen | Nagu pe 12.45 | Järvsor | 65–95 min | Seilin kautta tai ilman Seiliä |

Utön poikkeus syntyy ketjusta Pärnäs–Nötö–Jurmo. Neljä ajoa kestää noin
147–168 minuuttia ja yksi eri aluksella 243 minuuttia. Siinä ei ole pitkää
laituriin odottamista. Havainto säilytetään ja ryhmä merkitään
`wide_within_variant`-tilaan, mutta 154 minuutin mediaani kuvaa tavallista ajoa
paremmin kuin haarukan yläraja.

## Tuotokset

Väliaikaiset analyysitulokset ovat hakemistoissa:

- `/tmp/ais-connection-review-current-60d`
- `/tmp/ais-pier-calibration-current-60d`
- `/tmp/ais-connection-voyages-calibrated.sqlite`
- `/tmp/ais-service-journeys-calibrated`
- `/tmp/ais-arrival-prediction-model`
- `/tmp/ais-call-roles`
- `/tmp/ais-role-aware-arrivals`
- `/tmp/ais-role-aware-backtest`
- `/tmp/ais-aland-detours`

Käyntiketjut ovat tiedostossa `journeys.csv`, toistuvat reittimallit
`journey-patterns.csv` ja lähtöhetkestä lasketut kohdelaiturikohtaiset
aikahaarukat `arrival-windows.csv`. Suunnittaiset laituriväliajat ovat
`leg-windows.csv`:ssä ja laiturikalibroinnin tarkistuslista
`pier-calibration.csv`:ssä.
Lähtöaikaan sidottu malli on `arrival-prediction-model.json`:ssa. Sen
taulukkomuotoiset tarkistustiedostot ovat `departure-slots.csv`,
`destination-windows.csv`, `sequence-variant-windows.csv` ja
`wide-destination-windows.csv`.
Ensimmäisen, lähtöaikaan sidotun kokeilun 628 kilotavun tiedosto on saaristodatan
`future/structured-routing/ais-arrival-estimates.json`. Se sisältää 11 reittiä,
903 toistuvaa lähtövuoroa ja 1 519 kohdekohtaista ajoaika-arviota. Julkaistu
aikataulu on aina ensisijainen ja AIS-arvio neuvoa-antava.

Mallissa on lisäksi 448 vähintään viiteen havaintoon perustuvaa, lähtöajasta
riippumatonta reitti–välilaituriketjuarviota. Niitä käytetään uuden
aikataulukauden varatasona vain, jos ketju sopii julkaistun vuoron
pysähdysjärjestykseen. Ensimmäisessä liitoskokeessa, ennen kaikkien reittien
matkarakenteen normalisointia, saatiin vain kuusi arviota. Jäljempänä kuvattu
uusi liitos korvaa tämän välituloksen.

Aikataulusta riippumaton kokeellinen malli on samassa hakemistossa tiedostossa
`ais-arrival-estimates-flexible.json`. Se ei ole sovelluksen käytössä eikä
muuta julkaistua dataa. Malli sisältää erikseen laiturivälit, suoraan havaitut
ketjut, päälaituri–kohdelaituri-varahaarukat sekä väljien kalenteriluokkien
käyntiketjujen yleisyydet.

Käyntiroolit ja niiden perusteella erotellut ajoajat ovat kokeellisissa
`ais-call-role-model.json`- ja `ais-role-aware-arrival-estimates.json`-
tiedostoissa. Ahvenanmaan poikkeamavertailu on tiedostossa
`ais-aland-detour-validation.json`. Mikään näistä ei ole nykyisen sovelluksen
käytössä.

### Rakenteisten yhteysalusmatkojen AIS-liitos

Säännölliset viikkoaikataulut on nyt normalisoitu erilliseen kokeelliseen
aineistoon kaikilta 13 tarkastellulta yhteysalusreitiltä. Aineistossa on 241
matkamallia ja 1 406 laiturikäyntiä. Korppoon ja Utön aiemmat kahden matkan
osaluonnokset korvattiin lähdetaulukoista tulkituilla koko viikkoaikatauluilla.
Hiittisten Jurmon, Korppoon ja Utön pyhäpäiväsäännöt on normalisoitu
päiväkohtaisiksi korvaaviksi matkoiksi tai liikenteettömiksi päiviksi.

Aikataulun sisäisistä käynneistä 646:lta puuttuu julkaistu kellonaika. Näistä
461 sai vähintään viisi kertaa havaitun, julkaistun pysähdysjärjestyksen kanssa
yhteensopivan AIS-ketjun tyypillisen ajan ja vaihteluvälin. Lisäksi 90 käynnille
saatiin väljemmästä rooliryhmästä vain konservatiivinen havaittu min–max-
haarukka. Väljän ryhmän mediaania ei käytetä. Jonkinlainen historiallinen
ajoaikatieto kattaa siten 85,3 % kellonajattomista käynneistä. Jos Nauvon
poikittaisen AIS:ttömyys ja lähtöajattomat vuorot jätetään pois, kattavuus on
96,2 %. Pyhäpäivämatkoihin kopioitiin 139 niiden viikkopohjissa olevaa
välilaituriarviota ja 26 päättymisarviota, yhteensä 165 historiallista
ajoitustietoa.

Reittikohtaisesti täsmällinen tai konservatiivinen arvio kattaa Paraisten,
Velkuan ja Nauvon pohjoisen kellonajattomat käynnit kokonaan, Rymättylän 99 %,
Nauvon eteläisen 97 %, Houtskarin 94 %, Utön 90 %, Korppoon 81 %, Hiittisten
Jurmon 74 % ja Hiittisten itäisen 44 %. Nauvon poikittainen pidetään mukana
rakenteisessa aikataulussa, mutta sen 58 kellonajatonta käyntiä jää ilman
AIS-arviota, koska Cheriltä ei saada AIS-dataa. Lopetettu reitti on
Ahvenanmaan poikittainen. Ahvenanmaan pohjoisella ja eteläisellä linjalla
julkaistu aikataulu antaa jo kaikki ajat ja on aina AIS:ää määräävämpi.

Päälaiturimallia täydentävä ankkurimalli voi aloittaa laskennan myös muusta
julkaistun lähtöajan saaneesta laiturista, kuten Själöstä tai Åvensorista. Se
käyttää vain vähintään viisi kertaa havaittuja täsmällisiä ketjuja, katkaisee
ketjun yli 30 minuutin taukoon ja jättää epävarmat lähimmän ohituksen
ajoitukset pois. Matkan päätepisteelle malli laskee lisäksi seinäkelloajan,
jossa saman ketjun lyhyet välilaiturikäynnit ovat mukana. Näin julkaistun
päättymisajan rinnalla voidaan näyttää erillinen historiallinen toteumahaarukka
ja poikkeama aikataulusta. Viimeisten 90 päivän ajallisessa takautuvassa testissä mallilla
oli 36 629 ennustetta: mediaanivirhe 1,12 minuuttia, p90-virhe 5,83 minuuttia,
96,4 % virheistä enintään 10 minuuttia ja p10–p90-haarukan kattavuus 80,1 %.

Tuotokset ovat saaristodata-repositorion kokeellisessa hakemistossa:

- `structured-connection-timetables.json`
- `connection-trip-normalization-report.json`
- `structured-connection-timetables-with-ais.json`
- `connection-ais-estimate-link-report.json`
- `ais-anchor-path-estimates.json`
- `ais-anchor-path-backtest.json`
- `connection-arrival-prediction-catalog.json`
- `connection-arrival-prediction-catalog-report.json`

Nykyistä sovellusta tai sen julkaistua dataa ei ole muutettu.

Kokeellinen hakuluettelo sisältää 241 säännöllistä matkamallia, 60
pyhäpäivämatkaa ja 13 liikenteetöntä poikkeuspäivää. Matkojen sisäisissä
käynneissä on 627 julkaistua kellonaikaa, 575 täsmällistä historiallista
arviota, 115 konservatiivista historiallista haarukkaa ja 113 käyntiä ilman
ajoitusta. Historiallinen arvio tallennetaan lähtöhetkeen lisättävänä
minuuttimääränä, joten sitä voidaan käyttää aikataulun lähtöajan lisäksi myös
toteutuneen lähtöajan kanssa.

Matkan julkaistua päättymisaikaa ei korvata. Sen rinnalla on 206
matkamallissa historiallinen päättymisarvio: 170:ssä tyypillinen aika ja
vaihteluväli sekä 36:ssa vain konservatiivinen vaihteluväli. Arvio sisältää
normaalit lyhyet välilaiturikäynnit, mutta yli 30 minuutin tauko katkaisee
ketjun.
