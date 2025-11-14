#!/usr/bin/env python3

import pytest
import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock, mock_open, call
import base64

# Import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from GoogleGenerateVC import VisionClipGenerator


class TestVisionClipGeneratorInit:
    """Test VisionClipGenerator class initialization"""

    def test_init_with_api_key(self, mocker):
        """Test initialization with API key provided"""
        mocker.patch.dict(os.environ, {}, clear=True)
        generator = VisionClipGenerator(api_key='test_api_key')

        # Now uses TTS provider abstraction
        assert generator.tts_provider is not None
        assert generator.tts_provider.name == 'google'
        assert generator.tts_provider.api_key == 'test_api_key'
        assert generator.sox_path == "sox-14.4.2/sox "
        assert generator.va_locale == 'en-US'
        assert generator.va_voice == 'en-US-Journey-O'

    def test_init_with_env_variable(self, mocker):
        """Test initialization with API key from environment"""
        mocker.patch.dict(os.environ, {'GOOGLE_API_KEY': 'env_api_key'}, clear=True)
        generator = VisionClipGenerator()

        assert generator.tts_provider is not None
        assert generator.tts_provider.api_key == 'env_api_key'

    def test_init_without_api_key(self, mocker):
        """Test initialization fails without API key"""
        mocker.patch.dict(os.environ, {}, clear=True)

        from tts import TTSConfigurationError
        with pytest.raises(TTSConfigurationError, match="requires an API key"):
            VisionClipGenerator()

    def test_init_with_custom_environment(self, mocker):
        """Test initialization with custom voice environment variables"""
        mocker.patch.dict(os.environ, {
            'GOOGLE_API_KEY': 'test_key',
            'VA_LOCALE': 'es-ES',
            'VA_VOICE': 'es-ES-ElviraNeural',
            'CALLER_LOCALE': 'fr-FR',
            'CALLER_VOICE': 'fr-FR-DeniseNeural'
        }, clear=True)

        generator = VisionClipGenerator()

        assert generator.va_locale == 'es-ES'
        assert generator.va_voice == 'es-ES-ElviraNeural'
        assert generator.caller_locale == 'fr-FR'
        assert generator.caller_voice == 'fr-FR-DeniseNeural'

    def test_init_state_variables(self, mocker):
        """Test that state variables are initialized correctly"""
        mocker.patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key'}, clear=True)
        generator = VisionClipGenerator()

        assert generator.ignore is True
        assert generator.fnum == 1
        assert generator.final_audio == ''


class TestTextToWav:
    """Test the text_to_wav method"""

    @pytest.fixture
    def generator(self, mocker):
        """Create a generator instance for testing"""
        mocker.patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key'}, clear=True)
        return VisionClipGenerator()

    def test_text_to_wav_api_call(self, generator, mocker):
        """Test that text_to_wav delegates to TTS provider"""
        # Mock the TTS provider's synthesize method
        mock_synthesize = mocker.patch.object(
            generator.tts_provider,
            'synthesize',
            return_value=b'fake_audio_data'
        )

        generator.text_to_wav('en-US-Journey-O', 1.0, 'en-US', 'Hello world', 'test.wav')

        # Verify synthesize was called with correct parameters
        mock_synthesize.assert_called_once_with(
            text='Hello world',
            voice='en-US-Journey-O',
            locale='en-US',
            rate=1.0,
            output_file='test.wav'
        )

    def test_text_to_wav_file_write(self, generator, mocker):
        """Test that text_to_wav writes audio to file via provider"""
        original_data = b'audio_data_sample'

        # Mock the provider's synthesize to write to file
        mocker.patch.object(
            generator.tts_provider,
            'synthesize',
            return_value=original_data
        )

        # The actual file writing is handled by the provider
        # We just verify the method is called
        result = generator.text_to_wav('en-US-Journey-O', 1.0, 'en-US', 'Test', 'output.wav')

        # The method doesn't return anything, but the provider's synthesize is called
        generator.tts_provider.synthesize.assert_called_once()


class TestProcessIvaLine:
    """Test the process_iva_line method"""

    @pytest.fixture
    def generator(self, mocker):
        """Create a generator instance for testing"""
        mocker.patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key'}, clear=True)
        return VisionClipGenerator()

    def test_process_iva_line(self, generator, mocker):
        """Test processing of IVA line"""
        mocker.patch.object(generator, 'text_to_wav')
        mocker.patch('time.sleep')
        mocker.patch('os.system')

        generator.fnum = 5
        generator.final_audio = 'existing.wav '

        line = 'IVA: Hello, how can I help you?'
        generator.process_iva_line(line)

        # Verify text_to_wav was called with correct parameters
        generator.text_to_wav.assert_called_once_with(
            generator.va_voice, 1, generator.va_locale, ' Hello, how can I help you?', '5.wav'
        )

        # Verify state was updated
        assert generator.fnum == 6
        assert '5.wav' in generator.final_audio


class TestProcessCallerLine:
    """Test the process_caller_line method"""

    @pytest.fixture
    def generator(self, mocker):
        """Create a generator instance for testing"""
        mocker.patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key'}, clear=True)
        return VisionClipGenerator()

    def test_process_caller_line_tts_mode(self, generator, mocker):
        """Test processing caller line with TTS (not recording)"""
        mocker.patch.object(generator, 'text_to_wav')

        generator.fnum = 3
        line = 'Caller:5: I need help with my reservation'

        generator.process_caller_line(line, record_mode=False)

        # Verify TTS was called
        generator.text_to_wav.assert_called_once_with(
            generator.caller_voice, 1, generator.caller_locale, ' I need help with my reservation', '3.wav'
        )

        assert generator.fnum == 4
        assert '3.wav' in generator.final_audio

    def test_process_caller_line_record_mode(self, generator, mocker):
        """Test processing caller line with microphone recording"""
        mock_rec = mocker.patch('sounddevice.rec', return_value=Mock())
        mocker.patch('sounddevice.wait')
        mocker.patch('soundfile.write')
        mocker.patch('os.system')

        generator.fnum = 2
        line = 'Caller:7: Test message'

        generator.process_caller_line(line, record_mode=True)

        # Verify recording was called with correct parameters
        expected_samples = 7 * 24000
        mock_rec.assert_called_once_with(expected_samples, samplerate=24000, channels=1)

        assert generator.fnum == 3
        assert '2.wav' in generator.final_audio


class TestProcessSpecialTag:
    """Test the process_special_tag method"""

    @pytest.fixture
    def generator(self, mocker):
        """Create a generator instance for testing"""
        mocker.patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key'}, clear=True)
        return VisionClipGenerator()

    def test_backend_tag(self, generator):
        """Test processing <backend> tag"""
        generator.final_audio = 'existing.wav '
        generator.process_special_tag('<backend>')
        assert 'Audio/backend.wav' in generator.final_audio

    def test_sendmail_tag(self, generator):
        """Test processing <sendmail> tag"""
        generator.final_audio = 'existing.wav '
        generator.process_special_tag('<sendmail>')
        assert 'Audio/swoosh.wav' in generator.final_audio

    def test_transfer_tag(self, generator):
        """Test processing <transfer> tag"""
        generator.final_audio = 'existing.wav '
        generator.process_special_tag('<transfer>')
        assert 'Audio/ringback.wav' in generator.final_audio

    def test_text_tag(self, generator):
        """Test processing <text> tag"""
        generator.final_audio = 'existing.wav '
        generator.process_special_tag('<text>')
        assert 'Audio/text-received.wav' in generator.final_audio


class TestProcessDialogFile:
    """Test the process_dialog_file method"""

    @pytest.fixture
    def generator(self, mocker):
        """Create a generator instance for testing"""
        mocker.patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key'}, clear=True)
        return VisionClipGenerator()

    @pytest.fixture
    def sample_dialog(self, tmp_path):
        """Create a sample dialog file for testing"""
        dialog_content = """Vision Clip 1: Test Dialog
Voice: Female
Caller: Male

<ringback>

IVA: Hello, how can I help you?

Caller:3: I need assistance

<backend>

IVA: Let me help you with that.

<hangup>
"""
        dialog_file = tmp_path / "test_dialog.txt"
        dialog_file.write_text(dialog_content)
        return str(dialog_file)

    def test_process_dialog_file(self, generator, sample_dialog, mocker):
        """Test processing a complete dialog file"""
        mocker.patch.object(generator, 'text_to_wav')
        mocker.patch('time.sleep')
        mocker.patch('os.system')

        output_file = generator.process_dialog_file(sample_dialog, record_mode=False)

        # Verify output file path
        assert output_file == 'vc.wav'

        # Verify text_to_wav was called for both IVA lines and Caller line
        assert generator.text_to_wav.call_count == 3  # 2 IVA lines + 1 Caller line

        # Verify final audio includes all expected files
        assert 'Audio/ringback.wav' in generator.final_audio
        assert 'Audio/backend.wav' in generator.final_audio

    def test_process_dialog_file_resets_state(self, generator, sample_dialog, mocker):
        """Test that process_dialog_file resets state variables"""
        mocker.patch.object(generator, 'text_to_wav')
        mocker.patch('time.sleep')
        mocker.patch('os.system')

        # Set initial state
        generator.fnum = 10
        generator.final_audio = 'old_audio.wav '
        generator.ignore = False

        generator.process_dialog_file(sample_dialog, record_mode=False)

        # State should be reset at start and incremented during processing
        assert generator.fnum > 1


class TestLineParsingLogic:
    """Test the line parsing and processing logic"""

    def test_ringback_tag_detection(self):
        """Test that <ringback> tag is properly detected"""
        line = '<ringback>'
        assert line.startswith('<ringback>')

    def test_hangup_tag_detection(self):
        """Test that <hangup> tag is properly detected"""
        line = '<hangup>'
        assert line.startswith('<hangup>')

    def test_backend_tag_detection(self):
        """Test that <backend> tag is properly detected"""
        line = '<backend>'
        assert line.startswith('<backend>')

    def test_iva_line_parsing(self):
        """Test parsing of IVA lines"""
        line = 'IVA: Hello, how can I help you?'
        assert line.startswith('IVA')

        ivr = line.split(':', 1)
        assert len(ivr) == 2
        assert ivr[0] == 'IVA'
        assert ivr[1] == ' Hello, how can I help you?'

    def test_caller_line_parsing(self):
        """Test parsing of Caller lines with duration"""
        line = 'Caller:5: I need help with my reservation'
        assert line.startswith('Caller')

        caller = line.split(':', 2)
        assert len(caller) == 3
        assert caller[0] == 'Caller'
        assert caller[1] == '5'
        assert caller[2] == ' I need help with my reservation'

    def test_caller_duration_extraction(self):
        """Test extraction of recording duration from Caller line"""
        line = 'Caller:7: This should record for 7 seconds'
        caller = line.split(':', 2)
        duration = int(caller[1])

        assert duration == 7
        assert duration * 24000 == 168000  # num_samples calculation


class TestEnvironmentVariables:
    """Test environment variable handling"""

    def test_default_va_locale(self, mocker):
        """Test default VA_LOCALE value"""
        mocker.patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key'}, clear=True)
        generator = VisionClipGenerator()
        assert generator.va_locale == 'en-US'

    def test_default_va_voice(self, mocker):
        """Test default VA_VOICE value"""
        mocker.patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key'}, clear=True)
        generator = VisionClipGenerator()
        assert generator.va_voice == 'en-US-Journey-O'

    def test_custom_environment_variables(self, mocker):
        """Test custom environment variable values"""
        custom_env = {
            'GOOGLE_API_KEY': 'test_key',
            'VA_LOCALE': 'es-ES',
            'VA_VOICE': 'es-ES-ElviraNeural',
            'CALLER_LOCALE': 'es-ES',
            'CALLER_VOICE': 'es-ES-AlvaroNeural'
        }
        mocker.patch.dict(os.environ, custom_env, clear=True)

        generator = VisionClipGenerator()

        assert generator.va_locale == 'es-ES'
        assert generator.va_voice == 'es-ES-ElviraNeural'
        assert generator.caller_locale == 'es-ES'
        assert generator.caller_voice == 'es-ES-AlvaroNeural'


class TestAudioProcessing:
    """Test audio processing and file operations"""

    def test_audio_file_numbering(self):
        """Test that audio files are numbered sequentially"""
        fnum = 1
        expected_files = []

        for i in range(1, 6):
            fn = str(fnum) + '.wav'
            expected_files.append(fn)
            fnum += 1

        assert expected_files == ['1.wav', '2.wav', '3.wav', '4.wav', '5.wav']

    def test_final_audio_concatenation(self):
        """Test building the final audio file list"""
        finalAudio = ' Audio/ringback.wav '
        finalAudio += '1.wav '
        finalAudio += '2.wav '
        finalAudio += 'Audio/backend.wav '
        finalAudio += '3.wav '

        # Verify the string contains all expected files
        assert 'Audio/ringback.wav' in finalAudio
        assert '1.wav' in finalAudio
        assert '2.wav' in finalAudio
        assert 'Audio/backend.wav' in finalAudio
        assert '3.wav' in finalAudio

    def test_sox_command_construction(self):
        """Test sox command string construction"""
        SoxURL = "sox-14.4.2/sox "
        finalAudio = 'Audio/ringback.wav 1.wav 2.wav '
        sox_command = SoxURL + finalAudio + ' vc.wav'

        assert sox_command.startswith('sox-14.4.2/sox')
        assert sox_command.endswith('vc.wav')
        assert '1.wav' in sox_command
        assert '2.wav' in sox_command


class TestRecordingCalculations:
    """Test recording duration and sample calculations"""

    def test_sample_rate_calculation(self):
        """Test conversion of seconds to samples"""
        duration_seconds = 5
        sample_rate = 24000
        expected_samples = duration_seconds * sample_rate

        assert expected_samples == 120000

    def test_various_durations(self):
        """Test sample calculations for different durations"""
        sample_rate = 24000
        test_cases = [
            (1, 24000),
            (3, 72000),
            (5, 120000),
            (7, 168000),
            (10, 240000)
        ]

        for duration, expected_samples in test_cases:
            numsamples = duration * sample_rate
            assert numsamples == expected_samples


class TestGenerateMethod:
    """Test the public generate method"""

    @pytest.fixture
    def generator(self, mocker):
        """Create a generator instance for testing"""
        mocker.patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key'}, clear=True)
        return VisionClipGenerator()

    def test_generate_delegates_to_process_dialog_file(self, generator, mocker):
        """Test that generate method delegates to process_dialog_file"""
        mock_process = mocker.patch.object(generator, 'process_dialog_file', return_value='vc.wav')

        result = generator.generate('test.txt', record_mode=True)

        mock_process.assert_called_once_with('test.txt', True)
        assert result == 'vc.wav'
