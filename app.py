import logging

from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

load_dotenv()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! Please say something!",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")

async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /update is issued."""
    await update.message.reply_text("Upload your file!")


lm_studio_url = "http://host.docker.internal:1234/v1" # when running in docker
local_url = "http://localhost:1234/v1" # when running locally

client = AsyncOpenAI(base_url=local_url, api_key="not-needed")

# messages = [{'role': 'system', 'content': 'Always answer like Eminem. Keep it short.'}]
messages = [{'role': 'system', 'content': 'Always answer like Leonard Euler. Brilliant mathematician living in 21st century.'}]

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("Question from user: %s", update.message.text)

    if update.message.text != '':
        user_input = update.message.text

        messages.append({'role': 'user', 'content': user_input})        

        response = await client.chat.completions.create(
            model="llama-3.2-1b-instruct",
            messages=messages,
            temperature=0.7,
            max_tokens=-1,
        )

        messages.append({'role': 'assistant', 'content': response.choices[0].message.content})

        llm_reply = response.choices[0].message.content
    else:
        return
    
    await update.message.reply_text(llm_reply)

def main() -> None:            

    application = Application.builder().token(os.getenv("bot_token")).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("upload", upload_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()