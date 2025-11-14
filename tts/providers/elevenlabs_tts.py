"""ElevenLabs Text-to-Speech provider implementation."""

import requests
from typing import Optional, Iterator
from tts.base import TTSProvider, TTSAPIError, TTSConfigurationError, TTSRateLimitError
from tts.capabilities import TTSCapabilities
from tts.features import CustomVoiceCapable, StreamingCapable


class ElevenLabsTTSProvider(CustomVoiceCapable, StreamingCapable):
    """
    ElevenLabs Text-to-Speech provider.

    Uses ElevenLabs' API with support for:
    - High-quality voice cloning
    - Custom voice IDs
    - Multiple voice models
    - Streaming audio generation
    - Emotional and expressive speech

    Requires: API key from elevenlabs.io
    """

    # API endpoints
    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        va_voice: Optional[str] = None,
        caller_voice: Optional[str] = None,
        model: str = "eleven_monolingual_v1",
        **kwargs
    ):
        """
        Initialize ElevenLabs TTS provider.

        Args:
            api_key: ElevenLabs API key (required)
            va_voice: Voice ID for virtual assistant (required)
            caller_voice: Voice ID for caller (required)
            model: Model ID to use (default: 'eleven_monolingual_v1')
                   Options: 'eleven_monolingual_v1', 'eleven_multilingual_v1',
                           'eleven_multilingual_v2'
            **kwargs: Additional configuration (ignored)

        Raises:
            TTSConfigurationError: If API key or voice IDs are not provided
        """
        if not api_key:
            raise TTSConfigurationError(
                "ElevenLabs TTS requires an API key. "
                "Set ELEVENLABS_API_KEY environment variable or pass api_key parameter."
            )

        if not va_voice:
            raise TTSConfigurationError(
                "ElevenLabs TTS requires va_voice (voice ID for virtual assistant). "
                "Set ELEVENLABS_VA_VOICE environment variable or pass va_voice parameter."
            )

        if not caller_voice:
            raise TTSConfigurationError(
                "ElevenLabs TTS requires caller_voice (voice ID for caller). "
                "Set ELEVENLABS_CALLER_VOICE environment variable or pass caller_voice parameter."
            )

        self.api_key = api_key
        self.va_voice = va_voice
        self.caller_voice = caller_voice
        self.model = model

        # Headers for API requests
        self.headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }

        # Define capabilities
        self._capabilities = TTSCapabilities(
            supports_streaming=True,
            supports_ssml=False,  # ElevenLabs doesn't support SSML
            supports_custom_voices=True,
            supported_audio_formats=["mp3", "wav"],
            max_text_length=5000,
            max_requests_per_minute=None,  # Varies by tier
            supports_pitch_control=False,
            supports_rate_control=False,
            supports_volume_control=False,
            requires_api_key=True,
        )

    @property
    def name(self) -> str:
        """Get provider name."""
        return "elevenlabs"

    def get_capabilities(self) -> TTSCapabilities:
        """Get provider capabilities."""
        return self._capabilities

    def configure(self, **kwargs) -> None:
        """
        Configure the provider with additional settings.

        Args:
            **kwargs: Configuration options
        """
        if 'api_key' in kwargs:
            self.api_key = kwargs['api_key']
            self.headers["xi-api-key"] = self.api_key
        if 'va_voice' in kwargs:
            self.va_voice = kwargs['va_voice']
        if 'caller_voice' in kwargs:
            self.caller_voice = kwargs['caller_voice']
        if 'model' in kwargs:
            self.model = kwargs['model']

    def synthesize(
        self,
        text: str,
        voice: str,
        locale: str,
        rate: float = 1.0,
        output_file: str = None
    ) -> bytes:
        """
        Synthesize text to speech audio using ElevenLabs TTS.

        Args:
            text: Text to synthesize
            voice: Voice ID (not voice name - use custom voice ID)
            locale: Locale code (ignored - ElevenLabs auto-detects language)
            rate: Speaking rate (ignored - not supported by ElevenLabs)
            output_file: Optional path to write audio file

        Returns:
            Raw audio bytes (MP3 format)

        Raises:
            TTSAPIError: If API request fails
        """
        return self.synthesize_with_voice_id(
            text=text,
            voice_id=voice,
            output_file=output_file
        )

    def synthesize_with_voice_id(
        self,
        text: str,
        voice_id: str,
        locale: str = None,
        rate: float = 1.0,
        output_file: str = None,
        **voice_settings
    ) -> bytes:
        """
        Synthesize text using a custom voice ID.

        Args:
            text: Text to synthesize
            voice_id: ElevenLabs voice ID
            locale: Locale code (ignored)
            rate: Speaking rate (ignored)
            output_file: Optional path to write audio file
            **voice_settings: Voice settings (stability, similarity_boost, style, use_speaker_boost)

        Returns:
            Raw audio bytes (MP3 format)

        Raises:
            TTSAPIError: If synthesis fails
        """
        url = f"{self.BASE_URL}/text-to-speech/{voice_id}"

        # Default voice settings
        default_settings = {
            "stability": 0.5,
            "similarity_boost": 0.75,
        }
        default_settings.update(voice_settings)

        # Build request payload
        payload = {
            "text": text,
            "model_id": self.model,
            "voice_settings": default_settings
        }

        try:
            response = requests.post(url, json=payload, headers=self.headers)

            # Check for rate limiting
            if response.status_code == 429:
                raise TTSRateLimitError("ElevenLabs API rate limit exceeded")

            response.raise_for_status()
            audio_bytes = response.content

        except TTSRateLimitError:
            raise
        except requests.exceptions.RequestException as e:
            raise TTSAPIError(f"ElevenLabs TTS API request failed: {e}") from e

        # Write to file if requested
        if output_file:
            try:
                # Convert MP3 to WAV if needed
                if output_file.endswith('.wav'):
                    # For now, just write MP3 and note that conversion is needed
                    # In production, you'd use pydub or similar to convert
                    with open(output_file, 'wb') as f:
                        f.write(audio_bytes)
                else:
                    with open(output_file, 'wb') as f:
                        f.write(audio_bytes)
            except IOError as e:
                raise TTSAPIError(f"Failed to write audio file: {e}") from e

        return audio_bytes

    def synthesize_stream(
        self,
        text: str,
        voice: str,
        locale: str,
        rate: float = 1.0,
        chunk_size: int = 4096
    ) -> Iterator[bytes]:
        """
        Synthesize text to speech as a stream of audio chunks.

        Args:
            text: Text to synthesize
            voice: Voice ID
            locale: Locale code (ignored)
            rate: Speaking rate (ignored)
            chunk_size: Size of audio chunks in bytes

        Yields:
            Audio chunks as bytes (MP3 format)

        Raises:
            TTSAPIError: If synthesis fails
        """
        url = f"{self.BASE_URL}/text-to-speech/{voice}/stream"

        payload = {
            "text": text,
            "model_id": self.model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            }
        }

        try:
            response = requests.post(url, json=payload, headers=self.headers, stream=True)

            # Check for rate limiting
            if response.status_code == 429:
                raise TTSRateLimitError("ElevenLabs API rate limit exceeded")

            response.raise_for_status()

            # Stream the response
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    yield chunk

        except TTSRateLimitError:
            raise
        except requests.exceptions.RequestException as e:
            raise TTSAPIError(f"ElevenLabs TTS streaming failed: {e}") from e

    def list_custom_voices(self) -> list:
        """
        List available custom voices for this account.

        Returns:
            List of voice dictionaries with 'id' and 'name' keys

        Raises:
            TTSAPIError: If API call fails
        """
        url = f"{self.BASE_URL}/voices"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            voices = []
            for voice in data.get('voices', []):
                voices.append({
                    'id': voice['voice_id'],
                    'name': voice['name'],
                    'category': voice.get('category', 'custom'),
                    'labels': voice.get('labels', {}),
                })

            return voices

        except requests.exceptions.RequestException as e:
            raise TTSAPIError(f"Failed to list ElevenLabs voices: {e}") from e
