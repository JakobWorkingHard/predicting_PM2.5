
# Beslutslogg

Viktiga beslut som påverkat projektet. Nyaste beslutet längst ner.

| Datum | Beslut | Motivering | Alternativ som valdes bort |
|-------|--------|------------|----------------------------|
| 2026-10-03 | Alla konfigurationer samlas i `config.toml`, som läses in i `config.py` och skickas vidare till orkestreraren (`orchestrator.py`) | en enda plats för parametrar, och körningar blir reproducerbara | kommandorader |
| 2026-10-04 | Funktion i `io.py` som slår ihop två dataframes, motsvarande en SQL-join | luftkvalitets- och väderdata kommer från olika källor och behöver kopplas ihop på tidsstämpel. | att slå ihop manuellt i notebooks |
| 2026-10-08 | Den sammanslagna filen skapas automatiskt när datahämtningen körs | ett steg färre att göra manuellt | att köra sammanslagningen som ett separat steg |
| 2026-10-09 | Rader där något värde saknas (PM2.5 eller någon väderobservation) droppas helt, vilket ger luckor bland tidsstämplarna | modellerna klarar inte saknade värden | interpolering |
| 2026-10-12 | Rader med saknade värden droppas efter att validerad data hämtats men innan modellen körs (preciserar beslutet 2026-10-09) | reproducerbarhet, koden kan återanvändas | droppa raderna som del av att modellen körs |
| 2026-10-12 | Vindriktning delas upp i `vind_cos` och `vind_sin` som två features, implementeras i `src/features.py` | vindriktning är cirkulär. 359° och 1° ligger nära varandra men blir långt ifrån varandra som råa tal | behålla som rådata |
