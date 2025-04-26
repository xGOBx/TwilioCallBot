# constants.py
import json


TWILIO_ACCOUNT_SID = ''
TWILIO_AUTH_TOKEN = ''
TWILIO_PHONE_NUMBER = ''
CONFIG_FILE = 'config.json'
INPUT_FILE = ''
CURRENT_SCRIPT = ''
NGROK_PROCESS = None
AUDIO_DIR = 'audio_files'
SUCCESS_FILE = 'success.txt'
RETRY_FILE = 'retries.txt'
NUMBER_REGEX = r'[^0-9]'

def get_webhook_url():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get('webhook_url', '')
    except:
        return ""

WEBHOOK_URL = get_webhook_url()  # Initialize with value from config