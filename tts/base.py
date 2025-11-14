"""Base TTS provider interface and protocols."""

from typing import Protocol, runtime_checkable
from tts.capabilities import TTSCapabilities


@runtime_checkable
class TTSProvider(Protocol):
    """
    Base protocol for all TTS providers.

    All TTS providers must implement this interface to be compatible
    with the VisionClipGenerator.
    """

    def synthesize(
        self,
        text: str,
        voice: str,
        locale: str,
        rate: float = 1.0,
        output_file: str = None
    ) -> bytes:
        """
        Synthesize text to speech audio.

        Args:
            text: The text to synthesize
            voice: Voice identifier (provider-specific)
            locale: Locale code (e.g., 'en-US')
            rate: Speaking rate (1.0 is normal speed)
            output_file: Optional path to write audio file

        Returns:
            Raw audio bytes (WAV format)

        Raises:
            TTSProviderError: If synthesis fails
        """
        ...

    def get_capabilities(self) -> TTSCapabilities:
        """
        Get the capabilities supported by this provider.

        Returns:
            TTSCapabilities object describing what this provider supports
        """
        ...

    def configure(self, **kwargs) -> None:
        """
        Configure the provider with additional settings.

        Args:
            **kwargs: Provider-specific configuration options
        """
        ...

    @property
    def name(self) -> str:
        """
        Get the provider name.

        Returns:
            Provider name (e.g., 'google', 'azure', 'elevenlabs')
        """
        ...


class TTSProviderError(Exception):
    """Base exception for TTS provider errors."""
    pass


class TTSConfigurationError(TTSProviderError):
    """Exception raised for configuration errors."""
    pass


class TTSAPIError(TTSProviderError):
    """Exception raised for API errors."""
    pass


class TTSRateLimitError(TTSAPIError):
    """Exception raised when API rate limit is exceeded."""
    pass
