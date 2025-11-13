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
Two implementations exist:
- **GoogleGenerateVC.py**: Uses Google Text-to-Speech API (recommended/current)
- **GenerateVC.py**: Uses Azure Cognitive Services (legacy, contains hardcoded subscription keys)

For Google TTS, create `env.sh`:
```bash
export GOOGLE_API_KEY=<your-api-key>
```

Source the file before running:
```bash
source env.sh
```

### Voice Customization
Environment variables for GoogleGenerateVC.py:
- `VA_LOCALE`: Virtual assistant locale (default: en-US)
- `VA_VOICE`: Virtual assistant voice (default: en-US-Journey-O)
- `CALLER_LOCALE`: Caller locale (default: en-US)
- `CALLER_VOICE`: Caller voice (default: en-US-Journey-D)

## Running the Application

### Execute a Vision Clip
```bash
# Using uv run (recommended)
uv run python GoogleGenerateVC.py --file dialogs/confirmation.txt --record 1

# Or activate the virtual environment first
source .venv/bin/activate
python GoogleGenerateVC.py --file dialogs/confirmation.txt --record 1
```

**Arguments**:
- `--file`: Path to vision clip script file (required)
- `--record`: Set to `1` to record caller audio via microphone; omit to use TTS for both sides (currently unsupported)

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
   - Special tags (`<backend>`, `<sendmail>`, `<transfer>`, `<text>`) → Insert pre-recorded audio from `Audio/` directory
4. **Audio stitching**: Uses sox to concatenate all segments into `vc.wav`

### Key Components

**GoogleGenerateVC.py** (primary script) - Class-based architecture:

The application is built around the `VisionClipGenerator` class:

```python
from GoogleGenerateVC import VisionClipGenerator

# Create generator instance (reads GOOGLE_API_KEY from environment)
generator = VisionClipGenerator()

# Or pass API key explicitly
generator = VisionClipGenerator(api_key='your-api-key')

# Generate audio from dialog file
output_file = generator.generate('dialogs/confirmation.txt', record_mode=True)
```

**VisionClipGenerator Class Methods**:
- `__init__(api_key)`: Initialize with API configuration and voice settings
- `text_to_wav(voice, rate, locale, text, filename)`: Convert text to WAV using Google TTS API
- `process_iva_line(line)`: Process IVA dialogue lines (TTS + playback)
- `process_caller_line(line, record_mode)`: Process Caller lines (record or TTS)
- `process_special_tag(line)`: Handle special audio tags (backend, sendmail, etc.)
- `process_dialog_file(filepath, record_mode)`: Main processing logic for dialog scripts
- `generate(filepath, record_mode)`: Public API for generating vision clips

**Technologies**:
- TTS via Google API: `text_to_wav()` method handles API calls
- Audio playback: Uses `afplay` (macOS)
- Recording: Uses `sounddevice` library for mic input
- Audio processing: Uses sox for format conversion and concatenation

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
- Pre-recorded audio effects stored in `Audio/` directory:
  - `ringback.wav`: Phone ringing
  - `backend.wav`: Backend processing sound
  - `swoosh.wav`: Email sent sound
  - `text-received.wav`: Text message notification
- Generated audio: Numbered files `1.wav`, `2.wav`, etc., created during execution
- Final output: `vc.wav` (concatenated audio of entire conversation)

### Dependencies
- **sox-14.4.2/**: Local sox installation for audio manipulation
- **sounddevice**: Python audio recording interface
- **soundfile**: Audio file I/O
- **requests**: HTTP client for API calls
- **protobuf**: Google API protocol buffers

## Important Notes

- **Recording mode** (`--record 1`) records caller audio via microphone
- **TTS-only mode** (omit `--record` flag) generates both sides using TTS (now fully supported with class-based refactoring)
- `GenerateVC.py` contains hardcoded Azure credentials and should not be used in production
- Output file `vc.wav` is always created in the current working directory
- The script uses `afplay` for audio playback, which is macOS-specific
- The application uses a class-based architecture with the `VisionClipGenerator` class for better testability and maintainability
