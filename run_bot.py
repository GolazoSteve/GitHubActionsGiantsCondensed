import os
import re
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FORCE_POST = os.getenv("FORCE_POST") == "true"
POSTED_LOG = "posted_games.txt"


def load_posted_games():
    if not os.path.exists(POSTED_LOG):
        return set()
    with open(POSTED_LOG, "r") as f:
        return set(line.strip() for line in f.readlines())


def save_posted_game(game_pk):
    with open(POSTED_LOG, "a") as f:
        f.write(f"{game_pk}\n")


def get_recent_gamepks():
    url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2025-05-16"
    data = requests.get(url).json()
    gamepks = []
    for date in data.get("dates", []):
        for game in date.get("games", []):
            if game.get("status", {}).get("detailedState") == "Final":
                gamepks.append(str(game["gamePk"]))
    return gamepks


def get_condensed_game_url(game_pk):
    # Scrape fallback page: /gameday/{gamePk}/video
    url = f"https://www.mlb.com/gameday/{game_pk}/video"
    print(f"🔍 Scraping {url}")
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    pattern = re.compile(r'https://mlb-cuts-diamond\.mlb\.com/.*\.mp4')

    for tag in soup.find_all("a", href=True):
        if "condensed" in tag.text.lower():
            match = pattern.search(str(tag))
            if match:
                return match.group(0)

    # Fallback: look in raw HTML
    match = pattern.search(res.text)
    if match:
        return match.group(0)

    return None


def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    r = requests.post(url, data=data)
    return r.status_code == 200


def main():
    posted = load_posted_games()
    gamepks = get_recent_gamepks()
    print(f"🧾 Found {len(gamepks)} recent completed games")

    for game_pk in gamepks:
        if game_pk in posted and not FORCE_POST:
            continue

        print(f"🎬 Checking gamePk: {game_pk}")
        url = get_condensed_game_url(game_pk)

        if url:
            message = f"📽️ Condensed Game:\n{url}"
            print(f"✅ Posting: {message}")
            success = send_to_telegram(message)
            if success:
                save_posted_game(game_pk)
            else:
                print("⚠️ Failed to post to Telegram.")
        else:
            print(f"❌ No condensed game found for {game_pk}")


if __name__ == "__main__":
    main()
