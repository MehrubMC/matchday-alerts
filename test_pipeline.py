import os
import unittest
from datetime import datetime, timezone

import main

WATCHLIST = {
    "clubs": [{"name": "Barcelona"}],
    "leagues": ["eng.1", "esp.1"],
    "player_league": "eng.1",
    "players": ["Haaland", "Groß", "Gibbs-White", "Walle Egeli"],
}

BARCA_FIXTURE = {"id": "1", "league": "esp.1", "timestamp": 1800000000,
                 "home": "Barcelona", "away": "Atletico Madrid"}
CITY_FIXTURE = {"id": "2", "league": "eng.1", "timestamp": 1800000000,
                "home": "Manchester City", "away": "Liverpool"}


def make_lineup(team_name, starters, subs):
    start_list = []
    for name in starters:
        start_list.append({"player": {"name": name}})
    sub_list = []
    for name in subs:
        sub_list.append({"player": {"name": name}})
    return {"team": {"name": team_name}, "formation": "4-3-3",
            "startXI": start_list, "substitutes": sub_list}


HAALAND = {"name": "Haaland", "team": "Man City", "status": "a", "news": "",
           "chance": None}


class TestNameMatching(unittest.TestCase):
    def test_short_name_matches(self):
        self.assertTrue(main.name_matches("Haaland", "E. Haaland"))

    def test_full_name_matches(self):
        self.assertTrue(main.name_matches("Haaland", "Erling Haaland"))

    def test_accents_and_eszett(self):
        self.assertTrue(main.name_matches("Groß", "Pascal Gross"))

    def test_hyphenated_name(self):
        self.assertTrue(main.name_matches("Gibbs-White", "Morgan Gibbs-White"))

    def test_two_word_name_uses_last_word(self):
        self.assertTrue(main.name_matches("Walle Egeli", "Walle Egeli"))

    def test_different_player_does_not_match(self):
        self.assertFalse(main.name_matches("Haaland", "Julian Alvarez"))

    def test_team_names_match_with_aliases(self):
        self.assertTrue(main.team_names_match("Man City", "Manchester City"))
        self.assertTrue(main.team_names_match("Spurs", "Tottenham Hotspur"))
        self.assertTrue(main.team_names_match("Brighton",
                                              "Brighton & Hove Albion"))
        self.assertFalse(main.team_names_match("Arsenal", "Chelsea"))


class TestEspnParsing(unittest.TestCase):
    SCOREBOARD = {"events": [{
        "id": "401",
        "date": "2026-11-14T15:00Z",
        "competitions": [{"competitors": [
            {"homeAway": "home", "team": {"displayName": "Manchester City"}},
            {"homeAway": "away", "team": {"displayName": "Liverpool"}},
        ]}],
    }]}

    def test_scoreboard_is_parsed(self):
        fixtures = main.parse_scoreboard(self.SCOREBOARD, "eng.1")
        self.assertEqual(len(fixtures), 1)
        self.assertEqual(fixtures[0]["home"], "Manchester City")
        self.assertEqual(fixtures[0]["away"], "Liverpool")
        expected = datetime(2026, 11, 14, 15, 0,
                            tzinfo=timezone.utc).timestamp()
        self.assertEqual(fixtures[0]["timestamp"], expected)

    def test_odd_scoreboard_does_not_crash(self):
        self.assertEqual(main.parse_scoreboard({}, "eng.1"), [])
        self.assertEqual(main.parse_scoreboard({"events": [{"id": "1"}]},
                                               "eng.1"), [])

    def test_rosters_are_split_into_starters_and_subs(self):
        summary = {"rosters": [{
            "team": {"displayName": "Barcelona"},
            "formation": "4-3-3",
            "roster": [
                {"starter": True, "athlete": {"displayName": "Lamine Yamal"}},
                {"starter": False, "athlete": {"displayName": "Pedri"}},
            ],
        }]}
        lineups = main.parse_espn_rosters(summary)
        self.assertEqual(lineups[0]["team"]["name"], "Barcelona")
        self.assertEqual(len(lineups[0]["startXI"]), 1)
        self.assertEqual(len(lineups[0]["substitutes"]), 1)

    def test_lineup_not_announced_gives_empty_xi(self):
        summary = {"rosters": [{
            "team": {"displayName": "Barcelona"},
            "roster": [{"starter": True, "athlete": {"displayName": ""}}],
        }]}
        lineups = main.parse_espn_rosters(summary)
        self.assertEqual(lineups[0]["startXI"], [])


class TestRelevantFixtures(unittest.TestCase):
    def test_all_fpl_league_matches_count(self):
        self.assertTrue(main.is_relevant_fixture(CITY_FIXTURE, WATCHLIST))

    def test_watched_club_in_other_league_counts(self):
        self.assertTrue(main.is_relevant_fixture(BARCA_FIXTURE, WATCHLIST))

    def test_unrelated_match_is_ignored(self):
        fixture = {"id": "3", "league": "esp.1", "timestamp": 1,
                   "home": "Sevilla", "away": "Getafe"}
        self.assertFalse(main.is_relevant_fixture(fixture, WATCHLIST))


class TestAlerts(unittest.TestCase):
    def test_watched_club_xi_is_shown(self):
        lineups = [make_lineup("Barcelona", ["Joan Garcia", "Gavi"], []),
                   make_lineup("Atletico Madrid", [], [])]
        message = main.build_lineup_message(BARCA_FIXTURE, lineups, [],
                                            WATCHLIST, [])
        self.assertIn("Lineup Alert: Barcelona vs Atletico Madrid", message)
        self.assertIn("Barcelona XI", message)
        self.assertIn("Gavi", message)

    def test_watched_player_on_bench_is_reported(self):
        lineups = [make_lineup("Manchester City", ["Phil Foden"],
                               ["Erling Haaland"])]
        message = main.build_lineup_message(CITY_FIXTURE, lineups, [],
                                            WATCHLIST, [HAALAND])
        self.assertIn("Haaland (Manchester City) is on the BENCH", message)

    def test_watched_player_starting_is_reported(self):
        lineups = [make_lineup("Manchester City", ["Erling Haaland"], [])]
        message = main.build_lineup_message(CITY_FIXTURE, lineups, [],
                                            WATCHLIST, [HAALAND])
        self.assertIn("Haaland (Manchester City) is STARTING", message)

    def test_injury_news_appears_for_the_matching_match(self):
        flag = {"name": "Haaland", "team": "Man City", "status": "d",
                "news": "Knock", "chance": 75}
        lineups = [make_lineup("Manchester City", ["Phil Foden"], [])]
        message = main.build_lineup_message(CITY_FIXTURE, lineups, [flag],
                                            WATCHLIST, [flag])
        self.assertIn("Knock", message)
        self.assertIn("75% chance", message)

    def test_injury_news_for_other_club_is_left_out(self):
        flag = {"name": "Palmer", "team": "Chelsea", "status": "i",
                "news": "Groin", "chance": 0}
        lineups = [make_lineup("Manchester City", ["Phil Foden"], [])]
        message = main.build_lineup_message(CITY_FIXTURE, lineups, [flag],
                                            WATCHLIST, [flag])
        self.assertNotIn("Groin", message)

    def test_nothing_relevant_gives_empty_message(self):
        lineups = [make_lineup("Manchester City", ["Phil Foden"], [])]
        message = main.build_lineup_message(CITY_FIXTURE, lineups, [],
                                            WATCHLIST, [])
        self.assertEqual(message, "")


class TestLeftOutOfSquad(unittest.TestCase):
    def test_player_missing_from_squad_is_flagged(self):
        lineups = [make_lineup("Manchester City", ["Phil Foden"],
                               ["Nico O'Reilly"])]
        message = main.build_lineup_message(CITY_FIXTURE, lineups, [],
                                            WATCHLIST, [HAALAND])
        self.assertIn("Haaland (Man City) is NOT in the matchday squad",
                      message)

    def test_unpublished_lineup_is_not_flagged(self):
        lineups = [make_lineup("Manchester City", [], [])]
        message = main.build_lineup_message(CITY_FIXTURE, lineups, [],
                                            WATCHLIST, [HAALAND])
        self.assertNotIn("NOT in the matchday squad", message)

    def test_player_from_other_club_is_ignored(self):
        lineups = [make_lineup("Manchester City", ["Phil Foden"], [])]
        chelsea_player = {"name": "Palmer", "team": "Chelsea", "status": "a",
                          "news": "", "chance": None}
        message = main.build_lineup_message(CITY_FIXTURE, lineups, [],
                                            WATCHLIST, [chelsea_player])
        self.assertNotIn("NOT in the matchday squad", message)


class TestFplLookup(unittest.TestCase):
    FPL_DATA = {
        "teams": [{"id": 1, "name": "Man City"}, {"id": 2, "name": "Brighton"},
                  {"id": 3, "name": "Hull"}],
        "elements": [
            {"web_name": "Haaland", "team": 1, "status": "d",
             "news": "Knock", "chance_of_playing_next_round": 75},
            {"web_name": "Mendy", "team": 2, "status": "a", "news": "",
             "chance_of_playing_next_round": None},
            {"web_name": "Mendy", "team": 3, "status": "a", "news": "",
             "chance_of_playing_next_round": None},
        ],
    }

    def test_unique_player_gets_club_and_status(self):
        result = main.pick_player_clubs(self.FPL_DATA, {"players": ["Haaland"]})
        self.assertEqual(result[0]["team"], "Man City")
        self.assertEqual(result[0]["status"], "d")

    def test_ambiguous_name_is_skipped(self):
        result = main.pick_player_clubs(self.FPL_DATA, {"players": ["Mendy"]})
        self.assertEqual(result, [])

    def test_player_clubs_setting_fixes_ambiguity(self):
        wl = {"players": ["Mendy"], "player_clubs": {"Mendy": "Brighton"}}
        result = main.pick_player_clubs(self.FPL_DATA, wl)
        self.assertEqual(result[0]["team"], "Brighton")

    def test_only_unavailable_players_are_flagged(self):
        wl = {"players": ["Haaland", "Mendy"],
              "player_clubs": {"Mendy": "Brighton"}}
        clubs = main.pick_player_clubs(self.FPL_DATA, wl)
        flags = main.find_fpl_flags(clubs)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["name"], "Haaland")


class TestClubInjuries(unittest.TestCase):
    API_FIXTURES = [
        {"id": 11, "home": "Real Madrid", "away": "Getafe"},
        {"id": 12, "home": "FC Barcelona", "away": "Atletico Madrid"},
    ]
    INJURIES = [
        {"player": {"name": "Pedri", "type": "Missing Fixture",
                    "reason": "Knock"},
         "team": {"name": "Barcelona"}},
        {"player": {"name": "Some Guy", "type": "Missing Fixture",
                    "reason": "Illness"},
         "team": {"name": "Atletico Madrid"}},
    ]

    def test_match_is_found_by_team_names(self):
        self.assertEqual(main.find_api_fixture_id(self.API_FIXTURES,
                                                  BARCA_FIXTURE), 12)

    def test_unknown_match_gives_none(self):
        other = {"home": "Sevilla", "away": "Girona"}
        self.assertIsNone(main.find_api_fixture_id(self.API_FIXTURES, other))

    def test_only_watched_club_injuries_are_kept(self):
        kept = main.filter_club_injuries(self.INJURIES, WATCHLIST)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["player"]["name"], "Pedri")

    def test_injuries_show_up_in_the_alert(self):
        kept = main.filter_club_injuries(self.INJURIES, WATCHLIST)
        lineups = [make_lineup("Barcelona", ["Joan Garcia"], [])]
        message = main.build_lineup_message(BARCA_FIXTURE, lineups, [],
                                            WATCHLIST, [], kept)
        self.assertIn("Pedri (Barcelona): Missing Fixture - Knock", message)
        self.assertNotIn("Some Guy", message)

    def test_no_api_key_means_no_injuries_and_no_crash(self):
        old_key = os.environ.pop("API_FOOTBALL_KEY", None)
        try:
            result = main.get_club_injuries(BARCA_FIXTURE, "2026-11-11",
                                            WATCHLIST)
            self.assertEqual(result, [])
        finally:
            if old_key is not None:
                os.environ["API_FOOTBALL_KEY"] = old_key


def make_xi(names):
    xi = []
    for name in names:
        xi.append({"player": {"name": name}})
    return xi


FULL_XI = make_xi(["Joan Garcia", "Jules Kounde", "Pau Cubarsi",
                   "Ronald Araujo", "Alejandro Balde", "Marc Casado",
                   "Pedri", "Frenkie de Jong", "Lamine Yamal",
                   "Robert Lewandowski", "Raphinha"])


class TestFormationDrawing(unittest.TestCase):
    def test_formation_is_split_into_numbers(self):
        self.assertEqual(main.parse_formation("4-2-3-1"), [4, 2, 3, 1])
        self.assertEqual(main.parse_formation("?"), [])

    def test_short_name_uses_last_word(self):
        self.assertEqual(main.short_name("Lamine Yamal"), "Yamal")
        self.assertEqual(main.short_name("Gavi"), "Gavi")
        self.assertEqual(main.short_name("Frenkie de Jong"), "de Jong")

    def test_drawing_has_attackers_on_top_and_keeper_at_bottom(self):
        shape = main.draw_formation("Barcelona", "4-3-3", FULL_XI)
        lines = shape.split("\n")
        self.assertEqual(lines[1], "Barcelona (4-3-3)")
        self.assertIn("Lewandowski", lines[3])
        self.assertIn("Garcia", lines[len(lines) - 2])

    def test_incomplete_lineup_is_not_drawn(self):
        self.assertEqual(main.draw_formation("Barcelona", "4-3-3",
                                             FULL_XI[:5]), "")

    def test_odd_formation_is_not_drawn(self):
        self.assertEqual(main.draw_formation("Barcelona", "?", FULL_XI), "")

    def test_alert_uses_the_drawing_for_a_full_xi(self):
        lineup = {"team": {"name": "Barcelona"}, "formation": "4-3-3",
                  "startXI": FULL_XI, "substitutes": []}
        message = main.build_lineup_message(BARCA_FIXTURE, [lineup], [],
                                            WATCHLIST, [])
        self.assertIn("```", message)
        self.assertIn("Yamal", message)

    def test_espn_places_put_starters_in_order(self):
        summary = {"rosters": [{
            "team": {"displayName": "Barcelona"}, "formation": "4-3-3",
            "roster": [
                {"starter": True, "formationPlace": "2",
                 "athlete": {"displayName": "Jules Kounde"}},
                {"starter": True, "formationPlace": "1",
                 "athlete": {"displayName": "Joan Garcia"}},
            ],
        }]}
        lineups = main.parse_espn_rosters(summary)
        self.assertEqual(lineups[0]["startXI"][0]["player"]["name"],
                         "Joan Garcia")


class TestWatchedMarkers(unittest.TestCase):
    def test_watched_player_gets_a_star(self):
        shape = main.draw_formation("Barcelona", "4-3-3", FULL_XI, ["Yamal"])
        self.assertIn("Yamal*", shape)
        self.assertNotIn("Pedri*", shape)
        self.assertIn("* = on your watchlist", shape)

    def test_no_legend_when_nobody_is_watched(self):
        shape = main.draw_formation("Barcelona", "4-3-3", FULL_XI)
        self.assertNotIn("watchlist", shape)

    def test_team_with_watched_player_gets_a_drawing(self):
        city_xi = make_xi(["Trafford", "O'Reilly", "Gvardiol", "Dias", "Lewis",
                           "Gonzalez", "Foden", "Reijnders", "Silva",
                           "Jeremy Doku", "Marmoush"])
        lineup = {"team": {"name": "Manchester City"}, "formation": "4-1-4-1",
                  "startXI": city_xi, "substitutes": []}
        doku = {"name": "Doku", "team": "Man City", "status": "a", "news": "",
                "chance": None}
        message = main.build_lineup_message(CITY_FIXTURE, [lineup], [],
                                            WATCHLIST, [doku])
        self.assertIn("```", message)
        self.assertIn("Doku*", message)

    def test_team_without_watched_players_is_not_drawn(self):
        lineup = {"team": {"name": "Manchester City"}, "formation": "4-3-3",
                  "startXI": FULL_XI, "substitutes": []}
        message = main.build_lineup_message(CITY_FIXTURE, [lineup], [],
                                            WATCHLIST, [])
        self.assertEqual(message, "")


class TestBench(unittest.TestCase):
    BENCH = make_xi(["Wojciech Szczesny", "Eric Garcia", "Gavi"])

    def test_bench_is_listed_under_the_shape(self):
        shape = main.draw_formation("Barcelona", "4-3-3", FULL_XI, [],
                                    self.BENCH)
        self.assertIn("Bench: Szczesny, Garcia, Gavi", shape)

    def test_watched_bench_player_gets_a_star(self):
        shape = main.draw_formation("Barcelona", "4-3-3", FULL_XI, ["Gavi"],
                                    self.BENCH)
        self.assertIn("Gavi*", shape)
        self.assertIn("* = on your watchlist", shape)

    def test_empty_bench_adds_no_bench_line(self):
        shape = main.draw_formation("Barcelona", "4-3-3", FULL_XI, [], [])
        self.assertNotIn("Bench", shape)

    def test_long_bench_wraps_inside_the_block(self):
        many = make_xi(["Player Numberone", "Player Numbertwo",
                        "Player Numberthree", "Player Numberfour",
                        "Player Numberfive", "Player Numbersix"])
        shape = main.draw_formation("Barcelona", "4-3-3", FULL_XI, [], many)
        for line in shape.split("\n"):
            self.assertLessEqual(len(line), 42)

    def test_bench_shows_when_formation_cannot_be_drawn(self):
        lineup = {"team": {"name": "Barcelona"}, "formation": "4-3-3",
                  "startXI": FULL_XI[:3], "substitutes": self.BENCH}
        message = main.build_lineup_message(BARCA_FIXTURE, [lineup], [],
                                            WATCHLIST, [])
        self.assertIn("Bench: Szczesny, Garcia, Gavi", message)


class TestEmptyDayAndTiming(unittest.TestCase):
    def test_no_fixtures_does_not_crash(self):
        now = datetime.now(timezone.utc)
        self.assertEqual(main.run_lineup_check([], now, WATCHLIST, False), [])

    def test_window_around_75_minutes(self):
        self.assertTrue(main.in_window(75, 75))
        self.assertTrue(main.in_window(70, 75))
        self.assertFalse(main.in_window(40, 75))
        self.assertFalse(main.in_window(120, 75))


if __name__ == "__main__":
    unittest.main()
