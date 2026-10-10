# Rakenteellinen aikataulu ja reititys

Tämä hakemisto sisältää tulevaa rakenteellista aikataulua, sen generointia ja
sen avulla tehtävää reititystä koskevan kokeellisen työn. Hakemiston aineisto ei
ole tuotannossa eikä sitä julkaista nykyisen Saaristolautat-datan mukana.

Keskeiset tiedostot:

- `structured-timetables.json`: generoitu rakenteellisen aikataulun luonnos.
- `structured-timetables.schema.json`: luonnoksen JSON Schema.
- `structured-timetable-transcriptions/`: PDF-lähteiden litteroinnit.
- `scripts/`: aineiston poiminta- ja generointityökalut.
- `ROUTING_PLAN.md`: reitityksen suunnitelma ja perustelut.
- `STRUCTURED_TIMETABLE_UNCERTAINTIES.md`: tarkistettavat tulkinnat.

Generointi ajetaan repositorion juuresta:

```sh
python3 future/structured-routing/scripts/build_structured_timetables.py
python3 future/structured-routing/scripts/build_structured_timetables.py --check
```

Skriptit lukevat edelleen repositorion juuressa olevia nykyisiä lähdetietoja
sekä Gitin ulkopuolisen `.timetable-checker/originals/`-hakemiston tiedostoja.
