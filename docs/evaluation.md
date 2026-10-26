# Utvärdering och resultat

## Sammanfattning

Utvärderingen visar att maskininlärningsmodeller kan förbättra prognoserna för PM2.5 vid Malmö Dalaplan sex timmar framåt. I den aktuella körningen presterar Support Vector Regression (SVR) bäst, med cirka 11–12 % lägre MAE än persistence-baseline på testdata. Den förskjutna modellen uppnår något bättre resultat än den vanliga, men skillnaden är liten och utvärderingen bygger på observerade framtida vädervärden. Felanalysen visar samtidigt att modellerna har svårt att förutsäga höga PM2.5-koncentrationer. Resultaten stödjer därför användning för generella prognoser, men inte som ett tillförlitligt varningssystem för höga föroreningsnivåer.

## Vad vi mäter och varför
Modellerna utvärderas med flera mått:

MAE: Genomsnittligt prognosfel i µg/m³. Används för att välja bästa kandidatmodell.

RMSE: Ger större vikt åt stora prognosfel.

R²: Visar hur väl modellen förutsäger variationen i PM2.5 jämfört med en medelvärdesprognos. Används vid championval.

Bias: Visar om modellen systematiskt över- eller underskattar.

MAE vid höga PM2.5-halter: Visar prognosfelet vid koncentrationer över träningsdatans 90 percentil.

MAE prioriteras vid kandidatvalet för att minimera det genomsnittliga prognosfelet, medan R² används för att avgöra om en ny kandidat förbättrar resultatet jämfört med befintlig champion.

## Datauppdelning

Datan delas upp kronologiskt i träning, validering och test. Perioderna beräknas dynamiskt utifrån senast tillgängliga väderarkivdata från SMHI. Uppdelningen säkerställer att modellerna tränas på äldre observationer och utvärderas på senare data.

- **Träning:** Från 2023-05-26 till dagen före valideringsperiodens start. Används för att träna modellerna.
- **Validering:** De sex senaste hela kalendermånaderna före månaden för senast tillgängliga väderarkivdata. Används för att välja bästa kandidatmodell utifrån lägst MAE.
- **Test:** En dynamisk period med senare observationer. Används för att jämföra bästa kandidat med befintlig champion utifrån högst R².

**Prognoshorisonten är sex timmar.** Varje observation används för att förutsäga PM2.5-halten sex timmar senare. Projektet jämför två modellvarianter: en med väderobservationer vid prognostillfället och en förskjuten variant med väderdata från tidpunkten som prognosen avser. Vid live-prediktion använder den förskjutna varianten väderprognoser i stället för framtida observationer.

### Data från körningen 2026-10-23

| Del | Period | Rader före rensning | Rader efter rensning |
|---|---|---:|---:|
| Träning | 2023-05-26 – 2025-12-31 | 22 825 | 21 555 |
| Validering | 2026-01-01 – 2026-06-30 | 4 343 | 4 282 |
| Test | 2026-07-01 – 2026-10-23 | 2 744 | 2 619 |

Efter att perioderna fastställts bearbetas datan och rader med saknade värden tas bort. Vid denna körning försvann 5,6 % av träningsdatan, 1,4 % av valideringsdatan och 4,6 % av testdatan.

Vid den slutliga jämförelsen mellan de två championmodellerna och persistence-baseline användes 2 595 gemensamma testobservationer för att säkerställa att modellerna jämfördes på samma underlag.

Eftersom perioderna är dynamiska kan både datum och antal observationer förändras vid kommande körningar.

## Hur vi undviker dataläckage

Dataläckage innebär att modellen använder information som inte skulle vara tillgänglig vid prognostillfället. Det kan ge missvisande goda resultat vid utvärderingen.

Projektet minskar risken för dataläckage genom att:

- **Dela upp datan kronologiskt:** Modellerna tränas på äldre observationer och utvärderas på senare data.
- **Separera träning, validering och test:** Träningsdata används för modellträning, valideringsdata för kandidatval och testdata för jämförelse med befintlig champion.
- **Använda en tydlig prognoshorisont:** Målvärdet är PM2.5 sex timmar framåt. Framtida PM2.5-observationer används inte som indata.
- **Undvika interpolering:** Saknade värden interpoleras inte, eftersom interpolering kan använda framtida observationer och därmed orsaka dataläckage. I stället tas rader med saknade värden bort.

### Skillnad mellan modellvarianterna

**Den vanliga modellen** använder PM2.5 och väderobservationer från prognostillfället (T) för att förutsäga PM2.5 sex timmar senare (T+6). Modellen tar inte uttryckligen hänsyn till hur vädret förändras under dessa sex timmar, utan använder de aktuella förhållandena som underlag för prognosen.

**Den förskjutna modellen (T+6)** tränas och utvärderas med väderobservationer från prognostillfället (T), där vädervärdena antas vara desamma sex timmar senare (T+6). Vid liveprediktioner används däremot väderprognoser för T+6.

Eftersom båda modellerna tränas och utvärderas med information som är tillgänglig vid prognostillfället uppstår inget dataläckage från framtida väderobservationer.

### Begränsningar

**Skillnad mellan historisk utvärdering och liveprediktion.** Den förskjutna modellen (T+6) tränas och utvärderas med antagandet att väderförhållandena är oförändrade sex timmar framåt, medan liveprediktioner använder väderprognoser för T+6. Skillnaden i väderindata innebär att de historiska resultaten inte nödvändigtvis motsvarar modellens prognosprecision vid verklig användning.

**Testdata används vid championvalet.** Eftersom Test R² avgör om en ny kandidat ersätter befintlig champion är testperioden inte en helt oberoende slututvärdering. Upprepade jämförelser mot samma testdata kan innebära att modellvalet indirekt anpassas till testperioden, vilket kan ge en alltför optimistisk bild av framtida prestanda.

## Modeller som jämförs

Alla modeller tränas på träningsdata och jämförs på valideringsdata. Modellen med lägst Validation MAE väljs som bästa kandidat. Kandidaten jämförs därefter med befintlig champion utifrån Test R² för att avgöra om champion ska ersättas.

Följande modeller ingår i jämförelsen:

- **Persistence-baseline:** Antar att PM2.5-halten om sex timmar är densamma som vid prognostillfället. Används som en enkel referens för att bedöma om de övriga modellerna ger bättre prognoser.
- **Linear Regression:** En linjär modell som beskriver sambandet mellan olika features och framtida PM2.5-halter.
- **Ridge Regression:** Linjär regression med regularisering som begränsar modellens koefficienter och minskar risken för överanpassning.
- **Random Forest:** Kombinerar prognoser från många beslutsträd för att ge ett mer stabilt resultat.
- **HistGradientBoosting:** Bygger beslutsträd stegvis, där varje nytt träd försöker minska felen från de tidigare träden.
- **Support Vector Regression(SVR):** Använder stödvektorer och kan med hjälp av en kernel hitta icke-linjära samband. Modellen använder en toleransmarginal för små prognosfel.
- **LightGBM:** En snabb och effektiv variant av gradientboosting som bygger beslutsträd stegvis för att minska prognosfelen.
- **XGBoost:** En annan variant av gradientboosting som bygger beslutsträd stegvis och använder regularisering för att minska risken för överanpassning.

Samma modelltyper utvärderas för både den vanliga och den förskjutna modellvarianten. Den vanliga modellen använder väderobservationer från prognostillfället (T), medan den förskjutna modellen antar att väderförhållandena är oförändrade fram till T+6.

## Vinnande modeller (både vanlig och T+6)

Vid körningen den 23 oktober 2026 valdes SVR som bästa kandidat för både den vanliga och den förskjutna modellvarianten, baserat på lägst Validation MAE. Kandidaterna jämfördes därefter med befintliga championmodeller utifrån högst Test R². I båda fallen behölls den tidigare championmodellen.

### Resultat på testdata

Samtliga modeller jämfördes på samma 2 595 testobservationer från perioden 1 juli till 23 oktober 2026.

| Modell | MAE | RMSE | R² | Bias | Kommentar |
|---|---:|---:|---:|---:|---|
| Persistence-baseline | 1,741 | 2,628 | 0,414 | −0,004 | Senaste uppmätta PM2.5-värde används som prognos |
| SVR (vanlig) | 1,545 | 2,265 | 0,565 | 0,056 | Väder vid prognostillfället |
| **SVR (T+6)** | **1,536** | **2,231** | **0,578** | **0,103** | Antaget oförändrat väder vid T+6 |

### Tolkning

Båda SVR-modellerna presterar bättre än persistence-baseline. Den vanliga modellen har cirka 11,3 % lägre MAE och den förskjutna modellen cirka 11,8 % lägre MAE jämfört med baslinjen.

Den förskjutna modellen uppnår något bättre resultat än den vanliga, men skillnaden är liten. Den har också något högre positiv Bias, vilket innebär en större genomsnittlig överskattning av PM2.5-halten.

Resultatet för den förskjutna modellen bör tolkas med försiktighet eftersom den historiska utvärderingen bygger på antagandet att vädret vid T+6 är detsamma som vid T, medan liveprediktioner använder väderprognoser för T+6. Modellens träffsäkerhet vid liveprediktioner kan därför skilja sig från resultaten i den historiska utvärderingen.

## Felanalys

Felanalysen syftar till att undersöka hur stora prognosfel modellerna gör, om de systematiskt över- eller underskattar PM2.5-halten och hur väl de hanterar höga föroreningsnivåer.

Analysen bygger på de slutliga championmodellernas resultat på testdata samt den fördjupade modellutvärderingen på valideringsdata.

### Prognosfel på testdata

Som framgår av resultaten för de vinnande modellerna har båda SVR-modellerna lägre MAE och RMSE än persistence-baseline. Den förskjutna modellen har något lägre prognosfel än den vanliga modellen.

RMSE är tydligt högre än MAE för samtliga modeller, vilket tyder på att det förekommer enskilda prognoser med relativt stora fel.

### Systematiska fel (Bias)

Bias visar om modellen i genomsnitt över- eller underskattar den faktiska PM2.5-halten.

Persistence-baseline har en Bias på −0,004 µg/m³, vilket innebär att den genomsnittliga avvikelsen ligger nära noll. Den vanliga SVR-modellen har en Bias på 0,056 µg/m³ och den förskjutna modellen 0,103 µg/m³. Båda SVR-modellerna visar därmed en liten genomsnittlig överskattning på testdata.

En Bias nära noll innebär dock inte att modellen saknar systematiska fel. Över- och underskattningar kan ta ut varandra när resultaten sammanfattas över hela testperioden.

### Fel vid höga PM2.5-halter

För att undersöka hur modellerna fungerar vid höga föroreningsnivåer används den 90:e percentilen av PM2.5 i träningsdata som gränsvärde. Gränsen är cirka 14,4 µg/m³ och används som en projektintern analysgräns, inte som ett officiellt hälsogränsvärde.

Följande resultat avser de nytränade SVR-kandidaterna på **valideringsdata**, inte de slutliga championmodellerna på testdata.

| Modell | High PM2.5 MAE (µg/m³) | High PM2.5 Bias (µg/m³) |
|---|---:|---:|
| SVR (vanlig) | 6,766 | −5,796 |
| SVR (T+6) | 6,879 | −6,086 |

Resultaten visar att båda modellerna har betydande prognosfel vid höga PM2.5-halter. Den tydligt negativa Bias visar dessutom att modellerna systematiskt underskattar dessa koncentrationer.

Den vanliga SVR-modellen har något lägre MAE och mindre negativ Bias än den förskjutna modellen vid höga koncentrationer på valideringsdata.

Detta är en viktig begränsning eftersom höga PM2.5-halter är särskilt relevanta ur ett luftkvalitets- och hälsoperspektiv.

### Felmönster vid höga och låga PM2.5-halter

Den fördjupade modellutvärderingen i projektets notebook visar ett tydligt mönster där modellerna tenderar att överskatta låga PM2.5-koncentrationer och underskatta höga koncentrationer.

Mönstret har undersökts genom spridningsdiagram över verkliga och förutsagda värden och genom att beräkna Bias separat för observationer under och över den 90:e percentilen i träningsdata.

Analysen på valideringsdata visar också att persistence-baseline presterar bättre än samtliga sju undersökta maskininlärningsmodeller vid höga PM2.5-koncentrationer. När höga koncentrationer ges större betydelse i modelljämförelsen förändras därför rangordningen mellan modellerna.

Detta visar att den modell som har lägst genomsnittligt prognosfel inte nödvändigtvis är bäst på att förutsäga höga föroreningsnivåer.

Den separata Bias-analysen visar dessutom att positiva och negativa prognosfel delvis kan ta ut varandra. En låg genomsnittlig Bias kan därför dölja systematiska fel vid olika koncentrationsnivåer.

Dessa slutsatser bygger på valideringsdata. Motsvarande uppdelning efter koncentrationsnivå har inte genomförts för de slutliga championmodellerna på testdata.

### Sammanfattning

Båda SVR-modellerna presterar bättre än persistence-baseline på testdata sett till MAE och RMSE. Den förskjutna modellen uppvisar något bättre resultat totalt, men skillnaden mot den vanliga modellen är begränsad.

Den fördjupade analysen på valideringsdata visar samtidigt att modellernas prognosprecision varierar mellan olika PM2.5-nivåer. Låga koncentrationer tenderar att överskattas, medan höga koncentrationer underskattas.

Den viktigaste identifierade svagheten är därför modellernas svårighet att förutsäga höga PM2.5-halter. Detta bör beaktas vid tolkning och användning av prognoserna, särskilt om syftet är att uppmärksamma perioder med försämrad luftkvalitet.

En möjlig vidareutveckling är att genomföra motsvarande felanalys uppdelad efter koncentrationsnivå även på testdata, för att undersöka om mönstret kvarstår hos de slutliga championmodellerna.

## Vad resultaten betyder i praktiken

Modellerna kan ge användaren en uppskattning av hur PM2.5-halten i Malmö förväntas utvecklas sex timmar framåt. Prognoserna kan därmed fungera som ett stöd vid exempelvis planering av utomhusaktiviteter.

Även om SVR-modellerna förbättrar MAE med cirka 11–12 % jämfört med persistence-baseline motsvarar det endast omkring 0,2 µg/m³ i minskat genomsnittligt prognosfel. Förbättringen är alltså mätbar, men dess praktiska betydelse är begränsad och beror på hur prognoserna ska användas.

En viktig begränsning är att modellerna har svårt att förutsäga höga PM2.5-koncentrationer. De lämpar sig därför bättre för att ge en generell indikation på luftkvalitetens utveckling än för att varna för särskilt höga föroreningsnivåer.

För att kunna använda prognoserna som ett mer tillförlitligt beslutsstöd behöver framför allt förmågan att identifiera höga koncentrationer undersökas vidare.

## Slutsatser som resultaten stödjer

Utvärderingen visar att maskininlärningsmodellerna kan förbättra prognoserna för PM2.5 i Malmö sex timmar framåt, men också att det finns tydliga begränsningar.

- **SVR ger bäst generell prognosprecision.** Modellen valdes som bästa kandidat för både den vanliga och den förskjutna modellvarianten utifrån lägst MAE på valideringsdata.

- **Båda championmodellerna överträffar persistence-baseline.** På testdata uppnår de cirka 11–12 % lägre MAE, vilket visar att modellerna tillför prognosvärde. Förbättringen är dock relativt liten i absoluta tal.

- **Den förskjutna modellen presterar något bättre.** Skillnaden mot den vanliga modellen är liten. Eftersom den historiska utvärderingen bygger på antagandet att vädret vid T+6 är detsamma som vid T är det osäkert om fördelen kvarstår vid liveprediktioner med väderprognoser.

- **Den förskjutna modellen presterar något bättre.** Skillnaden mot den vanliga modellen är liten. Vid liveprediktioner används väderprognoser för T+6 i stället för antaget oförändrat väder, vilket kan påverka modellens träffsäkerhet både positivt och negativt.

- **Höga PM2.5-koncentrationer är en tydlig svaghet.** Den fördjupade analysen på valideringsdata visar att modellerna tenderar att underskatta höga halter och att persistence-baseline presterar bättre vid dessa nivåer.

- **Modellvalet beror på vad som prioriteras.** När generell prognosprecision prioriteras är SVR det bästa alternativet, men när höga koncentrationer ges större betydelse kan andra modeller eller persistence-baseline vara bättre.

Sammantaget stödjer resultaten användningen av SVR för generella sex-timmarsprognoser av PM2.5. Däremot ger utvärderingen inte tillräckligt stöd för att använda modellerna som ett tillförlitligt varningssystem för höga föroreningsnivåer.

## Slutsatser som resultaten inte stödjer

Även om modellerna visar förbättrad prognosprecision finns det vissa slutsatser som inte kan dras utifrån den genomförda utvärderingen.

- **Att resultaten gäller för framtida tidsperioder.** Modellerna har utvärderats på en avgränsad testperiod. Det är därför inte säkert att samma prognosprecision uppnås under andra årstider eller framtida perioder med förändrade förhållanden.

- **Att den förskjutna modellen generellt är bättre.** Även om SVR (T+6) uppvisar något bättre resultat på testdata har ingen statistisk prövning genomförts för att bedöma osäkerheten i skillnaden mellan modellerna. Det går därför inte att fastställa att den förskjutna modellen generellt presterar bättre än den vanliga modellen.

- **Att förbättringen har stor praktisk betydelse.** Modellerna ger lägre genomsnittliga prognosfel än persistence-baseline, men utvärderingen visar inte om förbättringen är tillräckligt stor för att påverka användarens beslut.

Sammantaget visar resultaten modellernas prognosprecision under de undersökta förhållandena, men ger inte tillräckligt underlag för att fastställa deras långsiktiga tillförlitlighet eller praktiska nytta som beslutsstöd.

## Begränsningar

**Borttagna rader och luckor i datan.** Rader där någon feature eller målvärdet saknas tas bort vid modellutvärderingen. Nederbörd har identifierats som en viktig orsak till saknade värden, bland annat i sammanhängande perioder där SMHI har underkänt mätningar. Eftersom bortfallet inte nödvändigtvis är slumpmässigt kan det påverka vilka väderförhållanden som ingår i utvärderingen.

**Prognosens tidshorisont.** Prognosen beräknas sex timmar framåt från den senaste kompletta observationen. Om den observationen ligger en bit tillbaka i tiden kan prognosen därför avse en tidpunkt som ligger mindre än sex timmar framåt från nu.

**Ovanliga föroreningshändelser.** Trots att tidsserien innehåller flera års timvisa observationer kan perioder med ovanligt höga PM2.5-koncentrationer vara få. Det begränsar möjligheten att bedöma modellernas prestanda vid sällsynta händelser.

**Dynamiska tidsperioder.** Uppdelningen mellan tränings-, validerings- och testdata förändras när ny data tillkommer. Resultat från olika körningar kan därför baseras på olika tidsperioder och behöver inte vara direkt jämförbara. Även årstidsvariationer kan påverka resultaten.

**Skillnader i datakvalitet.** Valideringsdatan består av kvalitetskontrollerade värden, medan testdatan kan innehålla preliminära mätvärden som senare korrigeras. Resultaten på testdata kan därför förändras om datan hämtas på nytt.

**Liveprediktioner är ännu inte utvärderade.** Den förskjutna modellen (T+6) använder väderprognoser vid liveprediktioner i stället för antaget oförändrat väder. Det är därför ännu inte fastställt om detta förbättrar eller försämrar modellens träffsäkerhet jämfört med den historiska utvärderingen.

**Geografisk avgränsning.** Modellen prognostiserar PM2.5 vid Malmö Dalaplan, med väderdata från Malmö A cirka fyra kilometer bort. Resultaten gäller de förhållanden som undersökts vid denna station.

## När lösningen inte bör användas

Prognoserna är avsedda att ge en generell indikation på PM2.5-koncentrationen vid Malmö Dalaplan och bör inte användas som enda beslutsunderlag i följande situationer:

**Varningar för höga föroreningsnivåer.** Modellerna tenderar att underskatta höga PM2.5-koncentrationer och bör därför inte användas som ett tillförlitligt varningssystem.

**Hälsorelaterade beslut.** Prognoserna bör inte ensamma ligga till grund för beslut som kan påverka människors hälsa, särskilt inte för personer som är känsliga för luftföroreningar.

**När aktuella indata saknas.** Prognosen utgår från den senaste kompletta observationen. Om denna ligger långt tillbaka i tiden kan prognosen avse en redan passerad tidpunkt och därmed vara olämplig för aktuella beslut.

**Utanför modellens användningsområde.** Modellen har utvecklats för Malmö Dalaplan och en prognoshorisont på sex timmar. Den bör därför inte användas för andra platser eller prognoshorisonter utan ytterligare utvärdering.

## Rekommendation och nästa steg

I den aktuella körningen valdes Support Vector Regression (SVR) som bästa kandidat för båda modellvarianterna. Vid jämförelsen på testdata behölls de befintliga championmodellerna, som också var SVR. Modellvalet är dynamiskt och kan förändras när nya data tillkommer och modellerna utvärderas på nytt.

Följande förbättringar föreslås:

1. **Förbättra prognoser vid höga PM2.5-halter.** Undersök alternativa modeller, viktade förlustfunktioner eller andra metoder som lägger större vikt vid höga koncentrationer..

2. **Utvärdera med verkliga väderprognoser.** Utvärdera den förskjutna modellen med väderprognoser som fanns tillgängliga vid respektive prognostillfälle och jämför resultaten med den historiska utvärderingen som bygger på antaget oförändrat väder.

3. **Undersök skillnadernas statistiska säkerhet.** Använd exempelvis konfidensintervall för att bedöma om skillnaderna mellan modellerna är tillräckligt tydliga för att motivera ett modellbyte.

4. **Följ upp modellernas prestanda över tid.** Utvärdera prognoserna löpande när nya mätvärden blir tillgängliga för att upptäcka försämrad precision och avgöra när modellerna behöver tränas om.

5. **Hantera saknade observationer med anpassad prognoshorisont.** Undersök möjligheten att träna modeller för längre eller varierande prognoshorisonter. Då skulle systemet kunna utgå från den senaste kompletta observationen och ändå leverera en prognos sex timmar framåt från aktuell tidpunkt.

6. **Utöka till fler mätstationer.** Undersök möjligheten att använda modellen för fler mätstationer genom att anpassa och utvärdera den med lokala mät- och väderdata. På längre sikt kan även en gemensam modell för flera stationer undersökas.