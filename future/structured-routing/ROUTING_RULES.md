# Reitityssäännöt

Tämä tiedosto kuvaa prototyypin **nykyisen toteutuksen** säännöt. Se on
reitityskäyttäytymisen koontilähde: yksityiskohdat toteutetaan edelleen
Python-koodissa, rakennettavassa reititysgraafissa ja käyttöliittymässä.

Säännöt on erotettu hakutulokseen vaikuttavista toimintasäännöistä,
hakutilaa rajaavista suojarajoista ja vielä avoimista asioista. Jos tämä
tiedosto ja koodi ovat ristiriidassa, ristiriita on korjattava eikä sitä pidä
tulkita uudeksi säännöksi.

## 1. Haun lähtötiedot

- Tuetut kulkutavat ovat auto, moottoripyörä ja polkupyörä.
- Auto ja moottoripyörä käyttävät sisäisillä tieosuuksilla samaa `auto`-aikaa;
  ulkoisessa Valhalla-haussa moottoripyörällä on oma profiili.
- Tieosuutta saa käyttää vain, jos valitun kulkutavan tila on `ok`.
- Lauttayhteyttä saa käyttää vain, jos sen kulkutapa-arvo on `allowed`,
  `allowed_subject_to_operator_conditions` tai
  `booking_validation_required`.
- Automaattisessa haussa ohitetaan graafin reunat, joilla
  `enabledForAutomaticRouting` on epätosi.
- Aikaprofiilit ovat `typical` ja `conservative`. Aikataulun tai AIS-arvion
  valinta tehdään graafia rakennettaessa ja aikatauluinstansseja laskettaessa.
- Tieajat pyöristetään lähimpään täyteen minuuttiin ja vähintään yhteen
  minuuttiin, koska julkaistut lautta-ajatkin ovat minuutin tarkkuudella.

## 2. Osoitteet, paikannimet ja tiealueet

- Käyttäjä valitsee yksikäsitteisen osoite- tai paikannimiosuman jo
  kirjoittaessaan. URL:ssa säilytetään myös valitun osuman tunniste, jotta
  sama paikka voidaan palauttaa ilman uutta valintaa.
- Tunnettu laiturin nimi tai tunniste voidaan ratkaista suoraan ilman
  geokoodausta, jos osuma on yksikäsitteinen. Tavallinen laiturin nimi
  hyväksytään suoraan vain singleton-tiealueella; muu laituri vaatii
  lauttarantaa ilmaisevan täsmennyksen.
- Paljas kunnan nimi pyritään kohdistamaan keskustaajamaan tai kunnan
  hallinnolliseen keskuspisteeseen, ei alueen geometriseen keskipisteeseen.
- Osoite-ehdotuksista poistetaan luonnonkohteet sekä historialliset rajat
  (`boundary` + `historic`). Hallinnollisia rajoja ei käytetä tavallisina
  reittipisteinä muuten kuin kunnan keskuksen ratkaisemiseen.
- Täsmälliset nimiosumat asetetaan osittaisten sana-alkuosumien edelle.
  Osittainen haku hyväksyy sanan alun, mutta ei vapaata sumeaa osumaa.
- Ehdotusten duplikaatit poistetaan sekä tunnisteen että saman kuvaustekstin
  perusteella.
- Geokoodattu piste luokitellaan tiealueeseen Valhallan reitillä:
  - jos pisteestä ei käytetä lauttaa, se kuuluu saavutetun ankkurin
    tiealueeseen;
  - muuten ensimmäinen tunnistettu lauttaylitys määrää, kummalla tiealueella
    piste on;
  - tuntemattomat lauttaylitykset ennen ensimmäistä tunnistettua ylitystä
    eivät muuta luokitusta.
- Kun tiealue on tiedossa, lähtöpiste yhdistetään tavallisesti ilman lauttoja
  kaikkiin sen tiealueen graafilaitureihin. Määränpää yhdistetään vastaavasti
  kaikista alueen laitureista. Saman tiealueen pisteiden välille lisätään myös
  suora tieyhteys.
- Valhallan matriisi on ensisijainen. Jos matriisi ei onnistu, kaikki alueen
  laiturit kokeillaan yksittäisillä hauilla; ehdokkaita ei rajata vain
  lähimpiin.
- Ulkoisilla tieosuuksilla Valhallalta kielletään lähtökohtaisesti lautat,
  koska saariston tunnetut lauttavalinnat kuuluvat omaan graafiin.
- Jos osoitteen tiealueluokitus osoittaa, että pisteestä pääsee tiealueelle
  vain graafille tuntemattomalla paikallislautalla, ulkoinen alku- tai
  loppuosuus saa käyttää sitä. Jokainen tällainen Valhalla-reitti
  luokitellaan erikseen ja hylätään heti, jos jokin sen lauttanousu osuu oman
  graafin tunnettuun laituriin. Ensimmäisen tunnetun nousun laituri kokeillaan
  ensin, mutta poikkeustapauksessa muutkin saman tiealueen laiturit tutkitaan,
  koska laiturin tiekoordinaatti voi korreloitua lautan väärälle puolelle.
- Polkupyörän ulkoinen alku- tai loppuosuus hylätään, jos se ylittää 150 km.
- Laiturilla voi olla erillinen `routingCoordinates`, jota käytetään
  tieverkolla. Muuten käytetään laiturin varsinaista koordinaattia.

## 3. Paikallisten lossien hakurajaus

- Lyhyttä paikallista lossia ei tutkita jokaisen kaukoreitin mahdollisena
  kiertotienä, jos kumpikaan päätepiste ei kuulu sen paikalliseen
  valuma-alueeseen.
- Kokkilan lossin paikallinen puoli on Angelniemi. Lossi otetaan mukaan, jos
  lähtö tai määränpää on Angelniemessä tai tieaikavertailu osoittaa pisteen
  kuuluvan Angelniemen puolelle.
- Kokkila itse on lossin mantereen puoli eikä yksinään laukaise paikallisen
  lossin mukaanottoa.
- Rajaus tehdään kulkutapakohtaisilla tieajoilla. Se on hakutilan optimointi,
  jonka tarkoitus on poistaa vain paluuseen johtavat epäolennaiset kiertotiet.

## 4. Aikataulujen voimassaolo

- Vuoro on käytettävissä vain, jos hakupäivä kuuluu sen voimassaolojaksoon ja
  viikonpäiväkuvio sallii liikenteen.
- Yksittäinen `operatingDate` ohittaa viikkokuvion kyseisen vuoron osalta.
- Reitin normalisoidut pyhäpäivät poistavat tavallisen liikenteen.
- Pyhäpäiväpoikkeus voi poistaa liikenteen tai määrätä käyttämään toisen
  viikonpäivän aikataulua.
- Kausittain suljettu pysähdys ei ole käytettävissä sulkujakson aikana.
- Yön yli jatkuva saatavuusikkuna kuuluu päivään, jona ikkuna alkaa.
- Tarvittaessa tai jatkuvasti liikennöivän lossin tauot siirtävät aikaisimman
  mahdollisen lähdön tauon loppuun.

## 5. Ensimmäinen lautta ja lähtöajan laskenta

- Käyttäjän antama aika on **aikaisintaan lähtö**, ei pakotettu lähtöhetki.
- Reitti ajoitetaan taaksepäin ensimmäisestä aikataululautasta niin, että
  turhaa odotusta lähtöpisteessä vältetään.
- Ensimmäiselle aikataululautalle on ehdittävä viimeistään julkaistun
  lastausvalmiusajan alkuun. Tätä ei tarjota käyttäjän hyväksyttäväksi
  vaihtoriskiksi.
- Ensimmäistä lauttaa edeltävään kokonaisajoaikaan lisätään yleinen varoaika:
  - alle 60 minuutin ajo: 5 minuuttia;
  - vähintään 60 mutta alle 120 minuutin ajo: 10 minuuttia;
  - vähintään 120 minuutin ajo: 15 minuuttia.
- Tämä varoaika lisätään lautan mahdolliseen julkaistuun
  lastausvalmiusaikaan.
- Jos ennen ensimmäistä aikataululauttaa on tieosuuksia tai jatkuvia losseja,
  koko alkuosa siirtyy valitun lautan mukana. Lähtöä ei siirretä käyttäjän
  aikaisintaan-aikaa edemmäksi menneisyyteen.
- Ensimmäistä käyttökelpoista lauttaa etsitään yhden kokonaisen
  seitsemänpäiväisen aikataulukierron ajalta. Ennen ensimmäistä lauttaa
  odotettu aika ei kuulu 12 tunnin matkaketjurajaan.

## 6. Jatkuvasti ja tarvittaessa liikennöivät lossit

- Jatkuva tai tarvittaessa liikennöivä lossi on reititettävissä vain, jos sen
  ylitysaika tunnetaan.
- Lähtö on aikaisin hetki, jolloin käyttäjä on valmis ja lossi on
  saatavuusikkunassa eikä tauolla.
- Kun lossille saavutaan tieosuudelta, tieajan päälle lisätään aina viisi
  minuuttia. Se esitetään ylimääräisenä aikana.
- Nykyinen viisi minuuttia on johdonmukainen suunnitteluvara, ei vielä malli
  todellisesta kutsuviiveestä, jonosta tai ylitysajan vaihtelusta.
- Tarvittaessa-liikennöinnin saatavuus näytetään kaaviossa, mutta sitä ei voi
  valita yksittäisenä aikatauluvuorona.

## 7. Vaihdot ja riskiluokat

- Ensimmäisen käytetyn lautan jälkeen seuraavalle lautalle riittää reitin
  löytymiseksi saapuminen viimeistään lähtöhetkellä. Lastausvalmius vaikuttaa
  tällöin riskiluokkaan, ei kelpoisuuteen.
- Raaka vaihtoaika on edellisen osuuden saapumisesta seuraavan lautan lähtöön.
  Tehokas marginaali on raaka vaihtoaika miinus vaadittu lastausvalmius.
- Riskiluokat ovat:
  - tehokas marginaali alle 0 min: `below_required_readiness`, saapuminen
    lastausvalmiuden jälkeen;
  - 0 min: `very_tight`;
  - 1–4 min: `tight`;
  - 5–29 min: `normal`;
  - vähintään 30 min: `relaxed`.
- Lastausvalmius voi olla reittikohtainen, lähtölaiturikohtainen ja
  kulkutapakohtainen.
- Julkaistu tieyhteys tunnistetaan vain, jos syöttövuoro, tieosuus,
  jatkoreitti ja yhteyden enimmäisaika vastaavat rakenteista
  yhteysmäärittelyä.
- Julkaistun yhteyden riskiä ei näytetä normaalia huonompana. Selosteessa
  säilytetään tieto siitä, onko yhteys taattu vai aikatauluun merkitty mutta
  ei taattu.
- Samassa satamassa saman operaattorin aikataululautasta toiseen tehtävä
  suora vaihto käsitellään suunniteltuna yhteytenä. Lastausvalmiudesta
  tinkiminen ei silloin huononna reitin laatua normaalia heikommaksi, vaikka
  yhteys ei olisi taattu.
- Saman aluksen saman matkakuvion peräkkäisiä osuuksia ei tulkita vaihdoksi;
  graafin suora osuus väliasemien yli edustaa aluksessa pysymistä.

## 8. Varaus-, kutsu- ja välipysähdyssäännöt

- Reittiä ei hylätä vain siksi, että varaus vaaditaan. Varausvaatimus,
  suositus, kanava, yhteystiedot ja määräaika liitetään lauttaosuuteen.
- Varausmääräaika voidaan laskea samalle päivälle, edelliselle
  liikennöintipäivälle, lähtöön suhteutettuna tai arvioituun
  välipysähdyssaapumiseen suhteutettuna.
- Kutsu- ja varauspysähdykset säilytetään reitillä ehtoineen. Kausittain
  suljetut välipysähdykset poistetaan.
- Välipysähdys on pakollinen, ellei sen ehto nimenomaan tarkoita varausta,
  tarvittaessa käyntiä, erillistä kutsua tai muuta ehtoa.
- Julkaistu tarkka aika tai aikaväli välitetään käyttöliittymälle; tuntematonta
  aikaa ei esitetä täsmällisenä.

## 9. Polun kelpoisuus ja hakutilan rajat

- Solmussa ei saa käydä uudelleen saman polun aikana, paitsi että määränpää
  saa päättää polun. Tämä tekee poluista yksinkertaisia ja estää silmukat.
- Kahta peräkkäistä tieosuutta ei käytetä, koska tiekomponenttien välille on
  rakennettu suorat reunat.
- Hausta poistetaan kyselykohtaisesti umpikujahaara, josta määränpäähän pääsee
  vain palaamalla saman lähtösolmun kautta.
- Kun ensimmäinen lautta tai lossi on käytetty, viimeiselle laiturille on
  saavuttava 12 tunnissa ensimmäisen lautan lähdöstä.
- Viimeinen tieosuus saa päättyä 12 tunnin rajan jälkeen. Näin raja koskee
  saariston lauttaketjua eikä pitkää loppuajoa.
- Osoitehaussa sallitaan enintään 21 osuutta: enintään 19 lauttaväliä sekä
  alku- ja loppuajo. Sisäisen yleishaun oletusraja on 12 osuutta.
- Hakutila säilyttää eri riskiluokat, viimeisimmät lauttatunnisteet, tiedon
  ensimmäisen lautan käytöstä ja ensimmäisen lautan lähtöajan, jotta aidosti
  erilaiset jatkot eivät romahda samaksi tilaksi.
- Yhdessä solmu-, tunti-, riski- ja reittitilassa säilytetään enintään 20
  etikettiä. Ehdokaspolkujen yläraja on 1000.
- A*-alaraja käyttää tie- ja tunnettuja ylitysaikoja mutta ei odotusaikaa,
  joten se ei saa yliarvioida jäljellä olevaa vähimmäisaikaa.
- Solmun vähimmäislegimäärä määränpäähän lasketaan etukäteen. Haara katkaistaan,
  jos jäljellä oleva legiraja ei voi enää riittää.
- Usein liikennöivien aikataululossien yksittäisiä lähtöjä voidaan tiivistää
  varsinaisessa ehdokashaussa, mutta päätösgraafia varten kaikki saavutettavat
  valittavat lähdöt säilytetään.

## 10. Ehdokkaiden muodostaminen ja myöhemmät hyödylliset lähdöt

- Perushaku löytää aikaisimpia saapumisia usean etiketin Pareto-haulla.
- Myöhempiä hyödyllisiä lähtöjä ei etsitä kiinteällä aika-askeleella. Uusi
  haku aloitetaan seuraavasta hetkestä, jolloin saavutettava aikatauluvuoro
  menetetään tai vaihtoriskin luokka vaihtuu.
- Sama täsmällinen lauttaketju yksilöidään reitin, matkakuvion,
  lähtöajan sekä lähtö- ja määräpaikan avulla. Duplikaateista säilytetään
  myöhemmin lähtöpisteestä lähtevä.
- Kun ensimmäinen perille pääsevä päivä löytyy, saman päivän hyödylliset
  vaihtoehdot käsitellään loppuun. Myöhempien päivien vastaavia vaihtoehtoja
  ei palauteta.

## 11. Dominointi, järjestys ja reittivaihtoehtojen monipuolisuus

- Eri kaupallisten operaattorien ketjut eivät dominoi toisiaan. Finnlines-,
  Tallink Silja- ja Viking Line -vaihtoehto voidaan siis säilyttää, vaikka
  toinen olisi pelkkien aikojen perusteella parempi.
- Muuten A dominoi B:tä, jos A lähtee aikaisintaan yhtä myöhään, saapuu
  viimeistään yhtä aikaisin ja sen pahin riski ei ole huonompi sekä vähintään
  yksi ominaisuus on aidosti parempi.
- Kun reitin muoto ja saapumisaika ovat samat ja molemmat riskit ovat enintään
  normaaleja, myöhempi hyödyllinen syöttö säilytetään. Väljä ei siis itsessään
  voita normaalia, jos se vain lähettää matkustajan aiemmin odottamaan.
- Pitkä kierto voidaan poistaa, jos se käyttää samaa fyysistä lauttavuoroa,
  lähtee aikaisemmin tai samaan aikaan, saapuu myöhemmin, ei ole riskiltään
  normaalia parempi ja käyttää vähintään yhtä monta lauttaa.
- Tulokset ryhmitellään viimeisen lauttapalvelun mukaan. Ryhmästä palautetaan
  oletuksena enintään kolme vaihtoehtoa, ensin yksi kustakin riskiluokasta ja
  sitten parhaat jäljelle jäävät.
- Lopullinen järjestys on saapumisaika ja sen jälkeen suositeltu lähtöaika.
- Palvelun oletusraja on 12 tulosta; käyttöliittymä pyytää enintään 16.
- Käyttöliittymä yhdistää saman reitinmuodon duplikaatit ja valitsee niistä
  tavallisesti aikaisimmin saapuvan, saman saapumisen tapauksessa myöhemmin
  lähtevän.
- Käyttöliittymä voi lisäksi piilottaa vaihtoehdon, joka lähtee kaikista
  aikaisimpana, saapuu kaikista viimeisimpänä, maksaa enemmän ja jonka riski
  ei ole parempi kuin toisella reitinmuodolla.
- Ahvenanmaan kauttakulkumaksu merkitään vain, jos ketjussa on kokonainen
  määritelty porttipari. Pelkkä yhden maksullisen lauttaosuuden tunniste ei
  riitä.

## 12. Päätösgraafi ja käyttäjän lauttavalinnat

- Päätösgraafi rakennetaan kaikista löytyneistä käyttökelpoisista ehdokkaista
  ennen lopullista dominointia ja tulosrajausta.
- Solmu tarkoittaa paikkaa tiettynä ajanhetkenä; yhteys on tie-, odotus- tai
  lauttaosuus kahden solmun välillä.
- Samat paikka–aika-solmut ja identtiset jatko-osuudet jaetaan ehdokkaiden
  kesken.
- Täsmällisen lauttavuoron vaihtovaihtoehdoista säilytetään kustakin
  riskiluokasta viimeisin mahdollinen saapuminen lähtölaituriin.
- Jos toinen ehdokas saapuu samaan lähtösatamaan myöhemmin mutta ennen saman
  lautan lähtöä, sama lauttavuoro liitetään myös tähän tilaan ja sen
  vaihtoriski lasketaan uudelleen. Tämä on yleinen sääntö, ei tietyn
  Nauvo–Korppoo-yhdistelmän poikkeus.
- Ensimmäisen lautan lastausvalmiudesta ei muodosteta valittavaa
  riskivaihtoehtoa.
- Valittu pääreittivaihtoehto muodostaa käyttöliittymässä pehmeän
  reittikäytävän. Lauttavalinta suosii samaa reitinmuotoa ja samoja reittejä,
  mutta paikallinen aliketju saa muuttua, jos valittu vuoro sitä vaatii eikä
  muutos vastaa kokonaan toista pääreittivaihtoehtoa.
- Toiseen pääreittivaihtoehtoon täsmälleen johtavia lauttavuoroja ei näytetä
  nykyisen vaihtoehdon sisäisinä valintoina.
- Automaattisesti valitun vuoron napsautus lukitsee saman vuoron eikä saa
  yksinään muuttaa matkaketjua.
- Kaikkien lukittujen vuorojen on mahduttava samaan alku–loppupolkuun. Jos
  uusi valinta estyy aiemman lukituksen takia, uusi valinta perutaan ja
  estävä rivi sekä lukittu vuoro välähtävät kerran.
- Lukituksen poistamisen jälkeen ketju valitaan jälleen automaattisesti.
- Lauttavalinnan jälkeen sitä edeltävien tieosuuksien ajat, odotukset,
  lähtöaika ja seuraavat yhteydet lasketaan valittuun vuoroon sopiviksi.

## 13. Nykyiset suojarajat ja toteutustekniset valinnat

Nämä eivät ole matkailijalle tarkoitettuja laatumääritelmiä. Niiden muuttaminen
voi kuitenkin vaikuttaa löydettyihin tuloksiin, joten ne testataan.

- Ensimmäisen lautan hakuikkuna: 7 päivää.
- Lauttaketjun enimmäiskesto ensimmäisestä lautasta viimeiselle laiturille:
  12 tuntia.
- Osoitehaun legiraja: 21; sisäisen haun oletus: 12.
- Enimmäisehdokkaat: 1000.
- Enimmäisetiketit samassa solmu–tunti–riskitilassa: 20.
- Enimmäistulokset viimeistä lauttapalvelua kohti: 3.
- Päätösgraafissa valittavat tiheät lossivuorot säilytetään erillisinä, vaikka
  tavallinen tuloshaku saa yhdistää niitä.
- Onnistuneet geokoodaus-, Valhalla- ja reititysvastaukset voidaan säilyttää
  30 päivän SQLite-välimuistissa. Reititysdatan sisältötiiviste kuuluu valmiin
  vastauksen avaimeen.

## 14. Tunnetut avoimet asiat

- Jatkuvien ja kutsusta ajavien lossien todellinen kutsuviive, jono,
  kapasiteettiriski ja vaihteleva ylitysaika eivät ole vielä mallinnettuja;
  käytössä on viiden minuutin suunnitteluvara ja kiinteä ylitysaika.
- Kaikilla laitureilla ei vielä ole erillistä tieverkon reittipistettä.
- Erikoiset pyhäpäivä-, parillisuus- ja taukosäännöt vaativat edelleen
  aineistokohtaista laajentamista, jos niitä ei ole normalisoitu tavallisiksi
  voimassaolo- ja saatavuusjaksoiksi.
- 20 etiketin ja 1000 ehdokkaan rajat ovat käytännön suojia. Testien tulee
  varmistaa, etteivät ne pudota tunnettuja pitkiä saaristoreittejä.

## 15. Toteutuksen lähteet

- `scripts/route_itineraries.py`: monivaihtoehtohaku, riskit, dominointi,
  päätösgraafi ja hakurajat.
- `scripts/route_itinerary.py`: kalenteri, yksittäiset vuorot,
  lastausvalmius, varaus- ja pysähdysehdot.
- `scripts/query_address_routes.py`: osoitteiden liittäminen tiealueisiin ja
  osoitehaun 21 osuuden raja.
- `scripts/external_routing.py`: geokoodaus, ehdotukset, tiealueluokitus ja
  ulkoinen Valhalla-reititys.
- `scripts/build_routing_graph.py`: graafin tie-, aikataulu- ja
  jatkuvien lossien reunat.
- `service/route-preview.html`: pääreittivaihtoehtojen yhdistäminen,
  pehmeä reittikäytävä ja lukittujen vuorojen yhteensopivuus.
- `tests/test_fast_route_search.py`, `tests/test_address_routing.py`,
  `tests/test_routing_service.py` ja `tests/test_external_routing.py`:
  sääntöjen regressiotestit.
