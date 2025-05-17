import requests
import re
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POSTED_GAMES_FILE = "posted_games.txt"

def get_recent_gamepks():
    url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId=137&startDate=2025-05-10&endDate=2025-05-17"
    r = requests.get(url)
    data = r.json()
    gamepks = []
    for date in data["dates"]:
        for game in date["games"]:
            if game["status"]["detailedState"] == "Final":
                gamepks.append(game["gamePk"])
    return gamepks

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

def main():
    print("🎬 Condensed Game Bot (GitHub Actions version)")
    gamepks = get_recent_gamepks()
    print(f"🧾 Found {len(gamepks)} recent completed Giants games")

    if not gamepks:
        print("🛑 No recent Giants games found")
        return

    latest_gamepk = max(gamepks)
    print(f"🎯 Latest gamePk: {latest_gamepk}")

    if already_posted(latest_gamepk):
        print("⏩ Already posted for latest game")
        return

    url = find_condensed_game(latest_gamepk)
    if url:
        msg = f"🎥 Condensed Game Available!\n{url}"
        success = send_telegram_message(msg)
        if success:
            mark_as_posted(latest_gamepk)
            print("✅ Posted to Telegram")
        else:
            print("❌ Failed to post to Telegram")
    else:
        print("❌ No condensed game found for latest Giants game")

if __name__ == "__main__":
    main()
