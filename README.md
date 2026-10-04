# RBFA for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/Maffiow/RBFA/actions/workflows/validate.yaml/badge.svg)](https://github.com/Maffiow/RBFA/actions/workflows/validate.yaml)
[![Release](https://img.shields.io/github/v/release/Maffiow/RBFA)](https://github.com/Maffiow/RBFA/releases)

Add the match calendar of your football team to Home Assistant. The data comes from the
Royal Belgian Football Association ([RBFA](https://www.rbfa.be/)) website, which serves
[Voetbal Vlaanderen](https://www.voetbalvlaanderen.be/) and [ACFF](https://www.acff.be/).

You get:

- a **calendar** with all matches of the team (score, series, location)
- **sensors** for the upcoming and the last match: start/end time, home/away team (with logo,
  goals and ranking position), location, series (with full ranking), referee and match ID.
  The sensors are disabled by default; enable the ones you need.

Based on the original [rgerbranda/rbfa](https://github.com/rgerbranda/rbfa) integration,
rewritten to work again with the current RBFA website.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Maffiow&repository=RBFA&category=integration)

Or manually:

1. In Home Assistant open **HACS** → menu (⋮) → **Custom repositories**.
2. Repository: `https://github.com/Maffiow/RBFA`, type: **Integration** → **Add**.
3. Search for **RBFA** in HACS, click **Download** and restart Home Assistant.

> Coming from `rgerbranda/rbfa`? Remove that repository in HACS first (or delete
> `/config/custom_components/rbfa`), then install this one. Your existing configuration
> and entity IDs are kept.

### Manual

Copy `custom_components/rbfa` to `/config/custom_components/rbfa` and restart Home Assistant.

## Configuration

**Settings → Devices & services → Add integration → RBFA**

![Configuration](https://raw.githubusercontent.com/Maffiow/RBFA/main/images/configuration.png)

| Field | Description |
|---|---|
| Team | The number after `ploeg` in the URL of the team page, e.g. `363016` for `https://www.rbfa.be/nl/club/2438/ploeg/363016` |
| Alternative name | Optional name for the calendar (default: `club \| team`) |
| Duration | Match duration in minutes, used for the end time of calendar events |
| Show ranking | Fetch the ranking of the series |
| Show referee | Fetch the referee and create the referee sensor |

These settings can be changed later via **Configure** on the integration.

> **Team IDs change every season.** If you get "Team … not found" in the log after the summer,
> remove the integration and add it again with the new ID from rbfa.be.

## Updates

New versions are published as [GitHub releases](https://github.com/Maffiow/RBFA/releases).
HACS checks for them automatically and shows an update in **Settings → Updates**.

### Install updates automatically

HACS creates an update entity for the integration (e.g. `update.rbfa_update`). This automation
installs new versions at night and restarts Home Assistant:

```yaml
alias: Auto-update RBFA
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

## Example cards

![Example](https://raw.githubusercontent.com/Maffiow/RBFA/main/images/example.png)

### Match card

<img src="https://raw.githubusercontent.com/Maffiow/RBFA/main/images/match_sheet.png" alt="Match card" width="528">

A [Markdown card](https://www.home-assistant.io/dashboards/markdown/). Replace the entity IDs
with the ones in your installation.

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
<tr>
<td align="center">Positie: {{ state_attr('sensor.thuis', 'position') }}</td>
<td align="center">Positie: {{ state_attr('sensor.uit', 'position') }}</td>
</tr>
<tr><td align="center" colspan="2">{{ states('sensor.locatie') | replace("\n", ", ") }}</td></tr>
<tr><td align="center" colspan="2">Scheidsrechter: {{ states('sensor.scheidsrechter') }}</td></tr>
</table>
```

### Ranking card

<img src="https://raw.githubusercontent.com/Maffiow/RBFA/main/images/ranking.png" alt="Ranking" width="528">

Uses the `ranking` attribute of the series sensor and the `baseid` attribute (your team ID):

```yaml
type: markdown
title: Ranking
content: >-
  {% set sensor = "sensor.reeks" %}
  **{{ states(sensor) }}**

  {% for item in state_attr(sensor, "ranking") or [] %}
  {{ item.position }}. {% if item.id == state_attr(sensor, "baseid") %}**{{ item.team }}**{% else %}{{ item.team }}{% endif %}
  {% endfor %}
```

## Releasing a new version (maintainers)

1. Change the code.
2. Bump `version` in `custom_components/rbfa/manifest.json` (e.g. `1.0.0` → `1.0.1`).
3. Push to `main`. The *Release* workflow creates tag `v1.0.1` and a GitHub release with
   generated notes; HACS users then see the update.

## Troubleshooting

The RBFA API is protected by a firewall that blocks requests that do not look like they
come from the website. The integration sends browser-like requests and limits itself to a
few calls every 30 minutes. If you still see *"request blocked by the RBFA firewall"* in the
log, the integration retries automatically; please open an
[issue](https://github.com/Maffiow/RBFA/issues) if it keeps happening.

Debug logging:

```yaml
logger:
  logs:
    custom_components.rbfa: debug
```

## License

[MIT](LICENSE)
