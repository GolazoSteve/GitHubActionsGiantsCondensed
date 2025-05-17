import requests
import re
import os
import json
import random
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POSTED_GAMES_FILE = "posted_games.txt"

# Load copy lines for WADE-isms
with open("copy_bank.json", "r") as f:
    copy_data = json.load(f)
    COPY_LINES = copy_data["lines"]

def get_recent_gamepks(team_id=137):
    url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2025-05-10&endDate=2025-05-17"
    r = requests.get(url)
    data = r.json()
    gamepks = []
    for date in data["dates"]:
        for game in date["games"]:
            if game["status"]["detailedState"] == "Final" and game["teams"]["home"]["team"]["id"] == team_id or game["teams"]["away"]["team"]["id"] == team_id:
                gamepks.append(game["gamePk"])
    return sorted(gamepks)

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
            return None, None

        data = res.json()
        items = data.get("highlights", {}).get("highlights", {}).get("items", [])
        for item in items:
            title = item.get("title", "").lower()
            desc = item.get("description", "").lower()
            if "condensed" in title or "condensed" in desc:
                for playback in item.get("playbacks", []):
                    if "mp4" in playback.get("name", "").lower():
                        return item.get("title", "Condensed Game"), playback["url"]
        return None, None
    except Exception as e:
        print(f"❌ Exception while calling content API: {e}")
        return None, None

def send_telegram_message(title, url):
    random_line = random.choice(COPY_LINES)
    message = (
        f"<b>📼 {title}</b>\n"
        f"<code>────────────────────────────</code>\n"
        f"🎥 <a href=\"{url}\">▶ Watch Condensed Game</a>\n\n"
        f"<i>{random_line}</i>"
    )
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    res = requests.post(api_url, data=payload)
    return res.ok

def main(force=False):
    print("🎬 Condensed Game Bot (GitHub Actions version)")
    gamepks = get_recent_gamepks()
    print(f"🧾 Found {len(gamepks)} recent completed Giants games")

    target_gamepk = gamepks[-1] if gamepks else None
    if not target_gamepk:
        print("🛑 No recent Giants game found")
        return

    if not force and already_posted(target_gamepk):
        print("⏩ Already posted")
        return

    title, url = find_condensed_game(target_gamepk)
    if url:
        success = send_telegram_message(title, url)
        if success:
            if not force:
                mark_as_posted(target_gamepk)
            print("✅ Posted to Telegram")
        else:
            print("❌ Failed to post to Telegram")
    else:
        print(f"❌ No condensed game found for {target_gamepk}")

if __name__ == "__main__":
    import sys
    force_flag = "--force" in sys.argv
    main(force=force_flag)
