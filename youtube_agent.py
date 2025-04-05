from google import genai
import google.genai.types as genai_types
import requests
import json
import urllib3
import os
import ssl
from telebot import telebot, types

# Configuration and Environment Variables
# TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_BOT_TOKEN = '7416209669:AAE_81vY0fbZTS_zwHU2D5biemnIfEOP-rU'
SUPADATA_API_KEY = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiIsImtpZCI6IjEifQ.eyJpc3MiOiJuYWRsZXMiLCJpYXQiOiIxNzQwODI0NjQzIiwicHVycG9zZSI6ImFwaV9hdXRoZW50aWNhdGlvbiIsInN1YiI6IjI5YjFhNDg4MTIwODRkZDhhMjg4YmQxZjUzNmZkYmM3In0.Q3dd1rk_F5zouxx_A1ww7Ki0nhOdVh90gtwRL4-OODs'
GEMINI_API_KEY = 'AIzaSyAwqQjI5LZWylzdsr4ymnaBMcsjiKAlpAs'

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

proxies = {
    'http': 'http://data:jK42wBE6qr2o@proxy.himart.ir:8880',
    'https': 'http://data:jK42wBE6qr2o@proxy.himart.ir:8880'
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

# headers = {
#   'x-api-key': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiIsImtpZCI6IjEifQ.eyJpc3MiOiJuYWRsZXMiLCJpYXQiOiIxNzQwODI0NjQzIiwicHVycG9zZSI6ImFwaV9hdXRoZW50aWNhdGlvbiIsInN1YiI6IjI5YjFhNDg4MTIwODRkZDhhMjg4YmQxZjUzNmZkYmM3In0.Q3dd1rk_F5zouxx_A1ww7Ki0nhOdVh90gtwRL4-OODs'
# }

# youtube_url = 'https://www.youtube.com/watch?v=Aw7iQjKAX2k'
# rr = requests.get(f'https://api.supadata.ai/v1/youtube/transcript?url={youtube_url}&text=true', headers=headers)
# content = rr.json()['content']

# sys_instruct = '''
#                 این متن رو به فارسی روان برام ترجمه کن
#                 '''
# client = genai.Client(api_key='AIzaSyAwqQjI5LZWylzdsr4ymnaBMcsjiKAlpAs')
# response = client.models.generate_content(
#                             model="gemini-2.0-flash",
#                             config=types.GenerateContentConfig(system_instruction=sys_instruct),
#                             contents=[content]
#                         )
# print(response.text)


client = genai.Client(api_key='AIzaSyAwqQjI5LZWylzdsr4ymnaBMcsjiKAlpAs')


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

    # while text:
    #     if len(text) <= max_length:
    #         messages.append(text)
    #         break

    #     split_index = text.rfind('', 0, max_length)
    #     if split_index == -1:
    #         split_index = max_length

    #     messages.append(text[:split_index])

    #     text = text[split_index].strip()

    # return messages

user_choices = {}
def generate_inline_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton(text="ترجمه ویدئو", callback_data="translate")
    button2 = types.InlineKeyboardButton(text="خلاصه ویدئو", callback_data="summarize")
    keyboard.add(button1, button2)
    return keyboard

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # bot.reply_to(message, 'سلام .لطفا لینک ویدئو یوتیوب موردنظر رو ارسال کنید. من ترجمه متنی ویدئو رو برای شما استخراج میکنم')
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

        if action == 'translate':
            process_text(chat_id, content, 'ترجمه')
        elif action == 'summarize':
            process_text(chat_id, content, 'خلاصه')
        
        # bot.send_message(message.chat.id, "در حال ترجمه متن ...")

        # sys_instruct = '''
        #                 این متن رو به فارسی روان برام ترجمه کن
        #                 '''
        # translation = genai.Client(api_key=GEMINI_API_KEY)
        # response = client.models.generate_content(
        #                             model="gemini-2.0-flash",
        #                             config=types.GenerateContentConfig(system_instruction=sys_instruct),
        #                             contents=[content]
        #                         )
        
        # translated_text = response.text
        # split_messages = split_message(translated_text)
        
        # if not split_messages:
        #     bot.send_message(message.chat.id, "متأسفانه ترجمه‌ای یافت نشد.")
        #     return

        # # total_parts = len(split_messages)
        # for i, part in enumerate(split_messages, 1):
        #     # if total_parts > 1:
        #     #     part_header = f""

        #     bot.send_message(message.chat.id, part)

    
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

    # total_parts = len(split_messages)
    for i, part in enumerate(split_messages, 1):
        # if total_parts > 1:
        #     part_header = f""

        bot.send_message(chat_id, part)

bot.polling()

        

