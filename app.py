import logging
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from langchain.document_loaders import PyPDFLoader
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from telegram.helpers import escape_markdown

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

load_dotenv()

text_splitter = RecursiveCharacterTextSplitter(    
    chunk_size=512,
    chunk_overlap=20,
    length_function=len,
    is_separator_regex=False,
)

embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')

def load_and_process_documents(file_path):
    loader = PyPDFLoader(file_path)
    pages = loader.load_and_split(text_splitter=text_splitter)
    for page in pages:
        page.page_content = page.page_content.replace('\n',' ')
    return pages

# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """Send a message when the command /start is issued."""
#     user = update.effective_user
#     await update.message.reply_html(
#         rf"Hi {user.mention_html()}! Please say something!",
#         reply_markup=ForceReply(selective=True),
#     )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command"""
    user_id = update.effective_user.id
    if user_id not in context.bot_data:
        context.bot_data[user_id] = {}
    await update.message.reply_text('✋ Welcome, my fellow student! \n\nI am Leonard Euler, a mathematician of some renown and distinction who has spent many years studying and refining various branches of mathematics. I have developed a range of techniques and methods that can help clarify even the most complex concepts. \n\nSo, please, let us begin by selecting a particular topic and setting forth some questions for me to ponder and solve!')

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for receiving PDF documents"""
    user_id = update.effective_user.id
    
     # Initialize user-specific data if it doesn't exist
    if user_id not in context.bot_data:
        context.bot_data[user_id] = {}
        
    document = update.message.document
    if document.mime_type == 'application/pdf':
        file_id = document.file_id
        new_file = await context.bot.get_file(file_id)
        file_path = f"{file_id}.pdf"
        await new_file.download_to_drive(file_path)
        
        pages = load_and_process_documents(file_path)
        if 'vectordb' not in context.bot_data[user_id]:
            vectordb = Chroma.from_documents(pages, embeddings)
            context.bot_data[user_id]['vectordb'] = vectordb
        else:
            vectordb = context.bot_data[user_id]['vectordb']
            vectordb.add_documents(pages)
        
        await update.message.reply_text('Your digital manuscript has been faithfully received and thoroughly analyzed. By all means, proffer thy queries concerning its matter.')
    else:
        await update.message.reply_text(f"Alas, the format of this file {document.mime_type} appears incompatible; henceforth, it shall be disregarded.")

async def question_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    """Handler for answering questions based on the processed documents"""
    user_id = update.effective_user.id
    question = update.message.text
    vectordb = context.bot_data.get(user_id, {}).get('vectordb')
    if vectordb:
        prompt = get_prompt(question, vectordb)
        
        messages.append({'role': 'user', 'content': prompt}) 
        response = await client.chat.completions.create(
            model="llama-3.2-1b-instruct",
            messages=messages,
            temperature=0.7,
            max_tokens=-1,
        )

        messages.append({'role': 'assistant', 'content': response.choices[0].message.content})
        llm_reply = response.choices[0].message.content

        await context.bot.send_message(chat_id=update.effective_chat.id, text=escape_markdown(llm_reply))
    else:
        await update.message.reply_text('Alack! No documents have heretofore been treated. Be kind enough to forward first those of the PDF variety.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Who else if not Leonard Euler could help you to prepare for a hard exam?\n Just attach a PDF of your lectures and feel free to ask anything to understand the topic better! 🤓")

async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /update is issued."""
    await update.message.reply_text("Upload your file!")

def get_prompt(question, vectordb):
    
    documents = vectordb.similarity_search(question, k=10)
    context = '\n'.join(doc.page_content for doc in documents)
    
    prompt = f"""Using only the context below, answer the following question in a style of Leonard Euler, a brilliant mathematician living in 21st century:
    context : {context}
    question: {question}"""
    
    return prompt

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

    application.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, question_handler))
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()