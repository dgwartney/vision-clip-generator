"""Google Cloud Text-to-Speech provider implementation."""

import base64
import requests
from typing import Optional
from tts.base import TTSProvider, TTSAPIError, TTSConfigurationError
from tts.capabilities import TTSCapabilities
from tts.features import AudioEffectsCapable


class GoogleTTSProvider(AudioEffectsCapable):
    """
    Google Cloud Text-to-Speech provider.

    Uses Google's TTS API with support for:
    - High-quality neural voices
    - Multiple languages and locales
    - Audio effects profiles (e.g., telephony-class-application)
    - Speaking rate and pitch control
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        va_voice: str = "en-US-Journey-O",
        va_locale: str = "en-US",
        caller_voice: str = "en-US-Journey-D",
        caller_locale: str = "en-US",
        **kwargs
    ):
        """
        Initialize Google TTS provider.

        Args:
            api_key: Google API key for TTS (required)
            va_voice: Default voice for virtual assistant
            va_locale: Default locale for virtual assistant
            caller_voice: Default voice for caller
            caller_locale: Default locale for caller
            **kwargs: Additional configuration (ignored)

        Raises:
            TTSConfigurationError: If API key is not provided
        """
        if not api_key:
            raise TTSConfigurationError(
                "Google TTS requires an API key. "
                "Set GOOGLE_API_KEY environment variable or pass api_key parameter."
            )

        self.api_key = api_key
        self.base_url = 'https://texttospeech.googleapis.com/v1beta1/text:synthesize'
        self.va_voice = va_voice
        self.va_locale = va_locale
        self.caller_voice = caller_voice
        self.caller_locale = caller_locale

        # Define capabilities
        self._capabilities = TTSCapabilities(
            supports_streaming=False,
            supports_ssml=True,
            supports_custom_voices=False,
            supported_audio_formats=["wav", "mp3", "ogg"],
            max_text_length=5000,
            max_requests_per_minute=None,
            supports_pitch_control=True,
            supports_rate_control=True,
            supports_volume_control=True,
            supports_audio_effects=True,
            requires_api_key=True,
        )

    @property
    def name(self) -> str:
        """Get provider name."""
        return "google"

    def get_capabilities(self) -> TTSCapabilities:
        """Get provider capabilities."""
        return self._capabilities

    def configure(self, **kwargs) -> None:
        """
        Configure the provider with additional settings.

        Args:
            **kwargs: Configuration options (api_key, va_voice, va_locale, etc.)
        """
        if 'api_key' in kwargs:
            self.api_key = kwargs['api_key']
        if 'va_voice' in kwargs:
            self.va_voice = kwargs['va_voice']
        if 'va_locale' in kwargs:
            self.va_locale = kwargs['va_locale']
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
        Synthesize text to speech audio using Google TTS.

        Args:
            text: Text to synthesize
            voice: Voice name (e.g., 'en-US-Journey-O')
            locale: Locale code (e.g., 'en-US')
            rate: Speaking rate (1.0 is normal)
            output_file: Optional path to write WAV file

        Returns:
            Raw audio bytes (LINEAR16 WAV format)

        Raises:
            TTSAPIError: If API request fails
        """
        return self._synthesize_internal(
            text=text,
            voice=voice,
            locale=locale,
            rate=rate,
            pitch=0,
            effects_profile="telephony-class-application",
            output_file=output_file
        )

    def synthesize_with_effects(
        self,
        text: str,
        voice: str,
        locale: str,
        rate: float = 1.0,
        effects_profile: str = None,
        output_file: str = None
    ) -> bytes:
        """
        Synthesize text with specific audio effects.

        Args:
            text: Text to synthesize
            voice: Voice name
            locale: Locale code
            rate: Speaking rate
            effects_profile: Effects profile ID (e.g., 'telephony-class-application')
            output_file: Optional path to write WAV file

        Returns:
            Raw audio bytes

        Raises:
            TTSAPIError: If API request fails
        """
        return self._synthesize_internal(
            text=text,
            voice=voice,
            locale=locale,
            rate=rate,
            pitch=0,
            effects_profile=effects_profile,
            output_file=output_file
        )

    def list_effects_profiles(self) -> list:
        """
        List available audio effects profiles.

        Returns:
            List of effects profile IDs
        """
        return [
            "telephony-class-application",
            "wearable-class-device",
            "handset-class-device",
            "headphone-class-device",
            "small-bluetooth-speaker-class-device",
            "medium-bluetooth-speaker-class-device",
            "large-home-entertainment-class-device",
            "large-automotive-class-device",
        ]

    def _synthesize_internal(
        self,
        text: str,
        voice: str,
        locale: str,
        rate: float,
        pitch: float,
        effects_profile: Optional[str],
        output_file: Optional[str]
    ) -> bytes:
        """
        Internal method to synthesize text with full control.

        Args:
            text: Text to synthesize
            voice: Voice name
            locale: Locale code
            rate: Speaking rate
            pitch: Pitch adjustment (-20.0 to 20.0)
            effects_profile: Effects profile ID
            output_file: Optional output file path

        Returns:
            Raw audio bytes

        Raises:
            TTSAPIError: If API request fails
        """
        url = f'{self.base_url}?alt=json&key={self.api_key}'
        headers = {'content-type': 'application/json'}

        # Build audio config
        audio_config = {
            "audioEncoding": "LINEAR16",
            "pitch": pitch,
            "speakingRate": rate
        }

        if effects_profile:
            audio_config["effectsProfileId"] = [effects_profile]

        # Build request payload
        payload = {
            "audioConfig": audio_config,
            "input": {
                "text": text
            },
            "voice": {
                "languageCode": locale,
                "name": voice
            }
        }

        # Make API request
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise TTSAPIError(f"Google TTS API request failed: {e}") from e

        # Parse response
        try:
            audio_json = response.json()
            audio_content = audio_json['audioContent']
            decoded_data = base64.b64decode(audio_content, ' /')
        except (KeyError, ValueError) as e:
            raise TTSAPIError(f"Failed to parse Google TTS API response: {e}") from e

        # Write to file if requested
        if output_file:
            try:
                with open(output_file, 'wb') as f:
                    f.write(decoded_data)
            except IOError as e:
                raise TTSAPIError(f"Failed to write audio file: {e}") from e

        return decoded_data
