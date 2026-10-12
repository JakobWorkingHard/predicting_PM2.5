# Utvärdering och resultat

## Sammanfattning
<!-- 3–5 meningar: vilken modell fungerade bäst, hur mycket bättre än baseline, och huvudslutsatsen. Skrivs sist. -->

## Vad vi mäter och varför
<!-- Vilka mätvärden (t.ex. MAE, RMSE) och varför de är relevanta för användaren. Vad betyder ett fel på X µg/m³ i praktiken? -->

## Datauppdelning

Datan delas upp i tid, inte slumpmässigt. Modellerna tränas på äldre data och utvärderas på senare data, på samma sätt som när modellen används för att förutsäga framtiden.

| Del | Från | Till | Timmar | Rader efter borttagning av saknade värden |
|---|---|---|---|---|
| Träning | 2023-05-26 | 2025-12-31 | 22 825 | 21 555 |
| Validering | 2026-01-01 | 2026-04-30 | [fylls i senare] | [fylls i senare] |
| Test | 2026-05-01 | [fylls i senare] | [fylls i senare] | [fylls i senare] |

Antalet timmar avser en komplett timaxel efter validering, med en rad per timme. Valideringsperioden har en timme mindre än 120 × 24, eftersom en timme försvinner vid omställningen till sommartid.

- **Träning** används för att träna modellerna. Den börjar 2023-05-26, när PM2.5-tidsserien vid Dalaplan startade.
- **Validering** används för att jämföra modeller och välja inställningar.
- **Test** används en enda gång, i slutet av projektet, för att utvärdera den slutliga modellen.

Rader där någon feature eller målet saknas tas bort. I träningsdatan är det 1 270 rader (cirka 5,6 %).

## Hur vi undviker dataläckage

**Tidsbaserad uppdelning.** Uppdelningen görs på datum i stället för slumpmässigt. Med en slumpmässig uppdelning skulle modellen tränas på timmar både före och efter de timmar den testas på, och då kunna "se in i framtiden". Det ger för bra resultat.

**Testdatan hålls undan.** Testdata från 2026-05-01 och framåt hämtas och committas inte under utvecklingen, så att ingen kan titta på den eller anpassa modellen efter den av misstag. Modellval och justeringar görs bara utifrån valideringsdatan.

**Bara information som är känd vid prediktionstillfället.** Varje rad innehåller PM2.5 och väder vid tidpunkten *t*, och målet är PM2.5 vid *t + 6 h*. Uppmätt väder vid *t + 6 h* används inte som feature, eftersom det inte är känt när prognosen görs.

**Målet skapas på en komplett timaxel.** Målet skapas med `shift(-6)` efter valideringen, när datan är sorterad i tidsordning med exakt en rad per timme. Först därefter tas rader med saknade värden bort. På så sätt betyder sex rader alltid sex timmar, även runt luckor och omställningen till vintertid.

**Målet skapas separat för varje period.** De sista sex timmarna i träningsperioden skulle annars få sitt mål från valideringsperioden. Eftersom målet skapas inom varje period saknar de raderna mål och tas bort.

**Inga värden fylls i.** Saknade värden interpoleras inte.

## Modeller som jämförs
<!-- Kort lista: baseline och övriga alternativ, en mening om varför var och en valdes. -->

### Baseline

### Alternativ 1

### Alternativ 2

## Resultat

| Modell | MAE | RMSE | Kommentar |
|--------|-----|------|-----------|
| Baseline | | | |
| Alternativ 1 | | | |
| Alternativ 2 | | | |

<!-- Hänvisa till figurer, t.ex. ![Prediktion mot verkligt värde](../results/figures/prediction.png) -->

## Felanalys
<!-- Vilka typer av fel gör modellen? T.ex. vid höga halter, vissa tider på dygnet, vissa årstider eller väderlägen. -->

## Vad resultaten betyder i praktiken
<!-- Vad kan användaren göra med resultatet? Är förbättringen mot baseline tillräcklig för att spela roll? -->

## Slutsatser som resultaten stödjer

## Slutsatser som resultaten inte stödjer
<!-- T.ex. att modellen fungerar på andra platser, andra tidsperioder eller vid extrema händelser. -->

## Begränsningar

**Borttagna rader och luckor.** Rader där någon feature eller målet saknas tas bort. I träningsdatan försvinner 1 270 av 22 825 timmar (cirka 5,6 %), och för valideringsdatan [fylls i senare]. Nederbörd står för flest saknade värden (1 069 timmar), ofta i hela dygnsblock där SMHI har underkänt mätningarna. Luckorna är alltså inte slumpmässigt utspridda, och om de sammanfaller med vissa väderlägen utvärderas modellen på ett något skevt urval av timmar.

**Utvärderingen täcker inte alla timmar.** Eftersom rader med saknade värden tas bort säger resultaten bara hur bra modellen är när all indata finns. Hur lösningen fungerar när indata saknas, till exempel live, ingår inte i utvärderingen.

**Kort tidsperiod.** PM2.5-tidsserien startade i maj 2023, så träningsdatan omfattar bara knappt tre år: tre somrar och höstar men bara två vintrar och vårar. Ovanliga händelser, som episoder med mycket höga halter, förekommer få gånger.

**Validering och test täcker olika årstider.** Valideringsperioden (januari–april) är vinter och vår, medan testperioden (maj och framåt) är sommar och höst. PM2.5 beter sig olika under året, så en modell som presterar bra på valideringsdatan kan prestera annorlunda på testdatan, utan att något är fel.

**Skillnad i datakvalitet mellan perioderna.** Träningsdatan är till största delen kvalitetskontrollerad, medan validerings- och testdatan delvis består av preliminära värden som kan korrigeras i efterhand. En del av prediktionsfelet kan därför bero på mätfel snarare än modellfel, och resultaten kan ändras något om datan hämtas på nytt senare.

**Medelvärden döljer toppar.** MAE och RMSE är genomsnitt över alla timmar. En modell kan ha lågt genomsnittligt fel men ändå missa de kortvariga toppar med höga halter som är viktigast ur hälsosynpunkt.

**En station.** Utvärderingen gäller PM2.5 vid Dalaplan, en station i trafikmiljö, med väderdata från Malmö A cirka 4 km bort. Resultaten säger inte hur modellen fungerar på andra platser.

## När lösningen inte bör användas

## Rekommendation och nästa steg