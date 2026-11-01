# Brreg: et KI-verktøy du kan kjøre selv

Søker etter firma og slår opp organisasjonsnummer i Enhetsregisteret hos Brønnøysundregistrene. Eksempelet fra
artikkelen [Bygg et KI-verktøy](https://nskarv.no/notater/bygg-et-ki-verktoy/) på nskarv.no, del 4 av serien om KI i praksis.

Én Python-fil, ingen pakker å installere, ingen nøkler, ingen konto. Én åpen tjeneste gjør jobben:
[Enhetsregisterets API](https://data.brreg.no/enhetsregisteret/api/dokumentasjon/no/index.html).

## Kjør som kommando

Krever Python 3.10 eller nyere.

```bash
python brreg.py Equinor
python brreg.py 923 609 016
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

Brreg svarer med 3 kB for ett firma og 21 kB for ti søketreff. Verktøyet gir modellen 0,7 og 2 kB.

## Kjør som MCP-server

Da kan en språkmodell bruke verktøyet. Ingenting mer skal installeres: filen snakker MCP selv, over stdin/stdout.

```bash
python brreg.py --mcp
```

Programmet venter på en klient. Du starter det normalt ikke selv; klienten gjør det. Serveren har to verktøy:
`sok_firma` (navn inn, treffliste ut) og `slaa_opp_firma` (organisasjonsnummer inn, detaljer ut).

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
hva feilkodene betyr og hvordan svaret skal se ut. Claude kan hente nettsider selv, så den trenger ikke programmet.

- **I en samtale:** dra `SKILL.md` inn i chatvinduet og spør: «Slå opp Equinor.» Websøk må være slått på.
- **Som fast skill i Claude:** pakk mappen `brreg/` med `SKILL.md` i en zip-fil og last den opp under
  Settings → Capabilities → Skills.
- **I Claude Code:** legg `SKILL.md` i `.claude/skills/brreg/` i prosjektet, eller i `~/.claude/skills/brreg/`.

Finnes MCP-verktøyene eller `brreg.py` fra før, sier skillen at de skal brukes først.

## ChatGPT: egendefinert GPT med Actions

ChatGPT legger `utm_source=chatgpt.com` til nettadressene den åpner, og Brreg avviser alle ukjente parametere med
HTTP 400. Skillen fanger opp feilen og ber brukeren lime inn svaret, men i ChatGPT er en egendefinert GPT med Actions enklere:

1. Åpne ChatGPT → Utforsk GPT-er → Opprett (krever Plus, Team eller Enterprise).
2. Lim inn innholdet i `SYSTEMPROMPT.md` som instruksjoner.
3. Under Actions, velg «Opprett ny action», lim inn innholdet i `actions/brreg.yaml`, autentisering «None».
4. Lagre, og spør: «Slå opp Equinor.»

Actions-filen beskriver to kall: `sokFirma` og `slaaOppFirma`. GPT-en bygger parameterne selv, så ingen nettadresser
settes sammen i chatten. Ikke testet i en egendefinert GPT ennå.

## Systemprompt for en agent

`SYSTEMPROMPT.md` er en ferdig systemprompt for en agent som bare gjør dette: hva den gjør ved start, en arbeidsflyt
i seks steg (samle inn, søk, velg riktig treff, slå opp, svar, tilby neste steg), reglene og et eksempel. Filen er bare
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
| Tjenesten svarer ikke innen 20 sekunder | `Fikk ikke svar fra data.brreg.no: …` |

Konkurs, avvikling og sletting er ikke feil. De står i feltet `status`, og modellen skal si dem først.

## Vilkår

- Enhetsregisteret er åpne data under [Norsk lisens for offentlige data (NLOD 2.0)](https://data.norge.no/nlod/no/2.0). Oppgi Brønnøysundregistrene som kilde.
- Brreg ber om at enheter som svarer 410, også fjernes fra kopier og cacher. Verktøyet lagrer ingenting.
- Det du søker på, sendes til Brønnøysundregistrene. Ingenting annet forlater maskinen din.

Koden er fri å bruke under [MIT-lisensen](LICENSE).
