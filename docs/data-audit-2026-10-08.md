# Saaristolauttojen tietojen auditointi 8.10.2026

## Tiivistelmä

Auditoinnin kohteena olivat `saaristodata/data.js`-tiedoston reitit, alukset,
aikataulut, operaattorit ja yhteystiedot. Aineistossa on 54 reittiä, joista 51
on aktiivisia ja kolme vanhentuneiksi merkittyjä. Aluksia on 84,
aikataulukokonaisuuksia 59 ja laitureita 215.

`data.js` on ensisijainen lähde. Julkaistava `data.json` generoidaan komennolla
`node data.js > data.json`. Auditointityökalu lukee generoidun JSON-tiedoston.

Rakenteellinen tarkastus löysi yhden virheellisen päivämäärän, joka korjattiin.
Uusinta-ajossa jäi 53 varoitusta. Varoituksista 49 johtui siitä, ettei paikallisessa aineistossa ollut
8.10.2026 voimassa olevaa aikataulua paikallisessa muodossa. Nämä reitit pitää
arvioida yksitellen: hyvä ulkoinen aikataulupalvelu voi olla riittävä ratkaisu,
mutta useimmissa tapauksissa havainto osoittaa korjattavaa ylläpitovelkaa.

Palvelun kaksi keskeistä tarkoitusta ovat reitistön kattava esittäminen kartalla
ja aikataulujen tekeminen helposti löydettäviksi. Aikataulujen pitää palvella
matkan suunnittelua laajasti eri päiville ja kausille, ei vain seuraavan lähdön
näyttämistä. Tavoitteena on siksi tuoda voimassa olevat aikataulut tähän
palveluun kuvana tai muussa helposti lähestyttävässä ja mobiilissa toimivassa
muodossa aina, kun palveluntarjoajan oma näkymä ei täytä tätä tarvetta.

Ulkoinen linkki voi olla pysyvä ratkaisu, jos se vie suoraan vakaaseen,
ajantasaiseen, koko suunnittelujakson kattavaan ja mobiilissa helposti
selattavaan aikatauluun. Pelkkä palveluntarjoajan etusivu, vaikeasti käytettävä
PDF tai vain seuraavan lähdön näyttävä näkymä ei yleensä riitä.

Operaattorin alkuperäinen PDF tai aikataulusivu säilytetään lähteenä ja
tarkistuslinkkinä. Erityisesti suurilla valkoisilla marginaaleilla julkaistut
PDF:t pitää rajata tai muuntaa puhelimella luettavaan esitysmuotoon niiden
sisältöä muuttamatta.

## Tehdyt korjaukset

- Saaristolinjan Turku–Seili–Nauvo-reitin pääalukseksi korjattiin **M/S
  Lövskär**, kapasiteetti 118 matkustajaa. M/S Sommarskär säilyi Seili–Nauvo-
  liikenteen aluksena.
- Wilson Charterin yleinen Rannikkoreitti-sivu mainitsee **M/S Joanan**, mutta
  nykyinen Örön varaus- ja tuotesivu nimeää aluksiksi vain Idunin, Sisselin ja
  Minandran. Joanaa ei liitetty reittiin ilman lisävahvistusta. Alustietue
  säilytettiin historiallisessa alusrekisterissä.
- Kasnäs–Örö-aikataulun virheellinen päivämäärä `2023-06-02 ` korjattiin
  ISO-muotoon `2023-06-02`.
- Kasnäs–Örö-reitin vanhentunut syvälinkki vaihdettiin Wilson Charterin
  nykyiseen Rannikkoreitti-sivuun.

## Virallisista lähteistä vahvistetut kokonaisuudet

| Kokonaisuus | Auditoinnin tulos | Ensisijainen lähde |
|---|---|---|
| Finferriesin lautta- ja yhteysalusreitit | Reitit ja nykyiset lähdesivut ovat olemassa. Sivut sisältävät vuoden 2026/2027 aikataulut, reittikohtaiset alukset ja puhelinnumerot. Paikalliset aikataulukuvat ovat lähes kaikki vanhentuneet. | [Finferries: lauttapaikat ja aikataulut](https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut.html) |
| Utön reitti | M/S Utö ja numero 020 7118 797 vastaavat lähdettä. Talviaikataulu 1.10.2026–31.5.2027 on julkaistu. | [Finferries: Utön reittialue](https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/uton-reittialue.html) |
| Rymättylän reitti | M/S Isla ja numero 020 7118 796 vastaavat lähdettä. Talviaikataulu jatkuu 2.5.2027 saakka. | [Finferries: Rymättylän reittialue](https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/rymattylan-reittialue.html) |
| Iniö–Kustavi | M/S Sterna ja numero 020 7118 706 vastaavat lähdettä. | [Finferries: Iniö–Kustavi](https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/inio-kustavi.html) |
| Korppoo–Houtskari ja Korppoo–Norrskata | M/S Stella ja M/S Aura sekä numerot 020 7118 704/705 vastaavat lähdettä. | [Finferries: Korppoo–Houtskari](https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/korppoo-houtskari.html) |
| Saariston rengastie Houtskari–Iniö | Replot 2 ja numero 020 7118 707 vastaavat nykyistä reittisivua; vuoden 2026 liikennekausi on 8.5.–13.9. | [Finferries: Houtskari–Iniö](https://www.finferries.fi/lauttaliikenne/lauttapaikat-ja-aikataulut/saariston-rengastie-houtskari-inio.html) |
| Ålandstrafiken | Keskitetty aikataulu- ja yhteystietolinkki on edelleen oikea. Paikalliset reittikohtaiset kuvat päättyvät vuoteen 2025. | [Ålandstrafiken: turlistor](https://www.alandstrafiken.ax/turlistor) |
| Pieni rengastie | M/S Östern liikennöi Nauvo–Seili–Hanka-reittiä 8.5.–13.9.2026. Reitti, alus ja lähdelinkki vastaavat dataa. | [M/S Östern: aikataulu 2026](https://www.ostern.fi/aikataulut/) |
| Saaristolinja | Vuoden 2026 liikenteessä Turku–Seili–Nauvo-alus on M/S Lövskär ja Seili–Nauvo-alus M/S Sommarskär. Data korjattiin. | [Vitharun: Turku–Seili–Nauvo](https://vitharun.fi/fi/aikataulut/turku-seili-nauvo/) |
| Korppoon reitti | M/S Fiskö liikennöi reittiä ympäri vuoden. Talviaikataulu on julkaistu ajalle 1.9.2026–1.6.2027. | [Saaristolinjat](https://saaristolinjat.fi/) |
| Kasnäs–Örö ja rannikkoreitti | Wilson Charterin yleinen sivu mainitsee Joanan, mutta nykyinen varaus- ja tuotesivu nimeää vain Idunin, Sisselin ja Minandran. Reitillä säilytettiin kolme jälkimmäistä, kunnes Joanan asema voidaan vahvistaa. | [Wilson Charter: Rannikkoreitti 2026](https://www.wilsoncharter.fi/rannikkoreitti), [Örön nykyinen tuotesivu](https://wilsoncharter.johku.com/fi_FI/merimatkat/oro) |
| Hanko–Bengtskär | JaLe Line Oy, M/S Summersea, puhelin 0400 536 930 ja sähköposti myynti@marinelines.fi vastaavat lähdettä. Vuoden 2026 aikataulu on julkaistu. | [Marine Lines: Bengtskär](https://marinelines.fi/bengtskar/) |

## Avoimet tarkistukset

Seuraavia tietoja ei pidä muuttaa ilman operaattorin tai liikenteen tilaajan
vahvistusta:

- Sorpön ja Petun reiteiltä puuttuu operaattori. Sorpön aikataululinkki käyttää
  lisäksi salaamatonta HTTP-yhteyttä.
- Skarpnåtö–Snäckö-reitin operaattorin tiedoista puuttuu oma verkkosivu.
- Yksityiset kausireitit `hankokasnas`, `naantalikustavi` ja `korpostromoro`
  on merkitty datassa vanhentuneiksi, eikä niitä käsitellä aktiivisten reittien
  auditointivirheinä.
- Ålandstrafikenin vuoden 2026 varsinaista koontiaikataulua ei ollut indeksoitu
  tarkastushetkellä yhtä selvästi kuin vuoden 2025 tiedostoa. Nykyinen
  keskitetty aikataulusivu on siksi turvallisin linkki.
- Alusvaihdokset voivat olla tilapäisiä. Dataan lisättiin vain sellaiset alukset,
  jotka operaattori itse nimeää vuoden 2026 reittikuvauksessa.

## Jatkotoimet

1. Hankitaan kaikille aktiivisille reiteille voimassa olevat aikataulut ja
   tallennetaan ne kuva- tai muussa helposti selattavassa muodossa. Lähde,
   voimassaolo ja sisältö tarkistetaan ennen julkaisua.
2. Lisätään jokaiselle ylläpidettävälle tiedolle `checkedAt` ja `source` tai
   pidetään vastaava lähderekisteri erillisessä manifestissa.
3. Ajetaan `scripts/audit_ferry_data.py` ennen jokaista datajulkaisua.
4. Tehdään linkkien HTTP-status- ja uudelleenohjaustarkistus erillisenä
   verkkoyhteyttä käyttävänä CI-ajona.
5. Lisätään PDF-aikatauluille toistettava rajaus- ja kuvanmuodostusprosessi,
   jotta tarpeettomat valkoiset reunukset eivät vaikeuta mobiilikäyttöä.
6. Tarkistetaan kausireitit vuosittain helmi–huhtikuussa ja ympärivuotiset
   reitit vähintään kaksi kertaa vuodessa.

## Toistaminen

```sh
python3 scripts/audit_ferry_data.py \
  ../saaristodata/data.json \
  --date 2026-10-08 \
  --json /tmp/ferry-audit.json \
  --markdown /tmp/ferry-audit.md
```
