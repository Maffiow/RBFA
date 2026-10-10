"""Constants for the RBFA integration."""
from datetime import timedelta

DOMAIN = "rbfa"
TZ = "Europe/Brussels"

API_URL = "https://datalake-prod2018.rbfa.be/graphql"

# The RBFA API sits behind Akamai bot protection. Requests that do not look
# like they come from the rbfa.be website get an HTML "Access Denied" page
# (with HTTP status 200) instead of JSON. Each of these headers is required;
# aiohttp in particular is refused without an explicit "Connection" header.
API_HEADERS = {
    "Connection": "keep-alive",
    "Accept": "*/*",
    "Accept-Language": "nl-BE,nl;q=0.9,en;q=0.8",
    "Content-Type": "application/json",
    "Origin": "https://www.rbfa.be",
    "Referer": "https://www.rbfa.be/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
    ),
}

UPDATE_INTERVAL = timedelta(minutes=30)
# Pause between consecutive API calls, to avoid tripping the rate limiter.
REQUEST_DELAY = 1.0
# Maximum number of match details (location / referee) fetched per update for
# matches that are not cached yet. The rest is filled in on later updates.
MAX_DETAIL_FETCHES = 5
# Squads (players and staff of every team in the series) change rarely, and
# fetching them costs one request per team, so they are refreshed sparingly.
SQUAD_REFRESH = timedelta(hours=12)

CONF_TEAM = "team"
CONF_ALT_NAME = "alt_name"
CONF_DURATION = "duration"
CONF_SHOW_RANKING = "show_ranking"
CONF_SHOW_REFEREE = "show_referee"

DEFAULT_DURATION = 105

VARIABLES = {
    "GetTeam": "teamId",
    "GetTeamCalendar": "teamId",
    "GetMatchDetail": "matchId",
    "GetSeriesRankings": "seriesId",
    "GetTeamMembers": "teamId",
}

HASHES = {
    "GetTeam": "e16f98f7985e6b7d6553c8ca60aea3a2b65b6b84dfcabbb02b4ee55261413858",
    "GetTeamCalendar": "3f0441e6723b9852b4f0cff2c872f4aa674c5de2d23589efc70c7a4ffb7f6383",
    "GetMatchDetail": "cd8867b845c206fe7aa75c1ebf7b53cbda0ff030253a45e2e2b4bcc13ee46c9a",
    "GetSeriesRankings": "0a53124a9bc8872b686f22d80fd545622dbaf4b27a7596e1207b097b92c87953",
}

# Operations sent as a full query document instead of a persisted-query hash.
QUERIES = {
    "GetTeamMembers": (
        "query GetTeamMembers($teamId: ID!, $language: Language!) {"
        " teamMembers(teamId: $teamId, language: $language) {"
        " players { id lastName firstName statistics { numberOfMatches numberOfGoals } }"
        " staff { id lastName firstName function } } }"
    ),
}

REQUIRED = {
    "GetTeam": "team",
    "GetTeamCalendar": "teamCalendar",
    "GetMatchDetail": "matchDetail",
    "GetSeriesRankings": "seriesRankings",
    "GetTeamMembers": "teamMembers",
}


def get_option(entry, key, default=None):
    """Return a setting from the entry options, falling back to its data."""
    if key in entry.options:
        return entry.options[key]
    return entry.data.get(key, default)
