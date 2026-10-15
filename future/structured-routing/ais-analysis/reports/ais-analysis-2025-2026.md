# AIS-analyysin ensimmäinen vaihe 2025–2026

Analyysi käyttää tiedostoa `lauttalive_20251023_20261011.db.gz` ja käyttäjän
karttakuvasta digitoitua Saaristomeren analyysipolygonia. Tulokset ovat
alustavia reittikandidaatteja, eivät vielä lopullisia reitti- tai
laiturikorjauksia.

## Esikäsittely

- Lähderivejä: 53 979 134
- Polygonin sisäpuolisia keräyshavaintoja: 24 789 780 (45,92 %)
- Peräkkäisten identtisten AIS-havaintojen yhdistämisen jälkeen: 19 849 042
- Polygonin sisällä havaittuja MMSI-tunnuksia: 117
- Vähintään 60 eri päivänä alueella havaittuja MMSI-tunnuksia: 68
- Pääteltyjä historiakantaan tallennettuja keräyskierroksia: 507 007
- Keräyskierrosten keskimääräinen väli: 60,1 sekuntia
- Yli viisi minuuttia vanhoja keräyshavaintoja: 1,19 %

Palvelu hakee tiedot kahdesti minuutissa, mutta historiakantaan tallennetaan
vain joka toinen haku. Tämä vastaa aineistosta pääteltyä noin minuutin väliä.

Keräyskierrokset päätellään alkuperäisestä SQLite-`rowid`-järjestyksestä.
Yhdellä kierroksella sama MMSI saa esiintyä vain kerran. Kierroksen arvioitu
keräysaika lasketaan sen uusimman aikaleimadesiilin mediaanista, jolloin yksi
virheellinen tulevaisuuteen osoittava AIS-aika ei siirrä koko kierrosta.

## Laiturikäyntien tunnistus

Tunnetun laiturin ympäriltä etsitään 250 metrin kohtaamiset. Kohtaaminen
hyväksytään laiturikäynniksi jollakin seuraavista perusteista:

1. vähintään 45 sekunnin viipymä ja SOG enintään 1,5 solmua
2. vähintään kaksi sijaintihavaintoa laiturialueella
3. enintään 50 metrin etäisyys ja SOG enintään 5 solmua
4. liikesuunnan vähintään 120 asteen muutos kolmesta sijaintipisteestä
5. yksittäinen hidas havainto enintään 150 metrin päässä

Kääntymisessä käytetään koordinaateista laskettua liikesuuntaa, ei
AIS-headingia. Laituria edeltävän ja seuraavan liikejakson täytyy kummankin olla
vähintään 75 metriä pitkä, jotta paikallaan olevan aluksen GPS-heilahtelu ei
näytä kääntymiseltä.

Yli kuuden tunnin yhtenäistä laiturissaoloa ei lasketa operatiiviseksi
laiturikäynniksi. Se voi olla esimerkiksi yöpyminen, huolto tai aluksen
säilytyspaikka.

### Tunnistustapojen osuudet

Alle 60 aktiivisen päivän alukset rajattiin tästä vaiheesta pois. Hyväksyttyjä
operatiivisia laiturikäyntejä löytyi rajauksen jälkeen 297 113.

| Tunnistusperuste | Käyntejä | Osuus |
|---|---:|---:|
| Viipymä ja SOG ≤ 1,5 solmua | 289 695 | 97,5033 % |
| Useita pisteitä laiturialueella, ei hidasta näytettä | 7 166 | 2,4119 % |
| Pelkkä sijaintiradan kääntyminen | 178 | 0,0599 % |
| Enintään 50 m ja SOG ≤ 5 solmua | 53 | 0,0178 % |
| Yksittäinen hidas piste | 21 | 0,0071 % |

Yhteensä 7 418 käyntiä eli 2,4967 % hyväksytyistä käynneistä tunnistettiin
ilman vähintään 45 sekunnin viipymää yhdistettynä korkeintaan 1,5 solmun
nopeuteen. Näistä 178 käyntiä eli 0,0599 % kaikista hyväksytyistä käynneistä
perustui nimenomaan kolmen sijaintipisteen osoittamaan kääntymiseen.

Nämä ovat algoritmin havaintoluokkia, eivät riippumattomasti vahvistettuja
totuuksia. Erityisesti usean pisteen `area_dwell` voi sisältää hitaita
ohituksia, ja 50 metrin `close_proximity` voi sisältää harvoja aivan laiturin
vierestä kulkevia ohituksia.

## Ensimmäiset reittikandidaatit

- Tunnettuja laitureita koordinaatteineen: 204
- Aktiivisia reittejä: 51
- Kaikilla aktiivisten reittien laitureilla on karttakoordinaatti
- Laiturikäyntejä sisältäviä MMSI–kuukausia: 604
- Vähintään kahden tunnetun reittilaiturin perusteella muodostettuja
  ykkösehdotuksia: 491 MMSI–kuukautta ja 48 MMSI-tunnusta
- Ykkösehdotuksen pistemäärä oli vähintään 0,5 kaikkiaan 441
  MMSI–kuukaudella ja 43 MMSI-tunnuksella
- Tunnettujen laiturien ulkopuolisia alustavia pysähdyssoluja: 268

Kuukausittainen tarkastelu näyttää myös reitin vaihtumisia. Esimerkiksi MMSI
230035990 vastaa touko–elokuussa selvästi Pientä rengastietä, syyskuussa
havainnot jakautuvat usealle reitille ja lokakuussa vahvin ehdotus on
Pohjoinen linja. Tämä tukee reitin päättelemistä ajanjaksolle sen sijaan, että
MMSI sidottaisiin pysyvästi yhteen reittiin.

Pysähdyssolut eivät vielä vastaa yksittäisiä laitureita. Vierekkäiset solut on
seuraavaksi yhdistettävä klustereiksi ja erotettava satamista, ankkuripaikoista
sekä alusten säilytyspaikoista.

## Seuraava vaihe

Seuraavaksi reittiehdotukset kannattaa muodostaa yksittäisistä
laiturikäyntiketjuista ja viikko- tai liikennöintijaksoista. Samalla tuotetaan
katselmointikartta, jossa näkyvät:

- tunnetut laiturit ja tunnistetut käynnit
- tuntemattomat pysähdysklusterit
- MMSI-kohtaiset ajourat
- ehdotettu reitti eri ajanjaksoina
- epävarmat ja ulkopuolisiksi arvioidut alukset
