#!/usr/bin/env python3

from typing import Optional
import argparse
import os
import sounddevice as sd
import soundfile as sf
import time
import requests
import base64


class VisionClipGenerator:
    """
    Vision Clip Generator - Creates conversational audio demos by combining
    Text-to-Speech (TTS) and live microphone recordings.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Vision Clip Generator.

        Args:
            api_key: Google API key for TTS. If None, reads from GOOGLE_API_KEY env var.
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY must be set in environment or passed to constructor")

        self.url = f'https://texttospeech.googleapis.com/v1beta1/text:synthesize?alt=json&key={self.api_key}'

        # Audio processing paths
        self.sox_path = "sox-14.4.2/sox "
        self.rec_path = "sox-14.4.2/rec "
        self.play_path = "afplay "

        # Voice configuration
        self.va_locale = os.getenv('VA_LOCALE', 'en-US')
        self.va_voice = os.getenv('VA_VOICE', 'en-US-Journey-O')
        self.caller_locale = os.getenv('CALLER_LOCALE', 'en-US')
        self.caller_voice = os.getenv('CALLER_VOICE', 'en-US-Journey-D')

        # Processing state
        self.ignore = True
        self.fnum = 1
        self.final_audio = ''

    def text_to_wav(self, voice: str, rate: float, locale: str, text: str, filename: str) -> None:
        """
        Convert text to WAV audio using Google Text-to-Speech API.

        Args:
            voice: Voice name (e.g., 'en-US-Journey-O')
            rate: Speaking rate (1.0 is normal)
            locale: Locale code (e.g., 'en-US')
            text: Text to convert to speech
            filename: Output WAV filename
        """
        headers = {'content-type': 'application/json'}
        payload = {
            "audioConfig": {
                "audioEncoding": "LINEAR16",
                "effectsProfileId": ["telephony-class-application"],
                "pitch": 0,
                "speakingRate": rate
            },
            "input": {
                "text": text
            },
            "voice": {
                "languageCode": locale,
                "name": voice
            }
        }

        response = requests.post(self.url, json=payload, headers=headers)
        audio_json = response.json()
        audio_content = audio_json['audioContent']
        decoded_data = base64.b64decode(audio_content, ' /')

        with open(filename, 'wb') as pcm:
            pcm.write(decoded_data)

    def process_iva_line(self, line: str) -> None:
        """
        Process an IVA (Interactive Voice Assistant) line.

        Args:
            line: The line containing IVA dialogue
        """
        ivr = line.split(':', 1)
        print(line)
        text = ivr[1]
        filename = str(self.fnum) + '.wav'

        self.text_to_wav(self.va_voice, 1, self.va_locale, text, filename)

        # Sleep to allow audio file to close
        time.sleep(1)

        # Play the audio
        os.system(self.play_path + filename)
        self.final_audio += filename + ' '
        self.fnum += 1

    def process_caller_line(self, line: str, record_mode: bool) -> None:
        """
        Process a Caller line (either record from microphone or generate with TTS).

        Args:
            line: The line containing caller dialogue
            record_mode: If True, record from microphone; if False, use TTS
        """
        caller = line.split(':', 2)
        print(line)
        text = caller[2]
        filename = str(self.fnum) + '.wav'

        if record_mode:
            print("Speak now")
            # Record audio from microphone
            duration_seconds = int(caller[1])
            numsamples = duration_seconds * 24000
            myrecording = sd.rec(numsamples, samplerate=24000, channels=1)
            sd.wait()

            # Write to temporary file and process with sox
            sf.write('tmp.wav', myrecording, 24000)
            os.system(self.sox_path + 'tmp.wav ' + filename + ' ')
        else:
            # Generate using TTS
            self.text_to_wav(self.caller_voice, 1, self.caller_locale, text, filename)

        self.final_audio += filename + ' '
        self.fnum += 1

    def process_special_tag(self, line: str) -> None:
        """
        Process special audio tags (backend, sendmail, transfer, text).

        Args:
            line: The line containing the special tag
        """
        if line.startswith('<backend>'):
            self.final_audio += 'Audio/backend.wav '
        elif line.startswith('<sendmail>'):
            self.final_audio += 'Audio/swoosh.wav '
        elif line.startswith('<transfer>'):
            self.final_audio += 'Audio/ringback.wav '
        elif line.startswith('<text>'):
            self.final_audio += 'Audio/text-received.wav '

    def process_dialog_file(self, filepath: str, record_mode: bool = False) -> str:
        """
        Process a dialog script file and generate audio.

        Args:
            filepath: Path to the dialog script file
            record_mode: If True, record caller audio from microphone

        Returns:
            Path to the final generated audio file (vc.wav)
        """
        # Reset state
        self.ignore = True
        self.fnum = 1
        self.final_audio = ''

        with open(filepath, 'r') as vfile:
            for line in vfile:
                if self.ignore:
                    if line.startswith('<ringback>'):
                        self.ignore = False
                        self.final_audio = ' Audio/ringback.wav '
                else:
                    if line.startswith('<hangup>'):
                        self.ignore = True
                    else:
                        if line.startswith('<backend>') or line.startswith('<sendmail>') or \
                           line.startswith('<transfer>') or line.startswith('<text>'):
                            self.process_special_tag(line)
                        elif line.startswith('IVA'):
                            self.process_iva_line(line)
                        elif line.startswith('Caller'):
                            self.process_caller_line(line, record_mode)

        # Concatenate all audio files into final output
        output_file = 'vc.wav'
        os.system(self.sox_path + self.final_audio + ' ' + output_file)

        return output_file

    def generate(self, filepath: str, record_mode: bool = False) -> str:
        """
        Generate a vision clip from a dialog script file.

        Args:
            filepath: Path to the dialog script file
            record_mode: If True, record caller audio from microphone

        Returns:
            Path to the final generated audio file
        """
        return self.process_dialog_file(filepath, record_mode)


def main():
    """Main entry point for command-line execution."""
    parser = argparse.ArgumentParser(
        prog="GoogleGenerateVC.py",
        description="Generate vision clip audio from dialog scripts"
    )

    parser.add_argument("--file", metavar="<path>", help="Path to Vision Clip File", required=True)
    parser.add_argument("--record", metavar="1", help="Record customer side using microphone rather than TTS")

    args = parser.parse_args()

    # Create generator instance
    try:
        generator = VisionClipGenerator()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set GOOGLE_API_KEY environment variable")
        return 1

    # Process the dialog file
    record_mode = args.record is not None
    output_file = generator.generate(args.file, record_mode)

    print(f"\nGenerated vision clip: {output_file}")
    return 0


if __name__ == '__main__':
    exit(main())
