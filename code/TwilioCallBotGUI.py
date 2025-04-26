from queue import Empty, Queue
import subprocess
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import json
import logging
import re
import requests
from TwilioCallBot import TwilioCallBot
from ElevenLabsTTS import ElevenLabsTTS
from constants import *
from ConfigPopup import ConfigPopup

class TwilioCallBotGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Twilio Call Bot with ElevenLabs TTS")
        self.master.geometry("600x600")
        self.audio_dir = AUDIO_DIR  # Define the audio directory attribute
        self.tts_service = ElevenLabsTTS(AUDIO_DIR)
        self.bot = None
        self.threads = []
        
        self.ensure_config_file()
        self.create_audio_dir()
        self.setup_ngrok()
        self.setup_gui()
        self.load_config()
    # Rest of the class methods
    def ensure_config_file(self):
        """
        Ensures the configuration file exists and contains valid data.
        If the file does not exist, prompts the user to create one.
        """
        try:
            if not os.path.exists(CONFIG_FILE):
                logging.info(f"Configuration file '{CONFIG_FILE}' not found. Creating a new one.")

                # Create a temporary Tkinter root window for the popup
                root = tk.Tk()
                root.withdraw()  # Hide the main window

                # Open the configuration popup
                config_popup = ConfigPopup(root, title="Create Configuration")
                config = config_popup.get_config()
                root.destroy()  # Close the popup window

                # Validate the configuration
                if not all(key in config and config[key] for key in ['account_sid', 'auth_token', 'phone_number']):
                    logging.error("Incomplete configuration. All fields are required.")
                    messagebox.showerror("Error", "Configuration is incomplete. Please try again.")
                    self.ensure_config_file()  # Restart the process
                    return

                # Write the configuration to the file
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(config, f, indent=4)
                logging.info(f"Configuration file '{CONFIG_FILE}' created successfully.")
            else:
                logging.info(f"Configuration file '{CONFIG_FILE}' already exists.")
        except Exception as e:
            logging.error(f"Error ensuring configuration file: {e}")
            messagebox.showerror("Error", f"Failed to ensure configuration file: {e}")

    def create_audio_dir(self):
        if not os.path.exists(AUDIO_DIR):
            os.makedirs(AUDIO_DIR)
            
    def setup_ngrok(self):
        global WEBHOOK_URL, NGROK_PROCESS
        try:
            NGROK_PROCESS = subprocess.Popen(
                ['ngrok', 'http', '8000'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            time.sleep(2)

            try:
                ngrok_response = requests.get('http://localhost:4040/api/tunnels')
                ngrok_data = ngrok_response.json()
                WEBHOOK_URL = ngrok_data['tunnels'][0]['public_url']
                logging.info(f"Ngrok webhook URL: {WEBHOOK_URL}")

                # Update the configuration file immediately after obtaining the webhook URL
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE, 'r+') as f:
                        config = json.load(f)
                        config['webhook_url'] = WEBHOOK_URL
                        f.seek(0)
                        json.dump(config, f, indent=4)
                        f.truncate()  # Ensure old content is removed
                    logging.info("Webhook URL updated in configuration file.")
                else:
                    logging.warning(f"Config file {CONFIG_FILE} not found to update Webhook URL.")

            except Exception as e:
                logging.error(f"Error fetching ngrok URL: {e}")
                messagebox.showerror("Ngrok Error", "Could not retrieve ngrok URL")
        except FileNotFoundError:
            messagebox.showerror("Ngrok Error", "Ngrok not found. Please install ngrok.")
        except Exception as e:
            logging.error(f"Ngrok setup error: {e}")
            messagebox.showerror("Ngrok Error", f"Error setting up ngrok: {e}")


    def setup_gui(self):
        self.status_label = tk.Label(self.master, text="Status: Ready (TTS Not Configured)", bg="#f0f0f0")
        self.status_label.pack(pady=10)

        self.frame = tk.Frame(self.master, bg="#f0f0f0")
        self.frame.pack(padx=20, pady=20)

        tk.Label(self.frame, text="Number of Concurrent Calls:", bg="#f0f0f0").grid(row=0, column=0, padx=10, pady=5)
        self.threads_entry = tk.Entry(self.frame)
        self.threads_entry.grid(row=0, column=1, padx=10, pady=5)
        self.threads_entry.insert(0, '1')

        tk.Button(self.frame, text="Select Phone Numbers File", command=self.select_file).grid(row=1, column=0, columnspan=2, pady=10)

        tk.Button(self.frame, text="Preview Voice", command=self.preview_voice, bg="#87CEFA").grid(row=2, column=0, columnspan=2, pady=10)

        tk.Label(self.frame, text="Call Script:", bg="#f0f0f0").grid(row=3, column=0, padx=10, pady=5)
        self.script_entry = tk.Text(self.frame, height=5, width=40)
        self.script_entry.grid(row=3, column=1)
        self.script_entry.insert('1.0', "Hello, this is an automated call. Please press 1 to confirm.")

        tk.Button(self.master, text="Start Calling", command=self.start_bot, bg="#4CAF50").pack(pady=20)
        tk.Button(self.master, text="Edit Config", command=self.show_config_window, bg="#FFA500").pack(pady=10)
        
    def show_config_window(self):
        config_window = tk.Toplevel(self.master)
        config_window.title("Configuration")
        config_window.geometry("400x500")

        current_config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                current_config = json.load(f)

        fields = {
            "account_sid": ("Twilio Account SID:", current_config.get("account_sid", "")),
            "auth_token": ("Twilio Auth Token:", current_config.get("auth_token", "")),
            "phone_number": ("Twilio Phone Number:", current_config.get("phone_number", "")),
            "elevenlabs_api_key": ("ElevenLabs API Key:", current_config.get("elevenlabs_api_key", ""))
        }

        entries = {}
        for key, (label, value) in fields.items():
            tk.Label(config_window, text=label).pack(pady=5)
            entry = tk.Entry(config_window, width=40)
            entry.insert(0, value)
            if key in ["auth_token", "elevenlabs_api_key"]:
                entry.config(show="*")
            entry.pack(pady=5)
            entries[key] = entry

        def save_config():
            config = {key: entry.get().strip() for key, entry in entries.items()}
            config['webhook_url'] = WEBHOOK_URL
            
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)

            if config['elevenlabs_api_key']:
                if self.tts_service.initialize(config['elevenlabs_api_key']):
                    self.status_label.config(text="Status: Ready (TTS Configured)")
                else:
                    self.status_label.config(text="Status: Ready (TTS Configuration Failed)")

            messagebox.showinfo("Success", "Configuration saved successfully")
            config_window.destroy()
            self.load_config()

        tk.Button(config_window, text="Save", command=save_config).pack(pady=20)
   
    def load_config(self):
        global TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, WEBHOOK_URL
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                
                TWILIO_ACCOUNT_SID = config.get('account_sid', '')
                TWILIO_AUTH_TOKEN = config.get('auth_token', '')
                TWILIO_PHONE_NUMBER = config.get('phone_number', '')
                
                WEBHOOK_URL = config.get('webhook_url', '')
                
                elevenlabs_api_key = config.get('elevenlabs_api_key', None)
                if elevenlabs_api_key:
                    if self.tts_service.initialize(elevenlabs_api_key):
                        self.status_label.config(text="Status: Ready (TTS Configured)")
                        logging.info("TTS service initialized successfully")
                    else:
                        self.status_label.config(text="Status: Ready (TTS Configuration Failed)")
                        logging.error("Failed to initialize TTS service")
                else:
                    self.status_label.config(text="Status: Ready (TTS Not Configured)")

                if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER:
                    self.bot = TwilioCallBot(
                        TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, self.tts_service, AUDIO_DIR
                    )
                    logging.info("TwilioCallBot initialized successfully")
                else:
                    logging.warning("Twilio credentials are missing. TwilioCallBot not initialized.")
                
                logging.info("Configuration loaded:")
                logging.info(f"Account SID: {'*' * len(TWILIO_ACCOUNT_SID) if TWILIO_ACCOUNT_SID else 'Not Set'}")
                logging.info(f"Auth Token: {'*' * len(TWILIO_AUTH_TOKEN) if TWILIO_AUTH_TOKEN else 'Not Set'}")
                logging.info(f"Phone Number: {TWILIO_PHONE_NUMBER if TWILIO_PHONE_NUMBER else 'Not Set'}")
                logging.info(f"Webhook URL: {WEBHOOK_URL if WEBHOOK_URL else 'Not Set'}")
                
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            messagebox.showerror("Error", f"Failed to load configuration: {e}")
            
    def select_file(self):
        global INPUT_FILE
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            INPUT_FILE = file_path
            self.status_label.config(text=f"Selected file: {INPUT_FILE}")

    def preview_voice(self):
        if not self.tts_service.is_initialized:
            messagebox.showerror("Error", "Please configure ElevenLabs API key first")
            return

        script_text = self.script_entry.get("1.0", "end").strip()
        if not script_text:
            messagebox.showerror("Error", "Please enter some text to preview")
            return

        try:
            self.status_label.config(text="Generating preview...")
            self.master.update()

            def generate_and_play():
                try:
                    if self.tts_service.preview_voice(script_text):
                        self.status_label.config(text="Ready")
                    else:
                        self.status_label.config(text="Preview failed")
                except Exception as e:
                    self.status_label.config(text="Preview error")
                    messagebox.showerror("Error", f"Failed to preview voice: {str(e)}")

            threading.Thread(target=generate_and_play, daemon=True).start()

        except Exception as e:
            self.status_label.config(text="Ready")
            messagebox.showerror("Error", f"Preview failed: {str(e)}")

    def show_config_window(self):
        config_window = tk.Toplevel(self.master)
        config_window.title("Configuration")
        config_window.geometry("400x500")

        current_config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                current_config = json.load(f)

        fields = {
            "account_sid": ("Twilio Account SID:", current_config.get("account_sid", "")),
            "auth_token": ("Twilio Auth Token:", current_config.get("auth_token", "")),
            "phone_number": ("Twilio Phone Number:", current_config.get("phone_number", "")),
            "elevenlabs_api_key": ("ElevenLabs API Key:", current_config.get("elevenlabs_api_key", ""))
        }

        entries = {}
        for key, (label, value) in fields.items():
            tk.Label(config_window, text=label).pack(pady=5)
            entry = tk.Entry(config_window, width=40)
            entry.insert(0, value)
            if key in ["auth_token", "elevenlabs_api_key"]:
                entry.config(show="*")
            entry.pack(pady=5)
            entries[key] = entry

        def save_config():
            config = {key: entry.get().strip() for key, entry in entries.items()}
            config['webhook_url'] = WEBHOOK_URL
            
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)

            if config['elevenlabs_api_key']:
                if self.tts_service.initialize(config['elevenlabs_api_key']):
                    self.status_label.config(text="Status: Ready (TTS Configured)")
                else:
                    self.status_label.config(text="Status: Ready (TTS Configuration Failed)")

            messagebox.showinfo("Success", "Configuration saved successfully")
            config_window.destroy()
            self.load_config()

        tk.Button(config_window, text="Save", command=save_config).pack(pady=20)


    def start_bot(self):
        global TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, WEBHOOK_URL, INPUT_FILE, CURRENT_SCRIPT, SUCCESS_FILE, RETRY_FILE
        
        # Validate credentials and configuration
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, WEBHOOK_URL]):
            messagebox.showerror("Error", "Please configure Twilio credentials first.")
            return
        
        if not INPUT_FILE:
            messagebox.showerror("Error", "Please select a phone numbers file.")
            return

        try:
            self.tts_service.check_api_key()
        except ValueError as e:
            messagebox.showerror("TTS Error", str(e))
            self.show_config_window()
            return

        script_text = self.script_entry.get("1.0", "end").strip()
        if not script_text:
            messagebox.showerror("Error", "Please provide a script for the call.")
            return

        # Read phone numbers
        try:
            with open(INPUT_FILE, 'r') as f:
                numbers = [re.sub(NUMBER_REGEX, '', line.strip()) for line in f if line.strip()]

            if not numbers:
                messagebox.showerror("Error", "No valid phone numbers found in file.")
                return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read phone numbers file: {str(e)}")
            return

        # Initialize bot
        bot = TwilioCallBot(
            TWILIO_ACCOUNT_SID,
            TWILIO_AUTH_TOKEN,
            TWILIO_PHONE_NUMBER,
            self.tts_service,
            self.audio_dir
        )

        # Get thread count
        try:
            thread_count = int(self.threads_entry.get())
            if thread_count < 1:
                raise ValueError("Thread count must be at least 1")
        except ValueError as e:
            messagebox.showerror("Error", "Invalid thread count. Using default of 1.")
            thread_count = 1

        self.status_label.config(text="Status: Starting calls...")

        # Setup queue for numbers
        queue = Queue()
        for number in numbers:
            queue.put(number)

        def process_numbers():
            while True:
                try:
                    try:
                        number = queue.get_nowait()
                    except Empty:
                        break

                    try:
                        call_sid = bot.make_call(number, script_text)
                        if call_sid:
                            while True:
                                status = bot.get_call_status(call_sid)
                                if status in ['completed', 'failed', 'busy', 'no-answer', 'canceled']:
                                    with open(SUCCESS_FILE if status == 'completed' else RETRY_FILE, 'a') as f:
                                        f.write(f"{number},{call_sid},{status}\n")
                                    break
                                time.sleep(1)
                        else:
                            with open(RETRY_FILE, 'a') as f:
                                f.write(f"{number},NO_SID,failed_to_initiate\n")
                    except Exception as e:
                        logging.error(f"Error processing number {number}: {e}")
                        with open(RETRY_FILE, 'a') as f:
                            f.write(f"{number},ERROR,{str(e)}\n")
                    finally:
                        queue.task_done()
                except Exception as e:
                    logging.error(f"Thread error: {e}")
                    break

        threads = []
        for _ in range(thread_count):
            thread = threading.Thread(target=process_numbers)
            thread.daemon = True
            thread.start()
            threads.append(thread)

        def monitor_progress():
            total = len(numbers)
            while not queue.empty():
                remaining = queue.qsize()
                progress = ((total - remaining) / total) * 100
                self.status_label.config(text=f"Status: Progress {progress:.1f}% ({total - remaining}/{total})")
                time.sleep(1)
            
            for thread in threads:
                if thread.is_alive():
                    thread.join()
            
            self.status_label.config(text="Status: All calls completed")
            messagebox.showinfo("Complete", "All calls have been processed")

        monitor_thread = threading.Thread(target=monitor_progress)
        monitor_thread.daemon = True
        monitor_thread.start()

