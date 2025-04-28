import json
from constants import CONFIG_FILE


def get_webhook_url():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get('webhook_url', '')
    except:
        return ""



def get_twilio_account_sid():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get('account_sid', '')
    except:
        return ""

def get_twilio_auth_token():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get('auth_token', '')
    except:
        return ""

def get_twilio_phone_number():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get('phone_number', '')
    except:
        return ""
