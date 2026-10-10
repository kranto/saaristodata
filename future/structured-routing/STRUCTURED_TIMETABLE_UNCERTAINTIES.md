# Rakenteellisten aikataulujen tarkistuslista

Tilanne 10.10.2026. Lista koskee koneellisesti poimittuja, vielä
reitityskäyttöön hyväksymättömiä PDF-aikatauluja. Alkuperäisen taulukon solut ja
sivuteksti on tallennettu, joten alla olevien kysymysten ratkaiseminen ei vaadi
PDF:n tekstin kopioimista uudelleen.

## Yhteiset epävarmuudet

- Finferriesin varsinaisilla monisatamaisilla yhteysalusreiteillä kaikki matkat
  käsitellään varattavina yhteisessä varauspalvelussa. `y` ei säätele matkan
  varausvelvollisuutta, vaan erillistä tilattavaa laiturikäyntiä; `x` on
  tarvittaessa tehtävä käynti ilman erillistä tilausta. Point-to-point-
  maantielauttoihin tätä oletusta ei sovelleta.
  Hypoteesina `y` esiintyy jokaisella tilattavalla välikäynnillä mutta voi
  puuttua päätelaiturin kellonajasta, jossa se ei toisi lisäinformaatiota.

- Finferriesin, Saaristolinjojen ja osan Ålandstrafikenin taulukoissa yksi vuoro
  muodostuu useasta peräkkäisestä satamarivistä. Taulukon värit ja tyhjät rivit
  ilmaisevat vuoron rajan, mutta niitä ei ole vielä hyväksytty rakenteiseksi
  `trips`-jaoksi.
- Merkinnät kuten `y`, `x`, `~`, `*`, numerot ja kirjainviitteet ovat mukana
  soluissa ja sivutekstissä, mutta niiden vaikutusta ei ole vielä kaikilla
  lähteillä purettu ajo-, tilaus-, poikkeamis- ja yhteysehdoiksi.
- PDF:n yhdistetyt solut näkyvät joissakin taulukoissa ensimmäisen solun
  monirivisenä tekstinä ja muissa soluissa `null`-arvoina. Kellonajat pitää
  kohdistaa sarakkeisiin ennen kuin vuoro on reitityskelpoinen.
- Kaikki tässä listassa olevat lähteet käyttävät siksi tilaa
  `machine_extracted_requires_semantic_review` ja `routingReady: false`.
- Yhteysaluskierroksen sama alku- ja päätelaituri on operatiivinen kehys eikä
  matkustajan lähtö–määränpääpari. Kierros ajetaan vain, jos vähintään yksi
  saarikuljetus on varattu. Esimerkiksi Nauvon eteläisellä reitillä klo 7.45
  lähtö Kirjaisista on tarkka mutta paluu noin klo 8.50 riippuu siitä, käydäänkö
  Pensarissa, Penossa vai molemmissa sekä olosuhteista. Lähteen `Penö`
  normalisoidaan nimeksi `Peno` alkuperäistä solutekstiä muuttamatta.
- Nauvon eteläisen reitin yhdistetty `Gloskär / Trunsö` -lähderivi puretaan
  kahdeksi erilliseksi `y`-laituriksi. Ne ovat lähekkäiset eri saaret; kumpikin
  voidaan varata erikseen ja samalla vuorolla voidaan käydä molemmissa.
- Rymättylän yhdistetty `Korvenmaa/Wihuri/Pyytti` -rivi puretaan kolmeksi
  itsenäiseksi käynniksi. Korvenmaa ja Pyytti ovat eri saaria, ja Wihuri on
  erillinen laituri Korvenmaan saaressa.
- Rymättylän sulkeissa olevat ajat ovat lähtöön sidottuja arvioita:
  Ruotsalainen noin +20 min ja Pakinainen noin +40 min. `x`-käynnit ovat
  tarvittaessa ajettavia mutta käytännössä tavallisia. Muille välikäynneille ei
  muodosteta lähteetöntä aikaa. Haapalan paluuaika voi aikaistua, jos
  valinnaisia käyntejä jää pois.
- Rymättylän sunnuntain Pakinaisen `(16.40/17.05)x` tarkoittaa noin klo 16.40
  ilman edeltävää Pähkinäisen käyntiä ja noin klo 17.05, jos Pähkinäisessä
  käydään. Ne ovat ehdollisia arvioaikoja, eivät kaksi erillistä lähtöä.
- Houtskarin talvi-PDF:n maanantain ja tiistain otsikoiden välistä puuttuu
  pystyviiva. Klo 5.50 aamukierros kuuluu tiistain ja keskiviikon sarakkeisiin
  (`_23____`); maanantaina sitä ei ajeta.
- Houtskarin sunnuntain Själö noin klo 13.20 – Torsholma 13.55/14.10 – Själö
  noin klo 14.50 on yksi edestakainen kierros. Själön ajat ovat menon ja paluun
  likimääräiset väliajat; Torsholman ajat ovat saapuminen ja paluulähtö.
- Iniön lisäreitiltä Houtskarin reitille on suunniteltu yksisuuntainen vaihto
  Själössä. Perjantain esimerkki on Åselholm 13.10 – Själö 13.40, odotus yli
  tunnin ja jatko Torsholmasta 14.30 alkavalla kierroksella Roslaxiin 17.40.
  Själön tarkka noutoaika puuttuu ja arvioidaan myöhemmin historiadatasta.
  Lähde ei sano, odottaako jatkava alus myöhästyvää ensimmäistä alusta.
  Maanantaina, keskiviikkona ja sunnuntaina molempien reittien alukset ovat
  iltapäivällä yhtä aikaa Själössä. PDF:n sininen värikoodaus osoittaa tämän
  viralliseksi kaksisuuntaiseksi vaihtoyhteydeksi. Sitä ei silti tulkita
  odottamistakuuksi ilman erillistä lupausta.
- Nauvon poikittaisen reitin `Ängsö / Lånholm` puretaan kahdeksi itsenäiseksi
  käynniksi. Laiturit ovat saman suuren saaren eri puolilla yli kahden
  kilometrin päässä toisistaan; solumerkintä periytyy kummallekin.
- Velkuan reitin Munninmaa, Kettumaa, Liettinen ja Tammisluoto ovat eri saaria.
  Kaikki niiden kauttaviivayhdistelmät puretaan erillisiksi kohteiksi, joille
  rivin käyntimerkintä periytyy.
- Kauttaviiva ei aina tarkoita eri kohteita: `Själö/Seili`, `Nagu/Nauvo` ja
  `Pärnäs/Pärnäinen` ovat saman laiturin kieliversioita. Seili tallennetaan
  yhdeksi solmuksi, mutta käyttöliittymälle suositellaan rinnakkaisnimeä
  `Seili / Själö` (ruotsiksi `Själö / Seili`), jotta käyttäjä tunnistaa paikan.
- Eri reittien samannimiset paikat tarkennetaan vain monitulkintaisissa
  hakutuloksissa, ei tavallisessa reitti- tai karttanäkymässä. Berghamn toimii
  tärkeimpänä testitapauksena; Själö-nimiset kohteet eivät esiinny samalla
  reitillä eikä niitä tarvitse nyt käsitellä erikseen.
- Nauvon pohjoisen reitin `Lavarn (Houtsala)` tarkoittaa yhtä laituria.
  Kanoninen ja käyttäjälle näytettävä nimi on `Lavarn`; Houtsala on vain
  ympäröivän saaren tai alueen sijaintikonteksti. Toista Lavarnia ei ole, joten
  suljetarkennetta ei tarvita edes erotteluun.
- Nauvon pohjoisen sunnuntain `y**` korvaa määräjaksoilla kaksi vuoroa yhdellä
  klo 17.50 lähtevällä kierroksella:
  Nauvo–Seili–Nauvo–Innamo–Järvsor–Maskinnamo–Ahvensaari. Nauvo–Seili–Nauvo ja
  Nauvo–…–Ahvensaari eivät silloin kulje erillisinä vuoroina.
- Nauvon eteläisen viikonloppukierto lähtee Kirjaisista lauantaina klo 10,
  saapuu Borstöön noin klo 13.25 ja palaa sunnuntaina klo 12–noin 18. Sunnuntain
  paluun `y+`-määräaika, edellinen päivä klo 12, koskee koko paluuvuoroa.
  Sunnuntain klo 18 Kirjais–Peno–Pensar–Kirjais on erillinen lyhyt `y`-kierros,
  vaikka taulukon vahva poikkiviiva tekee vuororajasta epäselvän.
  Sunnuntain `y*+` tulkitaan keskitason varmuudella niin, että sama M/S Falkö
  jatkaa Kopparholmin jälkeen ilman vaihtoa, ohittaa varmasti Knivskärin ja käy
  poikittaisen reitin Berghamn–Ängsö–Lånholm–Hummelholm-laitureissa ennen paluuta eteläiselle reitille
  Brännskärissä. Sen jälkeen järjestys on Grötö–Stenskär–Gullkrona–Kirjais.
  Merkintä saattaa koskea koko Borstö–Kopparholm-osuutta, vaikka se näkyy vain
  Kopparholmin solussa. Tämä tulkinta ei ole täysin varma.
  Brännskär, Grötö, Stenskär ja Gullkrona kuuluvat edelleen sekä poikittaiseen
  että eteläiseen reittiin. Poikittaisen aikataulun alaviite vahvistaa Grötön
  tilauksesta poikettavaksi laituriksi. Samassa luettelossa on Triören, joka
  puuttui paikallisesta reitti- ja laituridatasta kokonaan. Työoletuksena laituri
  on saaren kaakkoisrannalla ja reitti kulkee Gullkronasta Furuskärin ja
  Mottonskärin itäpuolitse. Tarkka laiturikoordinaatti varmistetaan myöhemmin
  historiallisen livedatan avulla.
  Tiistaisin M/S Falkö ajaa poikittaisen reitin kierroksen Kirjaisista noin klo
  9.30 ja palaa Kirjaisiin klo 12. Järjestys on
  Kirjais–Byskär–Brännskär–Ängsö–Lånholm–Hummelholm–Berghamn–Kirjais. Eteläisen
  reitin klo 16 lähtö on tästä erillinen myöhempi vuoro.
  Poikittaisen taulukon sunnuntain `Borstö → *` jatkaa samaa eteläisen reitin
  Borstöstä klo 12 alkanutta M/S Falkön vuoroa. Poikittaiselle ei muodosteta
  erillistä lähtöä. Vahvistettu loppujärjestys on
  Berghamn–Ängsö–Lånholm–Hummelholm–Brännskär–Grötö–Stenskär–Gullkrona–Kirjais.
  Yhteiset loppupään laiturit on jätetty poikittaisen taulukosta pois, jotta
  yhtä sunnuntaivuoroa varten ei tarvita omia rivejä. Yhteinen oranssi pohjaväri
  toimii lähteiden välisenä jatkuvuusmerkintänä.
  Arkipäivien ensimmäinen lähtö Kirjaisista tallennetaan aikaikkunana
  6.15–6.50. Tarkka aika määräytyy varausten mukaan ja vahvistetaan varauksen
  yhteydessä. Brännskär 7.20 ja paluu Kirjaisiin 7.45 ovat julkaistut
  kiintopisteet.

## Reittikohtaiset asiat

- **Hiittisten itäinen / Alva:** kaikki vuorot tulkitaan varattaviksi. Arkisin
  on ensisijaisesti koululaisia palveleva kierros Taalintehtaalta saarille ja
  takaisin Taalintehtaalle klo 8.05. Myös aamumatka Taalintehtaalta saariin on
  mahdollinen, mutta lähtöaikaa ei julkaista ja se voi olla noin klo 6 tai
  aiemmin. Iltapäiväkierros lähtee Taalintehtaalta klo 15.00 ja kulkee vain
  saariin; saarista Taalintehtaalle ei ole aikataulun mukaista iltapäiväyhteyttä.
  Muiden laiturikäyntien ajat puuttuvat. Niille voidaan myöhemmin laskea
  historiadatasta neuvovat vaihteluvälit. PDF:n satamajärjestys oletetaan
  lähes vakiona noudatettavaksi reittijärjestykseksi. Varaus ratkaisee käydäänkö
  kyseisessä laiturissa; sitä ei tulkita luvaksi järjestää reitti vapaasti
  uudelleen. Tarkistettavaksi jää vain, saadaanko historiasta puuttuville
  kellonajoille riittävän vakaat vaihteluvälit.
- **Houtskarin, Iniön lisä-, Nauvon pohjoisen, Nauvon eteläisen, Nauvon
  poikittaisen, Paraisten, Rymättylän, Utön ja Velkuan reitit:** vuorojen rajat
  sekä `y`/`x`/`~`-merkintöjen yhdistelmät on tarkistettava. Mukana ovat vain
  10.10.2026 voimassa olevat tai tulevat talvikaudet.
- **Paraisten reitti:** Pensarin sulkeissa olevat kellonajat ovat arvioituja
  laiturikäyntiaikoja. Pensar on kierroksen kauimmaisin piste, joten arvio voi
  tavallisesti olla melko tarkka ja toimii hyödyllisenä lähtöaika-arviona myös
  sen jälkeisille laitureille. Aikaa ei silti käsitellä minuutilleen taattuna;
  tilatut käynnit ja olosuhteet voivat siirtää sitä.
  Kaikki matkat ovat varattavia. Granholmen käsitellään omana varattavana
  laituririvinään ennen tai jälkeen jokaista Heisala-käyntiä kulkusuunnan
  mukaan. Lähde on jättänyt nämä toistuvat rivit painamatta, koska
  Granvik–Heisala on lähes heiluriliikennettä ja Granholmen vain pieni poikkeama
  reitiltä. Granvikista klo 7.45 ja 14.00 lähtevät kierrokset ajetaan vain
  Granvik–Heisala–Granvik, eikä niillä käydä Granholmenissa kumpaankaan
  matkustussuuntaan. Kaikilla muilla vuoroilla Granvik–Granholmen ja
  Granholmen–Granvik ovat varattavissa.
  Ramsholm on Heisalan saaren toisessa päässä oleva oma haettava laituri, mutta
  ei normaali aikataulupysähdys. Se merkitään käyttäjälle tekstillä
  `varattavissa vain olosuhteiden niin vaatiessa`; mahdollisia syitä ei
  selitetä tai arvailla.
  Granvikista tullessa järjestys on Björkholm–Ramsholm–Stenholm–Aspholm;
  Ramsholm ja Stenholm puuttuvat painetusta taulukosta.
  Stenholm on varattavissa kumpaankin suuntaan jokaisella Pensariin ulottuvalla
  kierroksella, mutta ei lyhyemmillä kierroksilla.
  Varausohjeen `aamuvuoro` tulkitaan vain Granvikista klo 6.00 lähteväksi päivän
  ensimmäiseksi vuoroksi. Tulkinta on todennäköinen mutta ei täysin varma, joten
  sille tallennetaan keskitason varmuus.
  Östra Tallholm on poistettu nykyisestä reitistä ja karttakohteista. Se esiintyi
  ainakin vuoden 2019 aikataulussa, mutta ei tarkistetuissa vuoden 2025
  kesäaikatauluissa eikä nykyisessä talviaikataulussa.
- **Iniö–Kustavi ja Kasnäs–Hiittinen:** taulukot ovat muita suoraviivaisempia,
  ja reitit luokitellaan point-to-point-maantielautoiksi (`conn2`), ei
  yhteysaluksiksi (`conn4`). Yhteysalusten yleistä varauspakkoa ei periytetä
  niille. Kirjain- ja yhteysviitteet pitää edelleen purkaa ehdoiksi.
  Iniö–Kustavin harmaat tiistain ja torstain Heponiemen klo 7.00 sekä Kannvikin
  klo 9.30 lähdöt merkitään vaarallisten aineiden kuljetuksiksi, joilla
  matkustajamäärä on rajoitettu.
  Kasnäs–Hiittinen-reitillä vastaava merkintä kuuluu kaikkiin arkipäivien
  Kasnäsin klo 6.30 ja Långnäsin klo 8.30 lähtöihin, viiteen lähtöön kumpaankin
  suuntaan eli yhteensä kymmeneen viikossa.
- **Utön reitti:** `(tx)` tarkoittaa yhtä sunnuntain ja maanantain yli jatkuvaa
  edestakaista kiertoa: Pärnäinen su 17.05 – Utö 19.30, yöpyminen Utössä ja Utö
  ma 6.00 – Pärnäinen 8.15. Molempien osuuksien määräaika on edeltävä lauantai
  klo 15. Vuoro on vain henkilökuljetukseen, ja koululaiset sekä paikalliset ovat
  ensisijaisia matkustajia. Se näytetään silti kaikille käyttäjille mahdollisena
  yhteytenä, jos varaus hyväksytään; ensisijaisuus on huomautus eikä rajaus.
  Perjantain Utö 5.30–Pärnäinen 10.00 -aamukierroksen Berghamn-käynti (`z`) on
  varattavissa vain parittomilla ISO-viikoilla, edellisenä päivänä klo 17
  mennessä. Parillisilla viikoilla käyntiä ei ole tarjolla.
  Pääsiäistorstaina 25.3.2027 ei ole liikennettä ennen klo 18. Sen jälkeen
  käytetään perjantain aikataulua; sitä ei yhdistetä normaaleihin torstain
  päivävuoroihin. Utön noin viiden tunnin matka estää kaksi tällaista kierrosta.
  Pääsiäisen `(tx)`-kierto siirtyy päivällä: Pärnäinen–Utö ma 29.3. klo
  17.05–19.30 ja Utö–Pärnäinen ti 30.3. klo 6.00–8.15. Tiistaina ei ole muuta
  liikennettä, ja keskiviikkona 31.3. jatketaan normaalia keskiviikkoaikataulua.
  Määräaika on edeltävä lauantai 27.3. klo 15.
  Maanantain 8.15–8.30 vaihto Pärnäisissä `(tx)`-alukselta M/S Utölle on
  fyysisesti mahdollinen mutta reitityksessä tarpeeton: `(tx)` on jo käynyt
  samoissa välisaarissa. Sitä ei tarjota suositeltuna yhteytenä.
- **Korppoon reittialue / M/S Fiskö:** tiistain kaksi Korppoo–Storpensar-
  edestakaista vuoroa on purettu varattaviksi koulukuljetuksiksi. Ne ajetaan
  joko M/S Fisköllä tai taksiveneellä; valintaperustetta ei julkaista.
  Tavallisia matkustajia ei lähtökohtaisesti hyväksytä. Auto voidaan tarjota
  vain, jos vuoro ajetaan Fisköllä ja autopaikka on varattu. Jäljellä ovat
  muiden päivien vuororajat.
  Autopaikan epäselvä varaus- ja vahvistamisohje tallennetaan vain käyttäjälle
  näytettäväksi lisätiedoksi, ei reititysehdoksi. Käytännön tulkinta on, että
  autopaikka varataan aikaisintaan kuukautta ja viimeistään viikkoa ennen
  lähtöä. Erillistä jälkivahvistusta ei mallinneta.
  Sunnuntain `#`-vuorot tulkitaan kahdeksi erilliseksi kierrokseksi:
  Österskär klo 10.00 alkaen ja Berghamn klo 13.00 alkaen. Österskärin lähteen
  klo 12.00 säilytetään, mutta noin 90 minuutin tyypillinen menomatka ja paluu
  ennen klo 13 tarkistetaan myöhemmin historiadatasta.
  Kierroksen `Brunskär/Kälö` on kaksi erillistä varattavaa laituria. Harmaa
  värialue ja `#` keskeyttävät koko kierroksen 2.11.2026–30.4.2027, joten myös
  Brunskärin ja Kälön käynnit jäävät talveksi pois.
- **Åva–Jurmo, Åva–Osnäs, Enklinge–Kumlinge, Föglö, pohjoinen linja sekä
  Seglinge:** käytössä on loppuvuoden sivu tai alku- ja loppuvuoden yhteinen
  taulukkopohja. Oletus on tehty `data.js`:n voimassaolojaksojen perusteella.
- **Eteläinen linja:** sivut 9–10 ovat perusaikataulu 28.9.–22.12. ja
  26.–29.12. Sivu 11 on joulun erikoisaikataulu 23.–25.12. ja uudenvuoden
  erikoisaikataulu 30.12.–1.1. Lähde sanoo erikseen, että 22.12. ja 26.12.
  ajetaan tavallisen aikataulun mukaan. Jaksot eivät mene päällekkäin.
  Husön ja Kyrkogårdsön lauttakäynnin voi varata ajoneuvolla matkustava.
  Ilman ajoneuvoa matkustava ohjataan ensisijaisesti Sottungassa vaihdettavaan
  yhteysveneeseen. Hän voi varata lautan poikkeaman, jos vuorolla ei ole sopivaa
  yhteysveneyhteyttä; Galtbyhyn tai Galtbystä matkustava saa varata poikkeaman
  ilman ajoneuvoa aina. Varaus tehdään viimeistään tuntia ennen lähtöä
  lähtösatamasta. Husön käynti viivästyttää myöhempiä aikoja noin 10 minuuttia
  ja Kyrkogårdsön käynti noin 20 minuuttia.
  Jos samalla vuorolla käydään molemmissa, käytetään toistaiseksi varovaista
  noin 30 minuutin kumulatiivista viivettä. Oletuksen varmuus on matala:
  saarten välillä näyttää olevan pienempi laivaväylä, joka voisi oikaista
  reittiä, jos nämä lautat käyttävät sitä. Todellinen yhteisviive tarkistetaan
  myöhemmin historiadatasta.
  Överön käynti tilataan viimeistään 45 minuuttia ennen arvioitua saapumista.
  Käynti on varattavissa vain, kun matka jatkuu Överöstä itään tai saapuu
  Överöhön idästä. Pelkkää Överö–Långnäs- tai Långnäs–Överö-matkaa ei voi
  varata; Långnäs on Överöstä länteen ja Galtbyn suunta itään.
  Vuoron lähtösatamasta alus ei lähde ennen painettua aikaa. Välisatamasta se
  voi lähteä enintään viisi minuuttia ennen painettua aikaa, joten rakenteessa
  välisataman lähtöaikaikkuna on `painettu aika − 5 min … painettu aika` ja
  käyttäjää neuvotaan olemaan valmiina vähintään viisi minuuttia aikaisemmin.
  Erityislauantaisin 3.10., 7.11. ja 5.12. Långnäsistä ajetaan klo 6.00 ja
  10.30, mutta ei klo 9.15; Galtbystä ajetaan klo 20.15 ja klo 14.45 vuoro
  ajetaan M/S Skiftetillä. Muina lauantaina Långnäsistä ajetaan klo 9.15 mutta
  ei klo 6.00 eikä 10.30; Galtbyn klo 20.15 jää pois ja klo 14.45 ajetaan M/S
  Gudingenillä. Viite `4` tarkoittaa eri suuntien taulukoissa eri asiaa:
  Långnäsistä vuoron poisjääntiä, Galtbystä vain aluksen vaihtumista.
- **Ahvenanmaan vaijerilossit:** reittikohtaisen kellonaikataulun aukot jo
  ilmaisevat tauot, joten yleissivun taukoja ei kahdenneta Seglingelle,
  Simskälalle eikä Toftölle. Yleissivulta liitetään niille vain joulun
  poikkeusliikenne. Embarsund liikennöi kesäaikataulun päätyttyä syys–
  joulukuussa tarvittaessa ilman kellonaikataulua; yleissivu on silloin sen
  aktiivinen lähde ja sisältää myös joulupoikkeuksen.
- **Simskäla ja Toftö:** poikkeamat ja tauot ovat tekstissä mukana, mutta niitä
  ei ole vielä kokonaan muutettu päivämäärä- ja palvelukatkoehdoiksi. Toftön
  lauantain, sunnuntain ja pyhäpäivän klo 6.00–7.45 viitteellä `2` merkityt
  neljännestuntilähdöt eivät ole aikataululähtöjä. Ne kuuluvat klo 22.00–7.50
  tarvittaessa ilman aikataulua ajettavaan jaksoon; normaali 15 minuutin
  aikataulu alkaa klo 8.00.
  Jouluaattona 24.12. käytetään sunnuntain aikataulua ilman klo 17.55–18.30
  taukoa. Viimeinen aikataululähtö on klo 21.45, minkä jälkeen liikennöidään
  tarvittaessa klo 22–24. Joulupäivän puolella on lisäksi erillinen klo 1.00
  tilauslähtö. Muuta liikennettä ei ole ennen klo 6.00; klo 6–7.50 liikennöidään
  tarvittaessa ja aikataululiikenne jatkuu klo 8.00.
  Simskälalinjan kanoniset laiturinimet ovat Timskär ja Vattungsrevet; lähteen
  sulkeissa käyttämät Simskäla ja Sandö ovat sijaintikontekstia. Aikatauluajat
  ovat lähtöjä Timskäristä. Vattungsrevetin paluulähtö on arviolta seitsemän
  minuuttia myöhemmin, mutta matkustajan pitää olla Vattungsrevetin laiturilla
  jo julkaistuna Timskärin lähtöaikana tai soittaa lautalle siihen mennessä.

## Tietoisesti pois jätetyt lähteet

- Päättyneet kesä- ja välikaudet, Seglingen alkuvuoden taulukko sekä
  Embarsundin päättynyt kesätaulukko eivät kuulu nykyiseen reititysdataan.
- Ålandstrafikenin erillinen polttoainekuljetusten kooste ei ole matkustajan
  aikataulu. Mahdollinen matkustajakapasiteetin vaikutus liitetään varsinaisen
  linjan kyseiseen lähtöön, kuten Brändö–Kumlinge-litteroinnissa.
- Ålandstrafikenin kesäinen passivene on päättynyt eikä kuulu nykyiseen dataan.
