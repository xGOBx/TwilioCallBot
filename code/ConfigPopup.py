import tkinter as tk
from tkinter import simpledialog

class ConfigPopup(simpledialog.Dialog):
    def __init__(self, parent, title="Setup Information"):
        """
        Initialize the configuration popup.
        :param parent: The parent widget.
        :param title: The title of the dialog window.
        """
        self.config = {}
        super().__init__(parent, title)

    def body(self, master):
        """
        Create the dialog's body with entry fields.
        :param master: The master widget.
        """
        tk.Label(master, text="Enter Account SID:").grid(row=0)
        tk.Label(master, text="Enter Auth Token:").grid(row=1)
        tk.Label(master, text="Enter Phone Number:").grid(row=2)
        tk.Label(master, text="Enter Webhook URL (optional):").grid(row=3)
        tk.Label(master, text="Enter ElevenLabs API Key:").grid(row=4)

        self.account_sid_entry = tk.Entry(master)
        self.auth_token_entry = tk.Entry(master, show="*")
        self.phone_number_entry = tk.Entry(master)
        self.webhook_url_entry = tk.Entry(master)
        self.elevenlabs_api_key_entry = tk.Entry(master)

        self.account_sid_entry.grid(row=0, column=1)
        self.auth_token_entry.grid(row=1, column=1)
        self.phone_number_entry.grid(row=2, column=1)
        self.webhook_url_entry.grid(row=3, column=1)
        self.elevenlabs_api_key_entry.grid(row=4, column=1)

    def apply(self):
        """
        Store the input data into the configuration dictionary.
        """
        self.config["account_sid"] = self.account_sid_entry.get()
        self.config["auth_token"] = self.auth_token_entry.get()
        self.config["phone_number"] = self.phone_number_entry.get()
        self.config["webhook_url"] = self.webhook_url_entry.get()
        self.config["elevenlabs_api_key"] = self.elevenlabs_api_key_entry.get()

    def get_config(self):
        """
        Retrieve the configuration dictionary.
        :return: A dictionary of configuration data.
        """
        return self.config

