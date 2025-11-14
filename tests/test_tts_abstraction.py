"""Tests for the TTS abstraction layer."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import tempfile

from tts import (
    TTSFactory,
    TTSConfig,
    TTSProvider,
    TTSConfigurationError,
    TTSAPIError,
    create_tts_provider,
    has_feature,
)
from tts.capabilities import TTSCapabilities
from tts.features import StreamingCapable, SSMLCapable, CustomVoiceCapable
from tts.providers.google_tts import GoogleTTSProvider


class TestTTSCapabilities:
    """Test TTSCapabilities class."""

    def test_capabilities_initialization(self):
        """Test capabilities initialization with defaults."""
        caps = TTSCapabilities()
        assert caps.supports_streaming is False
        assert caps.supports_ssml is False
        assert caps.supports_custom_voices is False
        assert caps.supported_audio_formats == ["wav"]

    def test_capabilities_custom_values(self):
        """Test capabilities with custom values."""
        caps = TTSCapabilities(
            supports_streaming=True,
            supports_ssml=True,
            max_text_length=1000
        )
        assert caps.supports_streaming is True
        assert caps.supports_ssml is True
        assert caps.max_text_length == 1000

    def test_has_feature(self):
        """Test has_feature method."""
        caps = TTSCapabilities(supports_streaming=True, supports_ssml=True)
        assert caps.has_feature("streaming") is True
        assert caps.has_feature("ssml") is True
        assert caps.has_feature("custom_voices") is False
        assert caps.has_feature("unknown") is False


class TestTTSConfig:
    """Test TTSConfig class."""

    def test_config_defaults(self):
        """Test configuration with default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = TTSConfig()
            assert config.get('provider') == 'google'
            assert config.get('google.api_key') is None
            assert config.get('google.va_voice') == 'en-US-Journey-O'

    def test_config_overrides(self):
        """Test configuration with overrides."""
        config = TTSConfig(provider='azure', google={'api_key': 'test-key'})
        assert config.get('provider') == 'azure'
        assert config.get('google.api_key') == 'test-key'

    def test_config_env_vars(self):
        """Test configuration from environment variables."""
        with patch.dict(os.environ, {
            'TTS_PROVIDER': 'elevenlabs',
            'GOOGLE_API_KEY': 'env-key'
        }):
            config = TTSConfig()
            assert config.get('provider') == 'elevenlabs'
            assert config.get('google.api_key') == 'env-key'

    def test_config_file_loading(self):
        """Test configuration from YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("provider: aws\n")
            f.write("google:\n")
            f.write("  api_key: file-key\n")
            config_file = f.name

        try:
            with patch.dict(os.environ, {}, clear=True):
                config = TTSConfig(config_file=config_file)
                assert config.get('provider') == 'aws'
                assert config.get('google.api_key') == 'file-key'
        finally:
            os.unlink(config_file)

    def test_config_precedence(self):
        """Test configuration precedence: overrides > env > file > defaults."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("provider: azure\n")
            config_file = f.name

        try:
            with patch.dict(os.environ, {'TTS_PROVIDER': 'aws'}):
                # File says azure, env says aws, override says google
                config = TTSConfig(config_file=config_file, provider='google')
                # Override should win
                assert config.get('provider') == 'google'
        finally:
            os.unlink(config_file)

    def test_get_provider_config(self):
        """Test getting provider-specific configuration."""
        config = TTSConfig(google={'api_key': 'test-key', 'va_voice': 'test-voice'})
        provider_config = config.get_provider_config('google')
        assert provider_config['api_key'] == 'test-key'
        assert provider_config['va_voice'] == 'test-voice'


class TestTTSFactory:
    """Test TTSFactory class."""

    def test_register_provider(self):
        """Test registering a custom provider."""
        class MockProvider:
            pass

        TTSFactory.register_provider('mock', MockProvider)
        assert 'mock' in TTSFactory.list_providers()

        # Cleanup
        TTSFactory.unregister_provider('mock')

    def test_register_duplicate_provider(self):
        """Test registering a duplicate provider raises error."""
        class MockProvider:
            pass

        TTSFactory.register_provider('mock', MockProvider)
        try:
            with pytest.raises(ValueError, match="already registered"):
                TTSFactory.register_provider('mock', MockProvider)
        finally:
            TTSFactory.unregister_provider('mock')

    def test_list_providers(self):
        """Test listing available providers."""
        providers = TTSFactory.list_providers()
        assert 'google' in providers

    def test_create_google_provider(self):
        """Test creating Google TTS provider."""
        with patch.dict(os.environ, {}, clear=True):
            provider = TTSFactory.create_provider('google', api_key='test-key')
            assert isinstance(provider, GoogleTTSProvider)
            assert provider.name == 'google'
            assert provider.api_key == 'test-key'

    def test_create_provider_without_name(self):
        """Test creating provider without specifying name (uses default)."""
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            provider = TTSFactory.create_provider()
            assert provider.name == 'google'

    def test_create_unknown_provider(self):
        """Test creating unknown provider raises error."""
        with pytest.raises(TTSConfigurationError, match="not registered"):
            TTSFactory.create_provider('unknown-provider')

    def test_convenience_methods(self):
        """Test factory convenience methods."""
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
            provider = TTSFactory.create_google_provider()
            assert provider.name == 'google'


class TestGoogleTTSProvider:
    """Test GoogleTTSProvider class."""

    def test_initialization_with_api_key(self):
        """Test provider initialization with API key."""
        provider = GoogleTTSProvider(api_key='test-key')
        assert provider.api_key == 'test-key'
        assert provider.name == 'google'

    def test_initialization_without_api_key(self):
        """Test provider initialization without API key raises error."""
        with pytest.raises(TTSConfigurationError, match="requires an API key"):
            GoogleTTSProvider()

    def test_get_capabilities(self):
        """Test getting provider capabilities."""
        provider = GoogleTTSProvider(api_key='test-key')
        caps = provider.get_capabilities()
        assert isinstance(caps, TTSCapabilities)
        assert caps.supports_ssml is True
        assert caps.supports_audio_effects is True
        assert caps.supports_streaming is False

    def test_configure_method(self):
        """Test configure method."""
        provider = GoogleTTSProvider(api_key='test-key')
        provider.configure(api_key='new-key', va_voice='new-voice')
        assert provider.api_key == 'new-key'
        assert provider.va_voice == 'new-voice'

    @patch('requests.post')
    def test_synthesize_success(self, mock_post):
        """Test successful text synthesis."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'audioContent': 'YXVkaW8gZGF0YQ=='  # base64 for "audio data"
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        provider = GoogleTTSProvider(api_key='test-key')

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            output_file = f.name

        try:
            audio_bytes = provider.synthesize(
                text="Hello world",
                voice="en-US-Journey-O",
                locale="en-US",
                rate=1.0,
                output_file=output_file
            )

            # Verify API was called
            assert mock_post.called
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert payload['input']['text'] == "Hello world"
            assert payload['voice']['name'] == "en-US-Journey-O"
            assert payload['voice']['languageCode'] == "en-US"

            # Verify audio bytes returned
            assert audio_bytes == b'audio data'

            # Verify file was written
            assert os.path.exists(output_file)
            with open(output_file, 'rb') as f:
                assert f.read() == b'audio data'
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    @patch('requests.post')
    def test_synthesize_api_error(self, mock_post):
        """Test synthesis with API error."""
        import requests
        mock_post.side_effect = requests.exceptions.RequestException("API error")

        provider = GoogleTTSProvider(api_key='test-key')

        with pytest.raises(TTSAPIError, match="API request failed"):
            provider.synthesize(
                text="Hello world",
                voice="en-US-Journey-O",
                locale="en-US"
            )

    def test_list_effects_profiles(self):
        """Test listing audio effects profiles."""
        provider = GoogleTTSProvider(api_key='test-key')
        profiles = provider.list_effects_profiles()
        assert 'telephony-class-application' in profiles
        assert isinstance(profiles, list)


class TestFeatureDetection:
    """Test feature detection helpers."""

    def test_has_feature_helper(self):
        """Test has_feature helper function."""
        provider = GoogleTTSProvider(api_key='test-key')

        # Google provider supports AudioEffectsCapable but not StreamingCapable
        from tts.features import AudioEffectsCapable
        assert has_feature(provider, AudioEffectsCapable) is True
        assert has_feature(provider, StreamingCapable) is False

    def test_isinstance_check_for_features(self):
        """Test isinstance checks for feature protocols."""
        provider = GoogleTTSProvider(api_key='test-key')

        # Test runtime protocol checking
        from tts.features import AudioEffectsCapable
        assert isinstance(provider, AudioEffectsCapable)


class TestCreateTTSProvider:
    """Test module-level convenience function."""

    def test_create_tts_provider_function(self):
        """Test create_tts_provider convenience function."""
        provider = create_tts_provider('google', api_key='test-key')
        assert isinstance(provider, TTSProvider)
        assert provider.name == 'google'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
