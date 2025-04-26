import logging
import os
import time
from twilio.rest import Client # type: ignore
from twilio.twiml.voice_response import VoiceResponse # type: ignore
from constants import WEBHOOK_URL

class TwilioCallBot:
    def __init__(self, account_sid, auth_token, from_number, tts_service, audio_dir):
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number
        self.tts_service = tts_service
        self.audio_dir = audio_dir

    def make_call(self, to_number, script_text):
        global CURRENT_SCRIPT
            
        try:
            self.tts_service.check_api_key()
            
            # Generate unique filename for this call
            filename = f"call_{int(time.time())}.mp3"
            output_path = os.path.join(self.audio_dir, filename)
            
            # Generate speech file
            speech_file = self.tts_service.generate_speech(script_text, output_path)
            if not speech_file:
                raise Exception("Failed to generate speech file")
            
            if not os.path.exists(speech_file) or os.path.getsize(speech_file) == 0:
                raise Exception("Generated speech file is empty or missing")
            
            # Set global variable to the filename only, not the full path
            CURRENT_SCRIPT = os.path.basename(speech_file)
            
            # Add logging to print the webhook URL
            webhook_url = f"{WEBHOOK_URL}/twiml"
            logging.info(f"Using webhook URL: {webhook_url}")
            logging.info(f"Audio file created: {speech_file}")
            
            # Ensure the URL is properly constructed
            call = self.client.calls.create(
                to=f"+1{to_number}",
                from_=self.from_number,
                url=webhook_url,
                status_callback=f"{WEBHOOK_URL}/status-callback",
                status_callback_event=['initiated', 'ringing', 'answered', 'completed']
            )
            logging.info(f"Call initiated to {to_number}, SID: {call.sid}")
            return call.sid
        except ValueError as ve:
            logging.error(f"TTS validation error for {to_number}: {ve}")
            raise ValueError(str(ve))
        except Exception as e:
            logging.error(f"Error making call to {to_number}: {e}")
            raise
        
    def get_call_status(self, call_sid):
        try:
            call = self.client.calls(call_sid).fetch()
            return call.status
        except Exception as e:
            logging.error(f"Error getting call status for {call_sid}: {e}")
            return None