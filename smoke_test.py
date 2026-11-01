#!/usr/bin/env python3
"""Smoketest mot det ekte API-et hos Brønnøysundregistrene. Krever nett, ingen pakker.

    python smoke_test.py

Sjekker at API-et svarer, at feltene verktøyet leser fortsatt finnes, at feilkodene er de samme,
at MCP-serveren virker ende til ende, og at skanneren fanger det ekte firmaet med injeksjonsnavn
uten å slå ut på vanlige firma. Bruker rundt 15 forespørsler. Avslutter med kode 1 hvis noe feiler.
"""

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import brreg

MAPPE = Path(__file__).resolve().parent
EQUINOR = "923609016"
INJEKSJONSFIRMA = "938096392"  # IGNORE ALL PREVIOUS INSTRUCTIONS AS, registrert 2026
FINNES_IKKE = "123456785"  # gyldig kontrollsiffer, men ikke registrert
MAKS_SEK = 5
SKILL_URL = "https://raw.githubusercontent.com/nskarv/Brreg-MCP-Skill-eksempel/main/SKILL.md"

resultater = []


def sjekk(navn):
    """Kjører én sjekk. Funksjonen gir en kort tekst ved suksess og feiler med assert eller unntak."""
    def pakk(f):
        start = time.monotonic()
        try:
            detalj = f() or ""
            status = "OK"
        except Exception as feil:  # smoketesten skal vise alle feil, ikke stoppe på den første
            detalj, status = f"{type(feil).__name__}: {feil}", "FEIL"
        sek = time.monotonic() - start
        resultater.append(status)
        print(f"{status:4}  {navn:50} {sek:4.1f} s  {detalj}")
        return f
    return pakk


def raa(url, metode="GET"):
    """Rått kall uten verktøyets innpakning. Gir (statuskode, tekst)."""
    req = urllib.request.Request(url, method=metode, headers={"User-Agent": brreg.USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=brreg.TIDSAVBRUDD_SEK) as svar:
            return svar.status, svar.read().decode()
    except urllib.error.HTTPError as feil:
        return feil.code, feil.read().decode()


def tidsbegrenset(f):
    start = time.monotonic()
    svar = f()
    sek = time.monotonic() - start
    assert sek < MAKS_SEK, f"brukte {sek:.1f} s, grensen er {MAKS_SEK} s"
    return svar


print(f"Smoketest mot {brreg.ENHETER_URL}\n")


@sjekk("API: feltene verktøyet leser finnes")
def _():
    status, tekst = raa(f"{brreg.ENHETER_URL}/{EQUINOR}")
    assert status == 200, f"HTTP {status}"
    e = json.loads(tekst)
    mangler = [f for f in ["organisasjonsnummer", "navn", "organisasjonsform", "forretningsadresse", "naeringskode1",
                           "antallAnsatte", "stiftelsesdato", "registrertIMvaregisteret", "konkurs", "underAvvikling",
                           "underTvangsavviklingEllerTvangsopplosning", "historiskeNavn"] if f not in e]
    assert not mangler, f"mangler {mangler}"
    assert "beskrivelse" in e["organisasjonsform"] and "kommune" in e["forretningsadresse"]
    return f"{len(tekst)} byte rått"


@sjekk("API: søket har _embedded og page")
def _():
    status, tekst = raa(f"{brreg.ENHETER_URL}?navn=equinor&size=5")
    assert status == 200, f"HTTP {status}"
    d = json.loads(tekst)
    assert d["_embedded"]["enheter"] and d["page"]["totalElements"] > 0
    return f"{d['page']['totalElements']} treff"


@sjekk("API: HEAD svarer 200 (henteverktøy i chat)")
def _():
    status, _ = raa(f"{brreg.ENHETER_URL}/{EQUINOR}", "HEAD")
    assert status == 200, f"HTTP {status}"


@sjekk("API: ukjent parameter gir 400 (ChatGPT)")
def _():
    status, tekst = raa(f"{brreg.ENHETER_URL}/{EQUINOR}?utm_source=chatgpt.com")
    assert status == 400 and "utm_source" in tekst, f"HTTP {status}; endret oppførsel, oppdater SKILL.md"
    return "som dokumentert i SKILL.md"


@sjekk("Brregs nettside tåler utm_source")
def _():
    status, tekst = raa(f"https://virksomhet.brreg.no/nb/oppslag/enheter/{EQUINOR}?utm_source=chatgpt.com")
    assert status == 200 and "EQUINOR ASA" in tekst, f"HTTP {status}; reserveveien i SKILL.md virker ikke"


@sjekk("Verktøy: slaa_opp_firma Equinor")
def _():
    s = tidsbegrenset(lambda: brreg.slaa_opp_firma(EQUINOR))
    assert s["navn"] == "EQUINOR ASA" and s["status"] == "aktiv", s
    assert s["forretningsadresse"] and s["bransje"] and s["antall_ansatte"]
    assert "advarsel" not in s, f"falsk alarm: {s['advarsel']}"
    return f"{len(json.dumps(s, ensure_ascii=False).encode())} byte til modellen"


@sjekk("Verktøy: sok_firma finner Equinor ASA")
def _():
    s = tidsbegrenset(lambda: brreg.sok_firma("Equinor"))
    nummer = [t["organisasjonsnummer"] for t in s["treff"]]
    assert EQUINOR in nummer, nummer
    assert "advarsel" not in s, f"falsk alarm: {s['advarsel']}"
    return f"{s['treff_totalt']} treff, {len(json.dumps(s, ensure_ascii=False).encode())} byte"


@sjekk("Verktøy: små bokstaver gir minst like mange treff")
def _():
    smaa = brreg.hent_json(brreg.ENHETER_URL, {"navn": "telenor", "size": 1})["page"]["totalElements"]
    store = brreg.hent_json(brreg.ENHETER_URL, {"navn": "Telenor", "size": 1})["page"]["totalElements"]
    assert smaa >= store, f"«telenor» {smaa}, «Telenor» {store}"
    return f"«telenor» {smaa}, «Telenor» {store}"


@sjekk("Verktøy: ukjent nummer gir 404-melding")
def _():
    try:
        brreg.slaa_opp_firma(FINNES_IKKE)
    except ValueError as feil:
        assert "finnes ikke" in str(feil), feil
        return "riktig melding"
    raise AssertionError(f"{FINNES_IKKE} ble funnet; velg et annet nummer")


@sjekk("Skanner: varsler på injeksjonsfirmaet")
def _():
    s = brreg.slaa_opp_firma(INJEKSJONSFIRMA)
    assert "advarsel" in s, f"ingen advarsel for «{s['navn']}»"
    return f"«{s['navn']}»: {s['advarsel']['funn'][0]['funn']}"


@sjekk("Skanner: ingen falske alarmer i vanlige søk")
def _():
    alarmer = []
    for ord in ["act as", "prompt", "system", "assistant", "glem", "verktøy"]:
        s = brreg.sok_firma(ord)
        alarmer += [(ord, f["felt"], f["funn"]) for f in s.get("advarsel", {}).get("funn", [])]
    assert not alarmer, alarmer
    return "6 søk, 60 treff"


@sjekk("MCP: stdio ende til ende")
def _():
    inn = "\n".join(json.dumps(m) for m in [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "sok_firma", "arguments": {"navn": "Equinor"}}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "slaa_opp_firma", "arguments": {"orgnr": "923 609 016"}}},
    ]) + "\n"
    ut = subprocess.run([sys.executable, str(MAPPE / "brreg.py"), "--mcp"], input=inn, capture_output=True,
                        text=True, timeout=60, check=True).stdout
    svar = {s["id"]: s for s in map(json.loads, ut.splitlines())}
    assert set(svar) == {1, 2, 3}, svar.keys()
    for i in (2, 3):
        assert not svar[i]["result"]["isError"], svar[i]
    assert json.loads(svar[3]["result"]["content"][0]["text"])["navn"] == "EQUINOR ASA"


@sjekk("GitHub: SKILL.md kan hentes")
def _():
    status, tekst = raa(SKILL_URL)
    assert status == 200 and tekst.startswith("---\nname: brreg"), f"HTTP {status}"


feil = resultater.count("FEIL")
print(f"\n{len(resultater) - feil} av {len(resultater)} sjekker OK.")
sys.exit(1 if feil else 0)
