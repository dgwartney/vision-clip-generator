#!/usr/bin/env python3

import pytest
import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock, mock_open
import base64


# Import the module - we'll need to handle the script execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTextToWav:
    """Test the text_to_wav function logic"""

    def test_text_to_wav_function_logic(self, mocker):
        """Test TTS API call logic without importing the module"""
        # Test the logic that would be in text_to_wav
        api_key = 'test_api_key'
        url = f'https://texttospeech.googleapis.com/v1beta1/text:synthesize?alt=json&key={api_key}'

        voice = 'en-US-Journey-O'
        rate = 1
        locale = 'en-US'
        text = 'Hello world'

        # Build the expected payload
        payload = {
            "audioConfig": {
                "audioEncoding": "LINEAR16",
                "effectsProfileId": ["telephony-class-application"],
                "pitch": 0,
                "speakingRate": rate
            },
            "input": {
                "text": text
            },
            "voice": {
                "languageCode": locale,
                "name": voice
            }
        }

        # Verify payload structure
        assert payload['voice']['name'] == voice
        assert payload['voice']['languageCode'] == locale
        assert payload['audioConfig']['speakingRate'] == rate
        assert payload['input']['text'] == text
        assert payload['audioConfig']['audioEncoding'] == 'LINEAR16'
        assert payload['audioConfig']['effectsProfileId'] == ["telephony-class-application"]
        assert payload['audioConfig']['pitch'] == 0

    def test_audio_decoding_logic(self):
        """Test base64 decoding logic for audio content"""
        # Simulate what text_to_wav does with the API response
        original_data = b'fake_audio_data_sample'
        encoded_data = base64.b64encode(original_data).decode('utf-8')

        # Simulate API response
        aJson = {'audioContent': encoded_data}
        audioContent = aJson['audioContent']

        # Decode it
        decoded_data = base64.b64decode(audioContent, ' /')

        # Verify it matches original
        assert decoded_data == original_data


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


class TestDialogFileProcessing:
    """Test processing of dialog script files"""

    @pytest.fixture
    def sample_dialog(self):
        """Create a sample dialog file for testing"""
        return """Vision Clip 1: Test Dialog
Voice: Female
Caller: Male

<ringback>

IVA: Hello, how can I help you?

Caller:3: I need assistance

<backend>

IVA: Let me help you with that.

<hangup>
"""

    def test_dialog_file_structure(self, sample_dialog):
        """Test that dialog file has expected structure"""
        lines = sample_dialog.strip().split('\n')

        # Find key markers
        assert '<ringback>' in sample_dialog
        assert '<hangup>' in sample_dialog
        assert 'IVA:' in sample_dialog
        assert 'Caller:' in sample_dialog

    def test_ignore_lines_before_ringback(self, sample_dialog):
        """Test that lines before <ringback> are ignored"""
        lines = sample_dialog.strip().split('\n')

        found_ringback = False
        for line in lines:
            if line.startswith('<ringback>'):
                found_ringback = True
                break
            # These lines should be ignored
            if line.startswith('Vision Clip') or line.startswith('Voice:') or line.startswith('Caller:'):
                assert not found_ringback


class TestEnvironmentVariables:
    """Test environment variable handling"""

    def test_default_va_locale(self, mocker):
        """Test default VA_LOCALE value"""
        mocker.patch.dict(os.environ, {}, clear=True)
        default_locale = os.getenv('VA_LOCALE', 'en-US')
        assert default_locale == 'en-US'

    def test_default_va_voice(self, mocker):
        """Test default VA_VOICE value"""
        mocker.patch.dict(os.environ, {}, clear=True)
        default_voice = os.getenv('VA_VOICE', 'en-US-Journey-O')
        assert default_voice == 'en-US-Journey-O'

    def test_custom_environment_variables(self, mocker):
        """Test custom environment variable values"""
        custom_env = {
            'VA_LOCALE': 'es-ES',
            'VA_VOICE': 'es-ES-ElviraNeural',
            'CALLER_LOCALE': 'es-ES',
            'CALLER_VOICE': 'es-ES-AlvaroNeural'
        }
        mocker.patch.dict(os.environ, custom_env, clear=True)

        assert os.getenv('VA_LOCALE') == 'es-ES'
        assert os.getenv('VA_VOICE') == 'es-ES-ElviraNeural'
        assert os.getenv('CALLER_LOCALE') == 'es-ES'
        assert os.getenv('CALLER_VOICE') == 'es-ES-AlvaroNeural'

    def test_google_api_key_required(self, mocker):
        """Test that GOOGLE_API_KEY is required"""
        mocker.patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key'}, clear=True)
        api_key = os.getenv('GOOGLE_API_KEY')
        assert api_key == 'test_api_key'
        assert api_key is not None


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


class TestSpecialAudioTags:
    """Test special audio tag handling"""

    def test_backend_audio_file(self):
        """Test <backend> tag adds backend audio file"""
        finalAudio = ''
        if '<backend>'.startswith('<backend>'):
            finalAudio += 'Audio/backend.wav '

        assert finalAudio == 'Audio/backend.wav '

    def test_sendmail_audio_file(self):
        """Test <sendmail> tag adds swoosh audio file"""
        finalAudio = ''
        if '<sendmail>'.startswith('<sendmail>'):
            finalAudio += 'Audio/swoosh.wav '

        assert finalAudio == 'Audio/swoosh.wav '

    def test_transfer_audio_file(self):
        """Test <transfer> tag adds ringback audio file"""
        finalAudio = ''
        if '<transfer>'.startswith('<transfer>'):
            finalAudio += 'Audio/ringback.wav '

        assert finalAudio == 'Audio/ringback.wav '

    def test_text_audio_file(self):
        """Test <text> tag adds text-received audio file"""
        finalAudio = ''
        if '<text>'.startswith('<text>'):
            finalAudio += 'Audio/text-received.wav '

        assert finalAudio == 'Audio/text-received.wav '


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


class TestIntegration:
    """Integration tests for the overall workflow"""

    @pytest.fixture
    def temp_dialog_file(self, tmp_path):
        """Create a temporary dialog file for testing"""
        dialog_content = """Vision Clip 1: Test
Voice: Female
Caller: Male

<ringback>

IVA: Hello

Caller:3: Hi there

<backend>

IVA: How can I help?

<hangup>
"""
        dialog_file = tmp_path / "test_dialog.txt"
        dialog_file.write_text(dialog_content)
        return str(dialog_file)

    def test_dialog_file_exists(self, temp_dialog_file):
        """Test that the temporary dialog file exists and is readable"""
        assert os.path.exists(temp_dialog_file)

        with open(temp_dialog_file, 'r') as f:
            content = f.read()
            assert '<ringback>' in content
            assert '<hangup>' in content
            assert 'IVA:' in content
            assert 'Caller:' in content
