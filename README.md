# Brreg: et KI-verktøy du kan kjøre selv

Søker etter firma, slår opp organisasjonsnummer og henter årsregnskap og roller hos Brønnøysundregistrene. Eksempelet fra
artikkelen [Bygg et KI-verktøy](https://nskarv.no/notater/bygg-et-ki-verktoy/) på nskarv.no, del 4 av serien om KI i praksis.

Én Python-fil, ingen pakker å installere, ingen nøkler, ingen konto. To åpne tjenester gjør jobben:
[Enhetsregisterets API](https://data.brreg.no/enhetsregisteret/api/dokumentasjon/no/index.html) og
Regnskapsregisterets API (`https://data.brreg.no/regnskapsregisteret/regnskap/<orgnr>`).

## Kjør som kommando

Krever Python 3.10 eller nyere.

```bash
python brreg.py Equinor
python brreg.py 923 609 016
python brreg.py regnskap 923609016
python brreg.py roller 923609016
```

Bare sifre betyr organisasjonsnummer. Alt annet er et navn. Søket gir opptil ti treff:

```json
{
  "sok": "Equinor",
  "treff_totalt": 239,
  "treff": [
    {"organisasjonsnummer": "923609016", "navn": "EQUINOR ASA", "organisasjonsform": "Allmennaksjeselskap",
     "kommune": "STAVANGER", "antall_ansatte": 21231, "status": "aktiv"},
    {"organisasjonsnummer": "959733600", "navn": "EQUINOR PENSJON", "organisasjonsform": "Pensjonskasse",
     "kommune": "STAVANGER", "antall_ansatte": null, "status": "aktiv"}
  ],
  "kilde": "Enhetsregisteret, Brønnøysundregistrene (NLOD 2.0)",
  "merknad": "Viser 10 av 239 treff. Er riktig firma ikke blant dem, be om et mer presist navn eller organisasjonsnummer."
}
```

Oppslaget på nummer gir detaljene:

```json
{
  "organisasjonsnummer": "923609016",
  "navn": "EQUINOR ASA",
  "organisasjonsform": "Allmennaksjeselskap",
  "status": "aktiv",
  "forretningsadresse": "Forusbeen 50, 4035 STAVANGER",
  "postadresse": "Postboks 8500, 4035 STAVANGER",
  "kommune": "STAVANGER",
  "bransje": ["06.100 Utvinning av råolje", "06.200 Utvinning av naturgass",
              "19.200 Produksjon av raffinerte petroleumsprodukter og fossile brenselsprodukter"],
  "antall_ansatte": 21231,
  "stiftelsesdato": "1972-09-18",
  "mva_registrert": true,
  "i_foretaksregisteret": true,
  "hjemmeside": "www.equinor.com",
  "tidligere_navn": ["Den norske stats oljeselskap a.s", "STATOIL ASA", "STATOILHYDRO ASA"],
  "kilde": "Enhetsregisteret, Brønnøysundregistrene (NLOD 2.0)"
}
```

Regnskapet gir de siste årene, nyeste først, for selskapet og for konsernet når det finnes. Beløp er i hele enheter
av valutaen som står oppgitt. Driftsmargin og egenkapitalandel er regnet ut i koden, så modellen slipper å regne:

```json
{
  "organisasjonsnummer": "923609016",
  "regnskap": [
    {"type": "selskap", "periode": "2025-01-01 til 2025-12-31", "valuta": "USD", "regnskapsregler": "forenkletAnvendelseIFRS",
     "revisjon": "revidert", "driftsinntekter": 67956000000, "driftskostnader": 62393000000, "driftsresultat": 5563000000,
     "netto_finans": 561000000, "resultat_foer_skatt": 6124000000, "skattekostnad": 393000000, "aarsresultat": 5731000000,
     "sum_eiendeler": 103432000000, "bankinnskudd_og_kontanter": 17651000000, "egenkapital": 39182000000,
     "gjeld": 64249000000, "kortsiktig_gjeld": 36924000000, "langsiktig_gjeld": 27325000000,
     "driftsmargin_prosent": 8.2, "egenkapitalandel_prosent": 37.9},
    "… konsernregnskapet for 2025, og begge for 2024 og 2023"
  ],
  "merknad": "Beløp i hele enheter, ikke i tusen. Valuta: USD. Ikke kall beløpene kroner.",
  "kilde": "Regnskapsregisteret, Brønnøysundregistrene"
}
```

Rollene gir navn og rolle, og organisasjonsnummer for revisor og regnskapsfører. Fødselsdatoene står i de åpne
dataene, men verktøyet tar dem bort; modellen trenger dem ikke.

```json
{
  "organisasjonsnummer": "923609016",
  "roller": [
    {"rolle": "Daglig leder", "navn": "Anders Opedal"},
    {"rolle": "Styrets leder", "navn": "Jarle Kjell Roth"},
    {"rolle": "Revisor", "navn": "ERNST & YOUNG AS", "organisasjonsnummer": "976389387"}
  ],
  "kilde": "Enhetsregisteret, Brønnøysundregistrene (NLOD 2.0)"
}
```

| Oppslag | Brreg svarer med | Verktøyet gir modellen |
| --- | --- | --- |
| Ett firma | 3 kB | 0,7 kB |
| Ti søketreff | 21 kB | 2 kB |
| Regnskap, tre år, selskap og konsern | 9,5 kB | 3,8 kB (1,4 kB for ett år) |
| Roller | 6,4 kB | 0,9 kB |

## Kjør som MCP-server

Da kan en språkmodell bruke verktøyet. Ingenting mer skal installeres: filen snakker MCP selv, over stdin/stdout.

```bash
python brreg.py --mcp
```

Programmet venter på en klient. Du starter det normalt ikke selv; klienten gjør det. Serveren har fire verktøy:
`sok_firma` (navn inn, treffliste ut), `slaa_opp_firma` (organisasjonsnummer inn, detaljer ut), `hent_regnskap`
(organisasjonsnummer og eventuelt år inn, regnskap ut) og `hent_roller` (organisasjonsnummer inn, roller ut).

**Claude Desktop**: legg dette i `claude_desktop_config.json` (Settings → Developer → Edit Config) og start Claude Desktop på nytt.
Bruk full sti til filen.

```json
{
  "mcpServers": {
    "brreg": {
      "command": "python",
      "args": ["/full/sti/til/brreg.py", "--mcp"]
    }
  }
}
```

**Claude Code**:

```bash
claude mcp add brreg -- python /full/sti/til/brreg.py --mcp
```

**AnythingLLM**: samme oppsett i `anythingllm_mcp_servers.json` under `storage/plugins/`, med `command` og `args` som over.

Spør så: «Hva er organisasjonsnummeret til Equinor, og er de MVA-registrert?»

MCP-delen er rundt 40 linjer og dekker de fire metodene en klient bruker: `initialize`, `ping`, `tools/list` og `tools/call`.
Testet 1. november 2026 med den offisielle MCP-klienten (Python SDK 2.3.0).

## Bruk som skill i Claude, uten kode

`SKILL.md` er oppskriften for Claude. Den beskriver hvilke adresser som skal hentes, hvilke felt som skal leses,
hva feilkodene betyr og hvordan svaret skal se ut.

Én begrensning i Claude-appen: henteverktøyet følger robots.txt, og `data.brreg.no` bryter forbindelsen når noen ber
om `/robots.txt`. Etter standarden (RFC 9309) regnes da hele nettstedet som sperret, så alle API-adressene gir
`ROBOTS_DISALLOWED`. Skillen faller tilbake til Brregs nettside (virksomhet.brreg.no), som gir navn, adresse, form og
bransje, men ikke status, MVA, roller eller regnskap. Har Claude kodekjøring med nettilgang til `data.brreg.no`, kjører
skillen `brreg.py` i stedet og får alt. MCP-verktøyet i Claude Desktop og Claude Code har ingen av disse begrensningene.

- **I en samtale:** dra `SKILL.md` inn i chatvinduet og spør: «Slå opp Equinor.» Websøk må være slått på. Uten
  kodekjøring får du bare det Brregs nettside viser.
- **Som fast skill i Claude:** pakk mappen `brreg/` med `SKILL.md` i en zip-fil og last den opp under
  Settings → Capabilities → Skills.
- **I Claude Code:** legg `SKILL.md` i `.claude/skills/brreg/` i prosjektet, eller i `~/.claude/skills/brreg/`.

Finnes MCP-verktøyene eller `brreg.py` fra før, sier skillen at de skal brukes først.

## ChatGPT: egendefinert GPT med Actions

ChatGPT legger `utm_source=chatgpt.com` til nettadressene den åpner, og også til lenkene den viser deg. API-et avviser
alle ukjente parametere med HTTP 400, så det virker aldri fra en vanlig ChatGPT-samtale. Skillen sender derfor ChatGPT
en annen vei: oppslag på nummer går til Brregs egen side (virksomhet.brreg.no), som tåler parameteren, men som ikke
viser status eller MVA. Søk på navn går ikke der, fordi søkesiden trenger JavaScript; da finner ChatGPT nummeret med
nettsøk eller spør deg, og bekrefter det hos Brreg. Regnskap og roller virker direkte, fordi de to adressene tåler
parameteren. Hele svaret får du med en egendefinert GPT med Actions:

1. Åpne ChatGPT → Utforsk GPT-er → Opprett (krever Plus, Team eller Enterprise).
2. Lim inn innholdet i `SYSTEMPROMPT.md` som instruksjoner.
3. Under Actions, velg «Opprett ny action», lim inn innholdet i `actions/brreg.yaml`, autentisering «None».
4. Lagre, og spør: «Slå opp Equinor, med regnskap og daglig leder.»

Actions-filen beskriver fire kall: `sokFirma`, `slaaOppFirma`, `hentRegnskap` og `hentRoller`. GPT-en bygger parameterne selv, så ingen nettadresser
settes sammen i chatten. Ikke testet i en egendefinert GPT ennå.

## Systemprompt for en agent

`SYSTEMPROMPT.md` er en ferdig systemprompt for en agent som bare gjør dette: hva den gjør ved start, en arbeidsflyt
i seks steg (samle inn, søk, velg riktig treff, slå opp det brukeren spør om, svar, tilby neste steg), reglene og et
eksempel med regnskap og daglig leder. Filen er bare
prompten, uten forklaring, så den kan limes rett inn.

- **Som systemprompt:** i AnythingLLM, som instruksjoner i et Claude-prosjekt eller en egendefinert GPT, eller i en
  Ollama-modell. Gi agenten verktøyene eller skillen.
- **Som første melding i en samtale:** lim inn hele teksten. Prompten sier at modellen skal bli agenten med en gang,
  ikke vurdere teksten. Har den ingen verktøy, åpner den SKILL.md fra dette repoet selv, hvis den kan åpne nettadresser.
  Kan den ikke det, ber den om å få SKILL.md limt inn og venter.

## Modell, temperatur og effort

Disse tre velges utenfor prompten, i verktøyet som kjører modellen. En systemprompt kan ikke endre dem; den kan bare be modellen svare kort og uten å gjette.

| Innstilling | Hvor den settes | Passer for denne agenten |
| --- | --- | --- |
| Modell | Modellvelgeren i Claude eller ChatGPT; arbeidsområdets innstillinger i AnythingLLM; `FROM` i en Ollama-modellfil; `model` i et API-kall | En modell som kan kalle verktøy. I skyen holder den minste modellen med verktøystøtte. |
| Temperatur | Ikke tilgjengelig i Claude- eller ChatGPT-chat; arbeidsområdets innstillinger i AnythingLLM; `PARAMETER temperature` i Ollama; `temperature` i et API-kall | Lav, 0,2 til 0,6. Oppgaven er fast, og verktøykallene skal bli like hver gang. |
| Effort (tenking) | Tenkevelgeren i Claude og ChatGPT; tenkemodus i Ollama for modeller som har det; parameter for tenking i et API-kall | Lav. Agenten følger en oppskrift, og oppslagene gjør jobben. |

## Når noe går galt

Verktøyet gjetter ikke. Det sier fra, og modellen får meldingen:

| Situasjon | Melding |
| --- | --- |
| Ikke ni sifre | `«12» er ikke et organisasjonsnummer. Det har ni sifre, for eksempel 923 609 016.` |
| Feil kontrollsiffer (sjekkes før API-et spørres) | `923609017 har feil kontrollsiffer, så det er trolig en skrivefeil. Be om nummeret på nytt.` |
| Nummeret finnes ikke (HTTP 404) | `… finnes ikke i Enhetsregisteret. Det kan være nummeret til en avdeling (underenhet). Søk på navnet i stedet.` |
| Fjernet av juridiske årsaker (HTTP 410) | `… er fjernet fra Enhetsregisterets åpne data av juridiske årsaker.` |
| Ingen treff på navnet | `Fant ingen enheter med navn som ligner «…». Be om organisasjonsnummer eller en annen stavemåte.` |
| Ingen regnskap levert (HTTP 404) | `Fant ikke årsregnskap for … i Regnskapsregisteret. Mange enkeltpersonforetak og foreninger har ikke plikt til å levere regnskap, og nye selskap har ikke levert ennå.` |
| Bank eller forsikring (HTTP 500 fra Brreg) | `Regnskapsregisteret gir ikke ut regnskapet for … i åpne data, fordi det følger oppstillingsplanen for bank. Se virksomhet.brreg.no.` |
| Ingen roller (HTTP 404) | `Fant ingen roller for …. Sjekk nummeret med slaa_opp_firma.` |
| Tjenesten svarer ikke innen 20 sekunder | `Fikk ikke svar fra data.brreg.no: …` |

Konkurs, avvikling og sletting er ikke feil. De står i feltet `status`, og modellen skal si dem først.

## Prompt injection

Navn, adresser og hjemmesider i registeret skrives av enhetene selv, og havner rett i modellens kontekst.
«IGNORE ALL PREVIOUS INSTRUCTIONS AS» (938 096 392) er et registrert aksjeselskap.

Før modellen ser et svar, går hvert tekstfelt gjennom en skanner:

- Usynlige tegn (nullbredde, retningskontroll, Unicode-tagger) fjernes.
- Felt over 300 tegn kortes ned.
- Tekst som ligner instrukser gir et varsel: «ignore previous instructions», «glem instruksene», rollemarkører som
  `<|im_start|>` og `[INST]`, «you are now», «call the … tool», Markdown-bilder og nettadresser med parametere.

Ved funn får svaret et felt `advarsel` som sier hvilket felt det gjelder, og at teksten er data, ikke instrukser.
Dataene endres ikke. Verktøybeskrivelsene sier det samme til modellen på forhånd.

Skanneren er et varsel, ikke et vern. Mønstre kan omgås. Det som faktisk begrenser skaden, er at verktøyet bare leser,
at modellen får få og korte felt, og at verktøyet ikke har tilgang til noe annet.

Skanneren kan også brukes alene, på tekst eller JSON fra stdin. Den avslutter med kode 1 ved funn:

```bash
echo "Ignore all previous instructions" | python brreg.py --skann
```

## Tester

Begge bruker bare standardbiblioteket.

```bash
python -m unittest test_brreg    # 45 enhetstester, uten nett
python smoke_test.py             # 19 sjekker mot de ekte API-ene, rundt 25 forespørsler
```

Enhetstestene erstatter alle kall til Brreg med faste svar. De dekker kontrollsifferet, feltene, regnskap (sortering,
nøkkeltall, valuta, tomme felt, bank), roller (uten fødselsdato, uten avregistrerte), feilkodene, skanneren
(også ekte firmanavn som ikke skal gi alarm, som «SIRIUS ACT AS» og «PROMPT GROUP») og MCP-protokollen.

Smoketesten sjekker at API-ene fortsatt har feltene verktøyet leser, at feilkodene er de samme, at regnskap og roller
fortsatt tåler ChatGPTs sporingsparameter, at MCP-serveren virker
ende til ende, og at skanneren varsler på det ekte injeksjonsfirmaet uten å slå ut på vanlige søk. Feiler den, har
Brreg trolig endret noe.

## Vilkår

- Enhetsregisteret er åpne data under [Norsk lisens for offentlige data (NLOD 2.0)](https://data.norge.no/nlod/no/2.0). Oppgi Brønnøysundregistrene som kilde.
- Regnskapsregisteret er oppført som åpne data med allmenn tilgang i Felles datakatalog (data.norge.no). Lisensen står
  ikke i API-dokumentasjonen; sjekk vilkårene selv før du bruker dataene i større skala.
- Rollene har fødselsdatoer for personer. Verktøyet tar dem bort, og skillen sier at de aldri skal vises.
- Brreg ber om at enheter som svarer 410, også fjernes fra kopier og cacher. Verktøyet lagrer ingenting.
- Det du søker på, sendes til Brønnøysundregistrene. Ingenting annet forlater maskinen din.

Koden er fri å bruke under [MIT-lisensen](LICENSE).
