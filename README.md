# VisionClip Generator

## Pre-requisites

This project uses `uv` for Python environment and dependency management.

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
- Install all required dependencies (protobuf, requests, sounddevice, soundfile)
- Lock dependency versions in `uv.lock`

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
CALLER_LOCALE = os.getenv('CALLER_LOCALE', 'en-US')
CALLER_VOICE = os.getenv('CALLER_VOICE', 'en-US-Journey-D')

## Running Tests

This project includes comprehensive unit tests to validate the execution of the program.

### Run All Tests

```shell
# Using uv directly
uv run pytest

# Or using make
make test
```

### Run Tests with Coverage Report

```shell
# Using uv directly
uv run pytest --cov=. --cov-report=html

# Or using make
make test-cov
```

This will generate an HTML coverage report in the `htmlcov/` directory.

### Test Coverage

The test suite includes:
- TTS API payload validation
- Line parsing logic (IVA, Caller, special tags)
- Dialog file processing
- Environment variable handling
- Audio file operations
- Recording duration calculations
- Integration tests

All tests use mocking to avoid external dependencies and actual API calls.

## Class-Based Architecture

The application uses a class-based architecture with the `VisionClipGenerator` class for better testability and maintainability.

### Programmatic Usage

You can also use the generator programmatically in your own Python code:

```python
from main import VisionClipGenerator

# Create generator instance (reads GOOGLE_API_KEY from environment)
generator = VisionClipGenerator()

# Or pass API key explicitly
generator = VisionClipGenerator(api_key='your-api-key')

# Generate audio from dialog file
output_file = generator.generate('dialogs/confirmation.txt', record_mode=True)
print(f"Generated: {output_file}")
```

### Main Class Methods

- `__init__(api_key=None)`: Initialize with optional API key
- `generate(filepath, record_mode=False)`: Main entry point to generate vision clips
- `text_to_wav(voice, rate, locale, text, filename)`: Convert text to WAV
- `process_dialog_file(filepath, record_mode)`: Process entire dialog script

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
- `--output <path>` or `-o <path>`: Output file path (default: vc.wav)

**Examples**:
```shell
# Basic usage with default output
vision-clip --file dialogs/confirmation.txt

# With custom output location
vision-clip --file dialogs/confirmation.txt --output output/demo.wav

# With recording and custom output
vision-clip --file dialogs/confirmation.txt --record -o demos/interactive-demo.wav
```

**Modes**:
- **With `--record`**: Records caller audio from microphone (interactive mode)
- **Without `--record`**: Generates both IVA and caller audio using TTS (fully automated, useful for quick prototypes)

The voices can be customized using environment variables (see Voice Configuration above).

### Temporary Files

Intermediate audio files are generated during processing with improved naming:
- Format: `{sequence}_{speaker}.wav` (e.g., `001_va.wav`, `002_caller.wav`)
- Location: `.temp/` directory (auto-created, auto-cleaned)
- Cleanup: Automatically removed after successful generation

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


