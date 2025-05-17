import requests
import json
import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FORCE_POST = os.getenv("FORCE_POST", "false").lower() == "true"

POSTED_GAMES_FILE = "posted_games.txt"

def get_recent_giants_games():
    today = datetime.utcnow()
    start_date = (today - timedelta(days=3)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    url = (
        f"https://statsapi.mlb.com/api/v1/schedule?"
        f"teamId=137&startDate={start_date}&endDate={end_date}&sportId=1"
    )
    r = requests.get(url)
    data = r.json()

    completed_gamepks = []
    for date in data["dates"]:
        for game in date["games"]:
            if game["status"]["abstractGameState"] == "Final":
                completed_gamepks.append(game["gamePk"])

    return completed_gamepks

def has_been_posted(game_pk):
    if not os.path.exists(POSTED_GAMES_FILE):
        return False
    with open(POSTED_GAMES_FILE, "r") as f:
        posted = f.read().splitlines()
    return str(game_pk) in posted

def mark_as_posted(game_pk):
    with open(POSTED_GAMES_FILE, "a") as f:
        f.write(f"{game_pk}\n")

def find_condensed_game_url(game_pk):
    # Try MLB Stats API first
    url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/content"
    r = requests.get(url)
    data = r.json()

    try:
        for item in data["media"]["epg"]:
            if item["title"] == "Extended Highlights":
                for media in item["items"]:
                    if "condensed" in media["title"].lower():
                        return media["playbacks"][0]["url"]
    except (KeyError, IndexError):
        pass

    # Fallback to scraping
    fallback_url = f"https://www.mlb.com/gameday/{game_pk}/video"
    r = requests.get(fallback_url)
    video_url = fallback_find_mp4_in_html(r.text)
    return video_url

def fallback_find_mp4_in_html(html):
    # First: classic .mp4 links
    mp4_links = re.findall(r'https?://[^\s"\']+?\.mp4', html)
    for link in mp4_links:
        if "condensed" in link.lower():
            return link

    # Second: source tags or lazy-loaded video URLs
    tag_matches = re.findall(r'(?:src|data-video-url)="(https?://[^\s"]+?\.mp4)"', html)
    for link in tag_matches:
        if "condensed" in link.lower():
            return link

    return None

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": False,
    }
    requests.post(url, data=payload)

def run():
    print("🎬 Condensed Game Bot (GitHub Actions version)")

    game_pks = get_recent_giants_games()
    for game_pk in sorted(game_pks):
        print(f"🔍 Checking gamePk: {game_pk}")
        if has_been_posted(game_pk) and not FORCE_POST:
            continue

        video_url = find_condensed_game_url(game_pk)
        if video_url:
            send_telegram_message(f"Giants Condensed Game: {video_url}")
            mark_as_posted(game_pk)
            print(f"✅ Posted condensed game: {video_url}")
            break
        else:
            print("🚫 No condensed game video found.")
            mark_as_posted(game_pk)

if __name__ == "__main__":
    run()
