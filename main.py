#!/usr/bin/env python3

from typing import Optional
import argparse
import logging
import os
import shutil
import signal
import sounddevice as sd
import soundfile as sf
import time
from pydub import AudioSegment

# Import TTS abstraction layer
from tts import create_tts_provider, TTSProvider

# Module-level logger
logger = logging.getLogger(__name__)


def setup_logging(
    console_level: str = 'INFO',
    log_file: Optional[str] = None,
    file_level: str = 'DEBUG'
) -> None:
    """
    Configure application logging with console and optional file output.

    Args:
        console_level: Logging level for console output (default: INFO)
        log_file: Path to log file. If None, no file logging. (default: None)
        file_level: Logging level for file output (default: DEBUG)
    """
    # Convert string levels to logging constants
    console_level_value = getattr(logging, console_level.upper(), logging.INFO)
    file_level_value = getattr(logging, file_level.upper(), logging.DEBUG)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all messages, handlers will filter

    # Remove any existing handlers
    root_logger.handlers = []

    # Console handler - user-friendly format
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level_value)
    console_format = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # File handler - detailed format (if log file specified)
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
            file_handler.setLevel(file_level_value)
            file_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_format)
            root_logger.addHandler(file_handler)
            logger.info(f"Logging to file: {log_file}")
        except Exception as e:
            logger.warning(f"Could not create log file {log_file}: {e}")


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
        keep_temp: bool = False,
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
            keep_temp: If True, preserve temporary audio files in .temp/ directory.
                      If False (default), clean up temp files after generation.
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
        self.keep_temp = keep_temp

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

        logger.info(f"Using TTS provider: {self.tts_provider.name}")
        logger.debug(f"Voice configuration: VA={self.va_voice}, Caller={self.caller_voice}")

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
        logger.info(line)
        text = ivr[1]
        filename = os.path.join(self.temp_dir, f'{self.fnum:03d}_va.wav')

        logger.debug(f"Synthesizing IVA audio to {filename}")
        self.text_to_wav(self.va_voice, 1, self.va_locale, text, filename)

        # Sleep to allow audio file to close
        time.sleep(1)

        # Play the audio using sounddevice
        logger.debug(f"Playing audio: {filename}")
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
        logger.info(line)
        text = caller[2]
        filename = os.path.join(self.temp_dir, f'{self.fnum:03d}_caller.wav')

        if record_mode:
            print("Speak now")  # Keep as print - user interaction prompt
            # Record audio from microphone
            duration_seconds = int(caller[1])
            logger.debug(f"Recording {duration_seconds}s of audio to {filename}")
            numsamples = duration_seconds * 24000
            myrecording = sd.rec(numsamples, samplerate=24000, channels=1)
            sd.wait()

            # Write to file (soundfile already writes proper WAV format)
            sf.write(filename, myrecording, 24000)
            logger.debug(f"Recording completed: {filename}")
        else:
            # Generate using TTS
            logger.debug(f"Synthesizing caller audio to {filename}")
            self.text_to_wav(self.caller_voice, 1, self.caller_locale, text, filename)

        self.final_audio += filename + ' '
        self.fnum += 1

    def process_special_tag(self, line: str) -> None:
        """
        Process special audio tags (backend, sendmail, transfer, text).

        Args:
            line: The line containing the special tag
        """
        logger.debug(f"Processing special tag: {line.strip()}")
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
        logger.info(f"Processing dialog file: {filepath}")

        # Create temp directory if it doesn't exist
        os.makedirs(self.temp_dir, exist_ok=True)
        logger.debug(f"Created temp directory: {self.temp_dir}")

        # Reset state
        self.ignore = True
        self.fnum = 1
        self.final_audio = ''

        with open(filepath, 'r') as vfile:
            for line in vfile:
                if self.ignore:
                    if line.startswith('<ringback>'):
                        logger.info("Starting dialog processing at <ringback> tag")
                        self.ignore = False
                        self.final_audio = ' audio/ringback.wav '
                else:
                    if line.startswith('<hangup>'):
                        logger.info("Dialog processing completed at <hangup> tag")
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
        num_segments = len(self.final_audio.split())
        logger.info(f"Concatenating {num_segments} audio segments into {output_file}")
        try:
            self.concatenate_audio_files(self.final_audio, output_file)
        except (PermissionError, OSError) as e:
            logger.error(f"Failed to write output file '{output_file}'")
            logger.error(f"Error: {e}")
            logger.error(f"Solution: Check permissions or choose a different output path")
            raise

        # Clean up temp directory (unless --keep-temp flag is set)
        if not self.keep_temp:
            try:
                shutil.rmtree(self.temp_dir)
                logger.debug(f"Removed temp directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Could not clean up temp directory: {e}")
        else:
            logger.info(f"Temporary files preserved in: {self.temp_dir}/")

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
    parser.add_argument("--output", "-o", metavar="<path>", help="Output file path (default: basename of input file with .wav extension)", default="vc.wav")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary audio files in .temp/ directory")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help="Set console logging level (default: INFO)")
    parser.add_argument("--log-file", nargs='?', const='vision-clip.log', metavar="<path>", help="Enable file logging. Optionally specify path (default: vision-clip.log)")
    parser.add_argument("--log-file-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='DEBUG', help="Set file logging level (default: DEBUG)")

    args = parser.parse_args()

    # Configure logging
    setup_logging(
        console_level=args.log_level,
        log_file=args.log_file,
        file_level=args.log_file_level
    )

    # Smart default output path: use basename of input file if output not explicitly set
    if args.output == "vc.wav":  # User didn't specify custom output
        input_basename = os.path.basename(args.file)
        input_name, _ = os.path.splitext(input_basename)
        args.output = f"{input_name}.wav"

    # Validate output directory
    output_dir = os.path.dirname(args.output)
    if output_dir:  # Only if output path includes a directory
        if not os.path.exists(output_dir):
            # Check if we have permission to create the directory
            # Find the first existing parent directory to check permissions
            parent_dir = output_dir
            while parent_dir and not os.path.exists(parent_dir):
                parent_dir = os.path.dirname(parent_dir)

            # Handle empty parent_dir (happens with relative paths like "output")
            if not parent_dir:
                parent_dir = '.'  # Current working directory

            # If we don't have write permission
            if not os.access(parent_dir, os.W_OK):
                logger.error(f"Cannot create output directory '{output_dir}'")
                logger.error(f"Reason: No write permission in parent directory '{os.path.abspath(parent_dir)}'")
                logger.error(f"Solution: Either:")
                logger.error(f"  1. Choose a different output path with --output <path>")
                logger.error(f"  2. Create the directory manually: mkdir -p {output_dir}")
                logger.error(f"  3. Fix permissions: chmod +w {os.path.abspath(parent_dir)}")
                return 1

            # Prompt user before creating directory
            print(f"\nOutput directory does not exist: {output_dir}")
            response = input(f"Create directory? (y/n): ").strip().lower()
            if response != 'y':
                logger.info("Directory creation cancelled by user")
                return 1

            # Create the directory
            try:
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"Created output directory: {output_dir}")
            except (PermissionError, OSError) as e:
                logger.error(f"Failed to create output directory '{output_dir}'")
                logger.error(f"Error: {e}")
                logger.error(f"Solution: Create the directory manually or choose a different path")
                return 1

    logger.info(f"Vision Clip Generator starting")
    logger.debug(f"Input file: {args.file}")
    logger.debug(f"Output file: {args.output}")
    logger.debug(f"Record mode: {args.record}")
    logger.debug(f"Keep temp files: {args.keep_temp}")

    # Create generator instance
    try:
        generator = VisionClipGenerator(keep_temp=args.keep_temp)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please set GOOGLE_API_KEY environment variable")
        return 1

    # Process the dialog file
    record_mode = args.record
    output_file = generator.generate(args.file, record_mode, args.output)

    logger.info(f"Generated vision clip: {output_file}")
    return 0


if __name__ == '__main__':
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n\nExiting...")
        exit(130)  # Unix convention: 128 + signal number (SIGINT=2) for signal-terminated processes
