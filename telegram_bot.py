import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from jarvis import JarvisAgent
from job_search import fetch_all_jobs, format_job_briefing, start_job_scheduler, send_telegram_message
from tools import set_telegram_sender, get_weather, list_todos, get_briefing

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

agent = JarvisAgent()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hey, I'm Jarvis — your personal AI assistant.\n\n"
        "Just talk to me naturally and I'll get things done.\n\n"
        "Commands:\n"
        "/start — this message\n"
        "/profile — show what I know about you\n"
        "/notes — list your saved notes\n"
        "/todos — list pending tasks\n"
        "/weather [city] — current weather (default: Calgary)\n"
        "/search <query> — web search\n"
        "/briefing — morning briefing (weather + tasks + jobs)\n"
        "/jobs — search IT jobs\n"
        "/clear — wipe conversation history"
    )


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = agent.memory.profile_text()
    await update.message.reply_text(f"What I know about you:\n\n{text}")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent.memory._history.clear()
    agent.memory._save_history()
    await update.message.reply_text("Conversation history cleared. I still remember your profile.")


async def cmd_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from tools import get_notes
    text = get_notes()
    await update.message.reply_text(text)


async def cmd_todos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = list_todos(show_done=False)
    await update.message.reply_text(text)


async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location = " ".join(context.args) if context.args else "Calgary"
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )
    text = get_weather(location)
    await update.message.reply_text(text)


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search <query>")
        return
    query = " ".join(context.args)
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )
    reply = agent.chat(f"Search the web for: {query}")
    await _send_long(update, reply)


async def cmd_briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )
    text = get_briefing()
    await _send_long(update, text)


async def cmd_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Searching IT jobs in Calgary and Edmonton...")
    jobs = fetch_all_jobs()
    message = format_job_briefing(jobs)
    chunks = [message[i:i + 4096] for i in range(0, len(message), 4096)]
    for chunk in chunks:
        await update.message.reply_text(
            chunk, parse_mode="HTML", disable_web_page_preview=True
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )
    try:
        reply = agent.chat(user_text)
        await _send_long(update, reply)
    except Exception as e:
        logger.error("Error generating response: %s", e, exc_info=True)
        await update.message.reply_text("Something went wrong on my end. Try again in a moment.")


async def _send_long(update: Update, text: str):
    if len(text) <= 4096:
        await update.message.reply_text(text)
    else:
        for chunk in [text[i:i + 4096] for i in range(0, len(text), 4096)]:
            await update.message.reply_text(chunk)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled exception: %s", context.error, exc_info=True)


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise EnvironmentError("TELEGRAM_BOT_TOKEN not set in .env")

    # Wire up the Telegram sender so reminders can fire notifications
    set_telegram_sender(send_telegram_message)

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("notes", cmd_notes))
    app.add_handler(CommandHandler("todos", cmd_todos))
    app.add_handler(CommandHandler("weather", cmd_weather))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("briefing", cmd_briefing))
    app.add_handler(CommandHandler("jobs", cmd_jobs))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    start_job_scheduler()
    logger.info("Jarvis is online.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
