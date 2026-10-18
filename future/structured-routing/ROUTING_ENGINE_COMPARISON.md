# Reitittimien vertailu 18.10.2026

Tässä muistiossa verrataan Saaristolauttojen ajasta riippuvaa reititintä,
paikallista Valhallaa ja Google Mapsia. Vertailun tarkoitus ei ole mitata
pelkkää tieajoa vaan selvittää, voiko yleinen reitityspalvelu korvata
saariston aikataulutetun reititysgraafin.

## Testiasetelma

- Haut tehtiin sunnuntaina 18.10.2026 noin klo 17.27 Suomen aikaa.
- Saaristolauttojen reititin haki seuraavan toteuttamiskelpoisen yhteyden myös
  seuraavalta päivältä. Sen ilmoittama kesto alkaa suositellusta lähtöajasta ja
  sisältää odotukset, lastausvalmiusvaatimukset ja aikataulutetut ylitykset.
- Google Mapsilta haettiin käyttöliittymän dynaaminen `Lähde nyt` -arvio. Se ei
  vastaa koko päivän eikä tulevan päivän aikatauluhakua.
- Valhalla tuotti nimellisen reitin Suomen OpenStreetMap-aineistosta. Se tuntee
  tie- ja lauttageometriaa, mutta ei Saaristolauttojen rakenteisia aikatauluja,
  varausehtoja tai yhteysalusten käyntiehtoja.

## Tiivistelmä

| Matka | Saaristolauttojen seuraava yhteys | Kesto lähdöstä | Google `Lähde nyt` | Johtopäätös |
|---|---|---:|---:|---|
| Turku–Storpensor | ma 19.10. klo 03.30–08.00 | 4 h 30 min | 2 h 56 min | Google ketjuttaa maantielauttoja mutta ei käytä Storpensorin aikataulutettua yhteysalusta luotettavasti. |
| Turku–Wihuri | ma 19.10. klo 04.55–06.55 | 2 h | 2 h | Nimelliset kestot osuvat yhteen, mutta vain oma reititin varmistaa M/S Islan vuoron ja lähtövalmiuden. |
| Nauvo–Degerby | su 18.10. klo 18.57 – ma 19.10. klo 07.14 | 12 h 17 min | 6 h 23 min | Google tunnistaa eteläisen linjan osia mutta summaa ajoajat tarkistamatta odotuksia ja yhteensopivia lähtöjä. |
| Helsinki–Degerby | su 18.10. klo 19.36 – ma 19.10. klo 07.14 | 11 h 38 min | 7 h 58 min | Google näyttää maantieteellisesti mahdollisen ketjun; oma reititin osoittaa seuraavan toteuttamiskelpoisen aikatauluketjun. |
| Tampere–Sund | su 18.10. klo 18.10 – ma 19.10. klo 01.53 | 7 h 43 min | 7 h 59 min | Vertailun paras Google-tulos: sama Turku–Långnäs-periaate, mutta oma reititin käyttää täsmällistä lähtöä. |

Jos kestoksi lasketaan hakukellonajasta perille saakka, tulokset olivat
Turku–Storpensor 14 h 33 min, Turku–Wihuri 13 h 28 min,
Nauvo–Degerby 13 h 47 min, Helsinki–Degerby 13 h 47 min ja Tampere–Sund
8 h 26 min. Näitä lukuja ei pidä verrata suoraan yllä olevan taulukon
`Lähde nyt` -arvioihin, koska oma haku odottaa tarvittaessa seuraavan päivän
ensimmäistä käyttökelpoista vuoroa.

## Valhallan havainnot

Paikallinen testi käytti Valhalla 3.9.1:tä ja Suomen graafia. Se soveltuu hyvin
osoitteiden ja saariston reititysgraafin laitureiden välisten tieosuuksien
laskemiseen, kun lautat estetään näillä liityntäosuuksilla. Koko saaristomatkan
reitittäjänä tulokset eivät kuitenkaan ole käyttökelpoisia:

- Turku–Storpensor: 3 h 54 min / 83,3 km, mutta reitti käyttää virheellistä
  pitkää lauttageometriaa Turusta Korppoon suuntaan.
- Turku–Wihuri: reittiä ei löytynyt.
- Nauvo–Degerby: 4 h 03 min, mutta Nauvon piste ankkuroituu ohi kulkevaan
  Turku–Långnäs-lauttageometriaan.
- Helsinki–Degerby: 7 h 08 min / 314,7 km; nimellinen
  Turku–Långnäs–Svinö–Degerby-ketju ilman aikataulujen yhteensopivuuden
  tarkistusta.
- Tampere–Sund: 7 h 34 min / 351,6 km; nimellinen Turku–Långnäs-ketju.

Erillisessä Hiittisten kirkonkylä–Seglinge-haussa 3.11.2026 oma reititin löysi
kolme aikataulutettua vaihtoehtoa. Ensimmäinen oli klo 08.04–18.06 (10 h 02
min). Valhallan 8 h 57 min / 285 km -reitti käytti muun muassa lopetettua
Långnäs–Snäckö-poikittaislinjaa, joten lyhyempi tulos ei ollut toteuttamiskelpoinen.

## Johtopäätös

Yleinen reitityspalvelu kannattaa rajata liityntäosuuksiin ennen ensimmäistä
tunnettua laituria ja viimeisen tunnetun laiturin jälkeen. Valhalla sopii tähän
tehtävään paikallisena ja hallittavana palveluna. Saariston sisäinen osuus on
ratkaistava omalla ajasta riippuvalla graafilla, koska vain siinä ovat mukana
vuorojen todelliset päivät ja kellonajat, lastausvalmius, varaus- ja
käyntiehdot sekä riskitasot lauttayhteyksien välillä.
