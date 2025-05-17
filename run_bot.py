import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FORCE_POST = os.getenv("FORCE_POST", "false").lower() == "true"
POSTED_GAMES_FILE = "posted_games.txt"

def get_latest_giants_gamepk():
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=3)
    end_date = today

    url = (
        f"https://statsapi.mlb.com/api/v1/schedule?"
        f"teamId=137&startDate={start_date}&endDate={end_date}&sportId=1"
    )

    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    games = []
    for date in data.get("dates", []):
        for game in date.get("games", []):
            if (
                game.get("gameType") == "R" and
                game.get("status", {}).get("detailedState") == "Final"
            ):
                games.append({
                    "gamePk": game["gamePk"],
                    "date": game["gameDate"]
                })

    if not games:
        print("❌ No recent completed regular-season Giants games found.")
        return None

    # Sort by gameDate descending to get most recent
    games.sort(key=lambda g: g["date"], reverse=True)
    latest_gamepk = games[0]["gamePk"]
    print(f"✅ Using latest gamePk: {latest_gamepk}")
    return latest_gamepk

def get_condensed_game_url(game_pk):
    url = f"https://www.mlb.com/gameday/{game_pk}/video"
    response = requests.get(url)
    if "condensed-game" not in response.text:
        return None

    import re
    match = re.search(r'(https://.+?condensed-game[^"]+\.mp4)', response.text)
    if match:
        return match.group(1)
    return None

def has_already_posted(game_pk):
    if not os.path.exists(POSTED_GAMES_FILE):
        return False
    with open(POSTED_GAMES_FILE, "r") as f:
        return str(game_pk) in f.read()

def mark_as_posted(game_pk):
    with open(POSTED_GAMES_FILE, "a") as f:
        f.write(f"{game_pk}\n")
    print(f"💾 Saved gamePk: {game_pk}")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("✅ Sent to Telegram.")
    else:
        print(f"❌ Failed to send message: {response.text}")

def main():
    print("🎬 Condensed Game Bot (GitHub Actions version)")

    game_pk = get_latest_giants_gamepk()
    if not game_pk:
        return

    if has_already_posted(game_pk) and not FORCE_POST:
        print("🟡 Already posted. Skipping.")
        return

    video_url = get_condensed_game_url(game_pk)
    if not video_url:
        print("🚫 No condensed game video found.")
        if FORCE_POST:
            mark_as_posted(game_pk)
        return

    send_telegram_message(f"📽️ <b>Condensed Game:</b>\n{video_url}")
    mark_as_posted(game_pk)

if __name__ == "__main__":
    main()
