# RBFA voor Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/Maffiow/RBFA/actions/workflows/validate.yaml/badge.svg)](https://github.com/Maffiow/RBFA/actions/workflows/validate.yaml)
[![Release](https://img.shields.io/github/v/release/Maffiow/RBFA)](https://github.com/Maffiow/RBFA/releases)

[English](README.md) · **Nederlands**

Volg je Belgische voetbalploeg in Home Assistant: de wedstrijdkalender, de volgende en de
vorige wedstrijd, de reeks met klassement en fairplay-stand, en de spelerslijsten van elke
ploeg in de reeks. De gegevens komen van de website van de Koninklijke Belgische Voetbalbond
([RBFA](https://www.rbfa.be/)), die ook [Voetbal Vlaanderen](https://www.voetbalvlaanderen.be/)
en [ACFF](https://www.acff.be/) bedient.

Het werkt voor elke ploeg die een pagina heeft op rbfa.be, van het eerste elftal tot de
jongste jeugdploegen.

## Inhoud

- [Wat je krijgt](#wat-je-krijgt)
- [Installatie](#installatie)
- [Configuratie](#configuratie)
- [Entiteiten](#entiteiten)
- [Attributen](#attributen)
- [Hoe en wanneer de gegevens ververst worden](#hoe-en-wanneer-de-gegevens-ververst-worden)
- [Jeugdreeksen: geen klassement, wel fairplay](#jeugdreeksen-geen-klassement-wel-fairplay)
- [Voorbeeldkaarten](#voorbeeldkaarten)
- [Updates](#updates)
- [Problemen oplossen](#problemen-oplossen)
- [Een nieuwe versie uitbrengen (beheerders)](#een-nieuwe-versie-uitbrengen-beheerders)

## Wat je krijgt

| | |
|---|---|
| 📅 **Kalender** | Elke wedstrijd van het seizoen als kalenderitem, met locatie, reeks en (als die gepubliceerd is) de uitslag. Bruikbaar in het kalenderpaneel, in kalenderkaarten en als trigger voor automatiseringen. |
| ⏭️ **Volgende wedstrijd** | Start- en eindtijd, thuis- en uitploeg met clublogo, locatie, reeks, scheidsrechter en het wedstrijdnummer van de RBFA. |
| ⏮️ **Vorige wedstrijd** | Dezelfde sensoren voor de laatste wedstrijd, met doelpunten en strafschoppen als de RBFA die publiceert. |
| 🏆 **Klassement** | Het klassement van de reeks als attribuut: positie, ploeg, logo en aantal gespeelde wedstrijden. |
| 🤝 **Fairplay** | Het fairplay-percentage van elke ploeg in de reeks. |
| 👥 **Spelerslijsten** | Spelers (met gespeelde wedstrijden en doelpunten) en staf (met hun functie) van *elke* ploeg in de reeks. |
| 🧑‍⚖️ **Scheidsrechter** | De scheidsrechter van de wedstrijd, als er een is aangeduid. |

Alles is alleen-lezen: de integratie wijzigt niets op rbfa.be en heeft geen account nodig.

## Installatie

### HACS (aanbevolen)

[![Open je Home Assistant en open deze repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Maffiow&repository=RBFA&category=integration)

Of handmatig:

1. Open in Home Assistant **HACS** → menu (⋮) → **Aangepaste repositories**.
2. Repository: `https://github.com/Maffiow/RBFA`, type: **Integratie** → **Toevoegen**.
3. Zoek **RBFA** in HACS, klik op **Downloaden** en herstart Home Assistant.

> Gebruik je al een andere `rbfa`-integratie? Verwijder die eerst in HACS (of wis
> `/config/custom_components/rbfa`) en installeer daarna deze. Je bestaande configuratie
> en entiteits-ID's blijven behouden.

### Handmatig

Kopieer `custom_components/rbfa` naar `/config/custom_components/rbfa` en herstart Home Assistant.

## Configuratie

**Instellingen → Apparaten & diensten → Integratie toevoegen → RBFA**

![Configuratie](https://raw.githubusercontent.com/Maffiow/RBFA/main/images/config-dialog.png)

| Veld | Uitleg |
|---|---|
| Identiteit van het team | Het nummer na `ploeg` in de URL van de ploegpagina. Voor `https://www.rbfa.be/nl/club/1932/ploeg/378177/overzicht` is dat `378177`. |
| Alternatieve naam | Optionele naam voor de kalender (standaard: `club \| ploeg`, bv. `EENDRACHT MECHELEN A/D MAAS \| U10 A`). |
| Duur van de wedstrijd | Duur in minuten, inclusief rust. Bepaalt de eindtijd van kalenderitems en wanneer een wedstrijd als gespeeld telt. |
| Toon uitslagen en rangschikking | Haalt het klassement, de fairplay-stand en de spelerslijsten van de reeks op. |
| Toon scheidsrechter | Haalt de scheidsrechter op en maakt de scheidsrechter-sensoren aan. |

Alle instellingen behalve de ploeg kun je later wijzigen via **Configureren** bij de integratie.
Wil je meerdere ploegen volgen, voeg de integratie dan één keer per ploeg toe.

> **Ploegnummers veranderen elk seizoen.** Zie je na de zomer "Team … not found" in het
> logboek, verwijder dan de integratie en voeg ze opnieuw toe met het nieuwe nummer van rbfa.be.

## Entiteiten

Elke ingestelde ploeg krijgt één kalender en twee sets sensoren: één voor de **volgende**
wedstrijd en één voor de **vorige** wedstrijd.

| Entiteit | Status | Opmerking |
|---|---|---|
| Kalender | `aan` terwijl er een wedstrijd bezig is | Heet `club \| ploeg` of je alternatieve naam. Bevat alle wedstrijden van het seizoen. |
| Start | Aftrap (tijdstip) | |
| Eind | Aftrap + duur (tijdstip) | |
| Thuis | Naam van de thuisploeg | De afbeelding van de entiteit is het clublogo. |
| Uit | Naam van de uitploeg | De afbeelding van de entiteit is het clublogo. |
| Locatie | Adres van het terrein, op drie regels | Leeg tot de RBFA het publiceert. |
| Reeks | Naam van de reeks | De afbeelding is het logo van de organisator. Bevat het klassement en de spelerslijsten. |
| Scheidsrechter | Naam van de scheidsrechter | Alleen als *Toon scheidsrechter* aanstaat; `onbekend` als er niemand is aangeduid. |
| Wedstrijd ID | Wedstrijdnummer van de RBFA | Handig voor een link naar `https://www.rbfa.be/nl/wedstrijd/<id>`. |

Goed om te weten:

- **Sensoren staan standaard uit.** Zet de sensoren die je nodig hebt aan onder
  **Instellingen → Apparaten & diensten → RBFA → entiteiten**.
- **Entiteits-ID's volgen de taal van je Home Assistant.** In het Nederlands krijg je
  `sensor.thuis`, in het Engels `sensor.home_team`. De voorbeelden hieronder gebruiken de
  Nederlandse ID's.
- **Twee sets, één achtervoegsel.** Beide sets hebben dezelfde namen, dus Home Assistant geeft
  de tweede set het achtervoegsel `_2` (`sensor.thuis` en `sensor.thuis_2`). Kijk naar het
  attribuut `tag` om te zien welke welke is: `upcoming` (volgende) of `lastmatch` (vorige).

## Attributen

Elke sensor heeft:

| Attribuut | Betekenis |
|---|---|
| `baseid` | Het ploegnummer dat je hebt ingesteld. |
| `tag` | `upcoming` of `lastmatch`. |

**Thuis** en **Uit** hebben daarnaast:

| Attribuut | Betekenis |
|---|---|
| `id` | Ploegnummer van die ploeg bij de RBFA. |
| `goals` | Gescoorde doelpunten, als de uitslag gepubliceerd is. |
| `penalties` | Gescoorde strafschoppen in een strafschoppenreeks, indien van toepassing. |
| `position` | Positie in het klassement van de reeks. |
| `entity_picture` | URL van het clublogo. |

**Reeks** heeft daarnaast:

| Attribuut | Betekenis |
|---|---|
| `ranking` | Lijst met één item per ploeg: `position`, `team`, `id`, `logo`, `matches` (gespeeld) en `fairplay` (percentage). |
| `squads` | Spelers en staf per ploeg, per ploegnummer (zie hieronder). Wordt niet in de recorder bewaard. |

`squads` ziet er zo uit:

```yaml
"378177":
  players:
    - name: Jan Janssens
      matches: 8        # gespeelde wedstrijden volgens de wedstrijdbladen
      goals: 0
  staff:
    - name: Piet Peeters
      function: T1      # T1, T2, Officiële Team Afgevaardigde, ...
```

> **Privacy.** De spelerslijsten bevatten de namen die de RBFA op de openbare ploegpagina
> publiceert. Bij jeugdploegen zijn dat namen van kinderen. Het attribuut wordt niet in de
> recorder-database bewaard. Denk na voor je screenshots deelt of het buiten je huis beschikbaar maakt.

## Hoe en wanneer de gegevens ververst worden

- Alles wordt **elke 30 minuten** ververst.
- Tussen twee verzoeken zit **één seconde**; de RBFA-website blokkeert wie te veel tegelijk opvraagt.
- De locatie en de scheidsrechter van de volgende wedstrijd worden bij elke update opgehaald.
  Andere wedstrijden worden één keer opgezocht, enkele per update, de dichtstbijzijnde eerst.
- **Spelerslijsten worden hoogstens om de 12 uur ververst**, met één verzoek per ploeg in de reeks.
- Is de RBFA onbereikbaar of blokkeert ze een verzoek, dan blijven de vorige gegevens staan en
  volgt een nieuwe poging bij de volgende update.

## Jeugdreeksen: geen klassement, wel fairplay

Voor de jongste leeftijdsgroepen (7 tot 12 jaar in Vlaanderen) publiceren de voetbalbonden
**bewust geen uitslagen en geen klassement**. De RBFA geeft wel de lijst van ploegen terug.
Voor die reeksen geldt dus:

- `position` is gewoon de volgorde waarin de RBFA de ploegen opsomt, geen echte stand;
- `goals` blijft leeg;
- `fairplay` is *wel* ingevuld. Na elke wedstrijd geeft wie het wedstrijdblad invult beide
  ploegen punten op vijf onderdelen: spelers, supporters, coaches, afgevaardigde en
  fairplayouder. Ploegen die gemiddeld boven 80% scoren, krijgen een fairplaycertificaat.
  [Meer over het fairplayklassement](https://voetbalvlaanderensupport.zendesk.com/hc/nl/articles/15311010709917-Hoe-gaat-het-fairplayklassement-in-zijn-werk).

In deze reeksen eindigen de ploegnamen van de RBFA ook op een korte code zoals `A 2`,
bijvoorbeeld `E. Mechelen a/d Maas A 2`.

## Voorbeeldkaarten

![Voorbeeld](https://raw.githubusercontent.com/Maffiow/RBFA/main/images/example-cards.png)

Alle voorbeelden zijn [Markdown-kaarten](https://www.home-assistant.io/dashboards/markdown/)
en hebben geen extra kaarten nodig. Vervang de entiteits-ID's door die van jouw installatie.

### Wedstrijdkaart

<img src="https://raw.githubusercontent.com/Maffiow/RBFA/main/images/match-card.png" alt="Wedstrijdkaart" width="528">

```
<table width="100%">
<tr><th colspan=2>{{ states('sensor.reeks') }}</th></tr>
<tr><th colspan=2>
<a href="https://www.rbfa.be/nl/wedstrijd/{{ states('sensor.wedstrijd_id') }}">{{ as_timestamp(states('sensor.start')) | timestamp_custom('%d-%m-%y om %H:%M uur') }}</a>
</th></tr>
<tr>
<td align="center"><img src="{{ state_attr('sensor.thuis', 'entity_picture') }}" width="64"></td>
<td align="center"><img src="{{ state_attr('sensor.uit', 'entity_picture') }}" width="64"></td>
</tr>
<tr>
<td align="center">{{ states('sensor.thuis') }}</td>
<td align="center">{{ states('sensor.uit') }}</td>
</tr>
<tr><td align="center" colspan="2">{{ states('sensor.locatie') | replace("\n", ", ") }}</td></tr>
<tr><td align="center" colspan="2">Scheidsrechter: {{ states('sensor.scheidsrechter') }}</td></tr>
</table>
```

### Klassementkaart

<img src="https://raw.githubusercontent.com/Maffiow/RBFA/main/images/ranking-card.png" alt="Klassement" width="528">

Gebruikt het attribuut `ranking` van de reeks-sensor en het attribuut `baseid` (je eigen
ploegnummer) om je eigen ploeg vet te zetten:

```yaml
type: markdown
title: Rangschikking
content: >-
  {% set sensor = "sensor.reeks" %}
  **{{ states(sensor) }}**

  {% for item in state_attr(sensor, "ranking") or [] %}
  {{ item.position }}. {% if item.id == state_attr(sensor, "baseid") %}**{{ item.team }}**{% else %}{{ item.team }}{% endif %}
  {% endfor %}
```

### Fairplaykaart

<img src="https://raw.githubusercontent.com/Maffiow/RBFA/main/images/fairplay-card.png" alt="Fairplay" width="528">

Sorteert de ploegen van de reeks op fairplay-percentage:

```yaml
type: markdown
title: Fairplay
content: >-
  {% set sensor = "sensor.reeks" %}
  {% for item in (state_attr(sensor, "ranking") or [])
     | selectattr("fairplay", "number")
     | sort(attribute="fairplay", reverse=true) %}
  {{ loop.index }}. {% if item.id == state_attr(sensor, "baseid") %}**{{ item.team }}**{% else %}{{ item.team }}{% endif %} — {{ item.fairplay }}% ({{ item.matches }} wedstrijden)
  {% endfor %}
```

### Spelerskaart

Toont de spelers en de staf van je eigen ploeg. Gebruik een ander ploegnummer in plaats van
`baseid` om een tegenstander te tonen, bijvoorbeeld `state_attr('sensor.thuis', 'id')`.

```yaml
type: markdown
title: Spelers
content: >-
  {% set sensor = "sensor.reeks" %}
  {% set squad = (state_attr(sensor, "squads") or {}).get(state_attr(sensor, "baseid"), {}) %}
  **Spelers**

  {% for p in (squad.players or []) | sort(attribute="matches", reverse=true) %}
  - {{ p.name }} — {{ p.matches }} wedstrijden{% if p.goals %}, {{ p.goals }} doelpunten{% endif %}

  {% endfor %}
  **Staf**

  {% for s in squad.staff or [] %}
  - {{ s.name }} ({{ s.function }})

  {% endfor %}
```

### Automatisering: herinnering voor de wedstrijd

```yaml
alias: Herinnering wedstrijd
triggers:
  - trigger: calendar
    event: start
    entity_id: calendar.rbfa_378177   # jouw RBFA-kalender
    offset: "-02:00:00"
actions:
  - action: notify.notify
    data:
      title: "⚽ {{ trigger.calendar_event.summary }}"
      message: "Aftrap over 2 uur op {{ trigger.calendar_event.location | replace('\n', ', ') }}"
mode: single
```

## Updates

Nieuwe versies verschijnen als [GitHub-releases](https://github.com/Maffiow/RBFA/releases).
HACS controleert dat automatisch en toont een update onder **Instellingen → Updates**.

### Updates automatisch installeren

HACS maakt een update-entiteit voor de integratie (bv. `update.rbfa_update`). Deze
automatisering installeert nieuwe versies 's nachts en herstart Home Assistant:

```yaml
alias: RBFA automatisch bijwerken
triggers:
  - trigger: time
    at: "04:00:00"
conditions:
  - condition: state
    entity_id: update.rbfa_update
    state: "on"
actions:
  - action: update.install
    target:
      entity_id: update.rbfa_update
  - delay: "00:01:00"
  - action: homeassistant.restart
mode: single
```

## Problemen oplossen

| Symptoom | Oorzaak en oplossing |
|---|---|
| *"Team … not found on rbfa.be"* | Ploegnummers veranderen elk seizoen. Zoek het nieuwe nummer op in de URL van de ploegpagina en voeg de integratie opnieuw toe. |
| *"request blocked by the RBFA firewall"* | De RBFA-API zit achter een firewall die verzoeken blokkeert die niet van de website lijken te komen. De integratie stuurt verzoeken zoals een browser en beperkt zich tot enkele verzoeken per update; ze probeert automatisch opnieuw. Open een [issue](https://github.com/Maffiow/RBFA/issues) als het blijft gebeuren. |
| Sensoren ontbreken | Ze staan standaard uit; zet ze aan op de pagina van de integratie. |
| `position` lijkt alfabetisch, `goals` is leeg | Die reeks heeft geen gepubliceerd klassement of uitslagen, zie [Jeugdreeksen](#jeugdreeksen-geen-klassement-wel-fairplay). |
| `squads` of `ranking` ontbreekt | *Toon uitslagen en rangschikking* staat uit, of de eerste verversing na een herstart loopt nog (spelerslijsten vragen één verzoek per ploeg). |
| Locatie of scheidsrechter is leeg | De RBFA heeft het nog niet gepubliceerd; het wordt bij een latere update opgepikt. |

Uitgebreid loggen:

```yaml
logger:
  logs:
    custom_components.rbfa: debug
```

## Een nieuwe versie uitbrengen (beheerders)

1. Pas de code aan.
2. Verhoog `version` in `custom_components/rbfa/manifest.json` (bv. `1.2.0` → `1.2.1`).
3. Push naar `main`. De workflow *Release* maakt de tag `v1.2.1` en een GitHub-release met
   automatische release-notes; HACS-gebruikers zien daarna de update.

## Licentie

[MIT](LICENSE)
