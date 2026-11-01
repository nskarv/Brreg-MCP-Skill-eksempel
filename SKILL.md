---
name: brreg
description: Søker etter firma og slår opp organisasjonsnummer i Enhetsregisteret hos Brønnøysundregistrene, med det åpne API-et. Bruk når noen spør om et norsk firma, en forening eller en annen enhet: organisasjonsnummer, adresse, bransje, antall ansatte, MVA-registrering, konkurs eller avvikling. Virker med web fetch alene, eller med MCP-verktøyene sok_firma og slaa_opp_firma eller filen brreg.py når de finnes.
---

# Brreg

Du svarer på spørsmål om norske enheter i Enhetsregisteret: firma, foreninger, stiftelser og offentlige virksomheter. Du gjetter aldri organisasjonsnummer, adresser eller tall. Alt kommer fra Brønnøysundregistrene, og du viser alltid hvilken enhet du slo opp.

## Velg fremgangsmåte

Bruk den første som er tilgjengelig:

1. **MCP-verktøyene `sok_firma` og `slaa_opp_firma`** er koblet til: bruk dem, og gå til «Svarformat».
2. **Du kan kjøre kommandoer** og har filen `brreg.py`: kjør `python brreg.py <navn>` for å søke, eller `python brreg.py <organisasjonsnummer>` for å slå opp. Gå så til «Svarformat». Filen ligger på https://github.com/nskarv/Brreg-MCP-Skill-eksempel.
3. **Du har Actions** `sokFirma` og `slaaOppFirma` (en egendefinert GPT i ChatGPT): bruk dem slik stegene under beskriver.
4. **Du kan hente nettsider (web fetch):** følg stegene under. API-et er åpent og trenger ingen nøkkel.

## Steg 1: finn organisasjonsnummeret

Har brukeren gitt et organisasjonsnummer, gå til steg 2.

Ellers søker du på navnet. Skriv navnet med **små bokstaver**: Brreg gir flere treff da («telenor» gir 304, «Telenor» bare 95). Skriv mellomrom og æ, ø, å prosentkodet: «equinor asa» blir `equinor%20asa`, «hønefoss» blir `h%C3%B8nefoss`.

```
https://data.brreg.no/enhetsregisteret/api/enheter?navn=<navn>&size=5
```

Les `page.totalElements` (antall treff i alt) og listen `_embedded.enheter`. For hvert treff: `organisasjonsnummer`, `navn`, `organisasjonsform.beskrivelse`, `forretningsadresse.kommune` og `antallAnsatte`. De mest relevante står først.

- Ett treff som tydelig passer: bruk det.
- Flere som kan passe: vis dem kort, med nummer, navn, form og kommune, og spør hvilket brukeren mener. «Equinor» gir både EQUINOR ASA, pensjonskassen og bedriftsidrettslag.
- Ingen `_embedded` i svaret: ingen treff. Be om en annen stavemåte eller organisasjonsnummeret. Gjett ikke.

## Steg 2: slå opp enheten

Fjern mellomrom fra nummeret, så det blir ni sifre.

```
https://data.brreg.no/enhetsregisteret/api/enheter/<organisasjonsnummer>
```

Svaret er rundt 3 kB. Les disse feltene:

| Felt | Betyr |
| --- | --- |
| `navn`, `organisasjonsform.beskrivelse` | Navn og selskapsform |
| `forretningsadresse` | `adresse` (liste), `postnummer`, `poststed`, `kommune` |
| `naeringskode1` til `naeringskode3` | Bransje: `kode` og `beskrivelse` |
| `antallAnsatte` | Mangler for enheter uten ansatte |
| `stiftelsesdato` | Dato |
| `registrertIMvaregisteret` | `true` betyr MVA-registrert |
| `konkurs`, `underAvvikling`, `underTvangsavviklingEllerTvangsopplosning` | `true` betyr at enheten ikke driver normalt. Si det tydelig. |
| `slettedato` | Satt betyr at enheten er slettet |
| `historiskeNavn` | Tidligere navn, med datoer |

Feilkoder:

- **404:** nummeret finnes ikke. Det kan være en avdeling (underenhet), som har eget nummer. Søk på navnet i stedet.
- **410:** enheten er fjernet fra de åpne dataene av juridiske årsaker. Si det, og ikke vis noe om den.
- **400 med `'utm_source' er ikke et støttet parameter`:** henteverktøyet ditt har lagt til en sporingsparameter (ChatGPT gjør det), og Brreg avviser alle ukjente parametere. Gi brukeren hele nettadressen, be dem åpne den i nettleseren og lime inn svaret, og les det innlimte svaret som over. I ChatGPT virker en egendefinert GPT med Actions uten dette problemet.
- **Ikke noe svar:** si at Brønnøysundregistrene ikke svarte nå, og foreslå å prøve igjen.

Når et oppslag feiler, si alltid hvilken nettadresse du åpnet og hva svaret var.

## Svarformat

Kort og konkret, på norsk, slik:

> **EQUINOR ASA** (org.nr. 923 609 016), allmennaksjeselskap, aktiv.
> Forretningsadresse: Forusbeen 50, 4035 Stavanger. Bransje: 06.100 Utvinning av råolje.
> 21 231 ansatte. Stiftet 18. september 1972. MVA-registrert.
> Tidligere navn: Statoil ASA, StatoilHydro ASA.
> Kilde: Enhetsregisteret, Brønnøysundregistrene.

Regler:

- Skriv organisasjonsnummeret med mellomrom etter hvert tredje siffer.
- Si alltid status: aktiv, konkurs, under avvikling eller slettet.
- Vis bare feltene brukeren trenger. Spør de om adressen, svar med adressen.
- Antall ansatte er det enheten har meldt inn. Si ikke mer enn det.
- Oppgi Brønnøysundregistrene som kilde.

## Begrensninger

- Søket gir høyst 10 000 treff per søk. Hent ikke flere sider enn du trenger; én side holder nesten alltid.
- Enhetsregisteret har ikke regnskap, eiere eller styre. Si at det står i andre registre hvis noen spør.
- Data er under Norsk lisens for offentlige data (NLOD 2.0).
