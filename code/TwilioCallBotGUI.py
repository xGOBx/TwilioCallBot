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
from VoiceSelectionPopup import VoiceSelectionPopup

class TwilioCallBotGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Twilio Call Bot with ElevenLabs TTS")
        self.master.geometry("800x700")
        self.master.configure(bg="#f5f5f5")
        self.master.resizable(True, True)
        
        # Define colors for consistent styling
        self.primary_color = "#4a6fa5"
        self.secondary_color = "#6b8cae"
        self.accent_color = "#47b39c"
        self.warning_color = "#e6ac00"
        self.error_color = "#d9534f"
        self.success_color = "#5cb85c"
        self.bg_color = "#f5f5f5"
        self.input_bg = "#ffffff"
        
        # Font configurations
        self.header_font = ("Helvetica", 14, "bold")
        self.normal_font = ("Helvetica", 11)
        self.small_font = ("Helvetica", 10)
        
        self.audio_dir = AUDIO_DIR
        self.tts_service = ElevenLabsTTS(AUDIO_DIR)
        self.bot = None
        self.threads = []
        self.phone_numbers_file = None
        
        self.ensure_config_file()
        self.create_audio_dir()
        self.setup_ngrok()
        self.setup_gui()
        self.load_config()

            
        self.creator_label = tk.Label(
                self.master,
                text="Made by @xGOBx",
                font=self.small_font,
                bg=self.bg_color,
                fg=self.primary_color
            )
        self.creator_label.place(relx=0.98, rely=0.98, anchor="se")
            
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
        # Create a main container with padding
        main_container = tk.Frame(self.master, bg=self.bg_color, padx=20, pady=20)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Add a title section
        title_frame = tk.Frame(main_container, bg=self.bg_color)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(title_frame, text="Twilio Automated Call System", 
                              font=("Helvetica", 18, "bold"), bg=self.bg_color, fg=self.primary_color)
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, text="Make automated calls with ElevenLabs voice synthesis", 
                                 font=("Helvetica", 12), bg=self.bg_color, fg=self.secondary_color)
        subtitle_label.pack(pady=(5, 0))
        
        # Status bar with border and better styling
        status_frame = tk.Frame(main_container, bg=self.bg_color, relief=tk.GROOVE, bd=1)
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.status_label = tk.Label(status_frame, text="Status: Ready (TTS Not Configured)", 
                                   font=self.normal_font, bg=self.bg_color, pady=8)
        self.status_label.pack(fill=tk.X)
        
        # Main content section
        content_frame = tk.Frame(main_container, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for configuration
        left_panel = tk.LabelFrame(content_frame, text="Configuration", font=self.header_font, 
                                  bg=self.bg_color, fg=self.primary_color, padx=15, pady=15)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Concurrent calls section
        calls_frame = tk.Frame(left_panel, bg=self.bg_color)
        calls_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(calls_frame, text="Number of Concurrent Calls:", 
               font=self.normal_font, bg=self.bg_color).pack(anchor=tk.W, pady=(0, 5))
        
        threads_frame = tk.Frame(calls_frame, bg=self.bg_color)
        threads_frame.pack(fill=tk.X)
        
        self.threads_entry = tk.Entry(threads_frame, font=self.normal_font, bg=self.input_bg)
        self.threads_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.threads_entry.insert(0, '1')
        
        # Phone numbers file selector
        file_frame = tk.Frame(left_panel, bg=self.bg_color)
        file_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(file_frame, text="Phone Numbers File:", 
               font=self.normal_font, bg=self.bg_color).pack(anchor=tk.W, pady=(0, 5))
        
        file_selector_frame = tk.Frame(file_frame, bg=self.bg_color)
        file_selector_frame.pack(fill=tk.X)
        
        self.file_label = tk.Label(file_selector_frame, text="No file selected", 
                                 font=self.small_font, bg=self.input_bg, fg="gray", 
                                 pady=5, anchor=tk.W)
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(file_selector_frame, text="Browse", command=self.select_file, 
                font=self.normal_font, bg=self.secondary_color, fg="white", 
                pady=3, padx=10).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Voice selection section
        voice_frame = tk.LabelFrame(left_panel, text="Voice Settings", font=self.normal_font, 
                                  bg=self.bg_color, fg=self.primary_color, padx=10, pady=10)
        voice_frame.pack(fill=tk.X, pady=(0, 15))
        
        voice_buttons_frame = tk.Frame(voice_frame, bg=self.bg_color)
        voice_buttons_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(voice_buttons_frame, text="Preview Voice", command=self.preview_voice, 
                font=self.normal_font, bg=self.accent_color, fg="white", 
                pady=5, padx=10).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
                
        tk.Button(voice_buttons_frame, text="Change Voice", command=self.show_voice_selection, 
                font=self.normal_font, bg=self.primary_color, fg="white", 
                pady=5, padx=10).pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Config button
        tk.Button(left_panel, text="Edit API Configuration", command=self.show_config_window, 
                font=self.normal_font, bg=self.warning_color, fg="white", 
                pady=5).pack(fill=tk.X)
        
        # Right panel for script and actions
        right_panel = tk.LabelFrame(content_frame, text="Call Script", font=self.header_font, 
                                   bg=self.bg_color, fg=self.primary_color, padx=15, pady=15)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Script text area
        script_frame = tk.Frame(right_panel, bg=self.bg_color)
        script_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        tk.Label(script_frame, text="Enter your call script below:", 
               font=self.normal_font, bg=self.bg_color).pack(anchor=tk.W, pady=(0, 5))
        
        # Add a scrollbar to the text area
        script_container = tk.Frame(script_frame, bg=self.bg_color)
        script_container.pack(fill=tk.BOTH, expand=True)
        
        scroll_y = tk.Scrollbar(script_container)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.script_entry = tk.Text(script_container, height=10, font=self.normal_font, 
                                  bg=self.input_bg, wrap=tk.WORD, yscrollcommand=scroll_y.set)
        self.script_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.script_entry.insert('1.0', "Hello, this is an automated call. Please press 1 to confirm.")
        
        scroll_y.config(command=self.script_entry.yview)
        
        # Script tips
        tips_frame = tk.Frame(right_panel, bg="#e8f4f9", padx=10, pady=10, bd=1, relief=tk.GROOVE)
        tips_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(tips_frame, text="Tips:", font=("Helvetica", 10, "bold"), 
               bg="#e8f4f9", fg=self.primary_color).pack(anchor=tk.W)
        tk.Label(tips_frame, text="• Keep your message clear and concise", 
               font=self.small_font, bg="#e8f4f9").pack(anchor=tk.W)
        tk.Label(tips_frame, text="• Include pauses by typing '...' where needed", 
               font=self.small_font, bg="#e8f4f9").pack(anchor=tk.W)
        tk.Label(tips_frame, text="• Test your script with Preview Voice before making calls", 
               font=self.small_font, bg="#e8f4f9").pack(anchor=tk.W)
        
        # Start calling button
        start_button = tk.Button(right_panel, text="START CALLING", command=self.start_bot, 
                               font=("Helvetica", 12, "bold"), bg=self.success_color, fg="white", 
                               pady=10, cursor="hand2")
        start_button.pack(fill=tk.X)

    def select_file(self):
        global INPUT_FILE
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            INPUT_FILE = file_path
            # Update the file label with just the filename, not the full path
            filename = os.path.basename(file_path)
            self.file_label.config(text=filename, fg=self.primary_color)
            self.status_label.config(text=f"Selected file: {filename}")

    def preview_voice(self):
        if not self.tts_service.is_initialized:
            messagebox.showerror("Error", "Please configure ElevenLabs API key first")
            return

        script_text = self.script_entry.get("1.0", "end").strip()
        if not script_text:
            messagebox.showerror("Error", "Please enter some text to preview")
            return

        try:
            # Make sure we're using the current voice name from the TTS service
            voice_name = self.tts_service.voice_name
            self.status_label.config(text=f"Generating preview with voice: {voice_name}...")
            self.master.update()

            def generate_and_play():
                try:
                    # The voice ID should already be set in the TTS service
                    if self.tts_service.preview_voice(script_text):
                        self.status_label.config(text=f"Ready (Voice: {voice_name})")
                    else:
                        self.status_label.config(text="Preview failed")
                except Exception as e:
                    self.status_label.config(text="Preview error")
                    messagebox.showerror("Error", f"Failed to preview voice: {str(e)}")

            threading.Thread(target=generate_and_play, daemon=True).start()

        except Exception as e:
            self.status_label.config(text="Ready")
            messagebox.showerror("Error", f"Preview failed: {str(e)}")
            
    def show_voice_selection(self):
        """Show voice selection popup window"""
        if not self.tts_service.is_initialized:
            messagebox.showerror("Error", "Please configure ElevenLabs API key first")
            self.show_config_window()
            return

        try:
            # Store current voice info before opening popup
            current_voice_id = self.tts_service.voice_id
            current_voice_name = self.tts_service.voice_name
            
            # Create and show the voice selection popup
            voice_popup = VoiceSelectionPopup(self.master, self.tts_service)
            self.master.wait_window(voice_popup.popup)  # Wait for popup to close
            
            # After popup closes, check if the voice was changed
            if self.tts_service.voice_id != current_voice_id:
                # Update the status label with the new voice name
                self.status_label.config(text=f"Status: Ready (Voice: {self.tts_service.voice_name})")
                
                # Save the voice selection to config file so it persists between sessions
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE, 'r+') as f:
                        config = json.load(f)
                        config['voice_id'] = self.tts_service.voice_id
                        config['voice_name'] = self.tts_service.voice_name
                        f.seek(0)
                        json.dump(config, f, indent=4)
                        f.truncate()
                
        except Exception as e:
            logging.error(f"Voice selection error: {e}")
            messagebox.showerror("Error", f"Failed to open voice selection: {str(e)}")
                    
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
                    # Initialize TTS service with the API key
                    if self.tts_service.initialize(elevenlabs_api_key):
                        # If voice_id exists in config, set it after initialization
                        if 'voice_id' in config and 'voice_name' in config:
                            self.tts_service.set_voice(config['voice_id'], config['voice_name'])
                            self.status_label.config(text=f"Status: Ready (Voice: {config['voice_name']})")
                        else:
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

    def show_config_window(self):
        config_window = tk.Toplevel(self.master)
        config_window.title("API Configuration")
        config_window.geometry("800x900")  # Increased size for better display
        config_window.configure(bg=self.bg_color)
        config_window.resizable(True, True)  # Allow resizing for better user experience
        
        # Add some padding around the content
        main_frame = tk.Frame(config_window, bg=self.bg_color, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        tk.Label(main_frame, text="Configure API Settings", 
            font=("Helvetica", 16, "bold"), bg=self.bg_color, fg=self.primary_color).pack(pady=(0, 20))

        current_config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                current_config = json.load(f)

        # Create scrollable frame for fields
        canvas = tk.Canvas(main_frame, bg=self.bg_color, highlightthickness=0)
        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.bg_color)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Configure canvas and scrollbar to expand properly
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Add mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        fields = {
            "account_sid": ("Twilio Account SID:", current_config.get("account_sid", "")),
            "auth_token": ("Twilio Auth Token:", current_config.get("auth_token", "")),
            "phone_number": ("Twilio Phone Number:", current_config.get("phone_number", "")),
            "elevenlabs_api_key": ("ElevenLabs API Key:", current_config.get("elevenlabs_api_key", ""))
        }

        entries = {}
        row = 0
        for key, (label, value) in fields.items():
            # Create label frame for each field
            field_frame = tk.LabelFrame(scrollable_frame, text=label, font=self.normal_font, 
                                    bg=self.bg_color, fg=self.primary_color, padx=10, pady=5)
            field_frame.pack(fill=tk.X, pady=10, padx=5)  # Added horizontal padding
            
            entry = tk.Entry(field_frame, font=self.normal_font, bg=self.input_bg, width=40)
            entry.pack(fill=tk.X, pady=5, padx=5)  # Added padding
            entry.insert(0, value)
            
            if key in ["auth_token", "elevenlabs_api_key"]:
                entry.config(show="*")
                
                # Add show/hide button for sensitive fields
                def toggle_show_password(entry=entry):
                    if entry.cget('show') == '*':
                        entry.config(show='')
                    else:
                        entry.config(show='*')
                
                show_btn = tk.Button(field_frame, text="Show/Hide", font=self.small_font,
                                command=toggle_show_password, bg=self.secondary_color, fg="white")
                show_btn.pack(pady=(0, 5))
            
            entries[key] = entry
            row += 1

        # Add tips section
        tips_frame = tk.LabelFrame(scrollable_frame, text="Tips", font=self.normal_font, 
                                bg="#e8f4f9", fg=self.primary_color, padx=10, pady=5)
        tips_frame.pack(fill=tk.X, pady=10, padx=5)  # Added horizontal padding
        
        tk.Label(tips_frame, text="• Twilio credentials can be found in your Twilio console", 
            font=self.small_font, bg="#e8f4f9", wraplength=500).pack(anchor=tk.W)  # Added wraplength
        tk.Label(tips_frame, text="• ElevenLabs API key is available in your ElevenLabs account settings", 
            font=self.small_font, bg="#e8f4f9", wraplength=500).pack(anchor=tk.W)  # Added wraplength
        tk.Label(tips_frame, text="• Include country code for phone numbers (e.g., +1 for US numbers)", 
            font=self.small_font, bg="#e8f4f9", wraplength=500).pack(anchor=tk.W)  # Added wraplength

        # Button frame
        button_frame = tk.Frame(main_frame, bg=self.bg_color, pady=10)
        button_frame.pack(fill=tk.X)
        
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

        def cancel_config():
            config_window.destroy()

        # Added more padding to buttons for better appearance
        tk.Button(button_frame, text="Save", command=save_config, font=self.normal_font,
                bg=self.success_color, fg="white", padx=25, pady=10).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="Cancel", command=cancel_config, font=self.normal_font,
                bg=self.secondary_color, fg="white", padx=25, pady=10).pack(side=tk.RIGHT, padx=10)

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

        # Show confirmation dialog
        confirm = messagebox.askyesno("Confirm", f"Ready to start {len(numbers)} calls with {thread_count} concurrent threads.\nContinue?")
        if not confirm:
            return

        # Create progress window
        progress_window = tk.Toplevel(self.master)
        progress_window.title("Call Progress")
        progress_window.geometry("500x300")
        progress_window.configure(bg=self.bg_color)
        
        # Add content to the progress window
        progress_frame = tk.Frame(progress_window, bg=self.bg_color, padx=20, pady=20)
        progress_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(progress_frame, text="Calling Progress", font=self.header_font, bg=self.bg_color, fg=self.primary_color).pack(pady=(0, 15))
        
        progress_status = tk.Label(progress_frame, text="Initializing calls...", font=self.normal_font, bg=self.bg_color)
        progress_status.pack(pady=(0, 10))
        
        # Progress bar
        progress_bar = tk.Canvas(progress_frame, width=450, height=30, bg="white", highlightthickness=1, highlightbackground="grey")
        progress_bar.pack(pady=(0, 15))
        
        # Progress statistics
        stats_frame = tk.Frame(progress_frame, bg=self.bg_color)
        stats_frame.pack(fill=tk.X, pady=(0, 15))
        
        stats_left = tk.Frame(stats_frame, bg=self.bg_color)
        stats_left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        stats_right = tk.Frame(stats_frame, bg=self.bg_color)
        stats_right.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        tk.Label(stats_left, text="Total Calls:", font=self.normal_font, bg=self.bg_color).pack(anchor=tk.W)
        total_calls_label = tk.Label(stats_right, text=str(len(numbers)), font=self.normal_font, bg=self.bg_color)
        total_calls_label.pack(anchor=tk.E)
        
        tk.Label(stats_left, text="Completed:", font=self.normal_font, bg=self.bg_color).pack(anchor=tk.W)
        completed_calls_label = tk.Label(stats_right, text="0", font=self.normal_font, bg=self.bg_color)
        completed_calls_label.pack(anchor=tk.E)
        
        tk.Label(stats_left, text="In Progress:", font=self.normal_font, bg=self.bg_color).pack(anchor=tk.W)
        in_progress_label = tk.Label(stats_right, text="0", font=self.normal_font, bg=self.bg_color)
        in_progress_label.pack(anchor=tk.E)
        
        tk.Label(stats_left, text="Failed:", font=self.normal_font, bg=self.bg_color).pack(anchor=tk.W)
        failed_calls_label = tk.Label(stats_right, text="0", font=self.normal_font, bg=self.bg_color)
        failed_calls_label.pack(anchor=tk.E)
        
        # Cancel button
        cancel_button = tk.Button(progress_frame, text="Cancel All Calls", font=self.normal_font,
                                bg=self.error_color, fg="white", padx=10, pady=5)
        cancel_button.pack()
        
        # Update the main status label
        self.status_label.config(text="Status: Calls in progress...")

        # Setup queue for numbers
        queue = Queue()
        for number in numbers:
            queue.put(number)
            
        # Shared variables for tracking progress
        progress_data = {
            'total': len(numbers),
            'completed': 0,
            'failed': 0,
            'in_progress': 0,
            'active_calls': {},  # Track active calls: {phone_number: call_sid}
            'cancel_requested': False
        }
        
        # Function to update the progress UI
        def update_progress_ui():
            completed = progress_data['completed']
            failed = progress_data['failed']
            in_progress = progress_data['in_progress']
            total = progress_data['total']
            
            # Update labels
            completed_calls_label.config(text=str(completed))
            failed_calls_label.config(text=str(failed))
            in_progress_label.config(text=str(in_progress))
            
            # Calculate percentage and update progress bar
            percent_done = ((completed + failed) / total) * 100 if total > 0 else 0
            progress_bar.delete("all")
            bar_width = 450 * (percent_done / 100)
            
            # Draw progress bar with gradient color
            if percent_done < 30:
                fill_color = "#ff9999"  # Light red
            elif percent_done < 60:
                fill_color = "#ffcc99"  # Light orange
            else:
                fill_color = "#99cc99"  # Light green
                
            progress_bar.create_rectangle(0, 0, bar_width, 30, fill=fill_color, outline="")
            progress_bar.create_text(225, 15, text=f"{percent_done:.1f}%", font=self.normal_font)
            
            # Update status text
            if completed + failed == total:
                if failed > 0:
                    progress_status.config(text=f"Completed with {failed} failed calls")
                else:
                    progress_status.config(text="All calls completed successfully!")
            else:
                progress_status.config(text=f"Processing calls... ({completed + failed}/{total})")
                
            # Update main window status as well
            self.status_label.config(text=f"Status: Calls {percent_done:.1f}% complete")
            
        # Handle cancel button click
        def request_cancel():
            if messagebox.askyesno("Cancel Calls", "Are you sure you want to cancel all remaining calls?"):
                progress_data['cancel_requested'] = True
                cancel_button.config(text="Cancelling...", state=tk.DISABLED)
                progress_status.config(text="Cancelling remaining calls...")
                
        cancel_button.config(command=request_cancel)

        def process_numbers():
            while not progress_data['cancel_requested']:
                try:
                    try:
                        number = queue.get_nowait()
                    except Empty:
                        break

                    # Update in_progress count
                    progress_data['in_progress'] += 1
                    progress_window.after(1, update_progress_ui)
                    
                    try:
                        call_sid = bot.make_call(number, script_text)
                        if call_sid:
                            # Add to active calls
                            progress_data['active_calls'][number] = call_sid
                            
                            while True:
                                status = bot.get_call_status(call_sid)
                                if status in ['completed', 'failed', 'busy', 'no-answer', 'canceled']:
                                    with open(SUCCESS_FILE if status == 'completed' else RETRY_FILE, 'a') as f:
                                        f.write(f"{number},{call_sid},{status}\n")
                                    
                                    # Update progress data
                                    if status == 'completed':
                                        progress_data['completed'] += 1
                                    else:
                                        progress_data['failed'] += 1
                                        
                                    progress_data['in_progress'] -= 1
                                    # Remove from active calls
                                    if number in progress_data['active_calls']:
                                        del progress_data['active_calls'][number]
                                        
                                    progress_window.after(1, update_progress_ui)
                                    break
                                time.sleep(1)
                        else:
                            with open(RETRY_FILE, 'a') as f:
                                f.write(f"{number},NO_SID,failed_to_initiate\n")
                            progress_data['failed'] += 1
                            progress_data['in_progress'] -= 1
                            progress_window.after(1, update_progress_ui)
                    except Exception as e:
                        logging.error(f"Error processing number {number}: {e}")
                        with open(RETRY_FILE, 'a') as f:
                            f.write(f"{number},ERROR,{str(e)}\n")
                        progress_data['failed'] += 1
                        progress_data['in_progress'] -= 1
                        progress_window.after(1, update_progress_ui)
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
            if queue.empty() and progress_data['in_progress'] == 0:
                # All done - enable the close button
                if not progress_data['cancel_requested']:
                    cancel_button.config(text="Close", command=progress_window.destroy, 
                                       bg=self.secondary_color, state=tk.NORMAL)
                else:
                    cancel_button.config(text="Close", command=progress_window.destroy, 
                                       bg=self.secondary_color, state=tk.NORMAL)
                    
                # Show completion message
                total_completed = progress_data['completed']
                total_failed = progress_data['failed']
                
                if progress_data['cancel_requested']:
                    self.status_label.config(text=f"Status: Calls cancelled. {total_completed} completed, {total_failed} failed")
                    messagebox.showinfo("Calls Cancelled", f"Call process was cancelled.\n\n{total_completed} calls completed\n{total_failed} calls failed")
                else:
                    self.status_label.config(text=f"Status: All calls completed. {total_completed} successful, {total_failed} failed")
                    
                    if total_failed > 0:
                        message = f"All calls completed.\n\n{total_completed} calls were successful\n{total_failed} calls failed"
                        icon = "warning"
                    else:
                        message = f"All {total_completed} calls completed successfully!"
                        icon = "info"
                        
                    messagebox.showinfo("Process Complete", message)
                
            else:
                # Still processing - check again in a second
                progress_window.after(1000, monitor_progress)

        # Start the monitor
        progress_window.after(1000, monitor_progress)
        
        # Make sure progress window stays on top
        progress_window.transient(self.master)
        progress_window.focus_set()
        progress_window.grab_set()