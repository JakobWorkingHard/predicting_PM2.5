
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
| 2026-10-13 | Veckonummer används inte som feature. | PM2.5 var förhöjd vecka 8–11 under 2024 och 2025, men i valideringsdatan 2026 låg toppen istället vecka 4. Vinterns höga halter verkar komma i episoder som inte återkommer på samma veckor varje år. Vi undersökte även median-temperatur och ostlig–sydlig vind per vecka, men ingen av dem följde PM2.5-kurvan. | Veckonummer som feature. |
| 2026-10-13 | Tid på dygnet läggs till som feature (timme sin/cos, helg, samt timme sin/cos för helg). | EDA visade en topp kring kl. 08 på vardagar och kring kl. 10 på helger. | Timme utan uppdelning på vardag/helg. Timme som 24 separata kategorier. |
| 2026-10-14 | Testdatan omfattar hela perioden i `latest-months` utom de 4 senaste timmarna | Om target eller någon feature laggar något så undviker vi att droppa så många rader | Att använda hela perioden i `latest-months` |
| 2026-10-15 | Testdata hämtades från `latest-months` och sparades som en fast ögonblicksbild i `data/test/`. Den slutliga modellen var redan vald innan dess | `latest-months` rullar framåt, så en fast kopia behövs för att testresultatet ska gå att återskapa. Testet körs en gång och inga ändringar görs efter att testdatan öppnats | Att hämta testdatan på nytt vid varje körning |
