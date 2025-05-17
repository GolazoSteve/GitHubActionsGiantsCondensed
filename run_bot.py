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
    url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2025-05-10&endDate=2025-05-17"
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

def extract_condensed_game_url(html):
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script")
    for script in scripts:
        if script.string:
            matches = re.findall(r"https://mlb-cuts-diamond\.mlb\.com/[^\"']+condensed[^\"']+\.mp4", script.string)
            if matches:
                return matches[0]
    return None

def find_condensed_game(gamepk):
    url = f"https://www.mlb.com/gameday/{gamepk}/video"
    print(f"🔍 Scraping {url}")
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            print(f"⚠️ HTTP {r.status_code} for {url}")
            return None
        return extract_condensed_game_url(r.text)
    except Exception as e:
        print(f"❌ Exception while scraping {url}: {e}")
        return None

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    r = requests.post(url, data=data)
    return r.ok

def main():
    print("🎬 Condensed Game Bot (GitHub Actions version)")
    gamepks = get_recent_gamepks()
    print(f"🧾 Found {len(gamepks)} recent completed games")

    for gamepk in gamepks:
        print(f"🎬 Checking gamePk: {gamepk}")
        if already_posted(gamepk):
            print("⏩ Already posted")
            continue

        url = find_condensed_game(gamepk)
        if url:
            msg = f"🎥 Condensed Game Available!\n{url}"
            success = send_telegram_message(msg)
            if success:
                mark_as_posted(gamepk)
                print("✅ Posted to Telegram")
            else:
                print("❌ Failed to post to Telegram")
        else:
            print(f"❌ No condensed game found for {gamepk}")

if __name__ == "__main__":
    main()
