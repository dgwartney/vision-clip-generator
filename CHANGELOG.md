# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-02-14

### Added
- Comprehensive unit tests for AWS Polly TTS provider (10 tests, 85% coverage)
- Comprehensive unit tests for Azure TTS provider (11 tests, 82% coverage)
- Comprehensive unit tests for ElevenLabs TTS provider (14 tests, 92% coverage)
- Development workflow makefile targets: `install-dev` and `check-dev`
- Enhanced testing documentation in README with multiple test execution approaches
- System dependencies documentation (Python, uv, ffmpeg)
- CHANGELOG.md following Keep a Changelog format

### Changed
- Overall test coverage increased from 75% to 93%
- Improved makefile `clean` target to remove all test artifacts (htmlcov, .coverage, .pytest_cache, *.log)
- Enhanced README with comprehensive testing instructions

## [0.1.0] - 2026-02-14

### Added
- TTS abstraction layer supporting multiple providers:
  - Google Cloud TTS (default)
  - Azure Cognitive Services TTS
  - AWS Polly
  - ElevenLabs (with voice cloning support)
- Cross-platform audio support using Python packages (sounddevice, pydub)
- Comprehensive Python standard library logging system with file and console output
- `--log-level` flag to control console logging verbosity
- `--log-file` flag to enable file logging with optional custom path
- `--keep-temp` flag to preserve temporary audio files for debugging
- Smart default output path (derives filename from input file basename)
- `-o`/`--output` flag for custom output file paths
- Console command entry point: `vision-clip`
- MIT License
- Comprehensive unit test suite (69 initial tests) covering:
  - TTS API interactions
  - Line parsing logic
  - Dialog file processing
  - Audio operations and concatenation
  - Environment variable handling

### Changed
- Replaced afplay (macOS-only) with sounddevice for cross-platform audio playback
- Replaced SOX (external dependency) with Python packages for audio processing
- Refactored audio file naming to sequential format (001_va.wav, 002_caller.wav)
- Improved `--record` argument to boolean flag (no argument value needed)
- Renamed `Audio` directory to `audio` for consistency

### Removed
- Legacy `GenerateVC.py` script (functionality superseded by TTS abstraction layer)
- SOX binaries (replaced with Python packages)
- afplay dependency (macOS-specific, replaced with cross-platform alternative)

### Fixed
- Cross-platform compatibility issues with audio playback and processing
- Platform-specific audio library dependencies

## Project Background

Vision Clip Generator creates conversational audio demos by combining Text-to-Speech (TTS) and live microphone recordings. It simulates phone conversations between an Interactive Voice Assistant (IVA) and a caller, stitching together audio segments to create realistic demo recordings.

**Key Features:**
- Multiple TTS provider support with easy switching
- Record caller audio via microphone or generate with TTS
- Process dialog scripts with IVA/Caller line parsing
- Insert pre-recorded audio effects (ringback, backend processing, notifications)
- Automatic audio concatenation and cleanup
- Class-based architecture with comprehensive test coverage

**Technologies:**
- Python 3.11+
- uv package manager
- sounddevice, soundfile, pydub for audio processing
- pytest for testing
