# VisionClip Generator

## Pre-requisites

This project uses `uv` for Python environment and dependency management.

### System Dependencies

**Required:**
- Python 3.11 or higher
- `uv` package manager

**Optional (Recommended):**
- **ffmpeg**: Required for full audio format support with pydub
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get install ffmpeg`
  - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

**Platform-specific audio libraries** (usually pre-installed):
- macOS: CoreAudio (built-in)
- Linux: ALSA, PulseAudio, or JACK
- Windows: Windows Audio Session API (built-in)

### Install uv

If you don't have `uv` installed, install it first:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Setup Python Virtual Environment

To set up the Python virtual environment and install all dependencies:

```shell
uv sync
```

This will:
- Create a `.venv` virtual environment
- Install all required dependencies (protobuf, requests, sounddevice, soundfile, pydub, pyyaml)
- Lock dependency versions in `uv.lock`

**For Development (includes testing tools):**
```shell
uv sync --extra dev
```

This additionally installs:
- pytest (testing framework)
- pytest-mock (mocking support)
- pytest-cov (coverage reporting)

### Optional TTS Provider Dependencies

By default, the application uses **Google Cloud TTS**. To use other providers, install the optional dependencies:

```shell
# For Azure Cognitive Services TTS
uv sync --extra azure

# For AWS Polly TTS
uv sync --extra aws

# For all TTS providers
uv sync --extra all-providers
```

**Supported TTS Providers:**
- **Google Cloud TTS** (default) - No additional dependencies needed
- **Azure Cognitive Services** - Requires `--extra azure`
- **AWS Polly** - Requires `--extra aws`
- **ElevenLabs** - No additional dependencies needed (uses REST API)

## Configure API Key

Create a file name `env.sh` and add the following to the file:

```bash
export GOOGLE_API_KEY=<Google API Key>
```

## Voice Configuration

The following environment variables can be set to change the voice

`VA_LOCALE` - Locale of the virtual assistant e.g. en-US
`VA_VOICE` = os.getenv('VA_VOICE', 'en-US-Journey-O')
`CALLER_LOCALE` = os.getenv('CALLER_LOCALE', 'en-US')
`CALLER_VOICE` = os.getenv('CALLER_VOICE', 'en-US-Journey-D')

## Running Tests

This project includes comprehensive unit tests to validate the execution of the program.

### Setup for Testing

**Option 1: Using Make (Automatic - Recommended)**

The Makefile automatically detects and installs dev dependencies if needed:

```shell
make test
```

**Option 2: Manual Setup**

Install dev dependencies first, then run tests:

```shell
# Install dev dependencies
uv sync --extra dev

# Run tests
uv run --extra dev pytest -v
```

### Run All Tests

```shell
# Using make (auto-installs dev dependencies if needed)
make test

# Or using uv directly (requires dev dependencies installed)
uv run --extra dev pytest -v
```

### Run Tests with Coverage Report

```shell
# Using make (auto-installs dev dependencies if needed)
make test-cov

# Or using uv directly (requires dev dependencies installed)
uv run --extra dev pytest --cov=. --cov-report=html --cov-report=term-missing
```

This will generate an HTML coverage report in the `htmlcov/` directory.

### Manual Dev Dependencies Installation

If you need to manually install or reinstall dev dependencies:

```shell
make install-dev
# Or directly: uv sync --extra dev
```

### Test Coverage

The test suite includes:
- TTS API payload validation
- Line parsing logic (IVA, Caller, special tags)
- Dialog file processing
- Environment variable handling
- Audio file operations
- Recording duration calculations
- Output directory validation and permission checking
- File write exception handling with informative error messages
- User prompt interaction for directory creation
- Integration tests

All tests use mocking to avoid external dependencies and actual API calls.

### Cleaning Test Artifacts

Remove generated files including test coverage reports:

```shell
make clean
```

This removes:
- Generated `.wav` files
- `.temp/` directory
- `htmlcov/` coverage reports
- `.coverage` data
- `.pytest_cache/`
- Log files (`*.log`)

## Class-Based Architecture

The application uses a class-based architecture with the `VisionClipGenerator` class for better testability and maintainability.

### Programmatic Usage

You can also use the generator programmatically in your own Python code:

```python
from main import VisionClipGenerator
import os

# Create generator instance (reads GOOGLE_API_KEY from environment)
generator = VisionClipGenerator()

# Or pass API key explicitly
generator = VisionClipGenerator(api_key='your-api-key')

# Generate audio from dialog file
output_file = generator.generate('dialogs/confirmation.txt', record_mode=True)
print(f"Generated: {output_file}")

# When using custom output paths, ensure the directory exists
output_path = 'output/demos/my-clip.wav'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
generator.generate('dialogs/confirmation.txt', record_mode=False, output_file=output_path)
```

### Main Class Methods

- `__init__(api_key=None)`: Initialize with optional API key
- `generate(filepath, record_mode=False, output_file='vc.wav')`: Main entry point to generate vision clips
- `text_to_wav(voice, rate, locale, text, filename)`: Convert text to WAV
- `process_dialog_file(filepath, record_mode, output_file)`: Process entire dialog script

**Note**: When using programmatically, ensure output directories exist before calling `generate()`. The class will raise `PermissionError` or `OSError` with descriptive messages if the output file cannot be written.

## How to Execute the Script

The application provides multiple execution methods for different use cases:

### Method 1: Console Command (After Installation)

First, sync the environment to install the package:
```shell
uv sync
```

Then run using the `vision-clip` command:
```shell
vision-clip --file dialogs/confirmation.txt --record
```

### Method 2: Using uv run (No Installation Required - Recommended)

```shell
uv run vision-clip --file dialogs/confirmation.txt --record
```

### Method 3: Direct Script Execution (Legacy Compatibility)

```shell
python main.py --file dialogs/confirmation.txt --record
```

**Note**: Choose based on your workflow:
- **Method 1** (console command): Best after installation for production use
- **Method 2** (uv run): Best for development without explicit installation
- **Method 3** (direct): Simple and direct, maintains backward compatibility

**Arguments**:
- `--file <path>`: Path to vision clip dialog script file (required)
- `--record`: Record caller audio from microphone (interactive mode)
- `--output <path>` or `-o <path>`: Output file path (default: basename of input file with .wav extension)
- `--keep-temp`: Keep temporary audio files in .temp/ directory (useful for debugging)
- `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}`: Set console logging level (default: INFO)
- `--log-file [PATH]`: Enable file logging. Optionally specify path (default: vision-clip.log)
- `--log-file-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}`: Set file logging level (default: DEBUG)

**Examples**:
```shell
# Basic usage with smart default output (confirmation.txt → confirmation.wav)
vision-clip --file dialogs/confirmation.txt

# With custom output location
vision-clip --file dialogs/confirmation.txt --output output/demo.wav

# With recording and custom output
vision-clip --file dialogs/confirmation.txt --record -o demos/interactive-demo.wav

# Keep temporary files for inspection
vision-clip --file dialogs/confirmation.txt --keep-temp

# Enable debug logging to console
vision-clip --file dialogs/confirmation.txt --log-level DEBUG

# Enable file logging (creates vision-clip.log)
vision-clip --file dialogs/confirmation.txt --log-file

# Custom log file path
vision-clip --file dialogs/confirmation.txt --log-file logs/session.log

# Quiet console, verbose file logging
vision-clip --file dialogs/confirmation.txt --log-level WARNING --log-file

# Maximum verbosity everywhere
vision-clip --file dialogs/confirmation.txt --log-level DEBUG --log-file --log-file-level DEBUG
```

**Smart Default Output Path**:
By default, the output filename is derived from the input file:
- `dialogs/confirmation.txt` → `confirmation.wav`
- `foo/bar/test.txt` → `test.wav`
- `myfile` → `myfile.wav`
- Explicit `--output` always overrides this behavior

**Output Directory Validation**:
The application validates output paths before processing to prevent errors:
- **Directory existence**: If the output path includes a directory that doesn't exist, you'll be prompted to create it
- **Permission checking**: Validates write permissions on parent directories before attempting creation
- **User confirmation**: Prompts for confirmation before creating new directories
  ```
  Output directory does not exist: /path/to/newdir
  Create directory? (y/n):
  ```
- **Clear error messages**: If permissions are insufficient, provides actionable solutions:
  - Use a different output path with `--output`
  - Create the directory manually with `mkdir -p`
  - Fix permissions with `chmod +w`
- **Automatic handling**: Existing directories are used without prompting

**Logging**:
The application uses Python's standard logging module with flexible configuration:
- **Console logging**: Displays progress and messages (default: INFO level)
- **File logging**: Optional detailed logs (default: DEBUG level when enabled)
- **Log levels**: DEBUG (detailed), INFO (progress), WARNING (issues), ERROR (failures), CRITICAL (severe)
- **Default behavior**: INFO messages to console, no file logging
- **File logging**: Use `--log-file` to enable (creates vision-clip.log by default)
- **Verbosity control**: Different log levels for console and file output
- **Debugging**: Use `--log-level DEBUG` to see detailed operation information

**Modes**:
- **With `--record`**: Records caller audio from microphone (interactive mode)
- **Without `--record`**: Generates both IVA and caller audio using TTS (fully automated, useful for quick prototypes)

The voices can be customized using environment variables (see Voice Configuration above).

### Temporary Files

Intermediate audio files are generated during processing with improved naming:
- Format: `{sequence}_{speaker}.wav` (e.g., `001_va.wav`, `002_caller.wav`)
- Location: `.temp/` directory (auto-created)
- Cleanup: Automatically removed after successful generation (unless `--keep-temp` is used)
- Preservation: Use `--keep-temp` flag to keep files for debugging or inspection

## Operation
After running the script it will iterate through the text file. When it hits an IVA line it will call the API to
generate the audio from the text and then play the TTS through the laptop speakers. When it hits a User line it will
print out what you are supposed to say and print out “Speak Now” when you are supposed to speak. The User audio is
recorded through the laptop microphone. At the end of the call it will stitch all of the audio together in a file called “vc.wav”. 


Structure of the Script
Here is an example of a script:

Vision Clip 1: Complex Booking
Voice: Female
Caller: Male, early 30’s.

<ringback>

IVA: Thank you for calling.  I'm your Alaska Airlines virtual assistant.  How can I help you today?

Caller:7: I’m trying to book these tickets online, but it’s not letting me use award travel and my companion certificate.

IVA: I’m sorry to hear you are having problems booking your tickets. 

<backend>

IVA: Are you trying to use a companion certificate combined with an award travel ticket?

Caller:2: Yes

IVA: Unfortunately, the companion fare code is only valid for use when traveling with a guest on a paid published coach airfare. Do you want to look into your alternatives?

Caller:4: Yeah, let's do that.

IVA: OK, let’s take a look.  What is your mileage plan number?

Caller:7: Um, sure. it's uh 576 551 268

IVA: Got it.  One moment while I look up your account.

<backend>

IVA: OK. And for extra security, what’s the billing zip code?

Caller:4: Sure, It's 98116

IVA: Thanks Ben

<backend>

IVA: You were trying to book a main cabin fare on flight 340 from Seattle to Orlando on Friday, August 25th at 7:55 am, returning on flight 347 on Saturday, September 2nd at 9:00 am.  Is this the flight you are calling about?

Caller:3: Yes, that's it.

IVA:  Great!  How many passengers will there be?

Caller:3: Three of us.

IVA: Let me look up fares for you.  Just a sec.

<backend>

## Acknowledgments

This project was inspired by the original idea and working code developed by **Matt Panaccione** (matthew.panaccione@gmail.com) during our time working together at Kore AI. His innovative approach to creating conversational audio demos laid the foundation for this implementation.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
