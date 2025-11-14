#!/usr/bin/env python3

from typing import Optional
import argparse
import os
import shutil
import sounddevice as sd
import soundfile as sf
import time
from pydub import AudioSegment

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
        self.temp_dir = ".temp"

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

    def play_audio(self, filename: str) -> None:
        """
        Play audio file and wait for completion using sounddevice.

        Args:
            filename: Path to audio file to play
        """
        data, samplerate = sf.read(filename)
        sd.play(data, samplerate)
        sd.wait()  # Block until playback finishes

    def concatenate_audio_files(self, file_list: str, output_file: str) -> None:
        """
        Concatenate multiple audio files into a single output file using pydub.

        Args:
            file_list: Space-separated string of audio file paths
            output_file: Path for the concatenated output file
        """
        combined = AudioSegment.empty()

        for audio_file in file_list.split():
            audio_file = audio_file.strip()
            if audio_file:
                combined += AudioSegment.from_wav(audio_file)

        combined.export(output_file, format="wav")

    def process_iva_line(self, line: str) -> None:
        """
        Process an IVA (Interactive Voice Assistant) line.

        Args:
            line: The line containing IVA dialogue
        """
        ivr = line.split(':', 1)
        print(line)
        text = ivr[1]
        filename = os.path.join(self.temp_dir, f'{self.fnum:03d}_va.wav')

        self.text_to_wav(self.va_voice, 1, self.va_locale, text, filename)

        # Sleep to allow audio file to close
        time.sleep(1)

        # Play the audio using sounddevice
        self.play_audio(filename)
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
        filename = os.path.join(self.temp_dir, f'{self.fnum:03d}_caller.wav')

        if record_mode:
            print("Speak now")
            # Record audio from microphone
            duration_seconds = int(caller[1])
            numsamples = duration_seconds * 24000
            myrecording = sd.rec(numsamples, samplerate=24000, channels=1)
            sd.wait()

            # Write to file (soundfile already writes proper WAV format)
            sf.write(filename, myrecording, 24000)
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

    def process_dialog_file(self, filepath: str, record_mode: bool = False, output_file: str = 'vc.wav') -> str:
        """
        Process a dialog script file and generate audio.

        Args:
            filepath: Path to the dialog script file
            record_mode: If True, record caller audio from microphone
            output_file: Path for the final output file (default: vc.wav)

        Returns:
            Path to the final generated audio file
        """
        # Create temp directory if it doesn't exist
        os.makedirs(self.temp_dir, exist_ok=True)

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

        # Concatenate all audio files into final output using pydub
        self.concatenate_audio_files(self.final_audio, output_file)

        # Clean up temp directory
        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Could not clean up temp directory: {e}")

        return output_file

    def generate(self, filepath: str, record_mode: bool = False, output_file: str = 'vc.wav') -> str:
        """
        Generate a vision clip from a dialog script file.

        Args:
            filepath: Path to the dialog script file
            record_mode: If True, record caller audio from microphone
            output_file: Path for the final output file (default: vc.wav)

        Returns:
            Path to the final generated audio file
        """
        return self.process_dialog_file(filepath, record_mode, output_file)


def main():
    """Main entry point for command-line execution."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Generate vision clip audio from dialog scripts"
    )

    parser.add_argument("--file", metavar="<path>", help="Path to Vision Clip File", required=True)
    parser.add_argument("--record", action="store_true", help="Record customer side using microphone rather than TTS")
    parser.add_argument("--output", "-o", metavar="<path>", help="Output file path (default: vc.wav)", default="vc.wav")

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
    output_file = generator.generate(args.file, record_mode, args.output)

    print(f"\nGenerated vision clip: {output_file}")
    return 0


if __name__ == '__main__':
    exit(main())
