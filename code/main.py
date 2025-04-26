import tkinter as tk
from tkinter import filedialog, messagebox
import re
import os
import json
import logging
import time
import threading
from queue import Queue
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from flask import Flask, request, Response
import urllib.parse
import subprocess
import requests

# Initialize logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Global variables for Twilio configuration
TWILIO_ACCOUNT_SID = ''
TWILIO_AUTH_TOKEN = ''
TWILIO_PHONE_NUMBER = ''  # Your Twilio phone number
WEBHOOK_URL = ''          # Your webhook URL
INPUT_FILE = ''
CONFIG_FILE = 'config.json'
CURRENT_SCRIPT = ''  # Global variable to store the current script
NGROK_PROCESS = None  # Global variable to store ngrok process

# Flask app for webhook handling
app = Flask(__name__)

# Success and retry files
SUCCESS_FILE = 'success.txt'
RETRY_FILE = 'retries.txt'
NUMBER_REGEX = r'[^0-9]'

class TwilioCallBot:
    def __init__(self, account_sid, auth_token, from_number):
        """
        Initialize Twilio client for making calls
        """
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number

    def make_call(self, to_number, script_text):
        """
        Initiate a call using Twilio with a custom script.
        """
        global CURRENT_SCRIPT
        CURRENT_SCRIPT = script_text  # Store the current script globally

        try:
            call = self.client.calls.create(
                to=f"+1{to_number}",
                from_=self.from_number,
                url=f"{WEBHOOK_URL}/twiml",
                status_callback=f"{WEBHOOK_URL}/status-callback",
                status_callback_event=['initiated', 'ringing', 'answered', 'completed']
            )
            logging.info(f"Call initiated to {to_number}, SID: {call.sid}")
            return call.sid
        except Exception as e:
            logging.error(f"Error making call to {to_number}: {e}")
            return None

    def get_call_status(self, call_sid):
        """
        Get the status of a specific call
        """
        try:
            call = self.client.calls(call_sid).fetch()
            return call.status
        except Exception as e:
            logging.error(f"Error getting call status for {call_sid}: {e}")
            return None

@app.route("/twiml", methods=['GET', 'POST'])
def generate_twiml():
    """
    Generate TwiML for the call with the current script
    """
    global CURRENT_SCRIPT
    response = VoiceResponse()
    response.say(CURRENT_SCRIPT)
    logging.info(f"Generating TwiML with script: {CURRENT_SCRIPT}")
    return Response(str(response), content_type='application/xml')

@app.route("/status-callback", methods=['POST'])
def status_callback():
    """
    Handle status callback updates from Twilio
    """
    # Extract call parameters
    call_sid = request.values.get('CallSid', '')
    call_status = request.values.get('CallStatus', '')
    from_number = request.values.get('From', '')
    to_number = request.values.get('To', '')
    
    logging.info(f"Call Status Callback - SID: {call_sid}, Status: {call_status}, From: {from_number}, To: {to_number}")

    return '', 200  # Return an empty response

@app.route("/", methods=['POST', 'GET'])
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

class TwilioCallBotGUI:
    def __init__(self, master):
        """
        Initialize the GUI for the Twilio Call Bot with ngrok integration.
        """
        global gui  # Make gui a global variable
        gui = self  # Set the global gui to this instance

        self.master = master
        self.master.title("Twilio Call Bot")
        self.master.geometry("600x500")
        self.bot = None
        self.threads = []

        # Initialize ngrok and get webhook URL
        self.setup_ngrok()

        # Initialize GUI components
        self.setup_gui()

        # Load configuration
        self.load_config()
    
    def edit_config_file(self):
        """
        Open the config.json file in the default text editor or show config window
        """
        try:
            # Use platform-specific file opening method
            if os.name == 'nt':  # Windows
                os.startfile(CONFIG_FILE)
            elif os.name == 'posix':  # macOS and Linux
                import subprocess
                subprocess.call(('xdg-open', CONFIG_FILE))
            else:
                messagebox.showerror("Error", "Unsupported operating system")
            
            # Always show the config window for editing
            self.show_config_window()
        except Exception as e:
            messagebox.showerror("Error", f"Could not open config file: {e}")    
        
    def setup_gui(self):
        """
        Set up the GUI components
        """
        self.status_label = tk.Label(self.master, text="Status: Ready", bg="#f0f0f0")
        self.status_label.pack(pady=10)

        self.frame = tk.Frame(self.master, bg="#f0f0f0")
        self.frame.pack(padx=20, pady=20)

        # Number of concurrent calls
        tk.Label(self.frame, text="Number of Concurrent Calls:", bg="#f0f0f0").grid(row=0, column=0, padx=10, pady=5)
        self.threads_entry = tk.Entry(self.frame)
        self.threads_entry.grid(row=0, column=1, padx=10, pady=5)
        self.threads_entry.insert(0, '5')

        # File selection button
        tk.Button(self.frame, text="Select Phone Numbers File", command=self.select_file).grid(row=1, column=0, columnspan=2, pady=10)

        # Call script
        tk.Label(self.frame, text="Call Script:", bg="#f0f0f0").grid(row=2, column=0, padx=10, pady=5)
        self.script_entry = tk.Text(self.frame, height=5, width=40)
        self.script_entry.grid(row=2, column=1)
        self.script_entry.insert('1.0', "Hello, please press 1 for Yes or 2 for No.")

        tk.Button(self.master, text="Start Calling", command=self.start_bot, bg="#4CAF50").pack(pady=20)
        tk.Button(self.master, text="Edit Config", command=self.show_config_window, bg="#FFA500").pack(pady=10)

    def setup_ngrok(self):
        """
        Start ngrok and retrieve the webhook URL
        """
        global WEBHOOK_URL, NGROK_PROCESS
        try:
            # Start ngrok process
            NGROK_PROCESS = subprocess.Popen(
                ['ngrok', 'http', '8000'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )

            # Wait a moment for ngrok to start
            time.sleep(2)

            # Fetch ngrok URL
            try:
                ngrok_response = requests.get('http://localhost:4040/api/tunnels')
                ngrok_data = ngrok_response.json()
                WEBHOOK_URL = ngrok_data['tunnels'][0]['public_url']
                logging.info(f"Ngrok webhook URL: {WEBHOOK_URL}")
                
                # Automatically update config with new webhook URL
                self.update_config_with_webhook(WEBHOOK_URL)
            except Exception as e:
                logging.error(f"Error fetching ngrok URL: {e}")
                messagebox.showerror("Ngrok Error", "Could not retrieve ngrok URL. Please check ngrok installation.")

        except FileNotFoundError:
            messagebox.showerror("Ngrok Error", "Ngrok not found. Please install ngrok and ensure it's in your system PATH.")
        except Exception as e:
            logging.error(f"Ngrok setup error: {e}")
            messagebox.showerror("Ngrok Error", f"Error setting up ngrok: {e}")

    def update_config_with_webhook(self, webhook_url):
        """
        Update the config file with the new webhook URL
        """
        try:
            # Load existing config
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            
            # Update webhook URL
            config['webhook_url'] = webhook_url
            
            # Save updated config
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            
            # Update global variable
            global WEBHOOK_URL
            WEBHOOK_URL = webhook_url
            
            logging.info(f"Updated config with webhook URL: {webhook_url}")
        except Exception as e:
            logging.error(f"Error updating config with webhook URL: {e}")
            messagebox.showerror("Config Error", f"Could not update config file: {e}")

    def load_config(self):
        """
        Load Twilio configuration from config file
        """
        global TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, WEBHOOK_URL
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            TWILIO_ACCOUNT_SID = config.get('account_sid', '')
            TWILIO_AUTH_TOKEN = config.get('auth_token', '')
            TWILIO_PHONE_NUMBER = config.get('phone_number', '')
            WEBHOOK_URL = config.get('webhook_url', WEBHOOK_URL)
        else:
            self.show_config_window()

    def show_config_window(self):
        """
        Show a window for inputting/updating Twilio configuration
        """
        config_window = tk.Toplevel(self.master)
        config_window.title("Twilio Configuration")
        config_window.geometry("400x400")

        # Create variables to store current configuration
        current_config = {
            "account_sid": TWILIO_ACCOUNT_SID,
            "auth_token": TWILIO_AUTH_TOKEN,
            "phone_number": TWILIO_PHONE_NUMBER,
            "webhook_url": WEBHOOK_URL
        }

        tk.Label(config_window, text="Account SID:").pack(pady=5)
        account_sid_var = tk.Entry(config_window)
        account_sid_var.insert(0, current_config["account_sid"])
        account_sid_var.pack(pady=5)

        tk.Label(config_window, text="Auth Token:").pack(pady=5)
        auth_token_var = tk.Entry(config_window, show="*")
        auth_token_var.insert(0, current_config["auth_token"])
        auth_token_var.pack(pady=5)

        tk.Label(config_window, text="Twilio Phone Number:").pack(pady=5)
        phone_number_var = tk.Entry(config_window)
        phone_number_var.insert(0, current_config["phone_number"])
        phone_number_var.pack(pady=5)

        tk.Label(config_window, text="Webhook URL:").pack(pady=5)
        webhook_url_var = tk.Entry(config_window)
        webhook_url_var.insert(0, current_config["webhook_url"])
        webhook_url_var.pack(pady=5)

        def save_config():
            # Only update fields that have been changed
            config = {}
            for key, entry_var, current_value in [
                ('account_sid', account_sid_var, current_config['account_sid']),
                ('auth_token', auth_token_var, current_config['auth_token']),
                ('phone_number', phone_number_var, current_config['phone_number']),
                ('webhook_url', webhook_url_var, current_config['webhook_url'])
            ]:
                new_value = entry_var.get().strip()
                config[key] = new_value if new_value else current_value

            # Save the updated configuration
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
            
            # Update global variables
            global TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, WEBHOOK_URL
            TWILIO_ACCOUNT_SID = config['account_sid']
            TWILIO_AUTH_TOKEN = config['auth_token']
            TWILIO_PHONE_NUMBER = config['phone_number']
            WEBHOOK_URL = config['webhook_url']
            
            config_window.destroy()

        tk.Button(config_window, text="Save", command=save_config).pack(pady=20)

    def select_file(self):
        """
        Select input file with phone numbers
        """
        global INPUT_FILE
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            INPUT_FILE = file_path
            self.update_status(f"Selected file: {INPUT_FILE}")

    def update_status(self, message):
        """
        Update status label
        """
        self.status_label.config(text=f"Status: {message}")

    def start_bot(self):
        """
        Start the bot to make calls with the user-provided script.
        """
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, WEBHOOK_URL]):
            messagebox.showerror("Error", "Please configure Twilio credentials and webhook URL first.")
            return
        if not INPUT_FILE:
            messagebox.showerror("Error", "Please select a phone numbers file.")
            return

        # Extract script text from the text box
        script_text = self.script_entry.get("1.0", "end").strip()
        if not script_text:
            messagebox.showerror("Error", "Please provide a script for the call.")
            return

        with open(INPUT_FILE, 'r') as f:
            numbers = [re.sub(NUMBER_REGEX, '', line.strip()) for line in f if line.strip()]

        bot = TwilioCallBot(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER)
        thread_count = int(self.threads_entry.get())
        self.update_status("Starting calls...")

        queue = Queue()
        for number in numbers:
            queue.put(number)

        def process_numbers():
            while True:
                number = queue.get()
                if number is None:
                    break
                try:
                    call_sid = bot.make_call(number, script_text)
                    if call_sid:
                        while True:
                            status = bot.get_call_status(call_sid)
                            if status in ['completed', 'failed', 'busy', 'no-answer', 'canceled']:
                                break
                            time.sleep(1)
                        logging.info(f"Call to {number} completed with status: {status}")
                    else:
                        logging.error(f"Failed to initiate call to {number}")
                finally:
                    queue.task_done()

        # Create threads
        for _ in range(thread_count):
            thread = threading.Thread(target=process_numbers)
            thread.start()
            self.threads.append(thread)

        # Wait for all threads to finish
        queue.join()

        # Stop all threads
        for _ in self.threads:
            queue.put(None)

        self.update_status("All calls completed.")

    def __del__(self):
        """
        Cleanup method to terminate ngrok process if it's running
        """
        global NGROK_PROCESS
        if NGROK_PROCESS:
            try:
                NGROK_PROCESS.terminate()
                NGROK_PROCESS.wait()
            except Exception as e:
                logging.error(f"Error terminating ngrok process: {e}")

if __name__ == "__main__":
    # Ensure the config file exists with a basic structure
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({
                "account_sid": "",
                "auth_token": "",
                "phone_number": "",
                "webhook_url": ""
            }, f, indent=4)

    # Create Tkinter root window
    root = tk.Tk()
    
    # Start Flask app in a separate thread
    app_thread = threading.Thread(
        target=lambda: app.run(port=8000, debug=False, use_reloader=False), 
        daemon=True
    )
    app_thread.start()
    
    # Create GUI
    gui = TwilioCallBotGUI(root)
    
    # Start Tkinter main loop
    root.mainloop()