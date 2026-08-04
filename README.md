# Visning af borgere uden NemKonto i Momentum – fjern markering

Automatisering der fjerner markeringen "Borger har ikke NemKonto" i Momentum for borgere,
der ikke længere har en tilhørende ubehandlet NemKonto-opgave i KY (Kommunernes
Ydelsessystem).

## Hvad gør robotten?

1. **Henter borgere** fra Momentum, der er aktivt tagget med "Borger har ikke NemKonto"
   (tag-id `bcb40b6b-66c8-457f-814b-2b7138dd0e93`)
2. **Slår hver borger op** i KY via CPR-nummer for at tjekke, om der stadig er en
   ubehandlet opgave "KH - Ingen NemKonto"
3. **Fjerner markeringen** i Momentum, hvis opgaven ikke længere findes, ved at sætte en
   slutdato på den aktive markering
4. **Rapporterer resultatet** (fuld eller delvis gennemførsel) til den fælles procestracker

## Forudsætninger

- Python ≥ 3.13
- [`uv`](https://docs.astral.sh/uv/) til pakkehåndtering
- Adgang til **Automation Server** (arbejdskø)
- Adgang til **KY** (Kommunernes Ydelsessystem)
- Adgang til **Momentum** (produktion)
- En **RoboA**-konto med adgang til KY
- En **Odense SQL Server**-konto til tracking

## Installation

```sh
uv sync
```

## Konfiguration

Kopiér `.env.example` til `.env` og udfyld følgende:

| Variabel | Beskrivelse |
|---|---|
| `ATS_URL` | URL til Automation Server API |
| `ATS_TOKEN` | Token til Automation Server |
| *(Credentials)* | "RoboA", "Odense SQL Server" og "Momentum - produktion" hentes fra Automation Server Credentials ved kørsel |

## Kørsel

```sh
# Fyld arbejdskøen med borgere, der har markeringen
uv run python main.py --queue

# Behandl arbejdskøen
uv run python main.py
```

## Afhængigheder

| Pakke | Formål |
|---|---|
| `automation-server-client` | Arbejdskø- og processtyring |
| `ky-client` | Opslag i KY (Kommunernes Ydelsessystem) |
| `momentum-client` | Opslag/opdatering af borgere og markeringer i Momentum |
| `odk-tools` | Aktivitetssporing/rapportering |

## Persondatasikkerhed

Robotten behandler personoplysninger på vegne af Odense Kommune, herunder CPR-numre og
borgernes navne.

- CPR-nummer bruges både som item-reference og data-felt i arbejdskøen og optræder derfor
  i klartekst i Automation Server samt i eventuelle fejlbeskeder, der logges
  (`logger.error(f"Error processing item: {data}...")`)
- Ingen personoplysninger må lægges i dette repository — hverken som testdata, i kode
  eller i kommentarer
- Legitimationsoplysninger håndteres udelukkende via miljøvariabler (`.env`, som er
  ekskluderet via `.gitignore`) og Automation Server Credentials
- Der behandles ikke særlige kategorier af personoplysninger (GDPR art. 9) i denne
  proces — kun CPR-nummer og navn, som anvendes til at identificere borgeren og afgøre
  NemKonto-status
