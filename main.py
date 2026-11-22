import json
import os
import sys
import textwrap
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

DEADLINE_MINUTES = 120
LINEUP_MINUTES = 75
WINDOW_MINUTES = 15


def log(text):
    print("[" + datetime.now(timezone.utc).strftime("%H:%M:%S") + "] " + text)


def load_watchlist(path="watchlist.json"):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_json(url, params=None, extra_headers=None):
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
    for index in range(len(arguments)):
        if arguments[index] == option and index + 1 < len(arguments):
            return arguments[index + 1]
    return None


def minutes_until(target_time, now):
    return (target_time - now).total_seconds() / 60


def in_window(minutes_left, target_minutes):
    low = target_minutes - (WINDOW_MINUTES / 2)
    high = target_minutes + (WINDOW_MINUTES / 2)
    return low < minutes_left <= high


def clean_name(text):
    text = text.replace("ß", "ss")
    text = unicodedata.normalize("NFKD", text)
    result = ""
    for character in text:
        if not unicodedata.combining(character):
            result = result + character
    return result.lower().strip()


def split_into_words(text):
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
    watch_words = clean_name(watch_name).split(" ")
    last_word = watch_words[len(watch_words) - 1]
    return last_word in split_into_words(other_name)


TEAM_ALIASES = {
    "man city": "manchester city",
    "man utd": "manchester united",
    "spurs": "tottenham",
    "nott'm forest": "nottingham forest",
}


def team_names_match(first_name, second_name):
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


def pick_player_clubs(fpl_data, watchlist):
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
    flags = []
    for player in player_clubs:
        if player["status"] != "a" or player["news"]:
            flags.append(player)
    return flags


def get_next_fpl_deadline(fpl_data):
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


def parse_espn_time(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def parse_scoreboard(data, league):
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
    if fixture["league"] == watchlist["player_league"]:
        return True
    if is_watched_club(fixture["home"], watchlist):
        return True
    if is_watched_club(fixture["away"], watchlist):
        return True
    return False


def get_todays_fixtures(today_text, watchlist):
    path = "cache/fixtures-" + today_text + ".json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    relevant = []
    failed = False
    for league in watchlist["leagues"]:
        data = get_json(ESPN_URL + "/" + league + "/scoreboard",
                        {"dates": today_text.replace("-", "")})
        if data is None:
            failed = True
            continue
        for fixture in parse_scoreboard(data, league):
            if is_relevant_fixture(fixture, watchlist):
                relevant.append(fixture)

    if failed:
        return relevant

    os.makedirs("cache", exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(relevant, file)
    return relevant


def get_place_number(entry):
    place = str(entry.get("formationPlace", ""))
    if place.isdigit():
        return int(place)
    return 0


def get_place(item):
    return item["place"]


def parse_espn_rosters(summary_data):
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
        starters.sort(key=get_place)
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


def api_football_get(path, params):
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
    for api_fixture in api_fixtures:
        if (team_names_match(fixture["home"], api_fixture["home"])
                and team_names_match(fixture["away"], api_fixture["away"])):
            return api_fixture["id"]
    return None


def filter_club_injuries(items, watchlist):
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


def find_omitted_players(team_lineup, player_clubs):
    if len(team_lineup["startXI"]) == 0:
        return []

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
    numbers = []
    for part in str(formation).split("-"):
        if not part.isdigit():
            return []
        numbers.append(int(part))
    return numbers


NAME_PARTS = ["de", "van", "ter", "von", "da", "dos", "di", "le", "el",
              "al", "mac"]


def short_name(full_name):
    words = full_name.split(" ")
    name = words[len(words) - 1]
    if len(words) > 2 and words[len(words) - 2].lower() in NAME_PARTS:
        name = words[len(words) - 2] + " " + name
    return name[:14]


def is_watched_name(full_name, watched_names):
    for watched in watched_names:
        if name_matches(watched, full_name):
            return True
    return False


def label_player(full_name, watched_names):
    label = short_name(full_name)
    if is_watched_name(full_name, watched_names):
        label = label + "*"
    return label


def bench_lines(substitutes, watched_names):
    if len(substitutes) == 0:
        return []
    labels = []
    for entry in substitutes:
        labels.append(label_player(entry["player"]["name"], watched_names))
    return textwrap.wrap("Bench: " + ", ".join(labels), width=42,
                         subsequent_indent="       ")


def draw_formation(team_name, formation, starters, watched_names=None,
                   substitutes=None):
    if watched_names is None:
        watched_names = []
    if substitutes is None:
        substitutes = []
    rows = parse_formation(formation)
    if len(starters) != 11 or sum(rows) != 10:
        return ""

    names = []
    for entry in starters:
        names.append(label_player(entry["player"]["name"], watched_names))
    bench = bench_lines(substitutes, watched_names)

    row_texts = []
    position = 1
    for count in rows:
        row_texts.append("   ".join(names[position:position + count]))
        position = position + count
    row_texts.reverse()
    row_texts.append(names[0])

    width = 0
    for text in row_texts:
        if len(text) > width:
            width = len(text)

    lines = ["```", team_name + " (" + str(formation) + ")", ""]
    for text in row_texts:
        lines.append(text.center(width).rstrip())
    if len(bench) > 0:
        lines.append("")
        lines = lines + bench

    marked_any = False
    for line in lines:
        if "*" in line:
            marked_any = True
    if marked_any:
        lines.append("")
        lines.append("* = on your watchlist")
    lines.append("```")
    return "\n".join(lines)


def build_lineup_message(fixture, lineups, flags, watchlist, player_clubs,
                         club_injuries=None):
    if club_injuries is None:
        club_injuries = []
    lines = []

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
                                   team_lineup["startXI"], team_watched,
                                   team_lineup["substitutes"])
            if shape != "":
                lines.append(shape)
            elif len(starters) > 0:
                lines.append("**" + team_name + " XI** ("
                             + str(team_lineup["formation"]) + "): "
                             + ", ".join(starters))
                for bench_line in bench_lines(team_lineup["substitutes"],
                                              team_watched):
                    lines.append(bench_line)

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

    for team_lineup in lineups:
        for player in find_omitted_players(team_lineup, player_clubs):
            lines.append("- " + player["name"] + " (" + player["team"]
                         + ") is NOT in the matchday squad")

    news_lines = []
    for flag in flags:
        if (team_names_match(flag["team"], fixture["home"])
                or team_names_match(flag["team"], fixture["away"])):
            news_lines.append("- " + describe_flag(flag))
    if len(news_lines) > 0:
        lines.append("**Injury news:**")
        lines = lines + news_lines

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
        if response.status_code in (200, 204):
            log("Alert sent to Discord.")
            return True
        log("Discord said " + str(response.status_code) + ": " + response.text)
        return False
    except requests.exceptions.RequestException as error:
        log("Could not reach Discord: " + str(error))
        return False


def send_demo_alerts(watchlist):
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

    player_clubs = []
    fpl_data = get_json(FPL_URL + "/bootstrap-static/")
    if fpl_data is not None:
        player_clubs = pick_player_clubs(fpl_data, watchlist)
        messages = messages + run_early_injury_check(now, force, fpl_data,
                                                     player_clubs)

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
