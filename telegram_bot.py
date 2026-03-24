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
from job_search import fetch_all_jobs, format_job_briefing, start_job_scheduler

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# One shared agent instance (keeps memory loaded in RAM between messages)
agent = JarvisAgent()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hey, I'm Jarvis — your personal AI assistant.\n\n"
        "I remember our conversations and learn about you over time. "
        "Just talk to me naturally.\n\n"
        "Commands:\n"
        "/start — this message\n"
        "/profile — show what I know about you\n"
        "/clear — wipe conversation history"
    )


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = agent.memory.profile_text()
    await update.message.reply_text(f"What I know about you:\n\n{text}")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent.memory._history.clear()
    agent.memory._save_history()
    await update.message.reply_text("Conversation history cleared. I still remember your profile.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        reply = agent.chat(user_text)
        # Telegram has a 4096-char message limit — split if needed
        if len(reply) <= 4096:
            await update.message.reply_text(reply)
        else:
            for chunk in [reply[i:i+4096] for i in range(0, len(reply), 4096)]:
                await update.message.reply_text(chunk)
    except Exception as e:
        logger.error("Error generating response: %s", e, exc_info=True)
        await update.message.reply_text(
            "Something went wrong on my end. Try again in a moment."
        )


async def cmd_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Searching IT jobs in Calgary and Edmonton... give me a moment!")
    jobs = fetch_all_jobs()
    message = format_job_briefing(jobs)
    chunks = [message[i:i+4096] for i in range(0, len(message), 4096)]
    for chunk in chunks:
        await update.message.reply_text(chunk, parse_mode="HTML", disable_web_page_preview=True)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled exception: %s", context.error, exc_info=True)


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise EnvironmentError("TELEGRAM_BOT_TOKEN not set in .env")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Jarvis bot is running. Press Ctrl+C to stop.")
    app.add_handler(CommandHandler("jobs", cmd_jobs))
    start_job_scheduler()
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
