import requests
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FORCE_POST = os.getenv("FORCE_POST", "").lower() == "true"
POSTED_LOG = "posted_games.txt"

def get_most_recent_completed_game_pk():
    url = 'https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId=137&startDate=2024-03-01&endDate=2025-11-30&hydrate=game(content(summary))'
    response = requests.get(url)
    data = response.json()
    dates = data.get("dates", [])

    for day in reversed(dates):
        for game in reversed(day.get("games", [])):
            if game.get("status", {}).get("detailedState") == "Final":
                return game.get("gamePk")
    return None

def get_condensed_game_url(game_pk):
    url = f"https://www.mlb.com/gameday/{game_pk}/video"
    response = requests.get(url)
    if "condensed-game" not in response.text:
        return None

    import re
    matches = re.findall(r'"(https:[^"]+?condensed-game[^"]+?\.mp4)"', response.text)
    return matches[0] if matches else None

def already_posted(game_pk):
    if not os.path.exists(POSTED_LOG):
        return False
    with open(POSTED_LOG, "r") as f:
        return str(game_pk) in f.read()

def mark_as_posted(game_pk):
    with open(POSTED_LOG, "a") as f:
        f.write(f"{game_pk}\n")

def send_to_telegram(text):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data={"chat_id": TELEGRAM_CHAT_ID, "text": text}
    )

def main():
    print("🎬 Condensed Game Bot (GitHub Actions version)")
    game_pk = get_most_recent_completed_game_pk()
    if not game_pk:
        print("❌ Could not find a recent completed Giants game.")
        return

    if already_posted(game_pk) and not FORCE_POST:
        print("🛑 Already posted this game. Skipping.")
        return

    video_url = get_condensed_game_url(game_pk)
    if video_url:
        send_to_telegram(f"🎥 Giants Condensed Game:\n{video_url}")
        print("✅ Sent to Telegram.")
    else:
        print("🚫 No condensed game video found.")

    mark_as_posted(game_pk)
    print(f"💾 Saved gamePk: {game_pk}")

if __name__ == "__main__":
    main()
