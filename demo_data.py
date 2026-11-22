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
        "formation": "4-1-4-1",
        "startXI": [
            {"player": {"name": "James Trafford"}, "place": 1},
            {"player": {"name": "Nico O'Reilly"}, "place": 2},
            {"player": {"name": "Josko Gvardiol"}, "place": 3},
            {"player": {"name": "Ruben Dias"}, "place": 4},
            {"player": {"name": "Rico Lewis"}, "place": 5},
            {"player": {"name": "Nico Gonzalez"}, "place": 6},
            {"player": {"name": "Phil Foden"}, "place": 7},
            {"player": {"name": "Tijjani Reijnders"}, "place": 8},
            {"player": {"name": "Bernardo Silva"}, "place": 9},
            {"player": {"name": "Jeremy Doku"}, "place": 10},
            {"player": {"name": "Omar Marmoush"}, "place": 11},
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
            {"player": {"name": "Giorgi Mamardashvili"}, "place": 1},
            {"player": {"name": "Jeremie Frimpong"}, "place": 2},
            {"player": {"name": "Ibrahima Konate"}, "place": 3},
            {"player": {"name": "Virgil van Dijk"}, "place": 4},
            {"player": {"name": "Milos Kerkez"}, "place": 5},
            {"player": {"name": "Ryan Gravenberch"}, "place": 6},
            {"player": {"name": "Alexis Mac Allister"}, "place": 7},
            {"player": {"name": "Dominik Szoboszlai"}, "place": 8},
            {"player": {"name": "Florian Wirtz"}, "place": 9},
            {"player": {"name": "Mohamed Salah"}, "place": 10},
            {"player": {"name": "Hugo Ekitike"}, "place": 11},
        ],
        "substitutes": [{"player": {"name": "Alisson"}},
            {"player": {"name": "Joe Gomez"}},
            {"player": {"name": "Curtis Jones"}},
            {"player": {"name": "Cody Gakpo"}},
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
            {"player": {"name": "Joan García"}, "place": 1},
            {"player": {"name": "João Cancelo"}, "place": 2},
            {"player": {"name": "Gerard Martín"}, "place": 3},
            {"player": {"name": "Pau Cubarsí"}, "place": 4},
            {"player": {"name": "Xavi Espart"}, "place": 5},
            {"player": {"name": "Fermín López"}, "place": 6},
            {"player": {"name": "Rodri"}, "place": 7},
            {"player": {"name": "Pedri"}, "place": 8},
            {"player": {"name": "Anthony Gordon"}, "place": 9},
            {"player": {"name": "Raphinha"}, "place": 10},
            {"player": {"name": "Lamine Yamal"}, "place": 11},
        ],
        "substitutes": [{"player": {"name": "Wojciech Szczesny"}},
            {"player": {"name": "Eric Garcia"}},
            {"player": {"name": "Gavi"}},
            {"player": {"name": "Ferran Torres"}},
            {"player": {"name": "Roony Bardghji"}}],
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
