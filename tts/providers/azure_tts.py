"""Azure Cognitive Services Text-to-Speech provider implementation."""

import time
from typing import Optional
from tts.base import TTSProvider, TTSAPIError, TTSConfigurationError
from tts.capabilities import TTSCapabilities
from tts.features import SSMLCapable

try:
    from azure.cognitiveservices.speech import (
        SpeechConfig,
        SpeechSynthesizer,
        SpeechSynthesisOutputFormat
    )
    from azure.cognitiveservices.speech.audio import AudioOutputConfig
    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False


class AzureTTSProvider(SSMLCapable):
    """
    Azure Cognitive Services Text-to-Speech provider.

    Uses Azure's Speech SDK with support for:
    - Neural voices
    - Multiple languages and locales
    - SSML (Speech Synthesis Markup Language)
    - Speaking rate and pitch control

    Requires: azure-cognitiveservices-speech package
    """

    def __init__(
        self,
        subscription_key: Optional[str] = None,
        region: str = "eastus",
        va_voice: str = "en-US-JennyNeural",
        va_locale: str = "en-US",
        caller_voice: str = "en-US-GuyNeural",
        caller_locale: str = "en-US",
        **kwargs
    ):
        """
        Initialize Azure TTS provider.

        Args:
            subscription_key: Azure subscription key (required)
            region: Azure region (e.g., 'eastus', 'westus')
            va_voice: Default voice for virtual assistant
            va_locale: Default locale for virtual assistant
            caller_voice: Default voice for caller
            caller_locale: Default locale for caller
            **kwargs: Additional configuration (ignored)

        Raises:
            TTSConfigurationError: If Azure SDK is not available or subscription key is missing
        """
        if not AZURE_SDK_AVAILABLE:
            raise TTSConfigurationError(
                "Azure TTS provider requires azure-cognitiveservices-speech package. "
                "Install with: pip install azure-cognitiveservices-speech"
            )

        if not subscription_key:
            raise TTSConfigurationError(
                "Azure TTS requires a subscription key. "
                "Set AZURE_SUBSCRIPTION_KEY environment variable or pass subscription_key parameter."
            )

        self.subscription_key = subscription_key
        self.region = region
        self.va_voice = va_voice
        self.va_locale = va_locale
        self.caller_voice = caller_voice
        self.caller_locale = caller_locale

        # Create speech config
        self.speech_config = SpeechConfig(
            subscription=self.subscription_key,
            region=self.region
        )
        self.speech_config.speech_synthesis_language = self.va_locale
        self.speech_config.speech_synthesis_voice_name = self.va_voice

        # Define capabilities
        self._capabilities = TTSCapabilities(
            supports_streaming=False,
            supports_ssml=True,
            supports_custom_voices=False,
            supported_audio_formats=["wav", "mp3"],
            max_text_length=None,  # Azure has no documented limit
            max_requests_per_minute=20,  # Varies by tier
            supports_pitch_control=True,
            supports_rate_control=True,
            supports_volume_control=True,
            requires_api_key=True,
        )

    @property
    def name(self) -> str:
        """Get provider name."""
        return "azure"

    def get_capabilities(self) -> TTSCapabilities:
        """Get provider capabilities."""
        return self._capabilities

    def configure(self, **kwargs) -> None:
        """
        Configure the provider with additional settings.

        Args:
            **kwargs: Configuration options
        """
        if 'subscription_key' in kwargs:
            self.subscription_key = kwargs['subscription_key']
            self.speech_config = SpeechConfig(
                subscription=self.subscription_key,
                region=self.region
            )
        if 'region' in kwargs:
            self.region = kwargs['region']
        if 'va_voice' in kwargs:
            self.va_voice = kwargs['va_voice']
            self.speech_config.speech_synthesis_voice_name = self.va_voice
        if 'va_locale' in kwargs:
            self.va_locale = kwargs['va_locale']
            self.speech_config.speech_synthesis_language = self.va_locale
        if 'caller_voice' in kwargs:
            self.caller_voice = kwargs['caller_voice']
        if 'caller_locale' in kwargs:
            self.caller_locale = kwargs['caller_locale']

    def synthesize(
        self,
        text: str,
        voice: str,
        locale: str,
        rate: float = 1.0,
        output_file: str = None
    ) -> bytes:
        """
        Synthesize text to speech audio using Azure TTS.

        Args:
            text: Text to synthesize
            voice: Voice name (e.g., 'en-US-JennyNeural')
            locale: Locale code (e.g., 'en-US')
            rate: Speaking rate (1.0 is normal) - applied via SSML if not 1.0
            output_file: Optional path to write WAV file

        Returns:
            Raw audio bytes (WAV format)

        Raises:
            TTSAPIError: If synthesis fails
        """
        # If rate is not 1.0, use SSML to apply rate
        if rate != 1.0:
            # Convert rate to percentage (0.5 -> 50%, 1.0 -> 100%, 2.0 -> 200%)
            rate_percent = f"{int(rate * 100)}%"
            ssml = (
                f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{locale}">'
                f'<voice name="{voice}">'
                f'<prosody rate="{rate_percent}">{text}</prosody>'
                f'</voice>'
                f'</speak>'
            )
            return self.synthesize_ssml(ssml, voice, locale, output_file)

        return self._synthesize_text(text, voice, locale, output_file)

    def _synthesize_text(
        self,
        text: str,
        voice: str,
        locale: str,
        output_file: Optional[str]
    ) -> bytes:
        """
        Internal method to synthesize plain text.

        Args:
            text: Text to synthesize
            voice: Voice name
            locale: Locale code
            output_file: Optional output file path

        Returns:
            Raw audio bytes

        Raises:
            TTSAPIError: If synthesis fails
        """
        try:
            # Create a new config for this specific synthesis
            speech_config = SpeechConfig(
                subscription=self.subscription_key,
                region=self.region
            )
            speech_config.speech_synthesis_language = locale
            speech_config.speech_synthesis_voice_name = voice

            if output_file:
                # Synthesize to file
                audio_config = AudioOutputConfig(filename=output_file)
                synthesizer = SpeechSynthesizer(
                    speech_config=speech_config,
                    audio_config=audio_config
                )
                result = synthesizer.speak_text_async(text).get()

                # Wait for file to be written
                time.sleep(1)

                # Read file and return bytes
                with open(output_file, 'rb') as f:
                    return f.read()
            else:
                # Synthesize to memory
                synthesizer = SpeechSynthesizer(
                    speech_config=speech_config,
                    audio_config=None
                )
                result = synthesizer.speak_text_async(text).get()

                if result.audio_data:
                    return result.audio_data
                else:
                    raise TTSAPIError(f"Azure TTS synthesis failed: {result.reason}")

        except Exception as e:
            raise TTSAPIError(f"Azure TTS synthesis failed: {e}") from e

    def synthesize_ssml(
        self,
        ssml: str,
        voice: str,
        locale: str,
        output_file: str = None
    ) -> bytes:
        """
        Synthesize SSML markup to speech audio.

        Args:
            ssml: SSML markup string
            voice: Voice name (may be overridden by SSML)
            locale: Locale code (may be overridden by SSML)
            output_file: Optional path to write WAV file

        Returns:
            Raw audio bytes (WAV format)

        Raises:
            TTSAPIError: If synthesis fails
        """
        try:
            # Create a new config for this specific synthesis
            speech_config = SpeechConfig(
                subscription=self.subscription_key,
                region=self.region
            )
            speech_config.speech_synthesis_language = locale
            speech_config.speech_synthesis_voice_name = voice

            if output_file:
                # Synthesize to file
                audio_config = AudioOutputConfig(filename=output_file)
                synthesizer = SpeechSynthesizer(
                    speech_config=speech_config,
                    audio_config=audio_config
                )
                result = synthesizer.speak_ssml_async(ssml).get()

                # Wait for file to be written
                time.sleep(1)

                # Read file and return bytes
                with open(output_file, 'rb') as f:
                    return f.read()
            else:
                # Synthesize to memory
                synthesizer = SpeechSynthesizer(
                    speech_config=speech_config,
                    audio_config=None
                )
                result = synthesizer.speak_ssml_async(ssml).get()

                if result.audio_data:
                    return result.audio_data
                else:
                    raise TTSAPIError(f"Azure TTS SSML synthesis failed: {result.reason}")

        except Exception as e:
            raise TTSAPIError(f"Azure TTS SSML synthesis failed: {e}") from e

    def validate_ssml(self, ssml: str) -> bool:
        """
        Validate SSML markup.

        Args:
            ssml: SSML markup string to validate

        Returns:
            True if valid (basic check only)
        """
        # Basic validation: check for <speak> root element
        return '<speak' in ssml and '</speak>' in ssml
