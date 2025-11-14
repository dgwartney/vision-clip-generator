"""TTS abstraction layer for Vision Clip Generator.

This module provides a flexible TTS abstraction that supports multiple
TTS providers (Google, Azure, ElevenLabs, AWS) with a unified interface.

Basic usage:
    from tts import create_tts_provider

    # Create provider from environment variables
    provider = create_tts_provider()

    # Synthesize text
    audio_bytes = provider.synthesize(
        text="Hello world",
        voice="en-US-Journey-O",
        locale="en-US",
        output_file="hello.wav"
    )

Advanced usage:
    from tts import TTSFactory

    # Create specific provider with config
    provider = TTSFactory.create_provider(
        'google',
        api_key='your-api-key',
        va_voice='en-US-Journey-O'
    )

    # Check capabilities
    caps = provider.get_capabilities()
    if caps.supports_streaming:
        for chunk in provider.synthesize_stream(...):
            play_audio(chunk)
"""

from tts.base import (
    TTSProvider,
    TTSProviderError,
    TTSConfigurationError,
    TTSAPIError,
    TTSRateLimitError,
)
from tts.capabilities import TTSCapabilities
from tts.config import TTSConfig, get_config, reset_config
from tts.factory import TTSFactory, create_tts_provider
from tts.features import (
    StreamingCapable,
    SSMLCapable,
    CustomVoiceCapable,
    AudioEffectsCapable,
    VolumeControlCapable,
    has_feature,
)

__all__ = [
    # Base classes
    'TTSProvider',
    'TTSProviderError',
    'TTSConfigurationError',
    'TTSAPIError',
    'TTSRateLimitError',
    # Capabilities
    'TTSCapabilities',
    # Configuration
    'TTSConfig',
    'get_config',
    'reset_config',
    # Factory
    'TTSFactory',
    'create_tts_provider',
    # Features
    'StreamingCapable',
    'SSMLCapable',
    'CustomVoiceCapable',
    'AudioEffectsCapable',
    'VolumeControlCapable',
    'has_feature',
]

__version__ = '0.1.0'
