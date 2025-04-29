# constants.py

import ConfigHelper


INPUT_FILE = ''
CURRENT_SCRIPT = ''
NGROK_PROCESS = None
AUDIO_DIR = 'audio_files'
SUCCESS_FILE = 'success.txt'
RETRY_FILE = 'retries.txt'
NUMBER_REGEX = r'[^0-9]'
CONFIG_FILE = ConfigHelper.CONFIG_FILE

# Initialize constants with values from config
TWILIO_ACCOUNT_SID = ConfigHelper.get_twilio_account_sid()
TWILIO_AUTH_TOKEN = ConfigHelper.get_twilio_auth_token()
TWILIO_PHONE_NUMBER = ConfigHelper.get_twilio_phone_number()
WEBHOOK_URL = ConfigHelper.get_webhook_url() 