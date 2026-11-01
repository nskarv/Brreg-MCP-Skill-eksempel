# HANDOVER.md

State of the Brreg tool for whoever works on it next, person or Claude Code. Read this first. Keep it a snapshot: replace outdated statements, remove resolved items, keep the log short. History is in git.

Last updated: 2026-11-01

## What this is

The example tool from part 4 of the KI series on nskarv.no (/notater/bygg-et-ki-verktoy/). Part 5 (/notater/nar-en-agent-feiler/) describes what went wrong in the chat apps. The tool looks up Norwegian entities in Brønnøysundregistrene's open APIs.

The files live in two places:

- The website repository, folder `tools/brreg/`. The website serves `brreg.py`, `SKILL.md` and `SYSTEMPROMPT.md` from there, with a copy box on part 4.
- This public repository, github.com/nskarv/Brreg-MCP-Skill-eksempel (MIT).

Edit in the website repository, then copy the folder here and push. The two must stay identical; the smoke test checks that GitHub serves the current `SKILL.md`. Nothing private may go into this folder.

## Files

| File | Purpose |
| --- | --- |
| `brreg.py` | The tool. Python 3.10+, standard library only. Command line and MCP server over stdio (hand-written JSON-RPC: initialize, ping, tools/list, tools/call). |
| `SKILL.md` | Recipe for a model without the tool: which addresses to fetch, which fields to read, what the errors mean, what to do in the Claude and ChatGPT apps. |
| `SYSTEMPROMPT.md` | Instructions for an agent that only does lookups. |
| `actions/brreg.yaml` | OpenAPI 3.1 for a custom GPT with Actions: sokFirma, slaaOppFirma, hentRegnskap, hentRoller. |
| `test_brreg.py` | 45 unit tests, no network. |
| `smoke_test.py` | 20 checks against the live APIs, about 25 requests. |
| `README.md` | User documentation in Norwegian. |

## The four tools

| Tool | Source | Notes |
| --- | --- | --- |
| `sok_firma(navn)` | `data.brreg.no/enhetsregisteret/api/enheter?navn=` | Sends the name in lower case: Brreg returns more hits that way ("telenor" 304, "Telenor" 95). Up to 10 hits. |
| `slaa_opp_firma(orgnr)` | `.../enheter/<orgnr>` | MOD11 check digit tested before the call. One `status` field for konkurs, avvikling, tvangsavvikling and sletting. 404 unknown, 410 removed for legal reasons. |
| `hent_regnskap(orgnr, aar=None)` | `data.brreg.no/regnskapsregisteret/regnskap/<orgnr>` | Last years (usually three), company and group, newest first. Margin and equity ratio computed in code. Currency always stated: Equinor reports in USD. 404 no accounts filed; 500 "oppstillingsplan som ikke er stottet" for banks and insurers. |
| `hent_roller(orgnr)` | `.../enheter/<orgnr>/roller` | Drops birth dates and deregistered or resigned roles. |

Every text field goes through the prompt injection scanner before the model sees it: invisible characters stripped, fields over 300 characters truncated, instruction-like text flagged in an `advarsel` field without changing the data. A registered company is named "IGNORE ALL PREVIOUS INSTRUCTIONS AS" (938 096 392); it is the live test case. The patterns are tuned so that real names like "SIRIUS ACT AS" and "PROMPT GROUP" do not flag.

## Where it works

| Environment | Search and lookup | Accounts and roles | Notes |
| --- | --- | --- | --- |
| Command line, MCP (Claude Desktop, Claude Code, AnythingLLM) | Yes | Yes | Tested with the official MCP Python client (SDK 2.3.0). |
| Custom GPT with Actions | Expected | Expected | Not tested. |
| ChatGPT app, fetch only | No: `utm_source` added, API answers 400 | Yes: these endpoints accept the parameter | Falls back to virksomhet.brreg.no for basic facts. Lookups confirmed working by the owner. |
| Claude app, fetch only | No | No | `data.brreg.no` drops the connection on `/robots.txt`; under RFC 9309 the whole host counts as disallowed (`ROBOTS_DISALLOWED`). Falls back to virksomhet.brreg.no. |
| Claude app with code execution | Expected, if network access to data.brreg.no is allowed | Expected | Not tested. |

virksomhet.brreg.no (Brreg's website) accepts `utm_source` and allows all robots, but its visible text has only name, number, addresses, form and industry code. Its search needs JavaScript.

## Data terms

- Enhetsregisteret: NLOD 2.0, stated in its API documentation.
- Regnskapsregisteret: listed as open data with public access in Felles datakatalog; the licence is not stated in its API documentation, so the tool's source label makes no NLOD claim.

## Open items

1. Test the custom GPT with `actions/brreg.yaml` (needs a ChatGPT Plus, Team or Enterprise account).
2. Test the Claude app with code execution and network access to data.brreg.no.
3. Test accounts and roles in the ChatGPT app.
4. `SYSTEMPROMPT.md` is only a true system prompt when set through an API call, Claude Code or a CLI. Pasted into the ChatGPT, Claude or Cowork apps it becomes a user message or project instructions. Fix the wording at the top of `SYSTEMPROMPT.md` and in the README section "Systemprompt for en agent". (Part 4 and part 5 on the website already say this.)

## Before every push

```bash
python -m unittest test_brreg
python smoke_test.py
```

The last smoke check (SKILL.md on GitHub) fails until the push has gone out and GitHub's cache (up to five minutes) has refreshed. Run it again after the push.

## Log

- 2026-11-01: accounts and roles added; chat-app sections rewritten after the owner's tests in ChatGPT and Claude; invisible characters in the source replaced with escapes; this file added.
