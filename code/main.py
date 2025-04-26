import os
import tkinter as tk
from tkinter import messagebox
import threading
from flask import Flask, send_file, request, Response
from TwilioCallBotGUI import TwilioCallBotGUI
from constants import CONFIG_FILE, AUDIO_DIR, CURRENT_SCRIPT, WEBHOOK_URL
import json
import logging
from twilio.twiml.voice_response import VoiceResponse 

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = Flask(__name__)  # Flask instance

@app.route("/audio/<filename>")
def serve_audio(filename):
    try:
        audio_path = os.path.join(AUDIO_DIR, filename)
        return send_file(audio_path, mimetype='audio/mpeg')
    except Exception as e:
        logging.error(f"Error serving audio file {filename}: {e}")
        return "File not found", 404
    
    
@app.route("/twiml", methods=['GET', 'POST'])
def generate_twiml():
    try:
        response = VoiceResponse()
        
        # Instead of relying on CURRENT_SCRIPT, get the audio file from the request
        call_sid = request.values.get('CallSid', '')
        logging.info(f"Handling TwiML request for call SID: {call_sid}")
        
        # Look for the most recent audio file in the directory
        audio_files = [f for f in os.listdir(AUDIO_DIR) if f.endswith('.mp3')]
        if not audio_files:
            raise ValueError("No audio files found in directory")
        
        # Sort by creation time, newest first
        audio_files.sort(key=lambda x: os.path.getctime(os.path.join(AUDIO_DIR, x)), reverse=True)
        
        # Use the most recent file
        filename = audio_files[0]
        audio_url = f"{WEBHOOK_URL}/audio/{filename}"
        
        logging.info(f"TwiML generating with audio URL: {audio_url}")
        
        # Check if the file exists
        audio_path = os.path.join(AUDIO_DIR, filename)
        if not os.path.exists(audio_path):
            logging.error(f"Audio file not found at: {audio_path}")
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        response.play(audio_url)
        
        return Response(str(response), content_type='application/xml')
    except Exception as e:
        logging.error(f"Error generating TwiML: {str(e)}")
        # Return a basic response even if there's an error
        error_response = VoiceResponse()
        error_response.say("Sorry, there was an error processing your call.")
        return Response(str(error_response), content_type='application/xml')
@app.route("/status-callback", methods=['POST'])
def status_callback():
    call_sid = request.values.get('CallSid', '')
    call_status = request.values.get('CallStatus', '')
    from_number = request.values.get('From', '')
    to_number = request.values.get('To', '')
    logging.info(f"Call Status Callback - SID: {call_sid}, Status: {call_status}, From: {from_number}, To: {to_number}")
    return '', 200

@app.route("/home", methods=['POST', 'GET'])
def landing():
    """
    Landing page for the Flask app
    """
    return """
    <html>
        <head><title>Twilio Call Bot</title></head>
        <body>
            <h1>Welcome to the Twilio Call Bot</h1>
            <p>This app allows you to initiate automated calls using Twilio.</p>
            <p>Configure your settings and start making calls through the bot interface.</p>
        </body>
    </html>
    """


def check_config_file():
    try:
        if not os.path.exists(CONFIG_FILE):
            return False
            logging.warning(f"Configuration file '{CONFIG_FILE}' does not exist.")
        
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        required_fields = ['account_sid', 'auth_token', 'phone_number']
        for field in required_fields:
            if not config.get(field):
                logging.warning(f"Configuration file is missing required field: {field}")
                return False
        
        logging.info("Configuration file contains valid Twilio credentials.")
        return True

    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON in '{CONFIG_FILE}': {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error while validating config file: {e}")
        return False

def run_flask():
    """Function to run the Flask app"""
    app.run(port=8000, debug=True, use_reloader=False)

if __name__ == "__main__":
    try:
        logging.info("Initializing the application...")

        # Create Tkinter root window
        root = tk.Tk()

        # Create GUI
        gui = TwilioCallBotGUI(root)

        # Ensure config file exists
        gui.ensure_config_file()

        # Create audio directory if it doesn't exist
        gui.create_audio_dir()

        # Ensure ngrok and webhook are initialized
        gui.setup_ngrok()

        # Reload configuration to reflect the updated webhook URL
        gui.load_config()

        # Check configuration file directly
        if not check_config_file():
            logging.warning("Twilio credentials are missing or incomplete. Opening configuration window.")
            gui.show_config_window()

            # Wait for the Twilio credentials to be updated
            try:
                root.wait_variable("<<TwilioCredentialsUpdated>>")
                logging.info("Twilio credentials updated successfully.")
            except Exception as e:
                logging.error(f"Error waiting for Twilio credentials update: {e}")
                messagebox.showerror("Error", f"Failed to update Twilio credentials: {e}")
                root.destroy()
                exit(1)

            root.mainloop()
        else:
            logging.info("Twilio credentials are set. Starting Flask application.")

            # Start Flask app in a separate thread to avoid blocking Tkinter
            flask_thread = threading.Thread(target=run_flask, daemon=True)
            flask_thread.start()
            logging.info("Flask application started in a separate thread.")

            root.mainloop()

    except Exception as e:
        logging.critical(f"Unexpected error occurred: {e}")
        messagebox.showerror("Critical Error", f"An unexpected error occurred: {e}")
        if 'root' in locals():
            root.destroy()
        exit(1)
