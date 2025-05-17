import os
import requests
import json
import re
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FORCE_POST = os.getenv("FORCE_POST", "false").lower() == "true"

POSTED_GAMES_FILE = "posted_games.txt"

logging.basicConfig(level=logging.INFO, format="%(message)s")

def send_telegram_message(game_date, video_url):
    message = f"📺 Condensed Game — {game_date}\n\n👉 {video_url}"
    res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    })
    if res.ok:
        logging.info("✅ Telegram post sent.")
    else:
        logging.error(f"❌ Telegram error: {res.text}")

def get_posted_games():
    try:
        with open(POSTED_GAMES_FILE, "r") as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()

def save_posted_game(game_pk):
    with open(POSTED_GAMES_FILE, "a") as f:
        f.write(f"{game_pk}\n")
    logging.info(f"💾 Saved gamePk: {game_pk}")

def get_recent_giants_games():
    today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    start = today - timedelta(days=3)
    url = f"https://statsapi.mlb.com/api/v1/schedule"
    params = {
        "sportId": 1,
        "teamId": 137,  # Giants
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d"),
    }
    res = requests.get(url, params=params)
    if not res.ok:
        logging.error("❌ Failed to fetch schedule")
        return []
    data = res.json()
    games = []
    for date_info in data.get("dates", []):
        for game in date_info.get("games", []):
            if game["status"]["detailedState"] == "Final":
                games.append((game["gamePk"], game["gameDate"][:10]))
    return sorted(games, key=lambda x: x[1], reverse=True)

def get_condensed_game_url(game_pk):
    url = f"https://www.mlb.com/gameday/{game_pk}/video"
    res = requests.get(url)
    if not res.ok:
        return None
    match = re.search(r'window\.__data\s*=\s*({.*?});\s*</script>', res.text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
        items = data.get("mediaPlayback", {}).get("media", {}).get("epg", [])
        for group in items:
            for video in group.get("items", []):
                title = video.get("title", "").lower()
                if "condensed game" in title:
                    for playback in video.get("playbacks", []):
                        if playback.get("name") == "mp4Avc":
                            return playback["url"]
    except Exception as e:
        logging.warning(f"⚠️ JSON parse error: {e}")
    return None

def main():
    print("🎬 Condensed Game Bot (GitHub Actions version)")
    posted = get_posted_games()
    games = get_recent_giants_games()
    for game_pk, date in games:
        if str(game_pk) in posted and not FORCE_POST:
            logging.info(f"⚪ Already posted gamePk: {game_pk}")
            continue
        logging.info(f"🔍 Checking gamePk: {game_pk}")
        video_url = get_condensed_game_url(game_pk)
        if video_url:
            logging.info(f"🎯 Found condensed game: {video_url}")
            send_telegram_message(date, video_url)
            save_posted_game(game_pk)
            return
        else:
            logging.info("🚫 No condensed game video found.")
            save_posted_game(game_pk)
            if FORCE_POST:
                return

if __name__ == "__main__":
    main()
