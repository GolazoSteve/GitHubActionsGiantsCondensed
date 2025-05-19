import requests
import re
import os
import json
import random
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import logging

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POSTED_GAMES_FILE = "posted_games.txt"

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log")
    ]
)

# Load copy lines for WADE-isms
try:
    with open("copy_bank.json", "r") as f:
        copy_data = json.load(f)
        COPY_LINES = copy_data["lines"]
except Exception as e:
    logging.exception("Failed to load copy_bank.json")
    COPY_LINES = ["Your copy bank is offline. Please reboot sarcasm module."]


def get_latest_giants_gamepk(team_id=137):
    logging.info("Fetching most recent Giants gamePk.")
    url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId=137&startDate=2025-05-17&endDate=2025-05-19"
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        dates = data.get("dates", [])
        for date in reversed(dates):
            games = date.get("games", [])
            for game in games:
                if game.get("teams", {}).get("home", {}).get("team", {}).get("id") == team_id or \
                   game.get("teams", {}).get("away", {}).get("team", {}).get("id") == team_id:
                    game_pk = game.get("gamePk")
                    logging.info(f"Found gamePk: {game_pk}")
                    return game_pk
    except Exception as e:
        logging.exception("Error fetching or parsing gamePk data.")
    return None


def check_for_condensed_video(game_pk):
    logging.info(f"Checking for condensed game video for gamePk: {game_pk}")
    url = f"https://www.mlb.com/gameday/{game_pk}/video"
    try:
        res = requests.get(url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        scripts = soup.find_all("script")

        for script in scripts:
            if "condensed game" in script.text.lower():
                matches = re.findall(r"https://.*?\.mp4", script.text)
                for m in matches:
                    if "condensed" in m:
                        logging.info(f"Found condensed game video: {m}")
                        return m
        logging.info("No condensed game video found.")
    except Exception as e:
        logging.exception("Error scraping video page.")
    return None


def send_telegram_message(text):
    logging.info(f"Sending Telegram message: {text}")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        res = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})
        res.raise_for_status()
        logging.info("Telegram message sent successfully.")
    except Exception as e:
        logging.exception("Failed to send Telegram message.")


def has_been_posted(game_pk):
    if not os.path.exists(POSTED_GAMES_FILE):
        return False
    with open(POSTED_GAMES_FILE, "r") as f:
        return str(game_pk) in f.read()


def log_posted_game(game_pk):
    with open(POSTED_GAMES_FILE, "a") as f:
        f.write(f"{game_pk}\n")
    logging.info(f"Logged gamePk as posted: {game_pk}")


def main():
    print("🎬 Condensed Game Bot (GitHub Actions version)")
    logging.info("Starting bot script.")

    try:
        game_pk = get_latest_giants_gamepk()
        if not game_pk:
            logging.warning("No gamePk returned — exiting.")
            return

        if has_been_posted(game_pk):
            logging.info("Already posted this game — exiting.")
            return

        video_url = check_for_condensed_video(game_pk)
        if video_url:
            message = f"⚾ Giants Condensed Game Available:\n{random.choice(COPY_LINES)}\n{video_url}"
            send_telegram_message(message)
            log_posted_game(game_pk)
        else:
            logging.info("Condensed video not found. Skipping post.")

    except Exception as e:
        logging.exception("Unhandled exception in main().")


if __name__ == "__main__":
    main()
