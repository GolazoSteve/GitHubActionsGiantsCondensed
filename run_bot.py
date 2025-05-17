def main():
    print("🎬 Condensed Game Bot (GitHub Actions version)")
    gamepks = get_recent_gamepks()
    print(f"🧾 Found {len(gamepks)} recent completed Giants games")

    for gamepk in reversed(gamepks):  # start from latest
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
            break  # ✅ only post the first (most recent) valid game
        else:
            print(f"❌ No condensed game found for {gamepk}")
