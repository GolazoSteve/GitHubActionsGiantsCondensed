import requests
import re
import os
import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POSTED_GAMES_FILE = "posted_games.txt"

def telegram_message(msg):
    print("📤 Sending Telegram message...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    response = requests.post(url, json=payload)
    print(f"✅ Telegram sent: {response.status_code}")
    return response.status_code == 200

def has_already_posted(game_pk):
    if not os.path.exists(POSTED_GAMES_FILE):
        return False
    with open(POSTED_GAMES_FILE, "r") as f:
        return str(game_pk) in f.read()

def mark_as_posted(game_pk):
    with open(POSTED_GAMES_FILE, "a") as f:
        f.write(f"{game_pk}\n")

def get_condensed_game_url(game_pk):
    print(f"🔍 Scraping video page for gamePk {game_pk}")
    video_url = f"https://www.mlb.com/gameday/{game_pk}/video"
    res = requests.get(video_url)
    if res.status_code != 200:
        print("❌ Failed to load video page.")
        return None

    soup = BeautifulSoup(res.text, "html.parser")
    pattern = re.compile(r'https://.*?condensed.*?\.mp4')
    match = pattern.search(soup.prettify())
    if match:
        print("✅ Condensed game video found!")
        return match.group(0)
    else:
        print("🚫 No condensed game video found.")
        return None

def get_most_recent_valid_gamepk():
    print("📅 Searching for the most recent Final Giants game with a condensed game video...")
    team_id = 137
    today = datetime.utcnow()
    for i in range(5):  # Check last 5 days
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}&teamId={team_id}"
        r = requests.get(url)
        data = r.json()
        dates = data.get("dates", [])
        if not dates:
            continue

        games = dates[0].get("games", [])
        for game in games:
            game_pk = game["gamePk"]
            status = game["status"]["detailedState"]
            if status != "Final":
                continue
            if has_already_posted(game_pk):
                continue
            if get_condensed_game_url(game_pk):
                return game_pk
    print("⚠️ No valid recent game found.")
    return None

def main():
    print("🎬 Condensed Game Bot (GitHub Actions version)")

    game_pk = get_most_recent_valid_gamepk()
    if not game_pk:
        print("🛑 No valid gamePk found to post.")
        return

    video_url = get_condensed_game_url(game_pk)
    if not video_url:
        print("🛑 No condensed game video found.")
        return

    msg = f"<b>🎞️ Giants Condensed Game</b>\n\n<a href='{video_url}'>Watch the highlights</a>"
    if telegram_message(msg):
        mark_as_posted(game_pk)
    else:
        print("❌ Failed to send Telegram message.")

if __name__ == "__main__":
    main()
