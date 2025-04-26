import logging
import os
import time
from constants import AUDIO_DIR
from elevenlabs.client import ElevenLabs # type: ignore
from elevenlabs import Voice, VoiceSettings, play # type: ignore

class ElevenLabsTTS:
    def __init__(self,audio_dir):
        self.client = None
        self.voice_id = "21m00Tcm4TlvDq8ikWAM"  # Default voice (Rachel)
        self.model = "eleven_multilingual_v2"
        self.available_voices = []
        self.is_initialized = False
        self.audio_dir = audio_dir

    def initialize(self, api_key):
        try:
            self.client = ElevenLabs(api_key=api_key)
            self._cache_available_voices()
            self.is_initialized = True
            return True
        except Exception as e:
            logging.error(f"Failed to initialize ElevenLabs: {e}")
            return False

    def _cache_available_voices(self):
        try:
            response = self.client.voices.get_all()
            self.available_voices = response.voices
            logging.info(f"Cached {len(self.available_voices)} voices from ElevenLabs")
        except Exception as e:
            logging.error(f"Error fetching voices: {e}")
            self.available_voices = []

    def check_api_key(self):
        if not self.client:
            raise ValueError("ElevenLabs API key not configured. Please add it in the configuration.")
        if not self.is_initialized:
            raise ValueError("TTS service not properly initialized. Please check your API key.")
        
    def generate_speech(self, text, output_file=None):
        self.check_api_key()
        try:
            if output_file is None:
                output_file = os.path.join(self.audio_dir, f'tts_output_{int(time.time())}.mp3')
            else:
                # Just use the path directly without joining it with audio_dir again
                # This fixes the audio_files/audio_files nesting issue
                output_file = output_file
                
            audio = self.client.generate(
                text=text,
                voice=Voice(
                    voice_id=self.voice_id,
                    settings=VoiceSettings(
                        stability=0.71,
                        similarity_boost=0.5,
                        style=0.0,
                        use_speaker_boost=True
                    )
                ),
                model=self.model,
                output_format="mp3_44100_128"
            )
            
            if hasattr(audio, '__iter__'):
                audio_data = b''.join(chunk for chunk in audio)
            else:
                audio_data = audio
            
            with open(output_file, 'wb') as f:
                f.write(audio_data)
            
            return output_file
        except Exception as e:
            logging.error(f"TTS generation error: {e}")
            return None
        
        
    def preview_voice(self, text):
        self.check_api_key()
        try:
            audio = self.client.generate(
                text=text,
                voice=Voice(
                    voice_id=self.voice_id,
                    settings=VoiceSettings(
                        stability=0.71,
                        similarity_boost=0.5,
                        style=0.0,
                        use_speaker_boost=True
                    )
                ),
                model=self.model,
                output_format="mp3_44100_128"
            )
            
            if hasattr(audio, '__iter__'):
                audio_data = b''.join(chunk for chunk in audio)
            else:
                audio_data = audio
            
            play(audio_data)
            return True
        except Exception as e:
            logging.error(f"Preview error: {e}")
            return False

    def get_available_voices(self):
        self.check_api_key()
        return [(voice.name, voice.voice_id) for voice in self.available_voices]

    def set_voice(self, voice_id):
        self.voice_id = voice_id

    def preview_voice(self, text):
        self.check_api_key()
        try:
            audio = self.client.generate(
                text=text,
                voice=Voice(
                    voice_id=self.voice_id,
                    settings=VoiceSettings(
                        stability=0.71,
                        similarity_boost=0.5,
                        style=0.0,
                        use_speaker_boost=True
                    )
                ),
                model=self.model
            )
            play(audio)
            return True
        except Exception as e:
            logging.error(f"Preview error: {e}")
            return False