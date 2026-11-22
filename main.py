"""
Matchday Lineup and Injury Alert Pipeline

Each time this script runs it does two checks:
  1. Pre-deadline check: about 120 minutes before the next FPL deadline,
     look for injury news on your FPL players.
  2. Lineup check: about 75 minutes before a kickoff, fetch the official
     lineup from ESPN and alert if it involves your watchlist.

GitHub Actions runs this every 15 minutes, so the script runs once and
exits instead of looping forever.

Data sources:
  - ESPN's public soccer API: fixtures and lineups (free, no key)
  - The official FPL API: injury news and which club each player is at
    (free, no key)
  - API-Football (optional, free plan): injuries for your watched clubs,
    like Barcelona. Set API_FOOTBALL_KEY to turn it on. The free plan only
    allows today's matches (about a day either side), which is all we need.

Usage:
    python main.py                  normal run (what GitHub Actions does)
    python main.py --force          skip the timing windows (good for testing)
    python main.py --test-alert     just send a test message to Discord
    python main.py --demo           send sample alerts to Discord (for presenting)
    python main.py --force --date 2026-11-08
                                    replay a past matchday with real lineups
"""

import json
import os
import sys
import unicodedata
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

import demo_data

ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer"
FPL_URL = "https://fantasy.premierleague.com/api"
API_FOOTBALL_URL = "https://v3.football.api-sports.io"
TIMEOUT_SECONDS = 15
HEADERS = {"User-Agent": "matchday-alerts-student-project"}

DEADLINE_MINUTES = 120   # injury check this long before the FPL deadline
LINEUP_MINUTES = 75      # lineup check this long before kickoff
WINDOW_MINUTES = 15      # must match how often the cron job runs


# ---------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------

def log(text):
    print("[" + datetime.now(timezone.utc).strftime("%H:%M:%S") + "] " + text)


def load_watchlist(path="watchlist.json"):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_json(url, params=None, extra_headers=None):
    """Make a GET request and return the JSON, or None if anything fails."""
    headers = dict(HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    try:
        response = requests.get(url, headers=headers, params=params,
                                timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as error:
        log("Request failed for " + url + ": " + str(error))
        return None
    except ValueError:
        log("Got something that was not JSON from " + url)
        return None


def get_option_value(arguments, option):
    """For '--date 2026-11-08' return '2026-11-08' (or None if missing)."""
    for index in range(len(arguments)):
        if arguments[index] == option and index + 1 < len(arguments):
            return arguments[index + 1]
    return None


def minutes_until(target_time, now):
    return (target_time - now).total_seconds() / 60


def in_window(minutes_left, target_minutes):
    """True if we are inside the check window for this target time."""
    low = target_minutes - (WINDOW_MINUTES / 2)
    high = target_minutes + (WINDOW_MINUTES / 2)
    return low < minutes_left <= high


# ---------------------------------------------------------------
# Matching names against the watchlist
# ---------------------------------------------------------------

def clean_name(text):
    """Lowercase and strip accents so 'Groß' and 'Gross' compare equal."""
    text = text.replace("ß", "ss")
    text = unicodedata.normalize("NFKD", text)
    result = ""
    for character in text:
        if not unicodedata.combining(character):
            result = result + character
    return result.lower().strip()


def split_into_words(text):
    """Split a name into words, also splitting hyphens ('Egan-Riley')."""
    words = []
    for word in clean_name(text).split(" "):
        if word == "":
            continue
        words.append(word)
        if "-" in word:
            for part in word.split("-"):
                words.append(part)
    return words


def name_matches(watch_name, other_name):
    """
    Sites write names differently ('E. Haaland' or 'Erling Haaland'), so
    we compare the last word of the watchlist name against the words in
    the other name.
    """
    watch_words = clean_name(watch_name).split(" ")
    last_word = watch_words[len(watch_words) - 1]
    return last_word in split_into_words(other_name)


# FPL and ESPN write some club names differently
TEAM_ALIASES = {
    "man city": "manchester city",
    "man utd": "manchester united",
    "spurs": "tottenham",
    "nott'm forest": "nottingham forest",
}


def team_names_match(first_name, second_name):
    """Compare club names, e.g. FPL 'Man City' vs ESPN 'Manchester City'."""
    first = clean_name(first_name)
    second = clean_name(second_name)
    if first in TEAM_ALIASES:
        first = TEAM_ALIASES[first]
    if first == "" or second == "":
        return False
    return first in second or second in first


def is_watched_club(team_name, watchlist):
    for club in watchlist["clubs"]:
        if team_names_match(club["name"], team_name):
            return True
    return False


# ---------------------------------------------------------------
# FPL data: which club each player is at, and their injury news
# ---------------------------------------------------------------

def pick_player_clubs(fpl_data, watchlist):
    """
    Look up each watchlist player in the FPL data.
    Returns a list of dicts with name, team, status, news and chance.
    If a name matches more than one player, add the club you mean to
    "player_clubs" in watchlist.json. Otherwise that player is skipped.
    """
    team_names = {}
    for team in fpl_data["teams"]:
        team_names[team["id"]] = team["name"]

    wanted_clubs = watchlist.get("player_clubs", {})
    result = []
    for watch_name in watchlist["players"]:
        matches = []
        for player in fpl_data["elements"]:
            if name_matches(watch_name, player["web_name"]):
                matches.append(player)

        if watch_name in wanted_clubs:
            narrowed = []
            for player in matches:
                club = team_names.get(player["team"], "")
                if team_names_match(club, wanted_clubs[watch_name]):
                    narrowed.append(player)
            matches = narrowed

        if len(matches) == 1:
            player = matches[0]
            result.append({
                "name": player["web_name"],
                "team": team_names.get(player["team"], "?"),
                "status": player["status"],
                "news": player["news"],
                "chance": player["chance_of_playing_next_round"],
            })
        elif len(matches) == 0:
            log("Could not find '" + watch_name + "' in FPL data.")
        else:
            log("'" + watch_name + "' matches " + str(len(matches))
                + " FPL players. Add it to player_clubs in watchlist.json.")
    return result


def find_fpl_flags(player_clubs):
    """Players whose FPL status is not 'available' or who have news."""
    flags = []
    for player in player_clubs:
        if player["status"] != "a" or player["news"]:
            flags.append(player)
    return flags


def get_next_fpl_deadline(fpl_data):
    """Return (gameweek name, deadline datetime) for the next gameweek."""
    for event in fpl_data["events"]:
        if event.get("is_next"):
            deadline = datetime.strptime(event["deadline_time"],
                                         "%Y-%m-%dT%H:%M:%SZ")
            return event["name"], deadline.replace(tzinfo=timezone.utc)
    return None, None


def describe_flag(flag):
    chance = ""
    if flag["chance"] is not None:
        chance = " [" + str(flag["chance"]) + "% chance]"
    news = flag["news"]
    if not news:
        news = "No details given"
    return flag["name"] + " (" + flag["team"] + ")" + chance + ": " + news


# ---------------------------------------------------------------
# Check 1: injury news before the FPL deadline
# ---------------------------------------------------------------

def build_deadline_message(gameweek, flags):
    lines = ["**Pre-deadline injury check** (" + gameweek + ")", ""]
    lines.append("**Your FPL squad:**")
    for flag in flags:
        lines.append("- " + describe_flag(flag))
    return "\n".join(lines)


def run_early_injury_check(now, force, fpl_data, player_clubs):
    gameweek, deadline = get_next_fpl_deadline(fpl_data)
    if deadline is None:
        log("No upcoming FPL deadline found.")
        return []

    minutes_left = minutes_until(deadline, now)
    log(gameweek + " deadline is in " + str(int(minutes_left)) + " minutes.")
    if not force and not in_window(minutes_left, DEADLINE_MINUTES):
        return []

    flags = find_fpl_flags(player_clubs)
    if len(flags) == 0:
        log("No injury news on your FPL players.")
        return []
    return [build_deadline_message(gameweek, flags)]


# ---------------------------------------------------------------
# ESPN: fixtures and lineups
# ---------------------------------------------------------------

def parse_espn_time(text):
    """ESPN times look like '2026-11-14T15:00Z'. Returns a UTC timestamp."""
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def parse_scoreboard(data, league):
    """Turn an ESPN scoreboard response into a simple list of fixtures."""
    fixtures = []
    for event in data.get("events", []):
        home = ""
        away = ""
        for competition in event.get("competitions", []):
            for competitor in competition.get("competitors", []):
                team_name = competitor.get("team", {}).get("displayName", "")
                if competitor.get("homeAway") == "home":
                    home = team_name
                elif competitor.get("homeAway") == "away":
                    away = team_name
        if home == "" or away == "" or "date" not in event:
            continue
        fixtures.append({
            "id": event["id"],
            "league": league,
            "timestamp": parse_espn_time(event["date"]),
            "home": home,
            "away": away,
        })
    return fixtures


def is_relevant_fixture(fixture, watchlist):
    """A fixture matters if it is in your FPL league or has a watched club."""
    if fixture["league"] == watchlist["player_league"]:
        return True
    if is_watched_club(fixture["home"], watchlist):
        return True
    if is_watched_club(fixture["away"], watchlist):
        return True
    return False


def get_todays_fixtures(today_text, watchlist):
    """
    Fetch today's fixtures for each league in the watchlist. The result is
    saved in cache/ so the many runs in one day only fetch once.
    """
    path = "cache/fixtures-" + today_text + ".json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    relevant = []
    failed = False
    for league in watchlist["leagues"]:
        # ESPN only accepts ONE date per request, in YYYYMMDD format
        data = get_json(ESPN_URL + "/" + league + "/scoreboard",
                        {"dates": today_text.replace("-", "")})
        if data is None:
            failed = True
            continue
        for fixture in parse_scoreboard(data, league):
            if is_relevant_fixture(fixture, watchlist):
                relevant.append(fixture)

    if failed:
        return relevant   # don't cache a partial result

    os.makedirs("cache", exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(relevant, file)
    return relevant


def get_place_number(entry):
    """ESPN numbers the starters 1 to 11 in 'formationPlace' (1 = goalkeeper)."""
    place = str(entry.get("formationPlace", ""))
    if place.isdigit():
        return int(place)
    return 0


def get_place(item):
    return item["place"]


def parse_espn_rosters(summary_data):
    """
    Turn an ESPN match summary into a list of lineups, one per team.
    Before the lineup is announced the names are empty, so startXI is empty.
    """
    lineups = []
    for team_roster in summary_data.get("rosters", []):
        starters = []
        substitutes = []
        for entry in team_roster.get("roster", []):
            name = entry.get("athlete", {}).get("displayName", "")
            if name == "":
                continue
            item = {"player": {"name": name}, "place": get_place_number(entry)}
            if entry.get("starter"):
                starters.append(item)
            else:
                substitutes.append(item)
        starters.sort(key=get_place)   # goalkeeper first, then by position
        lineups.append({
            "team": {"name": team_roster.get("team", {}).get("displayName", "")},
            "formation": team_roster.get("formation") or "?",
            "startXI": starters,
            "substitutes": substitutes,
        })
    return lineups


def fetch_lineups(fixture):
    data = get_json(ESPN_URL + "/" + fixture["league"] + "/summary",
                    {"event": fixture["id"]})
    if data is None:
        return []
    return parse_espn_rosters(data)


# ---------------------------------------------------------------
# API-Football (optional): injuries for watched clubs
# ---------------------------------------------------------------

def api_football_get(path, params):
    """Call API-Football. Returns the 'response' list, or None on any problem."""
    key = os.getenv("API_FOOTBALL_KEY")
    if not key:
        return None
    data = get_json(API_FOOTBALL_URL + path, params,
                    {"x-apisports-key": key})
    if data is None:
        return None
    if data.get("errors"):
        log("API-Football said: " + str(data["errors"]))
        return None
    return data.get("response", [])


def get_api_football_fixtures(today_text):
    """Today's matches from API-Football (cached, so 1 request per day)."""
    path = "cache/apifootball-fixtures-" + today_text + ".json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    items = api_football_get("/fixtures", {"date": today_text})
    if items is None:
        return []

    fixtures = []
    for item in items:
        fixtures.append({
            "id": item["fixture"]["id"],
            "home": item["teams"]["home"]["name"],
            "away": item["teams"]["away"]["name"],
        })

    os.makedirs("cache", exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(fixtures, file)
    return fixtures


def find_api_fixture_id(api_fixtures, fixture):
    """Match an ESPN fixture to the same match in API-Football by team names."""
    for api_fixture in api_fixtures:
        if (team_names_match(fixture["home"], api_fixture["home"])
                and team_names_match(fixture["away"], api_fixture["away"])):
            return api_fixture["id"]
    return None


def filter_club_injuries(items, watchlist):
    """Keep only injuries for players on a watched club."""
    kept = []
    for item in items:
        if is_watched_club(item["team"]["name"], watchlist):
            kept.append(item)
    return kept


def is_club_fixture(fixture, watchlist):
    return (is_watched_club(fixture["home"], watchlist)
            or is_watched_club(fixture["away"], watchlist))


def get_club_injuries(fixture, today_text, watchlist):
    if not os.getenv("API_FOOTBALL_KEY"):
        return []
    api_fixtures = get_api_football_fixtures(today_text)
    fixture_id = find_api_fixture_id(api_fixtures, fixture)
    if fixture_id is None:
        log("Could not find this match in API-Football, skipping injuries.")
        return []
    items = api_football_get("/injuries", {"fixture": fixture_id})
    if items is None:
        return []
    return filter_club_injuries(items, watchlist)


# ---------------------------------------------------------------
# Check 2: official lineups before kickoff
# ---------------------------------------------------------------

def find_omitted_players(team_lineup, player_clubs):
    """
    Watched players whose club has a published lineup but who are
    neither starting nor on the bench.
    """
    if len(team_lineup["startXI"]) == 0:
        return []   # lineup not published yet, so we can't say anyone is out

    omitted = []
    for player in player_clubs:
        if not team_names_match(player["team"], team_lineup["team"]["name"]):
            continue

        in_squad = False
        for entry in team_lineup["startXI"]:
            if name_matches(player["name"], entry["player"]["name"]):
                in_squad = True
        for entry in team_lineup["substitutes"]:
            if name_matches(player["name"], entry["player"]["name"]):
                in_squad = True

        if not in_squad:
            omitted.append(player)
    return omitted


def parse_formation(formation):
    """'4-3-3' becomes [4, 3, 3]. Returns [] if it isn't a normal formation."""
    numbers = []
    for part in str(formation).split("-"):
        if not part.isdigit():
            return []
        numbers.append(int(part))
    return numbers


NAME_PARTS = ["de", "van", "ter", "von", "da", "dos", "di", "le", "el",
              "al", "mac"]


def short_name(full_name):
    """'Lamine Yamal' becomes 'Yamal', 'Frenkie de Jong' becomes 'de Jong'."""
    words = full_name.split(" ")
    name = words[len(words) - 1]
    if len(words) > 2 and words[len(words) - 2].lower() in NAME_PARTS:
        name = words[len(words) - 2] + " " + name
    return name[:14]


def draw_formation(team_name, formation, starters, watched_names=None):
    """
    Draw the starting XI in its formation shape, attackers at the top.
    Players from your watchlist get a * after their name.
    Returns "" if the lineup isn't a normal 11-player formation.
    """
    if watched_names is None:
        watched_names = []
    rows = parse_formation(formation)
    if len(starters) != 11 or sum(rows) != 10:
        return ""

    names = []
    marked_any = False
    for entry in starters:
        full_name = entry["player"]["name"]
        label = short_name(full_name)
        for watched in watched_names:
            if name_matches(watched, full_name):
                label = label + "*"
                marked_any = True
        names.append(label)

    # Names are in goalkeeper-first order, so slice them into rows
    row_texts = []
    position = 1
    for count in rows:
        row_texts.append("   ".join(names[position:position + count]))
        position = position + count
    row_texts.reverse()          # attackers at the top
    row_texts.append(names[0])   # goalkeeper at the bottom

    width = 0
    for text in row_texts:
        if len(text) > width:
            width = len(text)

    lines = ["```", team_name + " (" + str(formation) + ")", ""]
    for text in row_texts:
        lines.append(text.center(width).rstrip())
    if marked_any:
        lines.append("")
        lines.append("* = on your watchlist")
    lines.append("```")
    return "\n".join(lines)


def build_lineup_message(fixture, lineups, flags, watchlist, player_clubs,
                         club_injuries=None):
    """Build the Discord message for one match. Returns "" if nothing matters."""
    if club_injuries is None:
        club_injuries = []
    lines = []

    # Starting XI for watched clubs and for teams with one of your players
    for team_lineup in lineups:
        team_name = team_lineup["team"]["name"]

        team_watched = []
        for player in player_clubs:
            if team_names_match(player["team"], team_name):
                team_watched.append(player["name"])

        if is_watched_club(team_name, watchlist) or len(team_watched) > 0:
            starters = []
            for entry in team_lineup["startXI"]:
                starters.append(entry["player"]["name"])
            shape = draw_formation(team_name, team_lineup["formation"],
                                   team_lineup["startXI"], team_watched)
            if shape != "":
                lines.append(shape)
            elif len(starters) > 0:
                lines.append("**" + team_name + " XI** ("
                             + str(team_lineup["formation"]) + "): "
                             + ", ".join(starters))

    # Starter/bench status for watched players
    for team_lineup in lineups:
        team_name = team_lineup["team"]["name"]
        for player in player_clubs:
            if not team_names_match(player["team"], team_name):
                continue
            for entry in team_lineup["startXI"]:
                if name_matches(player["name"], entry["player"]["name"]):
                    lines.append("- " + player["name"] + " ("
                                 + team_name + ") is STARTING")
            for entry in team_lineup["substitutes"]:
                if name_matches(player["name"], entry["player"]["name"]):
                    lines.append("- " + player["name"] + " ("
                                 + team_name + ") is on the BENCH")

    # Watched players missing from both the XI and the bench
    for team_lineup in lineups:
        for player in find_omitted_players(team_lineup, player_clubs):
            lines.append("- " + player["name"] + " (" + player["team"]
                         + ") is NOT in the matchday squad")

    # FPL injury news for watched players in this match
    news_lines = []
    for flag in flags:
        if (team_names_match(flag["team"], fixture["home"])
                or team_names_match(flag["team"], fixture["away"])):
            news_lines.append("- " + describe_flag(flag))
    if len(news_lines) > 0:
        lines.append("**Injury news:**")
        lines = lines + news_lines

    # Injuries for watched clubs (from API-Football, if a key is set)
    if len(club_injuries) > 0:
        lines.append("**Out / doubtful (club news):**")
        for item in club_injuries:
            lines.append("- " + item["player"]["name"] + " ("
                         + item["team"]["name"] + "): "
                         + str(item["player"]["type"]) + " - "
                         + str(item["player"]["reason"]))

    if len(lines) == 0:
        return ""
    title = "**Lineup Alert: " + fixture["home"] + " vs " + fixture["away"] + "**"
    return title + "\n" + "\n".join(lines)


def run_lineup_check(fixtures, now, watchlist, force, player_clubs=None,
                     today_text=None):
    if player_clubs is None:
        player_clubs = []
    if today_text is None:
        today_text = now.strftime("%Y-%m-%d")
    flags = find_fpl_flags(player_clubs)

    messages = []
    for fixture in fixtures:
        kickoff = datetime.fromtimestamp(fixture["timestamp"], timezone.utc)
        minutes_left = minutes_until(kickoff, now)
        if not force and not in_window(minutes_left, LINEUP_MINUTES):
            continue

        name = fixture["home"] + " vs " + fixture["away"]
        log("Checking " + name + " (kickoff in " + str(int(minutes_left))
            + " min)")

        lineups = fetch_lineups(fixture)
        if len(lineups) == 0:
            log("No lineup data yet for " + name)

        club_injuries = []
        if is_club_fixture(fixture, watchlist):
            club_injuries = get_club_injuries(fixture, today_text, watchlist)

        message = build_lineup_message(fixture, lineups, flags, watchlist,
                                       player_clubs, club_injuries)
        if message != "":
            messages.append(message)
    return messages


# ---------------------------------------------------------------
# Sending to Discord
# ---------------------------------------------------------------

def send_discord(message):
    url = os.getenv("DISCORD_WEBHOOK_URL")
    if not url:
        log("DISCORD_WEBHOOK_URL is not set, printing instead:")
        print(message)
        return False

    if len(message) > 1900:
        message = message[:1900] + "..."

    try:
        response = requests.post(url, json={"content": message},
                                 timeout=TIMEOUT_SECONDS)
        # Discord answers 204 No Content when the webhook works
        if response.status_code in (200, 204):
            log("Alert sent to Discord.")
            return True
        log("Discord said " + str(response.status_code) + ": " + response.text)
        return False
    except requests.exceptions.RequestException as error:
        log("Could not reach Discord: " + str(error))
        return False


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

def send_demo_alerts(watchlist):
    """Send two sample alerts built from fake data, so you can show the flow."""
    log("Demo mode: sending sample alerts built from fake data.")
    flags = find_fpl_flags(demo_data.PLAYER_CLUBS)
    first = build_lineup_message(demo_data.CITY_FIXTURE, demo_data.CITY_LINEUPS,
                                 flags, watchlist, demo_data.PLAYER_CLUBS)
    club_injuries = filter_club_injuries(demo_data.BARCA_INJURIES, watchlist)
    second = build_lineup_message(demo_data.BARCA_FIXTURE,
                                  demo_data.BARCA_LINEUPS, flags, watchlist,
                                  demo_data.PLAYER_CLUBS, club_injuries)
    for message in [first, second]:
        send_discord("**[DEMO - sample data]**\n" + message)


def main():
    load_dotenv()
    arguments = sys.argv[1:]

    if "--test-alert" in arguments:
        send_discord("Test alert from the matchday pipeline. It works!")
        return

    force = "--force" in arguments
    watchlist = load_watchlist()

    if "--demo" in arguments:
        send_demo_alerts(watchlist)
        return

    now = datetime.now(timezone.utc)
    today_text = now.strftime("%Y-%m-%d")

    # --date lets you replay a past matchday (use it together with --force)
    date_option = get_option_value(arguments, "--date")
    if date_option is not None:
        try:
            datetime.strptime(date_option, "%Y-%m-%d")
        except ValueError:
            log("--date must look like 2026-11-08")
            return
        today_text = date_option
        log("Replaying fixtures for " + today_text)

    messages = []

    # FPL data: club lookups and injury news (one request, no key needed)
    player_clubs = []
    fpl_data = get_json(FPL_URL + "/bootstrap-static/")
    if fpl_data is not None:
        player_clubs = pick_player_clubs(fpl_data, watchlist)
        messages = messages + run_early_injury_check(now, force, fpl_data,
                                                     player_clubs)

    # ESPN data: today's fixtures and lineups
    fixtures = get_todays_fixtures(today_text, watchlist)
    if len(fixtures) == 0:
        log("No relevant fixtures today.")
    messages = messages + run_lineup_check(fixtures, now, watchlist, force,
                                           player_clubs, today_text)

    if len(messages) == 0:
        log("Nothing to send this run.")
    for message in messages:
        send_discord(message)

    log("Done.")


if __name__ == "__main__":
    main()
