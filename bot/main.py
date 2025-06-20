import os
import json
import re
import requests
import asyncio
from telegram import Bot
from telegram.constants import ParseMode

FACTORIO_URL = "https://factorio.com/download/sha256sums/"
STATE_FILE = "state.json"

def get_sha256sums():
    resp = requests.get(FACTORIO_URL)
    resp.raise_for_status()
    return resp.text.strip()

def extract_version(sha256sums_text):
    # Ищем первую строку с factorio_win_ и вытаскиваем версию
    for line in sha256sums_text.splitlines():
        match = re.search(r'factorio_win_(\d+\.\d+\.\d+)\.zip', line)
        if match:
            return match.group(1)
    return "неизвестна"

def load_state():
    if not os.path.isfile(STATE_FILE):
        return {"sha256sums": "", "last_message_id": None}
    try:
        with open(STATE_FILE, "r") as f:
            data = f.read().strip()
            if not data:
                return {"sha256sums": "", "last_message_id": None}
            return json.loads(data)
    except (json.JSONDecodeError, OSError):
        return {"sha256sums": "", "last_message_id": None}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def thread_id():
    thread = os.environ.get("TELEGRAM_THREAD_ID")
    return int(thread) if thread else None

async def notify_and_pin(token, chat_id, message, reply_to=None):
    bot = Bot(token=token)
    msg = await bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode=ParseMode.MARKDOWN,
        message_thread_id=thread_id(),
        reply_to_message_id=reply_to
    )
    await bot.pin_chat_message(
        chat_id=chat_id,
        message_id=msg.message_id,
        disable_notification=True
    )
    return msg.message_id

async def unpin_previous(token, chat_id, message_id):
    if not message_id:
        return
    bot = Bot(token=token)
    try:
        await bot.unpin_chat_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Failed to unpin message: {e}")

def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("TELEGRAM_TOKEN and TELEGRAM_CHAT_ID must be set")
        return

    current_sums = get_sha256sums()
    version = extract_version(current_sums)
    state = load_state()

    if state.get("sha256sums") != current_sums:
        print(f"New version detected: {version}")
        asyncio.run(unpin_previous(token, chat_id, state.get("last_message_id")))
        message = (
            f"*Вышла новая версия Факторио* 🚀\n"
            f"Ссылка на обновление: https://factorio.com/download\n"
            f"[⚙️](https://t.me/FCTostin/14199)Версия: *{version}*"
        )
        message_id = asyncio.run(notify_and_pin(token, chat_id, message))
        state["sha256sums"] = current_sums
        state["last_message_id"] = message_id
        save_state(state)
    else:
        print("No updates detected.")

if __name__ == "__main__":
    main()
