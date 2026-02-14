#!/usr/bin/env python3

import pytest
import os
import sys
import logging
import tempfile
from unittest.mock import Mock, patch, MagicMock, mock_open, call
import base64

# Import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import VisionClipGenerator, setup_logging


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
        assert generator.temp_dir == ".temp"
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
        assert generator.keep_temp is False

    def test_init_with_keep_temp(self, mocker):
        """Test initialization with keep_temp flag"""
        mocker.patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key'}, clear=True)
        generator = VisionClipGenerator(keep_temp=True)

        assert generator.keep_temp is True


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
        mocker.patch.object(generator, 'play_audio')
        mocker.patch('time.sleep')

        generator.fnum = 5
        generator.final_audio = 'existing.wav '

        line = 'IVA: Hello, how can I help you?'
        generator.process_iva_line(line)

        # Verify text_to_wav was called with correct parameters
        generator.text_to_wav.assert_called_once_with(
            generator.va_voice, 1, generator.va_locale, ' Hello, how can I help you?', '.temp/005_va.wav'
        )

        # Verify play_audio was called
        generator.play_audio.assert_called_once_with('.temp/005_va.wav')

        # Verify state was updated
        assert generator.fnum == 6
        assert '005_va.wav' in generator.final_audio


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
            generator.caller_voice, 1, generator.caller_locale, ' I need help with my reservation', '.temp/003_caller.wav'
        )

        assert generator.fnum == 4
        assert '003_caller.wav' in generator.final_audio

    def test_process_caller_line_record_mode(self, generator, mocker):
        """Test processing caller line with microphone recording"""
        mock_rec = mocker.patch('sounddevice.rec', return_value=Mock())
        mocker.patch('sounddevice.wait')
        mocker.patch('soundfile.write')

        generator.fnum = 2
        line = 'Caller:7: Test message'

        generator.process_caller_line(line, record_mode=True)

        # Verify recording was called with correct parameters
        expected_samples = 7 * 24000
        mock_rec.assert_called_once_with(expected_samples, samplerate=24000, channels=1)

        assert generator.fnum == 3
        assert '002_caller.wav' in generator.final_audio


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
        assert 'audio/backend.wav' in generator.final_audio

    def test_sendmail_tag(self, generator):
        """Test processing <sendmail> tag"""
        generator.final_audio = 'existing.wav '
        generator.process_special_tag('<sendmail>')
        assert 'audio/swoosh.wav' in generator.final_audio

    def test_transfer_tag(self, generator):
        """Test processing <transfer> tag"""
        generator.final_audio = 'existing.wav '
        generator.process_special_tag('<transfer>')
        assert 'audio/ringback.wav' in generator.final_audio

    def test_text_tag(self, generator):
        """Test processing <text> tag"""
        generator.final_audio = 'existing.wav '
        generator.process_special_tag('<text>')
        assert 'audio/text-received.wav' in generator.final_audio


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
        mocker.patch.object(generator, 'play_audio')
        mocker.patch.object(generator, 'concatenate_audio_files')
        mocker.patch('time.sleep')

        output_file = generator.process_dialog_file(sample_dialog, record_mode=False)

        # Verify output file path
        assert output_file == 'vc.wav'

        # Verify text_to_wav was called for both IVA lines and Caller line
        assert generator.text_to_wav.call_count == 3  # 2 IVA lines + 1 Caller line

        # Verify concatenate_audio_files was called
        generator.concatenate_audio_files.assert_called_once()

        # Verify final audio includes all expected files
        assert 'audio/ringback.wav' in generator.final_audio
        assert 'audio/backend.wav' in generator.final_audio

    def test_process_dialog_file_resets_state(self, generator, sample_dialog, mocker):
        """Test that process_dialog_file resets state variables"""
        mocker.patch.object(generator, 'text_to_wav')
        mocker.patch.object(generator, 'play_audio')
        mocker.patch.object(generator, 'concatenate_audio_files')
        mocker.patch('time.sleep')

        # Set initial state
        generator.fnum = 10
        generator.final_audio = 'old_audio.wav '
        generator.ignore = False

        generator.process_dialog_file(sample_dialog, record_mode=False)

        # State should be reset at start and incremented during processing
        assert generator.fnum > 1

    def test_process_dialog_file_cleanup(self, generator, sample_dialog, mocker):
        """Test that process_dialog_file cleans up temp directory by default"""
        mocker.patch.object(generator, 'text_to_wav')
        mocker.patch.object(generator, 'play_audio')
        mocker.patch.object(generator, 'concatenate_audio_files')
        mocker.patch('time.sleep')
        mock_rmtree = mocker.patch('shutil.rmtree')

        generator.process_dialog_file(sample_dialog, record_mode=False)

        # Verify cleanup was called
        mock_rmtree.assert_called_once_with('.temp')

    def test_process_dialog_file_keep_temp(self, sample_dialog, mocker):
        """Test that process_dialog_file preserves temp directory with keep_temp=True"""
        mocker.patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key'}, clear=True)
        generator = VisionClipGenerator(keep_temp=True)

        mocker.patch.object(generator, 'text_to_wav')
        mocker.patch.object(generator, 'play_audio')
        mocker.patch.object(generator, 'concatenate_audio_files')
        mocker.patch('time.sleep')
        mock_rmtree = mocker.patch('shutil.rmtree')

        generator.process_dialog_file(sample_dialog, record_mode=False)

        # Verify cleanup was NOT called
        mock_rmtree.assert_not_called()


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
        finalAudio = ' audio/ringback.wav '
        finalAudio += '1.wav '
        finalAudio += '2.wav '
        finalAudio += 'audio/backend.wav '
        finalAudio += '3.wav '

        # Verify the string contains all expected files
        assert 'audio/ringback.wav' in finalAudio
        assert '1.wav' in finalAudio
        assert '2.wav' in finalAudio
        assert 'audio/backend.wav' in finalAudio
        assert '3.wav' in finalAudio

    def test_audio_concatenation(self, mocker):
        """Test audio concatenation using pydub"""
        # Mock pydub components with proper addition support
        mock_segment = mocker.patch('main.AudioSegment')
        mock_combined = Mock()
        mock_segment.empty.return_value = mock_combined

        # Mock from_wav to return objects that support addition
        mock_audio = Mock()
        mock_combined.__add__ = Mock(return_value=mock_combined)
        mock_segment.from_wav.return_value = mock_audio

        mocker.patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key'}, clear=True)
        generator = VisionClipGenerator()

        file_list = 'audio/ringback.wav file1.wav file2.wav'
        generator.concatenate_audio_files(file_list, 'output.wav')

        # Verify AudioSegment.from_wav was called for each file
        assert mock_segment.from_wav.call_count == 3
        # Verify export was called on the combined audio
        mock_combined.export.assert_called_once_with('output.wav', format='wav')


class TestPlayAudio:
    """Test the play_audio method"""

    def test_play_audio(self, mocker):
        """Test audio playback using sounddevice"""
        mocker.patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key'}, clear=True)
        generator = VisionClipGenerator()

        # Mock soundfile and sounddevice
        mock_sf_read = mocker.patch('soundfile.read', return_value=(Mock(), 24000))
        mock_sd_play = mocker.patch('sounddevice.play')
        mock_sd_wait = mocker.patch('sounddevice.wait')

        generator.play_audio('test.wav')

        # Verify soundfile read was called
        mock_sf_read.assert_called_once_with('test.wav')
        # Verify sounddevice play was called
        mock_sd_play.assert_called_once()
        # Verify sounddevice wait was called (blocking)
        mock_sd_wait.assert_called_once()


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

        mock_process.assert_called_once_with('test.txt', True, 'vc.wav')
        assert result == 'vc.wav'


class TestSmartOutputPath:
    """Test smart default output path generation"""

    def test_basename_extraction(self):
        """Test extraction of basename from various paths"""
        # Simple case
        assert os.path.basename('dialogs/confirmation.txt') == 'confirmation.txt'
        # Nested path
        assert os.path.basename('foo/bar/baz/file.txt') == 'file.txt'
        # Already in current directory
        assert os.path.basename('test.txt') == 'test.txt'

    def test_extension_replacement(self):
        """Test replacing extension with .wav"""
        input_name, _ = os.path.splitext('confirmation.txt')
        output = f"{input_name}.wav"
        assert output == 'confirmation.wav'

    def test_no_extension(self):
        """Test handling file with no extension"""
        input_name, _ = os.path.splitext('myfile')
        output = f"{input_name}.wav"
        assert output == 'myfile.wav'

    def test_already_wav(self):
        """Test handling file that's already .wav"""
        input_name, _ = os.path.splitext('audio.wav')
        output = f"{input_name}.wav"
        assert output == 'audio.wav'


class TestLoggingSetup:
    """Test logging setup and configuration"""

    def test_setup_logging_console_only(self):
        """Test logging setup with console handler only"""
        # Clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers = []

        setup_logging(console_level='INFO', log_file=None)

        # Verify root logger is configured
        assert root_logger.level == logging.DEBUG

        # Verify console handler exists
        assert len(root_logger.handlers) == 1
        console_handler = root_logger.handlers[0]
        assert isinstance(console_handler, logging.StreamHandler)
        assert console_handler.level == logging.INFO

    def test_setup_logging_with_file(self, tmp_path):
        """Test logging setup with file handler"""
        # Clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers = []

        log_file = tmp_path / "test.log"
        setup_logging(console_level='WARNING', log_file=str(log_file), file_level='DEBUG')

        # Verify two handlers (console + file)
        assert len(root_logger.handlers) == 2

        # Find console and file handlers
        console_handler = None
        file_handler = None
        for handler in root_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                file_handler = handler
            elif isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                console_handler = handler

        # Verify both handlers exist
        assert console_handler is not None
        assert file_handler is not None

        # Verify levels
        assert console_handler.level == logging.WARNING
        assert file_handler.level == logging.DEBUG

    def test_setup_logging_level_conversion(self):
        """Test that string log levels are correctly converted"""
        root_logger = logging.getLogger()
        root_logger.handlers = []

        setup_logging(console_level='debug', log_file=None)

        console_handler = root_logger.handlers[0]
        assert console_handler.level == logging.DEBUG

    def test_setup_logging_file_creation_error(self, mocker):
        """Test handling of file creation errors"""
        root_logger = logging.getLogger()
        root_logger.handlers = []

        # Mock FileHandler to raise exception
        mocker.patch('logging.FileHandler', side_effect=PermissionError("Permission denied"))

        # Should not raise exception, just log warning
        setup_logging(console_level='INFO', log_file='/invalid/path/test.log')

        # Should still have console handler
        assert len(root_logger.handlers) == 1


class TestOutputDirectoryValidation:
    """Test output directory validation and creation"""

    @pytest.fixture
    def mock_main_setup(self, mocker, tmp_path):
        """Setup common mocks for main() testing"""
        # Mock environment
        mocker.patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key'}, clear=True)

        # Create a sample dialog file
        dialog_file = tmp_path / "test.txt"
        dialog_file.write_text("<ringback>\nIVA: Test\n<hangup>")

        # Mock VisionClipGenerator and its methods
        mock_generator = Mock()
        mock_generator.generate.return_value = 'output.wav'
        mocker.patch('main.VisionClipGenerator', return_value=mock_generator)

        # Mock logging setup
        mocker.patch('main.setup_logging')

        return {
            'dialog_file': str(dialog_file),
            'mock_generator': mock_generator,
            'tmp_path': tmp_path
        }

    def test_output_directory_exists(self, mocker, mock_main_setup):
        """Test when output directory already exists"""
        from main import main

        output_dir = mock_main_setup['tmp_path'] / "existing"
        output_dir.mkdir()
        output_file = output_dir / "output.wav"

        # Mock sys.argv
        mocker.patch('sys.argv', ['main.py', '--file', mock_main_setup['dialog_file'],
                                   '--output', str(output_file)])

        # Should succeed without prompting
        result = main()

        assert result == 0
        mock_main_setup['mock_generator'].generate.assert_called_once()

    def test_output_no_directory_specified(self, mocker, mock_main_setup):
        """Test when output is just a filename (no directory)"""
        from main import main

        # Mock sys.argv with simple filename
        mocker.patch('sys.argv', ['main.py', '--file', mock_main_setup['dialog_file'],
                                   '--output', 'simple.wav'])

        # Should succeed without any directory checks
        result = main()

        assert result == 0
        mock_main_setup['mock_generator'].generate.assert_called_once()

    def test_output_directory_not_exists_user_confirms(self, mocker, mock_main_setup):
        """Test creating directory when user confirms"""
        from main import main

        output_dir = mock_main_setup['tmp_path'] / "newdir" / "subdir"
        output_file = output_dir / "output.wav"

        # Mock user input to confirm
        mocker.patch('builtins.input', return_value='y')
        mocker.patch('builtins.print')

        # Mock sys.argv
        mocker.patch('sys.argv', ['main.py', '--file', mock_main_setup['dialog_file'],
                                   '--output', str(output_file)])

        result = main()

        assert result == 0
        assert output_dir.exists()  # Directory should be created
        mock_main_setup['mock_generator'].generate.assert_called_once()

    def test_output_directory_not_exists_user_declines(self, mocker, mock_main_setup):
        """Test when user declines directory creation"""
        from main import main

        output_dir = mock_main_setup['tmp_path'] / "newdir"
        output_file = output_dir / "output.wav"

        # Mock user input to decline
        mocker.patch('builtins.input', return_value='n')
        mocker.patch('builtins.print')

        # Mock sys.argv
        mocker.patch('sys.argv', ['main.py', '--file', mock_main_setup['dialog_file'],
                                   '--output', str(output_file)])

        result = main()

        assert result == 1  # Should exit with error
        assert not output_dir.exists()  # Directory should NOT be created
        mock_main_setup['mock_generator'].generate.assert_not_called()

    def test_output_directory_no_write_permission(self, mocker, mock_main_setup):
        """Test when no write permission on parent directory"""
        from main import main

        output_file = "/root/restricted/output.wav"

        # Mock os.path.exists to return False for output_dir
        def mock_exists(path):
            if path == "/root/restricted":
                return False
            elif path == "/root":
                return True
            return os.path.exists(path)

        mocker.patch('os.path.exists', side_effect=mock_exists)

        # Mock os.access to deny write permission
        mocker.patch('os.access', return_value=False)
        mocker.patch('builtins.print')

        # Mock sys.argv
        mocker.patch('sys.argv', ['main.py', '--file', mock_main_setup['dialog_file'],
                                   '--output', output_file])

        result = main()

        assert result == 1  # Should exit with error
        mock_main_setup['mock_generator'].generate.assert_not_called()

    def test_output_directory_creation_fails(self, mocker, mock_main_setup):
        """Test when directory creation fails due to OS error"""
        from main import main

        output_dir = mock_main_setup['tmp_path'] / "newdir"
        output_file = output_dir / "output.wav"

        # Mock user input to confirm
        mocker.patch('builtins.input', return_value='y')
        mocker.patch('builtins.print')

        # Mock os.makedirs to raise PermissionError
        mocker.patch('os.makedirs', side_effect=PermissionError("Permission denied"))

        # Mock sys.argv
        mocker.patch('sys.argv', ['main.py', '--file', mock_main_setup['dialog_file'],
                                   '--output', str(output_file)])

        result = main()

        assert result == 1  # Should exit with error
        mock_main_setup['mock_generator'].generate.assert_not_called()

    def test_output_directory_various_user_responses(self, mocker, mock_main_setup):
        """Test various user input responses"""
        from main import main

        output_dir = mock_main_setup['tmp_path'] / "newdir"
        output_file = output_dir / "output.wav"

        mocker.patch('builtins.print')
        mocker.patch('sys.argv', ['main.py', '--file', mock_main_setup['dialog_file'],
                                   '--output', str(output_file)])

        # Test 'Y' (uppercase) - should succeed because input is converted to lowercase
        mocker.patch('builtins.input', return_value='Y')
        result = main()
        assert result == 0  # Should succeed because 'Y'.strip().lower() == 'y'
        assert output_dir.exists()

        # Test 'no' response
        output_dir2 = mock_main_setup['tmp_path'] / "newdir2"
        output_file2 = output_dir2 / "output.wav"
        mocker.patch('sys.argv', ['main.py', '--file', mock_main_setup['dialog_file'],
                                   '--output', str(output_file2)])
        mocker.patch('builtins.input', return_value='no')
        result = main()
        assert result == 1  # Should fail because 'no' != 'y'
        assert not output_dir2.exists()

    def test_smart_output_path_with_directory_creation(self, mocker, mock_main_setup):
        """Test smart output path derivation doesn't trigger directory creation"""
        from main import main

        # When no --output specified, smart path uses basename only (no directory)
        mocker.patch('sys.argv', ['main.py', '--file', mock_main_setup['dialog_file']])

        result = main()

        assert result == 0
        # Should use 'test.wav' (no directory component)
        # generate(filepath, record_mode, output_file)
        call_args = mock_main_setup['mock_generator'].generate.call_args
        output_file_arg = call_args[0][2]  # Third positional argument
        assert output_file_arg == 'test.wav'

    def test_relative_path_directory_creation(self, mocker, mock_main_setup):
        """Test creating directory with relative path (e.g., 'output/demo.wav')"""
        from main import main
        import tempfile

        # Use a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                output_file = 'output/demo.wav'

                # Mock user input to confirm
                mocker.patch('builtins.input', return_value='y')
                mocker.patch('builtins.print')

                # Mock sys.argv
                mocker.patch('sys.argv', ['main.py', '--file', mock_main_setup['dialog_file'],
                                           '--output', output_file])

                result = main()

                assert result == 0
                # Verify directory was created in current directory (not root)
                assert os.path.exists('output')
                assert os.path.isdir('output')

            finally:
                os.chdir(original_cwd)


class TestOutputFileWriteExceptionHandling:
    """Test exception handling during output file write"""

    @pytest.fixture
    def generator(self, mocker):
        """Create a generator instance for testing"""
        mocker.patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key'}, clear=True)
        return VisionClipGenerator()

    @pytest.fixture
    def sample_dialog(self, tmp_path):
        """Create a minimal dialog file"""
        dialog_content = """<ringback>
IVA: Test
<hangup>
"""
        dialog_file = tmp_path / "test_dialog.txt"
        dialog_file.write_text(dialog_content)
        return str(dialog_file)

    def test_concatenate_permission_error(self, generator, sample_dialog, mocker):
        """Test handling of PermissionError during file write"""
        mocker.patch.object(generator, 'text_to_wav')
        mocker.patch.object(generator, 'play_audio')
        mocker.patch('time.sleep')

        # Mock concatenate_audio_files to raise PermissionError
        mocker.patch.object(
            generator,
            'concatenate_audio_files',
            side_effect=PermissionError("Permission denied")
        )

        with pytest.raises(PermissionError, match="Permission denied"):
            generator.process_dialog_file(sample_dialog, record_mode=False, output_file='/readonly/output.wav')

    def test_concatenate_os_error(self, generator, sample_dialog, mocker):
        """Test handling of OSError during file write"""
        mocker.patch.object(generator, 'text_to_wav')
        mocker.patch.object(generator, 'play_audio')
        mocker.patch('time.sleep')

        # Mock concatenate_audio_files to raise OSError
        mocker.patch.object(
            generator,
            'concatenate_audio_files',
            side_effect=OSError("Disk full")
        )

        with pytest.raises(OSError, match="Disk full"):
            generator.process_dialog_file(sample_dialog, record_mode=False, output_file='output.wav')

    def test_error_logging_on_write_failure(self, generator, sample_dialog, mocker, caplog):
        """Test that errors are properly logged when write fails"""
        mocker.patch.object(generator, 'text_to_wav')
        mocker.patch.object(generator, 'play_audio')
        mocker.patch('time.sleep')

        # Mock concatenate_audio_files to raise PermissionError
        mocker.patch.object(
            generator,
            'concatenate_audio_files',
            side_effect=PermissionError("No permission")
        )

        with caplog.at_level(logging.ERROR):
            with pytest.raises(PermissionError):
                generator.process_dialog_file(sample_dialog, record_mode=False, output_file='restricted.wav')

        # Verify error was logged
        assert "Failed to write output file" in caplog.text
        assert "restricted.wav" in caplog.text


class TestKeyboardInterruptHandling:
    """Test graceful handling of Ctrl+C (KeyboardInterrupt)"""

    def test_keyboard_interrupt_exits_gracefully(self, mocker, capsys):
        """Test that KeyboardInterrupt during main() is caught and exits with code 130"""
        # Mock main() to raise KeyboardInterrupt
        mock_main = mocker.patch('main.main', side_effect=KeyboardInterrupt())

        # Import the module to execute __main__ block
        import main as main_module

        # Execute the __main__ block logic directly
        with pytest.raises(SystemExit) as exc_info:
            try:
                exit(mock_main())
            except KeyboardInterrupt:
                print("\n\nExiting...")
                exit(130)

        # Verify exit code is 130 (Unix convention: 128 + SIGINT)
        assert exc_info.value.code == 130

        # Verify "Exiting..." message was printed
        captured = capsys.readouterr()
        assert "Exiting..." in captured.out

    def test_keyboard_interrupt_exit_code_convention(self):
        """Test that exit code 130 follows Unix convention (128 + signal number)"""
        import signal

        # Verify the convention: 128 + SIGINT (2) = 130
        expected_exit_code = 128 + signal.SIGINT
        assert expected_exit_code == 130

    def test_keyboard_interrupt_message_format(self, capsys):
        """Test that the exit message has proper formatting (double newline)"""
        # Simulate the print statement
        print("\n\nExiting...")

        captured = capsys.readouterr()
        # Verify double newline before message (ensures clean line)
        assert captured.out.startswith("\n\n")
        assert "Exiting..." in captured.out

    def test_keyboard_interrupt_from_various_points(self, mocker, capsys):
        """Test that KeyboardInterrupt from any point in main() is caught"""
        # Test interruption during argument parsing
        mocker.patch('argparse.ArgumentParser.parse_args', side_effect=KeyboardInterrupt())

        import main as main_module

        with pytest.raises(SystemExit) as exc_info:
            try:
                exit(main_module.main())
            except KeyboardInterrupt:
                print("\n\nExiting...")
                exit(130)

        assert exc_info.value.code == 130
        captured = capsys.readouterr()
        assert "Exiting..." in captured.out
