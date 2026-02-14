"""Tests for the TTS abstraction layer."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
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
from tts.providers.elevenlabs_tts import ElevenLabsTTSProvider

# For AWS and Azure, we need to handle conditional imports differently
import tts.providers.aws_polly
import tts.providers.azure_tts


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


class TestAWSPollyTTSProvider:
    """Test AWSPollyTTSProvider class."""

    @pytest.fixture
    def mock_boto3(self):
        """Fixture to create and inject mock boto3 module."""
        mock_boto3 = Mock()
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        # Patch the module to add boto3 if it doesn't exist
        with patch.object(tts.providers.aws_polly, 'AWS_SDK_AVAILABLE', True):
            with patch.object(tts.providers.aws_polly, 'boto3', mock_boto3, create=True):
                with patch.object(tts.providers.aws_polly, 'ClientError', Exception, create=True):
                    with patch.object(tts.providers.aws_polly, 'BotoCoreError', Exception, create=True):
                        yield mock_boto3, mock_client

    def test_initialization_with_credentials(self, mock_boto3):
        """Test provider initialization with AWS credentials."""
        boto3_mock, mock_client = mock_boto3

        from tts.providers.aws_polly import AWSPollyTTSProvider
        provider = AWSPollyTTSProvider(
            access_key_id='test-key',
            secret_access_key='test-secret',
            region='us-west-2'
        )
        assert provider.access_key_id == 'test-key'
        assert provider.secret_access_key == 'test-secret'
        assert provider.region == 'us-west-2'
        assert provider.name == 'aws'

        # Verify boto3 client was created with correct params
        boto3_mock.client.assert_called_once()
        call_kwargs = boto3_mock.client.call_args[1]
        assert call_kwargs['region_name'] == 'us-west-2'
        assert call_kwargs['aws_access_key_id'] == 'test-key'
        assert call_kwargs['aws_secret_access_key'] == 'test-secret'

    def test_initialization_without_credentials(self, mock_boto3):
        """Test provider initialization without explicit credentials (uses IAM role)."""
        boto3_mock, mock_client = mock_boto3

        from tts.providers.aws_polly import AWSPollyTTSProvider
        provider = AWSPollyTTSProvider()
        assert provider.name == 'aws'

        # Verify boto3 client was created without credentials
        boto3_mock.client.assert_called_once()
        call_kwargs = boto3_mock.client.call_args[1]
        assert 'aws_access_key_id' not in call_kwargs
        assert 'aws_secret_access_key' not in call_kwargs

    def test_initialization_without_boto3(self):
        """Test provider initialization without boto3 raises error."""
        with patch.object(tts.providers.aws_polly, 'AWS_SDK_AVAILABLE', False):
            from tts.providers.aws_polly import AWSPollyTTSProvider
            with pytest.raises(TTSConfigurationError, match="requires boto3 package"):
                AWSPollyTTSProvider()

    def test_get_capabilities(self, mock_boto3):
        """Test getting provider capabilities."""
        boto3_mock, mock_client = mock_boto3

        from tts.providers.aws_polly import AWSPollyTTSProvider
        provider = AWSPollyTTSProvider()
        caps = provider.get_capabilities()
        assert isinstance(caps, TTSCapabilities)
        assert caps.supports_ssml is True
        assert caps.supports_streaming is True
        assert caps.supports_custom_voices is False

    def test_configure_method(self, mock_boto3):
        """Test configure method."""
        boto3_mock, mock_client = mock_boto3

        from tts.providers.aws_polly import AWSPollyTTSProvider
        provider = AWSPollyTTSProvider()
        provider.configure(
            va_voice='Amy',
            caller_voice='Brian',
            region='eu-west-1',
            engine='standard'
        )
        assert provider.va_voice == 'Amy'
        assert provider.caller_voice == 'Brian'
        assert provider.region == 'eu-west-1'
        assert provider.engine == 'standard'

    def test_synthesize_success(self, mock_boto3):
        """Test successful text synthesis."""
        boto3_mock, mock_client = mock_boto3

        # Mock Polly response
        mock_audio_stream = Mock()
        mock_audio_stream.read.return_value = b'pcm audio data'
        mock_response = {'AudioStream': mock_audio_stream}
        mock_client.synthesize_speech.return_value = mock_response

        from tts.providers.aws_polly import AWSPollyTTSProvider
        provider = AWSPollyTTSProvider()

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            output_file = f.name

        try:
            audio_bytes = provider.synthesize(
                text="Hello world",
                voice="Joanna",
                locale="en-US",
                rate=1.0,
                output_file=output_file
            )

            # Verify API was called
            assert mock_client.synthesize_speech.called
            call_kwargs = mock_client.synthesize_speech.call_args[1]
            assert call_kwargs['Text'] == "Hello world"
            assert call_kwargs['VoiceId'] == "Joanna"
            assert call_kwargs['LanguageCode'] == "en-US"
            assert call_kwargs['OutputFormat'] == 'pcm'

            # Verify file was written (with WAV header added)
            assert os.path.exists(output_file)
            with open(output_file, 'rb') as f:
                content = f.read()
                # Check for WAV header
                assert content[:4] == b'RIFF'
                assert content[8:12] == b'WAVE'
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_synthesize_with_rate(self, mock_boto3):
        """Test synthesis with custom speaking rate (uses SSML)."""
        boto3_mock, mock_client = mock_boto3

        mock_audio_stream = Mock()
        mock_audio_stream.read.return_value = b'pcm audio data'
        mock_response = {'AudioStream': mock_audio_stream}
        mock_client.synthesize_speech.return_value = mock_response

        from tts.providers.aws_polly import AWSPollyTTSProvider
        provider = AWSPollyTTSProvider()
        audio_bytes = provider.synthesize(
            text="Hello world",
            voice="Joanna",
            locale="en-US",
            rate=1.5
        )

        # Verify SSML was used
        call_kwargs = mock_client.synthesize_speech.call_args[1]
        assert call_kwargs['TextType'] == 'ssml'
        assert '<prosody rate="150%">Hello world</prosody>' in call_kwargs['Text']

    def test_synthesize_ssml(self, mock_boto3):
        """Test SSML synthesis."""
        boto3_mock, mock_client = mock_boto3

        mock_audio_stream = Mock()
        mock_audio_stream.read.return_value = b'pcm audio data'
        mock_response = {'AudioStream': mock_audio_stream}
        mock_client.synthesize_speech.return_value = mock_response

        from tts.providers.aws_polly import AWSPollyTTSProvider
        provider = AWSPollyTTSProvider()
        ssml = '<speak><prosody rate="slow">Hello world</prosody></speak>'
        audio_bytes = provider.synthesize_ssml(ssml, "Joanna", "en-US")

        # Verify API was called with SSML
        call_kwargs = mock_client.synthesize_speech.call_args[1]
        assert call_kwargs['TextType'] == 'ssml'
        assert call_kwargs['Text'] == ssml

    def test_synthesize_api_error(self, mock_boto3):
        """Test synthesis with API error."""
        boto3_mock, mock_client = mock_boto3

        mock_client.synthesize_speech.side_effect = Exception("API error")

        from tts.providers.aws_polly import AWSPollyTTSProvider
        provider = AWSPollyTTSProvider()

        with pytest.raises(TTSAPIError, match="AWS Polly synthesis failed"):
            provider.synthesize(
                text="Hello world",
                voice="Joanna",
                locale="en-US"
            )

    def test_validate_ssml(self, mock_boto3):
        """Test SSML validation."""
        boto3_mock, mock_client = mock_boto3

        from tts.providers.aws_polly import AWSPollyTTSProvider
        provider = AWSPollyTTSProvider()

        # Valid SSML
        assert provider.validate_ssml('<speak>Hello</speak>') is True

        # Invalid SSML (missing tags)
        assert provider.validate_ssml('Hello world') is False
        assert provider.validate_ssml('<speak>Hello') is False


class TestAzureTTSProvider:
    """Test AzureTTSProvider class."""

    @pytest.fixture
    def mock_azure_sdk(self):
        """Fixture to create and inject mock Azure SDK."""
        mock_speech_config_class = Mock()
        mock_config = Mock()
        mock_speech_config_class.return_value = mock_config

        # Patch the module to add Azure SDK if it doesn't exist
        with patch.object(tts.providers.azure_tts, 'AZURE_SDK_AVAILABLE', True):
            with patch.object(tts.providers.azure_tts, 'SpeechConfig', mock_speech_config_class, create=True):
                yield mock_speech_config_class, mock_config

    def test_initialization_with_subscription_key(self, mock_azure_sdk):
        """Test provider initialization with subscription key."""
        mock_speech_config, mock_config = mock_azure_sdk

        from tts.providers.azure_tts import AzureTTSProvider
        provider = AzureTTSProvider(
            subscription_key='test-key',
            region='westus'
        )
        assert provider.subscription_key == 'test-key'
        assert provider.region == 'westus'
        assert provider.name == 'azure'

        # Verify SpeechConfig was created
        mock_speech_config.assert_called_once_with(
            subscription='test-key',
            region='westus'
        )

    def test_initialization_without_subscription_key(self, mock_azure_sdk):
        """Test provider initialization without subscription key raises error."""
        from tts.providers.azure_tts import AzureTTSProvider
        with pytest.raises(TTSConfigurationError, match="requires a subscription key"):
            AzureTTSProvider()

    def test_initialization_without_azure_sdk(self):
        """Test provider initialization without Azure SDK raises error."""
        with patch.object(tts.providers.azure_tts, 'AZURE_SDK_AVAILABLE', False):
            from tts.providers.azure_tts import AzureTTSProvider
            with pytest.raises(TTSConfigurationError, match="requires azure-cognitiveservices-speech"):
                AzureTTSProvider(subscription_key='test-key')

    def test_get_capabilities(self, mock_azure_sdk):
        """Test getting provider capabilities."""
        from tts.providers.azure_tts import AzureTTSProvider
        provider = AzureTTSProvider(subscription_key='test-key')
        caps = provider.get_capabilities()
        assert isinstance(caps, TTSCapabilities)
        assert caps.supports_ssml is True
        assert caps.supports_streaming is False
        assert caps.supports_custom_voices is False

    def test_configure_method(self, mock_azure_sdk):
        """Test configure method."""
        from tts.providers.azure_tts import AzureTTSProvider
        provider = AzureTTSProvider(subscription_key='test-key')
        provider.configure(
            va_voice='en-US-AriaNeural',
            caller_voice='en-US-DavisNeural',
            region='eastus2'
        )
        assert provider.va_voice == 'en-US-AriaNeural'
        assert provider.caller_voice == 'en-US-DavisNeural'
        assert provider.region == 'eastus2'

    def test_synthesize_success(self, mock_azure_sdk):
        """Test successful text synthesis."""
        mock_speech_config, mock_config = mock_azure_sdk

        # Mock synthesizer and result
        mock_synthesizer = Mock()
        mock_result = Mock()
        mock_result.audio_data = b'azure audio data'
        mock_async = Mock()
        mock_async.get.return_value = mock_result
        mock_synthesizer.speak_text_async.return_value = mock_async

        mock_synthesizer_class = Mock()
        mock_synthesizer_class.return_value = mock_synthesizer

        with patch.object(tts.providers.azure_tts, 'SpeechSynthesizer', mock_synthesizer_class, create=True):
            from tts.providers.azure_tts import AzureTTSProvider
            provider = AzureTTSProvider(subscription_key='test-key')
            audio_bytes = provider.synthesize(
                text="Hello world",
                voice="en-US-JennyNeural",
                locale="en-US",
                rate=1.0
            )

            # Verify synthesizer was called
            assert mock_synthesizer.speak_text_async.called
            call_args = mock_synthesizer.speak_text_async.call_args[0]
            assert call_args[0] == "Hello world"

            # Verify audio bytes returned
            assert audio_bytes == b'azure audio data'

    def test_synthesize_to_file(self, mock_azure_sdk):
        """Test synthesis to file."""
        # Mock audio config
        mock_audio_config_class = Mock()
        mock_output_config = Mock()
        mock_audio_config_class.return_value = mock_output_config

        # Mock synthesizer and result
        mock_synthesizer = Mock()
        mock_result = Mock()
        mock_async = Mock()
        mock_async.get.return_value = mock_result
        mock_synthesizer.speak_text_async.return_value = mock_async

        mock_synthesizer_class = Mock()
        mock_synthesizer_class.return_value = mock_synthesizer

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            output_file = f.name
            # Write some dummy data
            f.write(b'azure audio data')

        try:
            with patch.object(tts.providers.azure_tts, 'SpeechSynthesizer', mock_synthesizer_class, create=True):
                with patch.object(tts.providers.azure_tts, 'AudioOutputConfig', mock_audio_config_class, create=True):
                    from tts.providers.azure_tts import AzureTTSProvider
                    provider = AzureTTSProvider(subscription_key='test-key')
                    audio_bytes = provider.synthesize(
                        text="Hello world",
                        voice="en-US-JennyNeural",
                        locale="en-US",
                        output_file=output_file
                    )

                    # Verify audio config was created with filename
                    mock_audio_config_class.assert_called_once_with(filename=output_file)

                    # Verify file was read
                    assert audio_bytes == b'azure audio data'
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_synthesize_with_rate(self, mock_azure_sdk):
        """Test synthesis with custom speaking rate (uses SSML)."""
        # Mock synthesizer and result
        mock_synthesizer = Mock()
        mock_result = Mock()
        mock_result.audio_data = b'azure audio data'
        mock_async = Mock()
        mock_async.get.return_value = mock_result
        mock_synthesizer.speak_ssml_async.return_value = mock_async

        mock_synthesizer_class = Mock()
        mock_synthesizer_class.return_value = mock_synthesizer

        with patch.object(tts.providers.azure_tts, 'SpeechSynthesizer', mock_synthesizer_class, create=True):
            from tts.providers.azure_tts import AzureTTSProvider
            provider = AzureTTSProvider(subscription_key='test-key')
            audio_bytes = provider.synthesize(
                text="Hello world",
                voice="en-US-JennyNeural",
                locale="en-US",
                rate=1.5
            )

            # Verify SSML was used
            assert mock_synthesizer.speak_ssml_async.called
            call_args = mock_synthesizer.speak_ssml_async.call_args[0]
            ssml = call_args[0]
            assert '<speak' in ssml
            assert '<prosody rate="150%">Hello world</prosody>' in ssml

    def test_synthesize_ssml(self, mock_azure_sdk):
        """Test SSML synthesis."""
        # Mock synthesizer and result
        mock_synthesizer = Mock()
        mock_result = Mock()
        mock_result.audio_data = b'azure audio data'
        mock_async = Mock()
        mock_async.get.return_value = mock_result
        mock_synthesizer.speak_ssml_async.return_value = mock_async

        mock_synthesizer_class = Mock()
        mock_synthesizer_class.return_value = mock_synthesizer

        with patch.object(tts.providers.azure_tts, 'SpeechSynthesizer', mock_synthesizer_class, create=True):
            from tts.providers.azure_tts import AzureTTSProvider
            provider = AzureTTSProvider(subscription_key='test-key')
            ssml = '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US"><voice name="en-US-JennyNeural">Hello world</voice></speak>'
            audio_bytes = provider.synthesize_ssml(ssml, "en-US-JennyNeural", "en-US")

            # Verify SSML was used
            call_args = mock_synthesizer.speak_ssml_async.call_args[0]
            assert call_args[0] == ssml

    def test_synthesize_api_error(self, mock_azure_sdk):
        """Test synthesis with API error."""
        # Mock synthesizer to raise error
        mock_synthesizer = Mock()
        mock_synthesizer.speak_text_async.side_effect = Exception("Azure API error")

        mock_synthesizer_class = Mock()
        mock_synthesizer_class.return_value = mock_synthesizer

        with patch.object(tts.providers.azure_tts, 'SpeechSynthesizer', mock_synthesizer_class, create=True):
            from tts.providers.azure_tts import AzureTTSProvider
            provider = AzureTTSProvider(subscription_key='test-key')

            with pytest.raises(TTSAPIError, match="Azure TTS synthesis failed"):
                provider.synthesize(
                    text="Hello world",
                    voice="en-US-JennyNeural",
                    locale="en-US"
                )

    def test_validate_ssml(self, mock_azure_sdk):
        """Test SSML validation."""
        from tts.providers.azure_tts import AzureTTSProvider
        provider = AzureTTSProvider(subscription_key='test-key')

        # Valid SSML
        assert provider.validate_ssml('<speak>Hello</speak>') is True

        # Invalid SSML (missing tags)
        assert provider.validate_ssml('Hello world') is False
        assert provider.validate_ssml('<speak>Hello') is False


class TestElevenLabsTTSProvider:
    """Test ElevenLabsTTSProvider class."""

    def test_initialization_with_all_params(self):
        """Test provider initialization with all required parameters."""
        provider = ElevenLabsTTSProvider(
            api_key='test-key',
            va_voice='voice-id-1',
            caller_voice='voice-id-2',
            model='eleven_multilingual_v2'
        )
        assert provider.api_key == 'test-key'
        assert provider.va_voice == 'voice-id-1'
        assert provider.caller_voice == 'voice-id-2'
        assert provider.model == 'eleven_multilingual_v2'
        assert provider.name == 'elevenlabs'

    def test_initialization_without_api_key(self):
        """Test provider initialization without API key raises error."""
        with pytest.raises(TTSConfigurationError, match="requires an API key"):
            ElevenLabsTTSProvider(va_voice='voice-id-1', caller_voice='voice-id-2')

    def test_initialization_without_va_voice(self):
        """Test provider initialization without va_voice raises error."""
        with pytest.raises(TTSConfigurationError, match="requires va_voice"):
            ElevenLabsTTSProvider(api_key='test-key', caller_voice='voice-id-2')

    def test_initialization_without_caller_voice(self):
        """Test provider initialization without caller_voice raises error."""
        with pytest.raises(TTSConfigurationError, match="requires caller_voice"):
            ElevenLabsTTSProvider(api_key='test-key', va_voice='voice-id-1')

    def test_get_capabilities(self):
        """Test getting provider capabilities."""
        provider = ElevenLabsTTSProvider(
            api_key='test-key',
            va_voice='voice-id-1',
            caller_voice='voice-id-2'
        )
        caps = provider.get_capabilities()
        assert isinstance(caps, TTSCapabilities)
        assert caps.supports_streaming is True
        assert caps.supports_ssml is False
        assert caps.supports_custom_voices is True

    def test_configure_method(self):
        """Test configure method."""
        provider = ElevenLabsTTSProvider(
            api_key='test-key',
            va_voice='voice-id-1',
            caller_voice='voice-id-2'
        )
        provider.configure(
            api_key='new-key',
            va_voice='voice-id-3',
            model='eleven_monolingual_v1'
        )
        assert provider.api_key == 'new-key'
        assert provider.va_voice == 'voice-id-3'
        assert provider.model == 'eleven_monolingual_v1'
        assert provider.headers['xi-api-key'] == 'new-key'

    @patch('requests.post')
    def test_synthesize_success(self, mock_post):
        """Test successful text synthesis."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'mp3 audio data'
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        provider = ElevenLabsTTSProvider(
            api_key='test-key',
            va_voice='voice-id-1',
            caller_voice='voice-id-2'
        )

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            output_file = f.name

        try:
            audio_bytes = provider.synthesize(
                text="Hello world",
                voice="voice-id-1",
                locale="en-US",
                output_file=output_file
            )

            # Verify API was called
            assert mock_post.called
            call_args = mock_post.call_args
            url = call_args[0][0]
            assert 'voice-id-1' in url

            payload = call_args[1]['json']
            assert payload['text'] == "Hello world"
            assert payload['model_id'] == 'eleven_monolingual_v1'

            # Verify audio bytes returned
            assert audio_bytes == b'mp3 audio data'

            # Verify file was written
            assert os.path.exists(output_file)
            with open(output_file, 'rb') as f:
                assert f.read() == b'mp3 audio data'
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    @patch('requests.post')
    def test_synthesize_with_voice_id(self, mock_post):
        """Test synthesis with custom voice ID and settings."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'mp3 audio data'
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        provider = ElevenLabsTTSProvider(
            api_key='test-key',
            va_voice='voice-id-1',
            caller_voice='voice-id-2'
        )

        audio_bytes = provider.synthesize_with_voice_id(
            text="Hello world",
            voice_id="custom-voice-id",
            stability=0.7,
            similarity_boost=0.8
        )

        # Verify API was called with custom settings
        payload = mock_post.call_args[1]['json']
        assert payload['voice_settings']['stability'] == 0.7
        assert payload['voice_settings']['similarity_boost'] == 0.8

    @patch('requests.post')
    def test_synthesize_rate_limit_error(self, mock_post):
        """Test synthesis with rate limit error."""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response

        provider = ElevenLabsTTSProvider(
            api_key='test-key',
            va_voice='voice-id-1',
            caller_voice='voice-id-2'
        )

        from tts.base import TTSRateLimitError
        with pytest.raises(TTSRateLimitError, match="rate limit exceeded"):
            provider.synthesize(
                text="Hello world",
                voice="voice-id-1",
                locale="en-US"
            )

    @patch('requests.post')
    def test_synthesize_api_error(self, mock_post):
        """Test synthesis with API error."""
        import requests
        mock_post.side_effect = requests.exceptions.RequestException("API error")

        provider = ElevenLabsTTSProvider(
            api_key='test-key',
            va_voice='voice-id-1',
            caller_voice='voice-id-2'
        )

        with pytest.raises(TTSAPIError, match="API request failed"):
            provider.synthesize(
                text="Hello world",
                voice="voice-id-1",
                locale="en-US"
            )

    @patch('requests.post')
    def test_synthesize_stream(self, mock_post):
        """Test streaming synthesis."""
        # Mock streaming response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = iter([b'chunk1', b'chunk2', b'chunk3'])
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        provider = ElevenLabsTTSProvider(
            api_key='test-key',
            va_voice='voice-id-1',
            caller_voice='voice-id-2'
        )

        chunks = list(provider.synthesize_stream(
            text="Hello world",
            voice="voice-id-1",
            locale="en-US"
        ))

        # Verify streaming API was called
        call_args = mock_post.call_args
        url = call_args[0][0]
        assert 'stream' in url
        assert mock_post.call_args[1]['stream'] is True

        # Verify chunks were received
        assert chunks == [b'chunk1', b'chunk2', b'chunk3']

    @patch('requests.post')
    def test_synthesize_stream_rate_limit(self, mock_post):
        """Test streaming with rate limit error."""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response

        provider = ElevenLabsTTSProvider(
            api_key='test-key',
            va_voice='voice-id-1',
            caller_voice='voice-id-2'
        )

        from tts.base import TTSRateLimitError
        with pytest.raises(TTSRateLimitError, match="rate limit exceeded"):
            list(provider.synthesize_stream(
                text="Hello world",
                voice="voice-id-1",
                locale="en-US"
            ))

    @patch('requests.get')
    def test_list_custom_voices(self, mock_get):
        """Test listing custom voices."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'voices': [
                {
                    'voice_id': 'voice-1',
                    'name': 'Voice One',
                    'category': 'generated',
                    'labels': {'accent': 'american'}
                },
                {
                    'voice_id': 'voice-2',
                    'name': 'Voice Two',
                    'category': 'cloned'
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        provider = ElevenLabsTTSProvider(
            api_key='test-key',
            va_voice='voice-id-1',
            caller_voice='voice-id-2'
        )

        voices = provider.list_custom_voices()

        # Verify API was called
        assert mock_get.called
        call_args = mock_get.call_args
        url = call_args[0][0]
        assert 'voices' in url

        # Verify voices were parsed correctly
        assert len(voices) == 2
        assert voices[0]['id'] == 'voice-1'
        assert voices[0]['name'] == 'Voice One'
        assert voices[1]['id'] == 'voice-2'

    @patch('requests.get')
    def test_list_custom_voices_api_error(self, mock_get):
        """Test listing voices with API error."""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("API error")

        provider = ElevenLabsTTSProvider(
            api_key='test-key',
            va_voice='voice-id-1',
            caller_voice='voice-id-2'
        )

        with pytest.raises(TTSAPIError, match="Failed to list"):
            provider.list_custom_voices()


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
