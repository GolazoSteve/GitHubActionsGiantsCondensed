import os
import requests
import json
import random
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

POSTED_GAMES_FILE = "posted_games.txt"

with open("copy_bank.json", "r") as f:
    COPY_LINES = json.load(f)["lines"]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
print("🎬 Condensed Game Bot (GitHub Actions version)")

def get_latest_giants_gamepk():
    now_uk = datetime.now(ZoneInfo("Europe/London"))
    start_date = (now_uk - timedelta(days=3)).strftime("%Y-%m-%d")
    end_date = (now_uk + timedelta(days=1)).strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId=137&startDate={start_date}&endDate={end_date}"
    res = requests.get(url)
    if res.status_code != 200:
        logging.error("❌ Failed to fetch schedule.")
        return None

    dates = res.json().get("dates", [])
    all_games = []
    for date in dates:
        for game in date.get("games", []):
            if game.get("status", {}).get("detailedState") == "Final":
                all_games.append((game["gameDate"], game["gamePk"]))

    if not all_games:
        logging.info("🛑 No recent completed Giants games found.")
        return None

    return sorted(all_games, key=lambda x: x[0])[-1][1]

def find_condensed_game_video(game_pk):
    url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/content"
    response = requests.get(url)
    if response.status_code != 200:
        logging.error(f"Failed to fetch content for gamePk {game_pk}")
        return None, None

    data = response.json()
    videos = data.get("highlights", {}).get("highlights", {}).get("items", [])
    for video in videos:
        title = video.get("title", "").lower()
        description = video.get("description", "").lower()
        if "condensed" in title or "condensed" in description:
            for playback in video.get("playbacks", []):
                if "mp4" in playback.get("name", "").lower():
                    return video["title"], playback.get("url")
            return video["title"], f"https://www.mlb.com{video.get('url', '')}"
    return None, None

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

def send_telegram_message(title, url):
    game_info = title.replace("Condensed Game: ", "").strip()
    message = (
        f"<b>📼 {game_info}</b>\n"
        f"<code>────────────────────────────</code>\n"
        f"🎥 <a href=\"{url}\">▶ Watch Condensed Game</a>\n\n"
        f"<i>{random.choice(COPY_LINES)}</i>\n\n"
        f"<code>Delivered by your dependable GitHub Actions Bot 🤖</code>"
    )
    res = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
    )
    if res.status_code == 200:
        logging.info("✅ Sent to Telegram.")
    else:
        logging.error(f"❌ Telegram error: {res.text}")

def run_bot():
    game_pk = get_latest_giants_gamepk()
    if not game_pk:
        return
    if str(game_pk) in get_posted_games():
        logging.info("🛑 Already posted for this gamePk.")
        return
    title, url = find_condensed_game_video(game_pk)
    if url:
        send_telegram_message(title, url)
        save_posted_game(str(game_pk))
