import requests
import re
import os
import json
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POSTED_GAMES_FILE = "posted_games.txt"
COPY_LINES = json.load(open("copy_bank.json"))['lines']


def get_recent_gamepks(team_id=137):
    now_uk = datetime.now(ZoneInfo("Europe/London"))
    start_date = (now_uk - timedelta(days=7)).strftime("%Y-%m-%d")
    end_date = (now_uk + timedelta(days=1)).strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId={team_id}&startDate={start_date}&endDate={end_date}"
    r = requests.get(url)
    data = r.json()
    games = []
    for date in data["dates"]:
        for game in date["games"]:
            if game["status"]["detailedState"] == "Final":
                game_pk = game["gamePk"]
                game_date = game["gameDate"]
                games.append((game_date, game_pk))
    games.sort(reverse=True)  # Most recent first
    return [pk for date, pk in games]


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
                        return item["title"], playback["url"]
        return None, None
    except Exception as e:
        print(f"❌ Exception while calling content API: {e}")
        return None, None


def send_telegram_message(title, url):
    game_info = title.replace("Condensed Game: ", "").strip()
    message = (
        f"<b>📼 {game_info}</b>\n"
        f"<code>────────────────────────────</code>\n"
        f"🎥 <a href=\"{url}\">▶ Watch Condensed Game</a>\n\n"
        f"<i>{random.choice(COPY_LINES)}</i>"
    )
    res = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
    )
    return res.ok


def main():
    print("🎬 Condensed Game Bot (GitHub Actions version)")
    gamepks = get_recent_gamepks()
    print(f"🧾 Found {len(gamepks)} recent Giants games")

    for gamepk in gamepks:
        print(f"🎬 Checking gamePk: {gamepk}")
        if already_posted(gamepk):
            print("⏩ Already posted")
            continue

        title, url = find_condensed_game(gamepk)
        if url:
            success = send_telegram_message(title, url)
            if success:
                mark_as_posted(gamepk)
                print("✅ Posted to Telegram")
            else:
                print("❌ Failed to post to Telegram")
            break  # Only post the most recent game
        else:
            print(f"❌ No condensed game found for {gamepk}")


if __name__ == "__main__":
    main()
