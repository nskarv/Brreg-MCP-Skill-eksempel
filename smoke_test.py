#!/usr/bin/env python3
"""Smoketest mot det ekte API-et hos Brønnøysundregistrene. Krever nett, ingen pakker.

    python smoke_test.py

Sjekker at API-et svarer, at feltene verktøyet leser fortsatt finnes, at feilkodene er de samme,
at MCP-serveren virker ende til ende, og at skanneren fanger det ekte firmaet med injeksjonsnavn
uten å slå ut på vanlige firma. Bruker rundt 25 forespørsler. Avslutter med kode 1 hvis noe feiler.
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
BANK = "937889275"  # SpareBank 1 Ringerike Hadeland: oppstillingsplan BANK, som det åpne API-et ikke gir ut
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


@sjekk("ChatGPT-veien: Brregs nettside tåler utm_source")
def _():
    status, tekst = raa(f"https://virksomhet.brreg.no/nb/oppslag/enheter/{EQUINOR}?utm_source=chatgpt.com")
    assert status == 200, f"HTTP {status}; ChatGPT-veien i SKILL.md virker ikke"
    # Skillen lover at navn, nummer, adresse og organisasjonsform står i teksten, ikke bare i skript.
    for ord in ["EQUINOR ASA", "923 609 016", "Forusbeen", "Allmennaksjeselskap"]:
        assert ord in tekst, f"«{ord}» mangler på siden; oppdater «ChatGPT uten Actions» i SKILL.md"
    return f"{len(tekst) // 1000} kB"


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


@sjekk("Regnskap API: feltene verktøyet leser finnes")
def _():
    status, tekst = raa(f"{brreg.REGNSKAP_URL}/{EQUINOR}")
    assert status == 200, f"HTTP {status}"
    r = json.loads(tekst)[0]
    mangler = [f for f in ["regnskapstype", "regnskapsperiode", "valuta", "revisjon", "regnkapsprinsipper",
                           "resultatregnskapResultat", "egenkapitalGjeld", "eiendeler"] if f not in r]
    assert not mangler, f"mangler {mangler}"
    assert "driftsinntekter" in r["resultatregnskapResultat"]["driftsresultat"]
    return f"{len(tekst)} byte rått"


@sjekk("ChatGPT-veien: regnskap og roller tåler utm_source")
def _():
    for url in [f"{brreg.REGNSKAP_URL}/{EQUINOR}", f"{brreg.ENHETER_URL}/{EQUINOR}/roller"]:
        status, _ = raa(url + "?utm_source=chatgpt.com")
        assert status == 200, f"{url}: HTTP {status}; oppdater «ChatGPT uten Actions» i SKILL.md"
    return "begge 200"


@sjekk("Verktøy: hent_regnskap Equinor")
def _():
    s = tidsbegrenset(lambda: brreg.hent_regnskap(EQUINOR))
    typer = {r["type"] for r in s["regnskap"]}
    assert typer == {"selskap", "konsern"}, typer
    nyeste = s["regnskap"][0]
    assert nyeste["driftsinntekter"] and nyeste["egenkapitalandel_prosent"], nyeste
    assert "USD" in s["merknad"], s["merknad"]
    return f"{len(s['regnskap'])} regnskap, nyeste {nyeste['periode'][-10:]}, {len(json.dumps(s, ensure_ascii=False).encode())} byte"


@sjekk("Verktøy: hent_regnskap gir klar melding for bank")
def _():
    try:
        brreg.hent_regnskap(BANK)
    except ValueError as feil:
        assert "bank" in str(feil), feil
        return "riktig melding"
    raise AssertionError("Brreg gir nå ut bankregnskap; oppdater verktøyet og SKILL.md")


@sjekk("Verktøy: hent_regnskap 404 for ukjent nummer")
def _():
    try:
        brreg.hent_regnskap(FINNES_IKKE)
    except ValueError as feil:
        assert "Fant ikke årsregnskap" in str(feil), feil
        return "riktig melding"
    raise AssertionError(f"{FINNES_IKKE} har regnskap; velg et annet nummer")


@sjekk("Verktøy: hent_roller Equinor, uten fødselsdato")
def _():
    s = tidsbegrenset(lambda: brreg.hent_roller(EQUINOR))
    roller = {r["rolle"] for r in s["roller"]}
    assert {"Daglig leder", "Styrets leder", "Revisor"} <= roller, roller
    assert "fodselsdato" not in json.dumps(s), "fødselsdato lekker gjennom"
    return f"{len(s['roller'])} roller, {len(json.dumps(s, ensure_ascii=False).encode())} byte"


@sjekk("MCP: stdio ende til ende")
def _():
    inn = "\n".join(json.dumps(m) for m in [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "sok_firma", "arguments": {"navn": "Equinor"}}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "slaa_opp_firma", "arguments": {"orgnr": "923 609 016"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "hent_regnskap", "arguments": {"orgnr": EQUINOR, "aar": 2025}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "hent_roller", "arguments": {"orgnr": EQUINOR}}},
    ]) + "\n"
    ut = subprocess.run([sys.executable, str(MAPPE / "brreg.py"), "--mcp"], input=inn, capture_output=True,
                        text=True, timeout=60, check=True).stdout
    svar = {s["id"]: s for s in map(json.loads, ut.splitlines())}
    assert set(svar) == {1, 2, 3, 4, 5}, svar.keys()
    for i in (2, 3, 4, 5):
        assert not svar[i]["result"]["isError"], svar[i]
    assert json.loads(svar[3]["result"]["content"][0]["text"])["navn"] == "EQUINOR ASA"


@sjekk("GitHub: SKILL.md kan hentes")
def _():
    status, tekst = raa(SKILL_URL + "?utm_source=chatgpt.com")  # slik ChatGPT henter den
    assert status == 200 and tekst.startswith("---\nname: brreg"), f"HTTP {status}"
    assert "ChatGPT uten Actions" in tekst, "GitHub har en eldre SKILL.md; push endringene"


feil = resultater.count("FEIL")
print(f"\n{len(resultater) - feil} av {len(resultater)} sjekker OK.")
sys.exit(1 if feil else 0)
