"""Optional feature interfaces for TTS providers.

These protocols define optional capabilities that providers may implement.
Code can use isinstance() checks to determine if a provider supports
advanced features at runtime.
"""

from typing import Protocol, Iterator, runtime_checkable


@runtime_checkable
class StreamingCapable(Protocol):
    """
    Protocol for providers that support streaming audio generation.

    Streaming allows audio to be generated and played incrementally
    rather than waiting for the complete synthesis.
    """

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
            text: The text to synthesize
            voice: Voice identifier (provider-specific)
            locale: Locale code (e.g., 'en-US')
            rate: Speaking rate (1.0 is normal speed)
            chunk_size: Size of audio chunks in bytes

        Yields:
            Audio chunks as bytes (WAV format)

        Raises:
            TTSProviderError: If synthesis fails
        """
        ...


@runtime_checkable
class SSMLCapable(Protocol):
    """
    Protocol for providers that support SSML (Speech Synthesis Markup Language).

    SSML allows fine-grained control over speech output including:
    - Pronunciation and phonetics
    - Prosody (pitch, rate, volume)
    - Emphasis and breaks
    - Say-as (dates, numbers, etc.)
    """

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
            ssml: SSML markup string (must include <speak> root element)
            voice: Voice identifier (provider-specific)
            locale: Locale code (e.g., 'en-US')
            output_file: Optional path to write audio file

        Returns:
            Raw audio bytes (WAV format)

        Raises:
            TTSProviderError: If synthesis fails
            ValueError: If SSML is malformed
        """
        ...

    def validate_ssml(self, ssml: str) -> bool:
        """
        Validate SSML markup before synthesis.

        Args:
            ssml: SSML markup string to validate

        Returns:
            True if valid, False otherwise
        """
        ...


@runtime_checkable
class CustomVoiceCapable(Protocol):
    """
    Protocol for providers that support custom voice IDs.

    This includes voice cloning services like ElevenLabs where users
    can create custom voices and reference them by ID.
    """

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
            text: The text to synthesize
            voice_id: Custom voice identifier (e.g., cloned voice ID)
            locale: Locale code (optional for some providers)
            rate: Speaking rate (1.0 is normal speed)
            output_file: Optional path to write audio file
            **voice_settings: Provider-specific voice settings

        Returns:
            Raw audio bytes (WAV format)

        Raises:
            TTSProviderError: If synthesis fails
            ValueError: If voice_id is invalid
        """
        ...

    def list_custom_voices(self) -> list:
        """
        List available custom voices for this account.

        Returns:
            List of voice dictionaries with 'id' and 'name' keys

        Raises:
            TTSProviderError: If API call fails
        """
        ...


@runtime_checkable
class AudioEffectsCapable(Protocol):
    """
    Protocol for providers that support audio effects.

    This includes effects profiles like telephony enhancement,
    studio quality, or specific acoustic environments.
    """

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
            text: The text to synthesize
            voice: Voice identifier
            locale: Locale code (e.g., 'en-US')
            rate: Speaking rate (1.0 is normal speed)
            effects_profile: Effects profile ID (provider-specific)
            output_file: Optional path to write audio file

        Returns:
            Raw audio bytes (WAV format)

        Raises:
            TTSProviderError: If synthesis fails
        """
        ...

    def list_effects_profiles(self) -> list:
        """
        List available audio effects profiles.

        Returns:
            List of effects profile names/IDs

        Raises:
            TTSProviderError: If API call fails
        """
        ...


@runtime_checkable
class VolumeControlCapable(Protocol):
    """
    Protocol for providers that support volume control.
    """

    def synthesize_with_volume(
        self,
        text: str,
        voice: str,
        locale: str,
        rate: float = 1.0,
        volume: float = 1.0,
        output_file: str = None
    ) -> bytes:
        """
        Synthesize text with specific volume level.

        Args:
            text: The text to synthesize
            voice: Voice identifier
            locale: Locale code (e.g., 'en-US')
            rate: Speaking rate (1.0 is normal speed)
            volume: Volume level (0.0 to 2.0, 1.0 is normal)
            output_file: Optional path to write audio file

        Returns:
            Raw audio bytes (WAV format)

        Raises:
            TTSProviderError: If synthesis fails
        """
        ...


# Helper function for feature detection
def has_feature(provider, feature_protocol) -> bool:
    """
    Check if a provider implements a specific feature protocol.

    Args:
        provider: TTS provider instance
        feature_protocol: Protocol class to check (e.g., StreamingCapable)

    Returns:
        True if provider implements the protocol, False otherwise

    Example:
        if has_feature(provider, StreamingCapable):
            for chunk in provider.synthesize_stream(text, voice, locale):
                play_audio(chunk)
    """
    return isinstance(provider, feature_protocol)
