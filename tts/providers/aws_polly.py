"""AWS Polly Text-to-Speech provider implementation."""

from typing import Optional
from tts.base import TTSProvider, TTSAPIError, TTSConfigurationError
from tts.capabilities import TTSCapabilities
from tts.features import SSMLCapable

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    AWS_SDK_AVAILABLE = True
except ImportError:
    AWS_SDK_AVAILABLE = False


class AWSPollyTTSProvider(SSMLCapable):
    """
    AWS Polly Text-to-Speech provider.

    Uses Amazon Polly with support for:
    - Neural and standard voices
    - Multiple languages and locales
    - SSML (Speech Synthesis Markup Language)
    - Speaking rate and pitch control
    - Multiple audio formats

    Requires: boto3 package (AWS SDK for Python)
    """

    def __init__(
        self,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        region: str = "us-east-1",
        va_voice: str = "Joanna",
        caller_voice: str = "Matthew",
        va_locale: str = "en-US",
        caller_locale: str = "en-US",
        engine: str = "neural",
        **kwargs
    ):
        """
        Initialize AWS Polly TTS provider.

        Args:
            access_key_id: AWS access key ID (optional if using IAM role)
            secret_access_key: AWS secret access key (optional if using IAM role)
            region: AWS region (e.g., 'us-east-1', 'eu-west-1')
            va_voice: Default voice for virtual assistant
            caller_voice: Default voice for caller
            va_locale: Default locale for virtual assistant
            caller_locale: Default locale for caller
            engine: Voice engine ('neural' or 'standard')
            **kwargs: Additional configuration (ignored)

        Raises:
            TTSConfigurationError: If boto3 is not available
        """
        if not AWS_SDK_AVAILABLE:
            raise TTSConfigurationError(
                "AWS Polly provider requires boto3 package. "
                "Install with: pip install boto3"
            )

        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region
        self.va_voice = va_voice
        self.caller_voice = caller_voice
        self.va_locale = va_locale
        self.caller_locale = caller_locale
        self.engine = engine

        # Create Polly client
        session_params = {
            'region_name': self.region
        }
        if access_key_id and secret_access_key:
            session_params['aws_access_key_id'] = access_key_id
            session_params['aws_secret_access_key'] = secret_access_key

        try:
            self.polly_client = boto3.client('polly', **session_params)
        except Exception as e:
            raise TTSConfigurationError(f"Failed to create AWS Polly client: {e}") from e

        # Define capabilities
        self._capabilities = TTSCapabilities(
            supports_streaming=True,
            supports_ssml=True,
            supports_custom_voices=False,
            supported_audio_formats=["pcm", "mp3", "ogg"],
            max_text_length=3000,  # For standard voices; 1500 for neural
            max_requests_per_minute=None,  # Based on AWS account limits
            supports_pitch_control=True,
            supports_rate_control=True,
            supports_volume_control=True,
            requires_api_key=True,
        )

    @property
    def name(self) -> str:
        """Get provider name."""
        return "aws"

    def get_capabilities(self) -> TTSCapabilities:
        """Get provider capabilities."""
        return self._capabilities

    def configure(self, **kwargs) -> None:
        """
        Configure the provider with additional settings.

        Args:
            **kwargs: Configuration options
        """
        if 'access_key_id' in kwargs:
            self.access_key_id = kwargs['access_key_id']
        if 'secret_access_key' in kwargs:
            self.secret_access_key = kwargs['secret_access_key']
        if 'region' in kwargs:
            self.region = kwargs['region']
        if 'va_voice' in kwargs:
            self.va_voice = kwargs['va_voice']
        if 'caller_voice' in kwargs:
            self.caller_voice = kwargs['caller_voice']
        if 'va_locale' in kwargs:
            self.va_locale = kwargs['va_locale']
        if 'caller_locale' in kwargs:
            self.caller_locale = kwargs['caller_locale']
        if 'engine' in kwargs:
            self.engine = kwargs['engine']

        # Recreate client if credentials changed
        if any(k in kwargs for k in ['access_key_id', 'secret_access_key', 'region']):
            session_params = {'region_name': self.region}
            if self.access_key_id and self.secret_access_key:
                session_params['aws_access_key_id'] = self.access_key_id
                session_params['aws_secret_access_key'] = self.secret_access_key
            self.polly_client = boto3.client('polly', **session_params)

    def synthesize(
        self,
        text: str,
        voice: str,
        locale: str,
        rate: float = 1.0,
        output_file: str = None
    ) -> bytes:
        """
        Synthesize text to speech audio using AWS Polly.

        Args:
            text: Text to synthesize
            voice: Voice ID (e.g., 'Joanna', 'Matthew', 'Amy')
            locale: Locale code (e.g., 'en-US')
            rate: Speaking rate (1.0 is normal) - applied via SSML if not 1.0
            output_file: Optional path to write audio file

        Returns:
            Raw audio bytes (PCM format)

        Raises:
            TTSAPIError: If synthesis fails
        """
        # If rate is not 1.0, use SSML to apply rate
        if rate != 1.0:
            # Convert rate to percentage (0.5 -> 50%, 1.0 -> 100%, 2.0 -> 200%)
            rate_percent = f"{int(rate * 100)}%"
            ssml = (
                f'<speak>'
                f'<prosody rate="{rate_percent}">{text}</prosody>'
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
            voice: Voice ID
            locale: Locale code
            output_file: Optional output file path

        Returns:
            Raw audio bytes

        Raises:
            TTSAPIError: If synthesis fails
        """
        try:
            response = self.polly_client.synthesize_speech(
                Text=text,
                OutputFormat='pcm',
                VoiceId=voice,
                Engine=self.engine,
                LanguageCode=locale,
                SampleRate='16000'
            )

            # Read audio stream
            audio_bytes = response['AudioStream'].read()

            # Write to file if requested
            if output_file:
                # For WAV format, we need to add a header
                if output_file.endswith('.wav'):
                    audio_bytes = self._add_wav_header(audio_bytes, 16000, 16, 1)

                with open(output_file, 'wb') as f:
                    f.write(audio_bytes)

            return audio_bytes

        except (BotoCoreError, ClientError) as e:
            raise TTSAPIError(f"AWS Polly synthesis failed: {e}") from e

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
            voice: Voice ID
            locale: Locale code
            output_file: Optional path to write audio file

        Returns:
            Raw audio bytes (PCM format)

        Raises:
            TTSAPIError: If synthesis fails
        """
        try:
            response = self.polly_client.synthesize_speech(
                Text=ssml,
                TextType='ssml',
                OutputFormat='pcm',
                VoiceId=voice,
                Engine=self.engine,
                LanguageCode=locale,
                SampleRate='16000'
            )

            # Read audio stream
            audio_bytes = response['AudioStream'].read()

            # Write to file if requested
            if output_file:
                # For WAV format, we need to add a header
                if output_file.endswith('.wav'):
                    audio_bytes = self._add_wav_header(audio_bytes, 16000, 16, 1)

                with open(output_file, 'wb') as f:
                    f.write(audio_bytes)

            return audio_bytes

        except (BotoCoreError, ClientError) as e:
            raise TTSAPIError(f"AWS Polly SSML synthesis failed: {e}") from e

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

    def _add_wav_header(
        self,
        pcm_data: bytes,
        sample_rate: int,
        bits_per_sample: int,
        channels: int
    ) -> bytes:
        """
        Add WAV header to raw PCM data.

        Args:
            pcm_data: Raw PCM audio data
            sample_rate: Sample rate in Hz
            bits_per_sample: Bits per sample
            channels: Number of channels

        Returns:
            WAV file bytes with header
        """
        import struct

        datasize = len(pcm_data)
        header = b''

        # RIFF header
        header += b'RIFF'
        header += struct.pack('<I', datasize + 36)
        header += b'WAVE'

        # fmt chunk
        header += b'fmt '
        header += struct.pack('<I', 16)  # Chunk size
        header += struct.pack('<H', 1)   # Audio format (1 = PCM)
        header += struct.pack('<H', channels)
        header += struct.pack('<I', sample_rate)
        header += struct.pack('<I', sample_rate * channels * bits_per_sample // 8)  # Byte rate
        header += struct.pack('<H', channels * bits_per_sample // 8)  # Block align
        header += struct.pack('<H', bits_per_sample)

        # data chunk
        header += b'data'
        header += struct.pack('<I', datasize)

        return header + pcm_data
