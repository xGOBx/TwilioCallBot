import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging

class VoiceSelectionPopup:
    def __init__(self, master, tts_service):
        """
        Creates a popup window for selecting ElevenLabs voices
        
        Args:
            master: The parent tkinter window
            tts_service: An initialized ElevenLabsTTS service
        """
        self.master = master
        self.tts_service = tts_service
        self.selected_voice_id = tts_service.voice_id  # Initialize with current voice
        self.selected_voice_name = tts_service.voice_name  # Initialize with current voice name
        self.voices = []  # Will store voice data (name, id)
        
        # Create popup window
        self.popup = tk.Toplevel(master)
        self.popup.title("Voice Selection")
        self.popup.geometry("500x600")
        self.popup.resizable(False, False)
        self.popup.transient(master)  # Set as transient to main window (dialog)
        self.popup.grab_set()  # Make window modal
        
        # Set window icon if available
        try:
            self.popup.iconbitmap("assets/voice_icon.ico")
        except:
            pass
            
        # Configure styles
        self.configure_styles()
        
        # Setup GUI elements
        self.setup_ui()
        
        # Load voices
        self.load_voices()
    
    def configure_styles(self):
        """Configure custom ttk styles for a modern look"""
        style = ttk.Style()
        
        # Configure main theme - use 'clam' as base as it's more customizable
        style.theme_use('clam')
        
        # Configure frame styles
        style.configure('TFrame', background='#f5f5f7')
        style.configure('TLabelframe', background='#f5f5f7', borderwidth=1)
        style.configure('TLabelframe.Label', background='#f5f5f7', foreground='#333333', font=('Segoe UI', 10, 'bold'))
        
        # Configure button styles
        style.configure('TButton', background='#e0e0e0', foreground='#333333', font=('Segoe UI', 9))
        style.map('TButton', 
                background=[('active', '#d0d0d0'), ('pressed', '#b0b0b0')],
                foreground=[('active', '#333333')])
                
        # Primary action button (Green)
        style.configure('Primary.TButton', 
                    background='#4CAF50', 
                    foreground='white', 
                    font=('Segoe UI', 9, 'bold'))
        style.map('Primary.TButton',
                background=[('active', '#45a049'), ('pressed', '#388e3c')],
                foreground=[('active', 'white')])
                
        # Secondary action button (Blue)
        style.configure('Secondary.TButton', 
                    background='#3875d0', 
                    foreground='white', 
                    font=('Segoe UI', 9))
        style.map('Secondary.TButton',
                background=[('active', '#2a67c2'), ('pressed', '#1e50a0')],
                foreground=[('active', 'white')])
        
        # Label styles
        style.configure('TLabel', background='#f5f5f7', foreground='#333333', font=('Segoe UI', 9))
        style.configure('Title.TLabel', font=('Segoe UI', 12, 'bold'), background='#f5f5f7', foreground='#222222')
        style.configure('Subtitle.TLabel', font=('Segoe UI', 10), background='#f5f5f7', foreground='#444444')
        style.configure('Status.TLabel', font=('Segoe UI', 9, 'italic'), background='#f5f5f7', foreground='#666666')
        
        # Entry style
        style.configure('TEntry', font=('Segoe UI', 9))
    
    def setup_ui(self):
        """Set up the user interface elements"""
        # Create main container frame with padding
        container = ttk.Frame(self.popup, style='TFrame')
        container.pack(fill=tk.BOTH, expand=True)
        
        # Add top header frame
        header_frame = ttk.Frame(container, style='TFrame')
        header_frame.pack(fill=tk.X, padx=20, pady=(20, 0))
        
        # Title label
        title_label = ttk.Label(
            header_frame, 
            text="ElevenLabs Voice Selection",
            style='Title.TLabel'
        )
        title_label.pack(anchor=tk.W)
        
        # Current voice display
        self.current_voice_label = ttk.Label(
            header_frame, 
            text=f"Current Voice: {self.selected_voice_name}",
            style='Subtitle.TLabel'
        )
        self.current_voice_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Add separator after header
        separator = ttk.Separator(container, orient='horizontal')
        separator.pack(fill=tk.X, padx=20, pady=15)
        
        # Main content area
        content_frame = ttk.Frame(container, style='TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=0)
        
        # Voice list frame
        list_frame = ttk.LabelFrame(content_frame, text="Available Voices", padding=(15, 10))
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Create voice listbox with custom styling
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        # Custom listbox with better styling
        self.voice_listbox = tk.Listbox(
            listbox_frame, 
            width=40, 
            height=12,
            font=('Segoe UI', 10),
            borderwidth=1,
            relief=tk.SOLID,
            activestyle='dotbox',
            highlightthickness=1,
            highlightcolor='#3875d0',
            selectbackground='#3875d0',
            selectforeground='white'
        )
        
        # Scrollbar with improved style
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.voice_listbox.yview)
        self.voice_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.voice_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Preview section
        preview_frame = ttk.LabelFrame(content_frame, text="Voice Preview", padding=(15, 10))
        preview_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Preview text entry with label
        ttk.Label(
            preview_frame, 
            text="Enter text to preview:",
            style='TLabel'
        ).pack(anchor=tk.W, pady=(5, 5))
        
        # Improved entry field
        self.preview_text = ttk.Entry(
            preview_frame, 
            width=40,
            font=('Segoe UI', 10)
        )
        self.preview_text.pack(fill=tk.X, pady=(0, 10))
        self.preview_text.insert(0, "Hello, this is a voice preview from ElevenLabs.")
        
        # Voice action buttons in a better layout
        voice_action_frame = ttk.Frame(preview_frame)
        voice_action_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Preview button with improved style
        self.preview_button = ttk.Button(
            voice_action_frame, 
            text="▶ Preview Voice", 
            command=self.preview_voice,
            style='Secondary.TButton'
        )
        self.preview_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Apply button with improved style
        self.apply_button = ttk.Button(
            voice_action_frame,
            text="✓ Apply Selected Voice",
            command=self.apply_voice_selection,
            style='Primary.TButton'
        )
        self.apply_button.pack(side=tk.RIGHT)
        
        # Status area
        status_frame = ttk.Frame(container, style='TFrame')
        status_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        # Status label with better styling
        self.status_label = ttk.Label(
            status_frame, 
            text="Loading voices...",
            style='Status.TLabel'
        )
        self.status_label.pack(fill=tk.X)
        
        # Add another separator before buttons
        separator2 = ttk.Separator(container, orient='horizontal')
        separator2.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        # Bottom buttons frame
        buttons_frame = ttk.Frame(container, style='TFrame')
        buttons_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Cancel button
        ttk.Button(
            buttons_frame, 
            text="Cancel", 
            command=self.cancel_selection,
            width=12
        ).pack(side=tk.LEFT)
        
        # Close button
        ttk.Button(
            buttons_frame, 
            text="Close", 
            command=self.close_popup,
            width=12
        ).pack(side=tk.RIGHT)
        
        # Bind selection event
        self.voice_listbox.bind('<<ListboxSelect>>', self.on_voice_select)
        self.voice_listbox.bind('<Double-1>', lambda e: self.preview_voice())
        
        # Flag to track if a voice has been applied
        self.voice_applied = False
    
    def load_voices(self):
        """Load available voices from the API"""
        def fetch_voices():
            try:
                self.voices = self.tts_service.get_available_voices()
                
                # Clear listbox
                self.voice_listbox.delete(0, tk.END)
                
                # Add voices to listbox
                for voice_name, voice_id in self.voices:
                    self.voice_listbox.insert(tk.END, f"{voice_name}")
                    
                    # Mark current selected voice
                    if voice_id == self.tts_service.voice_id:
                        idx = self.voices.index((voice_name, voice_id))
                        self.voice_listbox.selection_set(idx)
                        self.voice_listbox.see(idx)
                
                self.status_label.config(text=f"Found {len(self.voices)} voices. Select one to preview.")
                
            except Exception as e:
                logging.error(f"Error loading voices: {e}")
                self.status_label.config(text=f"Error loading voices: {str(e)}")
                messagebox.showerror("Error", f"Failed to load voices: {str(e)}")
        
        # Run in a separate thread to prevent UI freezing
        threading.Thread(target=fetch_voices, daemon=True).start()
    
    def on_voice_select(self, event):
        """Handle voice selection from listbox"""
        if not self.voice_listbox.curselection():
            return
            
        index = self.voice_listbox.curselection()[0]
        if index < len(self.voices):
            self.selected_voice_name, self.selected_voice_id = self.voices[index]
            self.status_label.config(text=f"Selected: {self.selected_voice_name}")
    
    def preview_voice(self):
        """Preview the selected voice"""
        if not self.selected_voice_id:
            messagebox.showinfo("Information", "Please select a voice first.")
            return
            
        preview_text = self.preview_text.get().strip()
        if not preview_text:
            messagebox.showinfo("Information", "Please enter text to preview.")
            return
            
        # Temporarily set the voice ID for preview
        original_voice_id = self.tts_service.voice_id
        original_voice_name = self.tts_service.voice_name
        
        # Set the voice for preview
        self.tts_service.set_voice(self.selected_voice_id, self.selected_voice_name)
        
        # Disable preview button during playback
        self.preview_button.config(state="disabled")
        self.apply_button.config(state="disabled")
        self.status_label.config(text=f"▶ Playing preview for {self.selected_voice_name}...")
        
        def play_preview():
            try:
                result = self.tts_service.preview_voice(preview_text)
                if not result:
                    self.status_label.config(text="Preview failed. Please try again.")
                else:
                    self.status_label.config(text=f"Voice: {self.selected_voice_name}")
            except Exception as e:
                logging.error(f"Voice preview error: {e}")
                self.status_label.config(text=f"Preview error: {str(e)}")
            finally:
                # Restore original voice ID unless this voice has been applied
                if self.popup.winfo_exists() and not self.voice_applied:  
                    self.tts_service.set_voice(original_voice_id, original_voice_name)
                # Re-enable buttons
                if self.preview_button.winfo_exists():  
                    self.preview_button.config(state="normal")
                if self.apply_button.winfo_exists():
                    self.apply_button.config(state="normal")
        
        # Play in separate thread to prevent UI freezing
        threading.Thread(target=play_preview, daemon=True).start()
    
    def apply_voice_selection(self):
        """Apply the currently selected voice without closing the popup"""
        if not self.selected_voice_id:
            messagebox.showinfo("Information", "Please select a voice first.")
            return
        
        # Set the new voice ID in the TTS service
        if self.tts_service.set_voice(self.selected_voice_id, self.selected_voice_name):
            self.voice_applied = True
            logging.info(f"Voice set to: {self.selected_voice_name} (ID: {self.selected_voice_id})")
            
            # Update current voice label
            self.current_voice_label.config(text=f"Current Voice: {self.selected_voice_name}")
            
            # Update status
            self.status_label.config(text=f"✓ Voice changed to {self.selected_voice_name}")
            messagebox.showinfo("Success", f"Voice changed to {self.selected_voice_name}")
        else:
            logging.error("Failed to set voice")
            messagebox.showerror("Error", "Failed to set voice")
    
    def cancel_selection(self):
        """Cancel selection and restore original voice"""
        # Check if we've applied a different voice
        if self.voice_applied:
            response = messagebox.askyesno("Confirm", 
                              "You've applied a new voice. Do you want to revert to the original voice?")
            if response:
                # Get the original voice ID that was set when the popup was created
                original_voice_id = self.tts_service.voice_id
                original_voice_name = self.tts_service.voice_name
                
                # Only revert if we're not already using the original voice
                if original_voice_id != self.selected_voice_id:
                    if self.tts_service.set_voice(original_voice_id, original_voice_name):
                        messagebox.showinfo("Reverted", f"Voice reverted to {original_voice_name}")
                    else:
                        messagebox.showerror("Error", "Failed to revert voice selection")
        
        # Close the popup
        self.popup.destroy()
    
    def close_popup(self):
        """Close the popup, keeping any applied voice selection"""
        if self.voice_applied:
            messagebox.showinfo("Voice Selected", f"Using voice: {self.selected_voice_name}")
        else:
            # If no voice was explicitly applied, keep the original
            messagebox.showinfo("No Change", "No new voice was applied.")
        
        self.popup.destroy()
    
    def get_selected_voice(self):
        """Return the selected voice information"""
        return (self.selected_voice_name, self.selected_voice_id)