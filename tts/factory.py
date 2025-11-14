"""Factory for creating TTS provider instances.

The factory pattern allows runtime selection of TTS providers based on
configuration, with support for multiple configuration sources.
"""

from typing import Optional, Dict, Any
from tts.base import TTSProvider, TTSConfigurationError
from tts.config import TTSConfig, get_config


class TTSFactory:
    """
    Factory for creating TTS provider instances.

    Supports multiple configuration sources with precedence:
    1. Explicit constructor arguments
    2. Environment variables
    3. Configuration file
    4. Built-in defaults
    """

    # Registry of available providers
    _providers: Dict[str, type] = {}

    @classmethod
    def register_provider(cls, name: str, provider_class: type) -> None:
        """
        Register a TTS provider class.

        Args:
            name: Provider name (e.g., 'google', 'azure')
            provider_class: Provider class that implements TTSProvider

        Raises:
            ValueError: If provider is already registered
        """
        if name in cls._providers:
            raise ValueError(f"Provider '{name}' is already registered")

        cls._providers[name] = provider_class

    @classmethod
    def unregister_provider(cls, name: str) -> None:
        """
        Unregister a TTS provider.

        Args:
            name: Provider name to unregister
        """
        if name in cls._providers:
            del cls._providers[name]

    @classmethod
    def list_providers(cls) -> list[str]:
        """
        List all registered provider names.

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())

    @classmethod
    def create_provider(
        cls,
        provider: Optional[str] = None,
        config_file: Optional[str] = None,
        **kwargs
    ) -> TTSProvider:
        """
        Create a TTS provider instance.

        Configuration precedence (highest to lowest):
        1. Explicit kwargs
        2. Environment variables
        3. Config file
        4. Defaults

        Args:
            provider: Provider name (e.g., 'google', 'azure', 'elevenlabs', 'aws')
                     If None, uses TTS_PROVIDER env var or config, defaults to 'google'
            config_file: Path to YAML configuration file (optional)
            **kwargs: Additional configuration overrides

        Returns:
            Configured TTS provider instance

        Raises:
            TTSConfigurationError: If provider is not registered or configuration is invalid

        Examples:
            # Create with explicit provider
            provider = TTSFactory.create_provider('google', api_key='xxx')

            # Create from environment variables
            provider = TTSFactory.create_provider()

            # Create from config file
            provider = TTSFactory.create_provider(config_file='tts_config.yaml')

            # Create with mixed configuration
            provider = TTSFactory.create_provider(
                'elevenlabs',
                config_file='config.yaml',
                api_key='override_key'
            )
        """
        # Build configuration
        config = TTSConfig(config_file=config_file, **kwargs)

        # Determine provider name
        if provider is None:
            provider = config.get('provider', 'google')

        # Check if provider is registered
        if provider not in cls._providers:
            available = ', '.join(cls.list_providers())
            raise TTSConfigurationError(
                f"TTS provider '{provider}' is not registered. "
                f"Available providers: {available}"
            )

        # Get provider configuration
        provider_config = config.get_provider_config(provider)

        # Merge any direct kwargs that aren't configuration-related
        # This allows passing provider-specific params directly
        config_keys = {'provider', 'config_file'}
        for key, value in kwargs.items():
            if key not in config_keys and '.' not in key:
                # This is a provider-specific parameter
                provider_config[key] = value

        # Create provider instance
        provider_class = cls._providers[provider]
        try:
            instance = provider_class(**provider_config)
            return instance
        except Exception as e:
            raise TTSConfigurationError(
                f"Failed to create TTS provider '{provider}': {e}"
            ) from e

    @classmethod
    def create_google_provider(cls, **kwargs) -> TTSProvider:
        """
        Convenience method to create Google TTS provider.

        Args:
            **kwargs: Google TTS configuration

        Returns:
            Google TTS provider instance
        """
        return cls.create_provider('google', **kwargs)

    @classmethod
    def create_azure_provider(cls, **kwargs) -> TTSProvider:
        """
        Convenience method to create Azure TTS provider.

        Args:
            **kwargs: Azure TTS configuration

        Returns:
            Azure TTS provider instance
        """
        return cls.create_provider('azure', **kwargs)

    @classmethod
    def create_elevenlabs_provider(cls, **kwargs) -> TTSProvider:
        """
        Convenience method to create ElevenLabs TTS provider.

        Args:
            **kwargs: ElevenLabs TTS configuration

        Returns:
            ElevenLabs TTS provider instance
        """
        return cls.create_provider('elevenlabs', **kwargs)

    @classmethod
    def create_aws_provider(cls, **kwargs) -> TTSProvider:
        """
        Convenience method to create AWS Polly TTS provider.

        Args:
            **kwargs: AWS Polly TTS configuration

        Returns:
            AWS Polly TTS provider instance
        """
        return cls.create_provider('aws', **kwargs)


def create_tts_provider(
    provider: Optional[str] = None,
    config_file: Optional[str] = None,
    **kwargs
) -> TTSProvider:
    """
    Module-level convenience function to create a TTS provider.

    This is a simple wrapper around TTSFactory.create_provider() for
    easier imports and usage.

    Args:
        provider: Provider name
        config_file: Path to configuration file
        **kwargs: Configuration overrides

    Returns:
        Configured TTS provider instance

    Example:
        from tts.factory import create_tts_provider

        provider = create_tts_provider('google', api_key='xxx')
    """
    return TTSFactory.create_provider(provider, config_file, **kwargs)


# Auto-register built-in providers when module is imported
def _register_builtin_providers():
    """Register built-in TTS providers."""
    try:
        from tts.providers.google_tts import GoogleTTSProvider
        TTSFactory.register_provider('google', GoogleTTSProvider)
    except ImportError:
        pass

    try:
        from tts.providers.azure_tts import AzureTTSProvider
        TTSFactory.register_provider('azure', AzureTTSProvider)
    except ImportError:
        pass

    try:
        from tts.providers.elevenlabs_tts import ElevenLabsTTSProvider
        TTSFactory.register_provider('elevenlabs', ElevenLabsTTSProvider)
    except ImportError:
        pass

    try:
        from tts.providers.aws_polly import AWSPollyTTSProvider
        TTSFactory.register_provider('aws', AWSPollyTTSProvider)
    except ImportError:
        pass


# Register providers on module import
_register_builtin_providers()
