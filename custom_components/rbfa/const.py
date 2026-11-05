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

# Every operation is sent as a full query document. The rbfa.be website uses
# persisted-query hashes, but those change whenever the site updates its
# queries (and the old hashes then fail with "PersistedQueryNotFound"); a full
# document keeps working as long as the fields below still exist.
QUERIES = {
    "GetTeam": (
        "query GetTeam($teamId: ID!, $language: Language!) {"
        " team(teamId: $teamId, language: $language) {"
        " id name clubName clubId logo } }"
    ),
    "GetTeamCalendar": (
        "query GetTeamCalendar($teamId: ID!, $language: Language!) {"
        " teamCalendar(teamId: $teamId, language: $language) {"
        " id startTime channel"
        " homeTeam { id name clubId logo }"
        " awayTeam { id name clubId logo }"
        " outcome { status homeTeamGoals homeTeamPenaltiesScored"
        " awayTeamGoals awayTeamPenaltiesScored subscript }"
        " series { id name }"
        " officials { lastName firstName status personAssigned }"
        " showScore state } }"
    ),
    "GetMatchDetail": (
        "query GetMatchDetail($matchId: ID!, $language: Language!) {"
        " matchDetail(matchId: $matchId, language: $language) {"
        " id startTime channel"
        " location { name city postalCode address }"
        " officials { lastName firstName function status personAssigned } } }"
    ),
    "GetSeriesRankings": (
        "query GetSeriesRankings($seriesId: ID!, $language: Language!) {"
        " seriesRankings(seriesId: $seriesId, language: $language) {"
        " id name rankings { type teams {"
        " teamId name position clubId logo points matchesPlayed"
        " fairplayPercentage } } } }"
    ),
    "GetTeamMembers": (
        "query GetTeamMembers($teamId: ID!, $language: Language!) {"
        " teamMembers(teamId: $teamId, language: $language) {"
        " players { lastName firstName statistics { numberOfMatches numberOfGoals } }"
        " staff { lastName firstName function } } }"
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
