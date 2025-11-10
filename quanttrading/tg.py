import requests
from dotenv import load_dotenv
import os


load_dotenv()

API_KEY = os.getenv("TG_API_KEY")
CHAT_ID = os.getenv("TG_CHAT_ID")

def send_message(message: str):
    base_url = 'https://api.telegram.org/bot'
    
    url = f'{base_url}{API_KEY}/sendMessage?chat_id={CHAT_ID}&text={message}'
    requests.get(url)
