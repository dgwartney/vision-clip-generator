# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vision Clip Generator is a Python application that creates conversational audio demos by combining Text-to-Speech (TTS) and live microphone recordings. It simulates phone conversations between an Interactive Voice Assistant (IVA) and a caller, stitching together audio segments to create realistic demo recordings.

## Setup and Configuration

### Installation
This project uses `uv` for Python environment and dependency management.

#### Prerequisites
Install `uv` if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Setup
```bash
# Sync dependencies and create virtual environment
uv sync

# Activate the virtual environment (optional, uv run handles this automatically)
source .venv/bin/activate
```

### API Configuration

The application now supports multiple TTS providers through a flexible abstraction layer:
- **Google Cloud TTS** (default/recommended)
- **Azure Cognitive Services**
- **ElevenLabs** (with voice cloning support)
- **AWS Polly**

#### Provider Selection

Choose a provider using environment variables or constructor parameters:

```bash
# Google TTS (default)
export TTS_PROVIDER=google
export GOOGLE_API_KEY=<your-api-key>

# Azure TTS
export TTS_PROVIDER=azure
export AZURE_SUBSCRIPTION_KEY=<your-key>
export AZURE_REGION=eastus

# ElevenLabs TTS
export TTS_PROVIDER=elevenlabs
export ELEVENLABS_API_KEY=<your-key>
export ELEVENLABS_VA_VOICE=<voice-id>
export ELEVENLABS_CALLER_VOICE=<voice-id>

# AWS Polly
export TTS_PROVIDER=aws
export AWS_ACCESS_KEY_ID=<your-key>
export AWS_SECRET_ACCESS_KEY=<your-secret>
export AWS_REGION=us-east-1
```

Or use constructor parameters:
```python
# Explicit provider selection
generator = VisionClipGenerator(tts_provider='google', api_key='xxx')

# Pre-configured provider instance
from tts import create_tts_provider
provider = create_tts_provider('elevenlabs', api_key='xxx', va_voice='voice-id')
generator = VisionClipGenerator(tts_instance=provider)
```

### Voice Customization

Environment variables for voice configuration (provider-specific defaults):

**Google TTS**:
- `VA_LOCALE`: Virtual assistant locale (default: en-US)
- `VA_VOICE`: Virtual assistant voice (default: en-US-Journey-O)
- `CALLER_LOCALE`: Caller locale (default: en-US)
- `CALLER_VOICE`: Caller voice (default: en-US-Journey-D)

**Azure TTS**:
- `AZURE_VA_VOICE`: Virtual assistant voice (default: en-US-JennyNeural)
- `AZURE_CALLER_VOICE`: Caller voice (default: en-US-GuyNeural)

**ElevenLabs**:
- `ELEVENLABS_VA_VOICE`: Virtual assistant voice ID (required)
- `ELEVENLABS_CALLER_VOICE`: Caller voice ID (required)
- `ELEVENLABS_MODEL`: Model to use (default: eleven_monolingual_v1)

**AWS Polly**:
- `AWS_VA_VOICE`: Virtual assistant voice (default: Joanna)
- `AWS_CALLER_VOICE`: Caller voice (default: Matthew)

## Running the Application

The application provides multiple execution methods for different use cases:

### Method 1: Console Command (After Installation)

First, sync the environment to install the package:
```bash
uv sync
```

Then run using the `vision-clip` command:
```bash
vision-clip --file dialogs/confirmation.txt --record 1
```

### Method 2: Using uv run (No Installation Required - Recommended)

```bash
uv run vision-clip --file dialogs/confirmation.txt --record 1
```

### Method 3: Direct Script Execution (Legacy Compatibility)

```bash
python main.py --file dialogs/confirmation.txt --record 1
```

**Arguments**:
- `--file`: Path to vision clip script file (required)
- `--record`: Set to `1` to record caller audio via microphone; omit to use TTS for both sides

### Clean Generated Audio Files
```bash
make clean
```
Removes all generated `.wav` files.

### Run Tests
```bash
# Run all tests
make test

# Run tests with coverage report
make test-cov
```

The project includes comprehensive unit tests in the `tests/` directory covering:
- TTS API payload validation and audio decoding
- Line parsing logic (IVA, Caller, special tags)
- Dialog file processing
- Environment variable handling
- Audio file operations and sox command construction
- Recording duration calculations
- Integration tests with temporary files

All tests use mocking to avoid external dependencies and actual API calls.

## Architecture

### Script Processing Flow
1. **Parse script file**: Reads line-by-line from dialog text file
2. **State management**: Ignores lines until `<ringback>` tag, stops at `<hangup>`
3. **Line-by-line processing**:
   - `IVA:` lines → Generate TTS, play through speakers, add to final audio
   - `Caller:N:` lines → Record from mic for N seconds (when `--record` flag present)
   - Special tags (`<backend>`, `<sendmail>`, `<transfer>`, `<text>`) → Insert pre-recorded audio from `audio/` directory
4. **Audio stitching**: Uses sox to concatenate all segments into `vc.wav`

### Key Components

**main.py** (primary script) - Class-based architecture:

The application is built around the `VisionClipGenerator` class:

```python
from main import VisionClipGenerator

# Create generator instance (reads GOOGLE_API_KEY from environment)
generator = VisionClipGenerator()

# Or pass API key explicitly
generator = VisionClipGenerator(api_key='your-api-key')

# Generate audio from dialog file
output_file = generator.generate('dialogs/confirmation.txt', record_mode=True)
```

**VisionClipGenerator Class Methods**:
- `__init__(api_key, tts_provider, tts_instance, **tts_config)`: Initialize with TTS provider and voice settings
- `text_to_wav(voice, rate, locale, text, filename)`: Convert text to WAV using configured TTS provider
- `process_iva_line(line)`: Process IVA dialogue lines (TTS + playback)
- `process_caller_line(line, record_mode)`: Process Caller lines (record or TTS)
- `process_special_tag(line)`: Handle special audio tags (backend, sendmail, etc.)
- `process_dialog_file(filepath, record_mode)`: Main processing logic for dialog scripts
- `generate(filepath, record_mode)`: Public API for generating vision clips

**Technologies**:
- **TTS Abstraction Layer**: Flexible provider system supporting Google, Azure, ElevenLabs, and AWS
- Audio playback: Uses `afplay` (macOS)
- Recording: Uses `sounddevice` library for mic input
- Audio processing: Uses sox for format conversion and concatenation

### TTS Abstraction Layer

The application now uses a modular TTS abstraction layer (`tts/` module) that enables easy switching between different TTS providers.

#### Architecture

**Core Components**:

1. **TTSProvider Protocol** (`tts/base.py`): Base interface all providers implement
   - `synthesize(text, voice, locale, rate, output_file)`: Generate speech audio
   - `get_capabilities()`: Return provider capabilities
   - `configure(**kwargs)`: Configure provider settings

2. **TTSFactory** (`tts/factory.py`): Factory pattern for creating providers
   - Auto-registers available providers on import
   - Supports hybrid configuration (constructor > env vars > config file > defaults)
   - Runtime provider selection

3. **TTSCapabilities** (`tts/capabilities.py`): Feature detection system
   - Describes what each provider supports (streaming, SSML, custom voices, etc.)
   - Runtime capability checking

4. **Optional Features** (`tts/features.py`): Protocol-based feature interfaces
   - `StreamingCapable`: For providers supporting audio streaming
   - `SSMLCapable`: For providers supporting SSML markup
   - `CustomVoiceCapable`: For providers with voice cloning (e.g., ElevenLabs)
   - `AudioEffectsCapable`: For providers with audio effects profiles

#### Provider Implementations

**Google TTS Provider** (`tts/providers/google_tts.py`):
- HTTP API-based implementation
- Supports audio effects profiles (telephony-class-application)
- Supports rate and pitch control
- No SSML support in current implementation

**Azure TTS Provider** (`tts/providers/azure_tts.py`):
- Uses Azure Cognitive Services SDK
- Supports SSML for fine-grained control
- Neural and standard voices
- Requires: `azure-cognitiveservices-speech` package

**ElevenLabs Provider** (`tts/providers/elevenlabs_tts.py`):
- HTTP API-based implementation
- Voice cloning support with custom voice IDs
- Streaming audio generation
- Best for high-quality, expressive voices

**AWS Polly Provider** (`tts/providers/aws_polly.py`):
- Uses boto3 SDK
- Supports SSML
- Neural and standard engines
- Requires: `boto3` package

#### Usage Examples

**Basic usage with default provider**:
```python
from main import VisionClipGenerator

# Uses Google TTS by default (from GOOGLE_API_KEY env var)
generator = VisionClipGenerator()
output = generator.generate('dialogs/demo.txt', record_mode=False)
```

**Explicit provider selection**:
```python
# Use Azure TTS
generator = VisionClipGenerator(
    tts_provider='azure',
    subscription_key='your-azure-key',
    region='eastus'
)

# Use ElevenLabs with voice cloning
generator = VisionClipGenerator(
    tts_provider='elevenlabs',
    api_key='your-elevenlabs-key',
    va_voice='voice-id-1',
    caller_voice='voice-id-2'
)
```

**Pre-configured provider instance**:
```python
from tts import create_tts_provider

# Create and configure provider separately
provider = create_tts_provider(
    'google',
    api_key='your-key',
    va_voice='en-US-Journey-O'
)

# Use with generator
generator = VisionClipGenerator(tts_instance=provider)
```

**Configuration file approach**:
```yaml
# tts_config.yaml
provider: google
google:
  api_key: your-api-key
  va_voice: en-US-Journey-O
  caller_voice: en-US-Journey-D
```

```python
from tts import create_tts_provider

provider = create_tts_provider(config_file='tts_config.yaml')
generator = VisionClipGenerator(tts_instance=provider)
```

**Feature detection**:
```python
from tts import has_feature
from tts.features import StreamingCapable, SSMLCapable

# Check if provider supports specific features
if has_feature(provider, StreamingCapable):
    # Use streaming synthesis
    for chunk in provider.synthesize_stream(text, voice, locale):
        process_audio_chunk(chunk)

if has_feature(provider, SSMLCapable):
    # Use SSML for fine-grained control
    ssml = '<speak><prosody rate="slow">Hello world</prosody></speak>'
    audio = provider.synthesize_ssml(ssml, voice, locale)
```

#### Configuration Precedence

The TTS abstraction uses a hybrid configuration system with the following precedence (highest to lowest):

1. **Constructor arguments**: Direct parameters passed to `VisionClipGenerator()` or `create_tts_provider()`
2. **Environment variables**: Provider-specific env vars (e.g., `GOOGLE_API_KEY`, `TTS_PROVIDER`)
3. **Configuration file**: YAML file specified via `config_file` parameter
4. **Built-in defaults**: Sensible defaults for each provider

This allows flexible deployment across different environments while maintaining backward compatibility.

**Caller line format**: `Caller:N: text`
- N = duration in seconds for recording
- Example: `Caller:5: Our flight does not arrive until 5PM.` → record for 5 seconds

**Dialog Script Structure**:
```
Vision Clip 1: [Title]
Voice: [Description]
Caller: [Description]

<ringback>
IVA: [Virtual assistant speech]
Caller:N: [What user should say, with N-second recording duration]
<backend>
...
<hangup>
```

### Audio Files
- Pre-recorded audio effects stored in `audio/` directory:
  - `ringback.wav`: Phone ringing
  - `backend.wav`: Backend processing sound
  - `swoosh.wav`: Email sent sound
  - `text-received.wav`: Text message notification
- Generated audio: Numbered files `1.wav`, `2.wav`, etc., created during execution
- Final output: `vc.wav` (concatenated audio of entire conversation)

### Dependencies

**Core Dependencies** (always required):
- **sox-14.4.2/**: Local sox installation for audio manipulation
- **sounddevice**: Python audio recording interface
- **soundfile**: Audio file I/O
- **requests**: HTTP client for API calls (used by Google and ElevenLabs providers)
- **protobuf**: Protocol buffers (used by Google API)
- **pyyaml**: YAML configuration file support

**Provider-Specific Dependencies** (install as needed):
- **Google TTS** (default): No additional dependencies (uses `requests`)
- **Azure TTS**: `azure-cognitiveservices-speech` package
  ```bash
  pip install azure-cognitiveservices-speech
  ```
- **AWS Polly**: `boto3` package
  ```bash
  pip install boto3
  ```
- **ElevenLabs**: No additional dependencies (uses `requests`)

## Important Notes

- **TTS Abstraction Layer**: The application now supports multiple TTS providers (Google, Azure, ElevenLabs, AWS) through a unified interface
- **Recording mode** (`--record 1`) records caller audio via microphone
- **TTS-only mode** (omit `--record` flag) generates both sides using TTS (fully supported)
- **Backward compatibility**: Existing scripts using `VisionClipGenerator(api_key='...')` continue to work with Google TTS
- **Provider selection**: Use `TTS_PROVIDER` environment variable or `tts_provider` parameter to select a different provider
- `GenerateVC.py` (legacy Azure implementation) contains hardcoded credentials and should not be used - use the new TTS abstraction layer instead
- Output file `vc.wav` is always created in the current working directory
- The script uses `afplay` for audio playback, which is macOS-specific
- The application uses a class-based architecture with comprehensive test coverage for maintainability

## Adding New TTS Providers

To add a new TTS provider to the abstraction layer:

1. **Create provider class** in `tts/providers/your_provider.py`:
   ```python
   from tts.base import TTSProvider, TTSConfigurationError
   from tts.capabilities import TTSCapabilities

   class YourTTSProvider:
       def __init__(self, api_key, **kwargs):
           # Initialize provider
           pass

       @property
       def name(self) -> str:
           return "your_provider"

       def get_capabilities(self) -> TTSCapabilities:
           return TTSCapabilities(...)

       def synthesize(self, text, voice, locale, rate, output_file):
           # Implement synthesis logic
           pass

       def configure(self, **kwargs):
           # Configure provider
           pass
   ```

2. **Register provider** in `tts/factory.py`:
   ```python
   from tts.providers.your_provider import YourTTSProvider
   TTSFactory.register_provider('your_provider', YourTTSProvider)
   ```

3. **Add configuration defaults** in `tts/config.py`:
   ```python
   DEFAULTS = {
       ...
       "your_provider": {
           "api_key": None,
           "va_voice": "default-voice",
           ...
       }
   }
   ```

4. **Add tests** in `tests/test_tts_abstraction.py` to verify provider functionality

The factory will automatically make your provider available via `create_tts_provider('your_provider', ...)`
