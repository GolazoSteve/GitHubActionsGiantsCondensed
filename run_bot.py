import os
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POSTED_GAMES_FILE = "posted_games.txt"

def load_posted_games():
    if not os.path.exists(POSTED_GAMES_FILE):
        return set()
    with open(POSTED_GAMES_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_posted_game(game_id):
    with open(POSTED_GAMES_FILE, "a") as f:
        f.write(f"{game_id}\n")

def get_condensed_game_url(game_id):
    # Construct the URL for the condensed game video
    return f"https://www.mlb.com/gameday/{game_id}/condensed"

def check_condensed_game_available(game_id):
    url = get_condensed_game_url(game_id)
    response = requests.head(url)
    return response.status_code == 200

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    response = requests.post(url, data=data)
    return response.ok

def main():
    posted_games = load_posted_games()
    # Example list of game IDs to check
    game_ids = ["777891", "777916"]  # Replace with actual game IDs

    for game_id in game_ids:
        if game_id in posted_games:
            continue

        print(f"Checking game ID: {game_id}")
        if check_condensed_game_available(game_id):
            message = f"Condensed game available: {get_condensed_game_url(game_id)}"
            if send_telegram_message(message):
                print(f"Posted condensed game for game ID: {game_id}")
                save_posted_game(game_id)
            else:
                print(f"Failed to send message for game ID: {game_id}")
        else:
            print(f"Condensed game not available for game ID: {game_id}. Retrying in 30 minutes.")
            time.sleep(1800)  # Wait for 30 minutes before retrying
            if check_condensed_game_available(game_id):
                message = f"Condensed game available: {get_condensed_game_url(game_id)}"
                if send_telegram_message(message):
                    print(f"Posted condensed game for game ID: {game_id}")
                    save_posted_game(game_id)
                else:
                    print(f"Failed to send message for game ID: {game_id}")
            else:
                print(f"Condensed game still not available for game ID: {game_id}")

if __name__ == "__main__":
    main()
