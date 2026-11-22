PLAYER_CLUBS = [
    {"name": "Haaland", "team": "Man City", "status": "a", "news": "",
     "chance": None},
    {"name": "Doku", "team": "Man City", "status": "d",
     "news": "Knock - 75% chance of playing", "chance": 75},
    {"name": "Isak", "team": "Liverpool", "status": "a", "news": "",
     "chance": None},
]

CITY_FIXTURE = {
    "id": "1", "league": "eng.1", "timestamp": 1800000000,
    "home": "Manchester City", "away": "Liverpool",
}

CITY_LINEUPS = [
    {
        "team": {"name": "Manchester City"},
        "formation": "4-2-3-1",
        "startXI": [
            {"player": {"name": "James Trafford"}, "place": 1},
            {"player": {"name": "Rico Lewis"}, "place": 2},
            {"player": {"name": "Nico O'Reilly"}, "place": 3},
            {"player": {"name": "Nico Gonzalez"}, "place": 4},
            {"player": {"name": "Ruben Dias"}, "place": 5},
            {"player": {"name": "Josko Gvardiol"}, "place": 6},
            {"player": {"name": "Bernardo Silva"}, "place": 7},
            {"player": {"name": "Tijjani Reijnders"}, "place": 8},
            {"player": {"name": "Omar Marmoush"}, "place": 9},
            {"player": {"name": "Phil Foden"}, "place": 10},
            {"player": {"name": "Jeremy Doku"}, "place": 11},
        ],
        "substitutes": [{"player": {"name": "Stefan Ortega"}},
            {"player": {"name": "Abdukodir Khusanov"}},
            {"player": {"name": "Mateo Kovacic"}},
            {"player": {"name": "Rayan Cherki"}},
            {"player": {"name": "Savinho"}}],
    },
    {
        "team": {"name": "Liverpool"},
        "formation": "4-2-3-1",
        "startXI": [
            {"player": {"name": "Alisson Becker"}, "place": 1},
            {"player": {"name": "Jeremie Frimpong"}, "place": 2},
            {"player": {"name": "Milos Kerkez"}, "place": 3},
            {"player": {"name": "Alexis Mac Allister"}, "place": 4},
            {"player": {"name": "Ibrahima Konate"}, "place": 5},
            {"player": {"name": "Virgil van Dijk"}, "place": 6},
            {"player": {"name": "Mohamed Salah"}, "place": 7},
            {"player": {"name": "Dominik Szoboszlai"}, "place": 8},
            {"player": {"name": "Hugo Ekitike"}, "place": 9},
            {"player": {"name": "Florian Wirtz"}, "place": 10},
            {"player": {"name": "Cody Gakpo"}, "place": 11},
        ],
        "substitutes": [{"player": {"name": "Giorgi Mamardashvili"}},
            {"player": {"name": "Joe Gomez"}},
            {"player": {"name": "Curtis Jones"}},
            {"player": {"name": "Conor Bradley"}},
            {"player": {"name": "Alexander Isak"}}],
    },
]


BARCA_FIXTURE = {
    "id": "2", "league": "esp.1", "timestamp": 1800000000,
    "home": "Barcelona", "away": "Real Madrid",
}

BARCA_LINEUPS = [
    {
        "team": {"name": "Barcelona"},
        "formation": "4-3-3",
        "startXI": [
            {"player": {"name": "Joan Garcia"}, "place": 1},
            {"player": {"name": "Eric Garcia"}, "place": 2},
            {"player": {"name": "Joao Cancelo"}, "place": 3},
            {"player": {"name": "Marc Bernal"}, "place": 4},
            {"player": {"name": "Frenkie de Jong"}, "place": 5},
            {"player": {"name": "Gerard Martin"}, "place": 6},
            {"player": {"name": "Fermin Lopez"}, "place": 7},
            {"player": {"name": "Pedri"}, "place": 8},
            {"player": {"name": "Raphinha"}, "place": 9},
            {"player": {"name": "Lamine Yamal"}, "place": 10},
            {"player": {"name": "Karim Adeyemi"}, "place": 11},
        ],
        "substitutes": [{"player": {"name": "Wojciech Szczesny"}},
            {"player": {"name": "Gavi"}},
            {"player": {"name": "Ferran Torres"}},
            {"player": {"name": "Roony Bardghji"}},
            {"player": {"name": "Marc Casado"}}],
    },
    {
        "team": {"name": "Real Madrid"},
        "formation": "4-3-3",
        "startXI": [],
        "substitutes": [],
    },
]

BARCA_INJURIES = [
    {"player": {"name": "Dani Olmo", "type": "Missing Fixture",
                "reason": "Hamstring"},
     "team": {"name": "Barcelona"}},
    {"player": {"name": "Vinicius Junior", "type": "Missing Fixture",
                "reason": "Illness"},
     "team": {"name": "Real Madrid"}},
]
