# Automated Soccer Matchday Lineup and Injury Alert Pipeline

Python pipeline that checks soccer lineups and injury news against your own
watchlist and sends alerts to a private Discord channel. It runs on a schedule
through GitHub Actions.

## Data sources

- **ESPN's public soccer API:** today's fixtures and official lineups
  (Premier League, La Liga, Champions League). It is unofficial and
  undocumented, so it could change without notice.
- **Official FPL API:** injury news and which club each of your players is at.
- **API-Football (optional, free plan):** injuries for watched clubs like
  Barcelona. Turn it on by adding `API_FOOTBALL_KEY`. The free plan only
  answers for matches within about a day of today, which is all this needs.
  It uses 1 request per day for fixtures plus 1 per watched-club match.

## What it does

1. **~120 min before the next FPL deadline:** sends injury news for the players
   in `watchlist.json`.
2. **~75 min before kickoff:** pulls the official lineup from ESPN for Premier
   League matches and matches involving your watched clubs. It alerts you if a
   watched player is starting, on the bench, or left out of the matchday squad
   entirely, and shows FPL injury news for players in that match. It also draws the starting XI in formation, with the bench listed underneath, for watched
   clubs and for teams with one of your players (marked with *).

If nothing relevant turns up, it sends nothing.

## Setup

1. Make a Discord webhook (Server Settings > Integrations > Webhooks).
2. Local use: copy `.env.example` to `.env` and paste the webhook URL.
3. `pip install -r requirements.txt`
4. `python main.py --test-alert` sends a test message to Discord.
5. `python main.py --demo` sends two sample alerts (fake data) to Discord. Best for presenting.
6. `python main.py --force` skips the timing windows and runs on real data. You only get a message if something relevant is happening today.
7. `python main.py --force --date 2026-11-08` replays a past matchday with real lineups from ESPN (change the date to any day with matches). Good for testing when there are no games today.
8. `python -m unittest test_pipeline.py -v` runs the mock-data tests.

## GitHub Actions

Push this repo to GitHub, then add repository secrets
(Settings > Secrets and variables > Actions): `DISCORD_WEBHOOK_URL`, and
optionally `API_FOOTBALL_KEY`.

The workflow in `.github/workflows/matchday-alerts.yml` runs every 15 minutes
between 08:00 and 22:59 UTC. To trigger it by hand: Actions tab > Matchday Alerts >
Run workflow, and type `--demo` or `--force` in the flags box.

## Customizing

Edit `watchlist.json`:

- `clubs`: clubs to follow fully (use the name ESPN shows, e.g. "Barcelona")
- `leagues`: ESPN league codes to check (`eng.1`, `esp.1`, `uefa.champions`, `ger.1`, `ita.1`, ...)
- `player_league`: the league your fantasy players play in (`eng.1` = Premier League)
- `players`: your fantasy players (last names work; accents are ignored)
- `player_clubs`: only needed if a name matches more than one FPL player, e.g.
  `{"Mendy": "Brighton"}`. The log tells you when this is needed.

## Known limits

- ESPN has no injury data. Injury news for your FPL players comes from FPL.
  Injuries for watched clubs like Barcelona need the optional API-Football key;
  without it you only get their starting XI.
- API-Football's free plan can't look at past dates, so `--date` replays won't
  show club injuries.
- ESPN only fills in lineups once they're officially announced. If they aren't
  out at the 75-minute check, that match is skipped for the day.
- Names are matched by last name. If a name matches more than one FPL player,
  that player is skipped until you add them to `player_clubs`.
- "Not in the squad" only fires once the lineup is published.
- The formation drawing currently supports 4-3-3 and 4-2-3-1. Other formations show a plain list
  of names, and the log prints each player's ESPN slot number so a new layout can be added.
