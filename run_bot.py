import requests
import re
import os
import sys
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POSTED_GAMES_FILE = "posted_games.txt"

def get_most_recent_giants_gamepk():
    url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId=137&startDate=2025-05-10&endDate=2025-05-17"
    r = requests.get(url)
    data = r.json()
    games = []

    for date in data["dates"]:
        for game in date["games"]:
            if game["status"]["detailedState"] == "Final":
                games.append((game["gameDate"], game["gamePk"]))

    if not games:
        return None

    most_recent = sorted(games, key=lambda x: x[0])[-1]
    return most_recent[1]

def already_posted(gamepk):
    if not os.path.exists(POSTED_GAMES_FILE):
        return False
    with open(POSTED_GAMES_FILE, "r") as f:
        return str(gamepk) in f.read()

def mark_as_posted(gamepk):
    with open(POSTED_GAMES_FILE, "a") as f:
        f.write(f"{gamepk}\n")

def find_condensed_game(gamepk):
    url = f"https://statsapi.mlb.com/api/v1/game/{gamepk}/content"
    print(f"🔍 Checking MLB content API: {url}")
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            print(f"⚠️ HTTP {res.status_code} for {url}")
            return None

        data = res.json()
        items = data.get("highlights", {}).get("highlights", {}).get("items", [])
        for item in items:
            title = item.get("title", "").lower()
            desc = item.get("description", "").lower()
            if "condensed" in title or "condensed" in desc:
                for playback in item.get("playbacks", []):
                    if "mp4" in playback.get("name", "").lower():
                        return playback["url"]
        return None
    except Exception as e:
        print(f"❌ Exception while calling content API: {e}")
        return None

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    r = requests.post(url, data=data)
    return r.ok

def main(force=False):
    print("🎬 Condensed Game Bot (GitHub Actions version)")
    gamepk = get_most_recent_giants_gamepk()
    if not gamepk:
        print("🛑 No recent Giants games found")
        return

    print(f"🎬 Checking gamePk: {gamepk}")
    if not force and already_posted(gamepk):
        print("⏩ Already posted")
        return

    url = find_condensed_game(gamepk)
    if url:
        msg = f"🎥 Condensed Game Available!\n{url}"
        success = send_telegram_message(msg)
        if success and not force:
            mark_as_posted(gamepk)
            print("✅ Posted to Telegram")
        elif success:
            print("✅ Forced post to Telegram")
        else:
            print("❌ Failed to post to Telegram")
    else:
        print(f"❌ No condensed game found for {gamepk}")

if __name__ == "__main__":
    force = "--force" in sys.argv
    main(force=force)
