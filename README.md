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

## SOX

## How to Execute the Script

From the command line, use one of the following methods:

### Option 1: Using uv run (recommended)

```shell
uv run python GoogleGenerateVC.py --file ScriptName.txt --record 1
```

### Option 2: Activate virtual environment first

```shell
source .venv/bin/activate
python GoogleGenerateVC.py --file ScriptName.txt --record 1
```

**Note**: in the above there are two _- signs before "file" and "record". The script name is the name of the vision clip definition file (the script of the conversation). Without the record option the script is supposed to record both sides of the conversation in TTS, caller in one voice and the IVA in another. Currently I have not updated that code so it should fail, if for some reason we want to support this to make quick pro-types without re-recording every time I can update the script to support this. Currently we also would need to modify the python script to change the voice used in the demo.

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


