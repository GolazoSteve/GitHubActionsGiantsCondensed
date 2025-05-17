import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FORCE_POST = os.getenv("FORCE_POST", "false").lower() == "true"

def get_today_date():
    return datetime.utcnow().strftime("%Y-%m-%d")

def get_highlight_video():
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={get_today_date()}"
    response = requests.get(url)
    data = response.json()

    for date in data.get("dates", []):
        for game in date.get("games", []):
            if "Giants" in game.get("teams", {}).get("home", {}).get("team", {}).get("name", "") \
            or "Giants" in game.get("teams", {}).get("away", {}).get("team", {}).get("name", ""):
                game_pk = game.get("gamePk")
                vid_url = f"https://www.mlb.com/gameday/{game_pk}/video"

                page = requests.get(vid_url).text
                if "Condensed Game" in page:
                    # Extract the MP4 URL
                    start_index = page.find('https://cut4.video.mlb.com')
                    end_index = page.find('.mp4', start_index) + 4
                    video_url = page[start_index:end_index]
                    if video_url.endswith(".mp4"):
                        return game_pk, video_url
    return None, None

def game_already_logged(game_pk):
    if not os.path.exists("posted_games.txt"):
        return False
    with open("posted_games.txt", "r") as file:
        return str(game_pk) in file.read()

def log_game_pk(game_pk):
    with open("posted_games.txt", "a") as file:
        file.write(f"{game_pk}\n")

def send_to_telegram(video_url):
    message = f"🎬 *San Francisco Giants Condensed Game Highlights*\n\n{video_url}"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data=payload)

def main():
    game_pk, video_url = get_highlight_video()

    if not game_pk or not video_url:
        print("🚫 No condensed game video found.")
        return

    if not FORCE_POST and game_already_logged(game_pk):
        print("🛑 Already posted for this gamePk.")
        return

    send_to_telegram(video_url)
    log_game_pk(game_pk)
    print(f"✅ Sent to Telegram.")
    print(f"💾 Saved gamePk: {game_pk}")
    print("🎬 Condensed Game Bot (GitHub Actions version)")

if __name__ == "__main__":
    main()
