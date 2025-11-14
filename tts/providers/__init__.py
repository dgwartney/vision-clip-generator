"""TTS provider implementations.

This package contains concrete implementations of the TTSProvider interface
for various TTS services.
"""

__all__ = []

# Import providers that are available
try:
    from tts.providers.google_tts import GoogleTTSProvider
    __all__.append('GoogleTTSProvider')
except ImportError:
    pass

try:
    from tts.providers.azure_tts import AzureTTSProvider
    __all__.append('AzureTTSProvider')
except ImportError:
    pass

try:
    from tts.providers.elevenlabs_tts import ElevenLabsTTSProvider
    __all__.append('ElevenLabsTTSProvider')
except ImportError:
    pass

try:
    from tts.providers.aws_polly import AWSPollyTTSProvider
    __all__.append('AWSPollyTTSProvider')
except ImportError:
    pass
