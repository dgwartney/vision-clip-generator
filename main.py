#!/usr/bin/env python3

from typing import Optional
import argparse
import os
import sounddevice as sd
import soundfile as sf
import time

# Import TTS abstraction layer
from tts import create_tts_provider, TTSProvider


class VisionClipGenerator:
    """
    Vision Clip Generator - Creates conversational audio demos by combining
    Text-to-Speech (TTS) and live microphone recordings.

    Now supports multiple TTS providers through the abstraction layer:
    - Google Cloud TTS (default)
    - Azure Cognitive Services
    - ElevenLabs
    - AWS Polly
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        tts_provider: Optional[str] = None,
        tts_instance: Optional[TTSProvider] = None,
        **tts_config
    ):
        """
        Initialize the Vision Clip Generator.

        Args:
            api_key: API key for TTS provider. If None, reads from environment.
                    For backward compatibility with Google TTS.
            tts_provider: TTS provider name ('google', 'azure', 'elevenlabs', 'aws').
                         If None, defaults to 'google' or reads from TTS_PROVIDER env var.
            tts_instance: Pre-configured TTS provider instance (optional).
                         If provided, overrides api_key and tts_provider.
            **tts_config: Additional TTS configuration options.

        Examples:
            # Backward compatible - Google with API key
            generator = VisionClipGenerator(api_key='xxx')

            # Explicit provider selection
            generator = VisionClipGenerator(tts_provider='azure', subscription_key='xxx')

            # Pre-configured provider
            provider = create_tts_provider('elevenlabs', api_key='xxx')
            generator = VisionClipGenerator(tts_instance=provider)

            # Configuration from environment
            generator = VisionClipGenerator()  # Uses TTS_PROVIDER and provider-specific env vars
        """
        # Audio processing paths
        self.sox_path = "sox-14.4.2/sox "
        self.rec_path = "sox-14.4.2/rec "
        self.play_path = "afplay "

        # Processing state
        self.ignore = True
        self.fnum = 1
        self.final_audio = ''

        # Initialize TTS provider
        if tts_instance:
            # Use provided TTS instance
            self.tts_provider = tts_instance
        else:
            # Create TTS provider from configuration
            # For backward compatibility, map api_key to google.api_key
            if api_key:
                if tts_provider is None or tts_provider == 'google':
                    tts_config['api_key'] = api_key

            self.tts_provider = create_tts_provider(
                provider=tts_provider,
                **tts_config
            )

        # Get voice configuration from provider or environment
        provider_config = getattr(self.tts_provider, 'va_voice', None)
        self.va_locale = getattr(self.tts_provider, 'va_locale', os.getenv('VA_LOCALE', 'en-US'))
        self.va_voice = getattr(self.tts_provider, 'va_voice', os.getenv('VA_VOICE', 'en-US-Journey-O'))
        self.caller_locale = getattr(self.tts_provider, 'caller_locale', os.getenv('CALLER_LOCALE', 'en-US'))
        self.caller_voice = getattr(self.tts_provider, 'caller_voice', os.getenv('CALLER_VOICE', 'en-US-Journey-D'))

    def text_to_wav(self, voice: str, rate: float, locale: str, text: str, filename: str) -> None:
        """
        Convert text to WAV audio using the configured TTS provider.

        Args:
            voice: Voice name (provider-specific)
            rate: Speaking rate (1.0 is normal)
            locale: Locale code (e.g., 'en-US')
            text: Text to convert to speech
            filename: Output WAV filename
        """
        self.tts_provider.synthesize(
            text=text,
            voice=voice,
            locale=locale,
            rate=rate,
            output_file=filename
        )

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
            self.final_audio += 'audio/backend.wav '
        elif line.startswith('<sendmail>'):
            self.final_audio += 'audio/swoosh.wav '
        elif line.startswith('<transfer>'):
            self.final_audio += 'audio/ringback.wav '
        elif line.startswith('<text>'):
            self.final_audio += 'audio/text-received.wav '

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
                        self.final_audio = ' audio/ringback.wav '
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
        prog="main.py",
        description="Generate vision clip audio from dialog scripts"
    )

    parser.add_argument("--file", metavar="<path>", help="Path to Vision Clip File", required=True)
    parser.add_argument("--record", action="store_true", help="Record customer side using microphone rather than TTS")

    args = parser.parse_args()

    # Create generator instance
    try:
        generator = VisionClipGenerator()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set GOOGLE_API_KEY environment variable")
        return 1

    # Process the dialog file
    record_mode = args.record
    output_file = generator.generate(args.file, record_mode)

    print(f"\nGenerated vision clip: {output_file}")
    return 0


if __name__ == '__main__':
    exit(main())
