#!/usr/bin/env python3
"""Brreg: søk etter firma og slå opp organisasjonsnummer i Enhetsregisteret.

Eksempelet fra «Bygg et KI-verktøy», del 4 av serien om KI i praksis på nskarv.no.
Bruker Brønnøysundregistrenes åpne API, uten nøkkel og uten konto. Krever bare
Python 3.10 eller nyere, ingen pakker.

Som kommando:
    python brreg.py Equinor
    python brreg.py 923609016

Som MCP-server for Claude Desktop, Claude Code, AnythingLLM og lignende:
    python brreg.py --mcp
"""

import inspect
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

ENHETER_URL = "https://data.brreg.no/enhetsregisteret/api/enheter"
USER_AGENT = "brreg-eksempel (nskarv.no)"
TIDSAVBRUDD_SEK = 20
MAKS_TREFF = 10
KILDE = "Enhetsregisteret, Brønnøysundregistrene (NLOD 2.0)"


class TjenesteFeil(RuntimeError):
    """Feil fra Brønnøysundregistrene, med HTTP-koden når det finnes en."""

    def __init__(self, melding: str, kode: int | None = None):
        super().__init__(melding)
        self.kode = kode


def hent_json(url: str, params: dict | None = None) -> dict:
    """Én GET-forespørsel som returnerer JSON. Feiler med en lesbar melding."""
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIDSAVBRUDD_SEK) as svar:
            return json.load(svar)
    except urllib.error.HTTPError as feil:
        raise TjenesteFeil(f"data.brreg.no svarte med HTTP {feil.code} {feil.reason}", feil.code) from feil
    except urllib.error.URLError as feil:
        raise TjenesteFeil(f"Fikk ikke svar fra data.brreg.no: {getattr(feil, 'reason', feil)}") from feil


def rens_orgnr(tekst: str) -> str:
    """Gir ni sifre uten mellomrom, eller feiler. Kontrollsifferet sjekkes her, før API-et spørres."""
    orgnr = "".join(t for t in str(tekst) if not t.isspace() and t not in ".-")
    if len(orgnr) != 9 or not orgnr.isdigit():
        raise ValueError(f"«{tekst}» er ikke et organisasjonsnummer. Det har ni sifre, for eksempel 923 609 016.")
    # Modulus 11 med vektene 3 2 7 6 5 4 3 2. Rest 10 betyr at nummeret ikke kan finnes.
    rest = 11 - sum(int(s) * v for s, v in zip(orgnr, [3, 2, 7, 6, 5, 4, 3, 2])) % 11
    if rest == 10 or rest % 11 != int(orgnr[8]):
        raise ValueError(f"{orgnr} har feil kontrollsiffer, så det er trolig en skrivefeil. Be om nummeret på nytt.")
    return orgnr


def _adresse(a: dict | None) -> str | None:
    if not a:
        return None
    linjer = [*(a.get("adresse") or []), f"{a.get('postnummer', '')} {a.get('poststed', '')}".strip()]
    return ", ".join(l for l in linjer if l)


def _status(e: dict) -> str:
    if e.get("slettedato"):
        return f"slettet {e['slettedato']}"
    if e.get("konkurs"):
        return "konkurs"
    if e.get("underTvangsavviklingEllerTvangsopplosning"):
        return "under tvangsavvikling"
    if e.get("underAvvikling"):
        return "under avvikling"
    return "aktiv"


def _sted(e: dict) -> str | None:
    a = e.get("forretningsadresse") or e.get("postadresse") or {}
    return a.get("kommune")


def sok_firma(navn: str) -> dict:
    """Søker etter firma og andre enheter i Enhetsregisteret på navn.

    Bruk når noen nevner et firma uten organisasjonsnummer. Gir opptil ti treff med
    organisasjonsnummer, navn, organisasjonsform, kommune og antall ansatte, mest
    relevante først. Velg riktig treff, og spør brukeren hvis flere kan passe. Hent
    så detaljene med slaa_opp_firma.
    """
    navn = (navn or "").strip()
    if len(navn) < 2:
        raise ValueError("Skriv minst to tegn av navnet.")
    # Brreg gir flere treff på små bokstaver: «telenor» gir 304, «Telenor» bare 95.
    data = hent_json(ENHETER_URL, {"navn": navn.lower(), "size": MAKS_TREFF})
    enheter = (data.get("_embedded") or {}).get("enheter") or []
    totalt = (data.get("page") or {}).get("totalElements", len(enheter))
    if not enheter:
        raise ValueError(f"Fant ingen enheter med navn som ligner «{navn}». Be om organisasjonsnummer eller en annen stavemåte.")
    svar = {
        "sok": navn,
        "treff_totalt": totalt,
        "treff": [
            {
                "organisasjonsnummer": e["organisasjonsnummer"],
                "navn": e.get("navn"),
                "organisasjonsform": (e.get("organisasjonsform") or {}).get("beskrivelse"),
                "kommune": _sted(e),
                "antall_ansatte": e.get("antallAnsatte"),
                "status": _status(e),
            }
            for e in enheter
        ],
        "kilde": KILDE,
    }
    if totalt > len(enheter):
        svar["merknad"] = f"Viser {len(enheter)} av {totalt} treff. Er riktig firma ikke blant dem, be om et mer presist navn eller organisasjonsnummer."
    return svar


def slaa_opp_firma(orgnr: str) -> dict:
    """Henter fakta om én enhet i Enhetsregisteret fra organisasjonsnummeret.

    Bruk når du har et organisasjonsnummer, fra brukeren eller fra sok_firma. Gir navn,
    organisasjonsform, status (aktiv, konkurs, under avvikling eller slettet), adresse,
    bransje, antall ansatte, stiftelsesdato, om enheten er MVA-registrert, og tidligere navn.
    Nummeret kan skrives med eller uten mellomrom.
    """
    orgnr = rens_orgnr(orgnr)
    try:
        e = hent_json(f"{ENHETER_URL}/{orgnr}")
    except TjenesteFeil as feil:
        if feil.kode == 404:
            raise ValueError(
                f"{orgnr} finnes ikke i Enhetsregisteret. Det kan være nummeret til en avdeling (underenhet). "
                "Søk på navnet i stedet."
            ) from feil
        if feil.kode == 410:  # slik svarer Brreg når en enhet er fjernet av juridiske årsaker
            raise ValueError(f"{orgnr} er fjernet fra Enhetsregisterets åpne data av juridiske årsaker.") from feil
        raise
    return {
        "organisasjonsnummer": e["organisasjonsnummer"],
        "navn": e.get("navn"),
        "organisasjonsform": (e.get("organisasjonsform") or {}).get("beskrivelse"),
        "status": _status(e),
        "forretningsadresse": _adresse(e.get("forretningsadresse")),
        "postadresse": _adresse(e.get("postadresse")),
        "kommune": _sted(e),
        "bransje": [
            f"{n['kode']} {n['beskrivelse']}"
            for n in (e.get(f"naeringskode{i}") for i in (1, 2, 3))
            if n
        ],
        "antall_ansatte": e.get("antallAnsatte"),
        "stiftelsesdato": e.get("stiftelsesdato"),
        "mva_registrert": e.get("registrertIMvaregisteret", False),
        "i_foretaksregisteret": e.get("registrertIForetaksregisteret", False),
        "hjemmeside": e.get("hjemmeside"),
        "tidligere_navn": list(dict.fromkeys(h["navn"] for h in e.get("historiskeNavn") or [])),
        "kilde": KILDE,
    }


FUNKSJONER = {f.__name__: f for f in (sok_firma, slaa_opp_firma)}
VERKTOY = [
    {
        "name": "sok_firma",
        "description": inspect.cleandoc(sok_firma.__doc__),
        "inputSchema": {
            "type": "object",
            "properties": {"navn": {"type": "string", "description": "Hele eller deler av navnet, for eksempel «Equinor»"}},
            "required": ["navn"],
        },
    },
    {
        "name": "slaa_opp_firma",
        "description": inspect.cleandoc(slaa_opp_firma.__doc__),
        "inputSchema": {
            "type": "object",
            "properties": {"orgnr": {"type": "string", "description": "Organisasjonsnummer med ni sifre, for eksempel «923 609 016»"}},
            "required": ["orgnr"],
        },
    },
]


def svar_paa(melding: dict) -> dict | None:
    """Behandler én MCP-melding (JSON-RPC 2.0). Returnerer svaret, eller None for varsler."""
    metode, params, mid = melding.get("method"), melding.get("params") or {}, melding.get("id")
    if mid is None:  # varsel, for eksempel notifications/initialized: ingen respons
        return None
    if metode == "initialize":
        resultat = {
            "protocolVersion": params.get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "brreg", "version": "1.0"},
        }
    elif metode == "ping":
        resultat = {}
    elif metode == "tools/list":
        resultat = {"tools": VERKTOY}
    elif metode == "tools/call" and params.get("name") in FUNKSJONER:
        try:
            svar = FUNKSJONER[params["name"]](**(params.get("arguments") or {}))
            resultat = {"content": [{"type": "text", "text": json.dumps(svar, ensure_ascii=False)}], "isError": False}
        except (ValueError, RuntimeError, TypeError) as feil:
            # Meldingen går tilbake til modellen som en feil, så den kan spørre brukeren i stedet for å gjette.
            resultat = {"content": [{"type": "text", "text": str(feil)}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Ukjent metode: {metode}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": resultat}


def kjor_mcp() -> None:
    """Kjører som MCP-server over stdio: én JSON-melding per linje inn, én per linje ut.

    Klienten (Claude Desktop, Claude Code, AnythingLLM) starter programmet selv.
    Hele protokollen som trengs her er fire metoder, derfor ingen biblioteker.
    """
    for linje in sys.stdin:
        if not linje.strip():
            continue
        svar = svar_paa(json.loads(linje))
        if svar is not None:
            sys.stdout.write(json.dumps(svar, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    if sys.argv[1:] == ["--mcp"]:
        kjor_mcp()
    elif len(sys.argv) >= 2:
        tekst = " ".join(sys.argv[1:])
        # Bare sifre, mellomrom og punktum betyr organisasjonsnummer. Alt annet er et navn.
        try:
            if all(t.isdigit() or t in " .-" for t in tekst):
                svar = slaa_opp_firma(tekst)
            else:
                svar = sok_firma(tekst)
            print(json.dumps(svar, ensure_ascii=False, indent=2))
        except (ValueError, RuntimeError) as feil:
            print(f"Feil: {feil}", file=sys.stderr)
            sys.exit(1)
    else:
        print(__doc__)
        sys.exit(2)
