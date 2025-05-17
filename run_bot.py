import os
import requests
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FORCE_POST = os.getenv("FORCE_POST", "").lower() == "true"
POSTED_LOG = "posted_games.txt"


def get_recent_giants_games():
    url = "https://statsapi.mlb.com/api/v1/schedule"
    params = {
        "sportId": 1,
        "teamId": 137,  # SF Giants
        "startDate": (datetime.today() - timedelta(days=3)).strftime("%Y-%m-%d"),
        "endDate": datetime.today().strftime("%Y-%m-%d"),
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    game_pks = []
    for date in data.get("dates", []):
        for game in date.get("games", []):
            if game["status"]["detailedState"] == "Final":
                game_pks.append(game["gamePk"])
    return game_pks


def load_posted_gamepks():
    if not os.path.exists(POSTED_LOG):
        return set()
    with open(POSTED_LOG, "r") as f:
        return set(line.strip() for line in f)


def save_posted_gamepk(game_pk):
    with open(POSTED_LOG, "a") as f:
        f.write(f"{game_pk}\n")


def find_mp4_url(game_pk):
    url = f"https://www.mlb.com/gameday/{game_pk}/video"
    resp = requests.get(url)
    html = resp.text

    # First, try your existing method: __INITIAL_STATE__ blob
    match = re.search(r"__INITIAL_STATE__\s*=\s*(\{.*?\});", html)
    if match:
        json_blob = match.group(1)
        mp4_matches = re.findall(r"https.*?\.mp4", json_blob)
        if mp4_matches:
            return mp4_matches[0]

    # Fallback: scan whole HTML for MP4
    return fallback_find_mp4_in_html(html)


def fallback_find_mp4_in_html(html):
    mp4_links = re.findall(r'https?://[^\s"\']+?\.mp4', html)
    for link in mp4_links:
        # crude filter to avoid ads or irrelevant clips
        if "condensed" in link.lower():
            return link
    return None


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    requests.post(url, data=data)


def main():
    print("🎬 Condensed Game Bot (GitHub Actions version)")
    posted = load_posted_gamepks()
    game_pks = get_recent_giants_games()

    for game_pk in sorted(game_pks):
        if not FORCE_POST and str(game_pk) in posted:
            continue

        print(f"🔍 Checking gamePk: {game_pk}")
        mp4_url = find_mp4_url(game_pk)

        if mp4_url:
            message = f"📺 Giants condensed game: {mp4_url}"
            print("✅ Found condensed game!")
            send_telegram_message(message)
            save_posted_gamepk(game_pk)
            break  # stop after one successful post
        else:
            print("🚫 No condensed game video found.")
            save_posted_gamepk(game_pk)


if __name__ == "__main__":
    main()
