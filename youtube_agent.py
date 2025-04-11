from google import genai
import google.genai.types as genai_types
import numpy as np
from numpy.linalg import norm
import requests
import json
import urllib3
import os
import ssl
from telebot import telebot, types
from datetime import datetime
from sentence_transformers import SentenceTransformer
from huggingface_hub import login
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

login(token=os.getenv('HUGGINGFACE_TOKEN'))

# Configuration and Environment Variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
SUPADATA_API_KEY = os.getenv('SUPADATA_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')


bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=True, num_threads=4)
chroma_client = chromadb.PersistentClient(path="./chromadb")

labse_embedding_function  = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name='sentence-transformers/LaBSE'
)
labse_model = SentenceTransformer('sentence-transformers/LaBSE')

collection = chroma_client.get_or_create_collection(
    name="youtube_transcripts",
    embedding_function=labse_embedding_function
)


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

proxies = {
    'http': os.getenv('HTTP_PROXY'),
    'https': os.getenv('HTTP_PROXY')
}

os.environ['HTTP_PROXY'] = proxies['http']
os.environ['HTTPS_PROXY'] = proxies['https']

def _create_unverified_https_context():
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context

def configure_requests_with_proxy():
    requests.Session().verify = False   
    requests.Session().proxies.update(proxies)


configure_requests_with_proxy()
_create_unverified_https_context()


client = genai.Client(api_key=GEMINI_API_KEY)

def save_to_knowledge_base(video_url, translated_text):
    embedding = labse_model.encode(translated_text).tolist()
    print(f"Embedding shape: {len(embedding)}")  # Should be 768 for LaBSE
    doc_id = str(hash(translated_text))[:10]

    collection.add(
        documents=[translated_text],
        embeddings=[embedding],
        metadatas=[{"video_url": video_url}],
        ids=[doc_id]
    )
    print(collection.peek()) 
    print(f"Total documents in ChromaDB: {collection.count()}")
    print(collection.get(include=["metadatas"]))


    
def search_knowledge(query, top_k=3):
    try:
        query_embedding = labse_model.encode(query).tolist()
        print(f"Query embedding shape: {len(query_embedding)}")  

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas"]
        )

        if not results["documents"][0]:
            return []

        retrieved_docs = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            retrieved_docs.append({
                "text": doc,
                "video_url": meta.get("video_url") if meta else None,
            })

        return retrieved_docs
    
    except Exception as e:
        print(f"Search error: {e}")
        return []


def split_message(text, max_length=4096):

    if not text:
        return []
    
    paragraphs = text.split('\n\n')
    messages = []
    current_message = ""

    for paragraph in paragraphs:
        if len(current_message) + len(paragraph) + 2 > max_length:
            messages.append(current_message.strip())
            current_message = ""

        if current_message:
            current_message += "\n\n"
        current_message += paragraph

    if current_message:
        messages.append(current_message.strip())

    return messages


user_choices = {}
def generate_inline_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton(text="دستیار هوش مصنوعی", callback_data="translate")
    button2 = types.InlineKeyboardButton(text="خلاصه ویدئو", callback_data="summarize")
    keyboard.add(button1, button2)
    return keyboard

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = 'سلام لطفا یکی از گزینه های زیر را انتخاب کنید'
    bot.send_message(message.chat.id, welcome_text, reply_markup=generate_inline_keyboard())


@bot.callback_query_handler(func=lambda call: call.data in ['translate', 'summarize'])
def handle_callback(call):
    chat_id = call.message.chat.id
    user_choices[chat_id] = call.data
    bot.send_message(chat_id, 'لطفا لینک ویدئو یوتیوب موردنظر رو ارسال کنید')


@bot.message_handler(func=lambda message: 'youtube.com' in message.text or 'youtu.be' in message.text)
def fetch_and_process(message):
    chat_id = message.chat.id
    youtube_url = message.text.strip()

    if chat_id not in user_choices:
        bot.send_message(chat_id, 'لطفا یک گزینه را انتخاب کنید')
        return

    action = user_choices[chat_id]
    bot.send_message(chat_id, "در حال استخراج متن ویدئو ...")

    headers = {'x-api-key': SUPADATA_API_KEY}
    api_url = f'https://api.supadata.ai/v1/youtube/transcript?url={youtube_url}&text=true'

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        content = response.json()['content']

        if not content:
            bot.send_message(message.chat.id, 'متاسفانه در حال حاضر امکان استخراج متن وجود ندارد')
            return

        if action == 'summarize':
            process_text(chat_id, content, 'خلاصه')
        elif action == 'translate':
            sys_instruct = 'این متن را به فارسی روان ترجمه کن.'
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                config=genai_types.GenerateContentConfig(system_instruction=sys_instruct),
                contents=[content]
            )
            translated_text = response.text
            save_to_knowledge_base(youtube_url, translated_text)
            bot.send_message(chat_id, "ویدئو پردازش شد! حالا می‌توانید سوالات خود را بپرسید.")
        
    except requests.exceptions.RequestException as e:
        bot.send_message(message.chat.id, f"Error fetching transcript: {str(e)}")
    except Exception as e:
        bot.send_message(message.chat.id, f"Error translating: {str(e)}")

def process_text(chat_id, content, mode):
    bot.send_message(chat_id, "در حال پردازش متن ...")
    sys_instruct = 'این متن رو به فارسی روان برام ترجمه کن' if mode == 'ترجمه' else 'این متن رو به فارسی برام خلاصه کن'
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=genai_types.GenerateContentConfig(system_instruction=sys_instruct),
        contents=[content]
    )
    
    translated_text = response.text
    split_messages = split_message(translated_text)
    
    if not split_messages:
        bot.send_message(chat_id, "متأسفانه ترجمه‌ای یافت نشد.")
        return

    for i, part in enumerate(split_messages, 1):
        bot.send_message(chat_id, part)

@bot.message_handler(func=lambda msg:True)
def handle_question(message):
    chat_id = message.chat.id
    query = message.text

    bot.send_message(chat_id, "در حال جستجو ...")
    results = search_knowledge(query, top_k=2)

    if not results:
        bot.send_message(chat_id, "اطلاعاتی یافت نشد")
        return
    
    context = "\n\n".join([res["text"] for res in results])
    prompt = f'''
    با استفاده از اطلاعات زیر به سوال پاسخ دهید

    {context}

    سوال: {query}

    پاسخ را حداکثر در 3 جمله به فارسی ارائه دهید
    '''

    bot.send_message(chat_id, "در حال تولید پاسخ...")
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt]
    )
    bot.send_message(chat_id, response.text)


bot.polling(timeout=60)


        

