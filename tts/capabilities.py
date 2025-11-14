"""TTS provider capabilities system."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TTSCapabilities:
    """
    Describes the capabilities supported by a TTS provider.

    This allows runtime feature detection so code can gracefully handle
    providers with different feature sets.
    """

    # Core capabilities
    supports_streaming: bool = False
    """Whether the provider supports streaming audio generation"""

    supports_ssml: bool = False
    """Whether the provider supports SSML (Speech Synthesis Markup Language)"""

    supports_custom_voices: bool = False
    """Whether the provider supports custom voice IDs (e.g., voice cloning)"""

    # Audio format capabilities
    supported_audio_formats: List[str] = field(default_factory=lambda: ["wav"])
    """List of supported audio formats (e.g., ['wav', 'mp3', 'ogg'])"""

    # Limitations
    max_text_length: Optional[int] = None
    """Maximum text length per request (characters). None means no limit."""

    max_requests_per_minute: Optional[int] = None
    """Rate limit for API requests. None means no documented limit."""

    # Voice configuration
    supports_pitch_control: bool = True
    """Whether the provider supports pitch adjustment"""

    supports_rate_control: bool = True
    """Whether the provider supports speaking rate adjustment"""

    supports_volume_control: bool = False
    """Whether the provider supports volume adjustment"""

    # Advanced features
    supports_phoneme_input: bool = False
    """Whether the provider supports phonetic transcription input"""

    supports_audio_effects: bool = False
    """Whether the provider supports audio effects (e.g., telephony profile)"""

    supports_multi_speaker: bool = False
    """Whether the provider supports multiple speakers in one synthesis"""

    # Provider metadata
    requires_api_key: bool = True
    """Whether the provider requires an API key for authentication"""

    supports_offline_mode: bool = False
    """Whether the provider can work without internet connection"""

    def __repr__(self) -> str:
        """Return a human-readable representation of capabilities."""
        features = []
        if self.supports_streaming:
            features.append("streaming")
        if self.supports_ssml:
            features.append("SSML")
        if self.supports_custom_voices:
            features.append("custom voices")
        if self.supports_audio_effects:
            features.append("audio effects")

        feature_str = ", ".join(features) if features else "basic synthesis only"
        return f"TTSCapabilities({feature_str})"

    def has_feature(self, feature: str) -> bool:
        """
        Check if a specific feature is supported.

        Args:
            feature: Feature name (e.g., 'streaming', 'ssml', 'custom_voices')

        Returns:
            True if the feature is supported, False otherwise
        """
        feature_map = {
            "streaming": self.supports_streaming,
            "ssml": self.supports_ssml,
            "custom_voices": self.supports_custom_voices,
            "pitch_control": self.supports_pitch_control,
            "rate_control": self.supports_rate_control,
            "volume_control": self.supports_volume_control,
            "phoneme_input": self.supports_phoneme_input,
            "audio_effects": self.supports_audio_effects,
            "multi_speaker": self.supports_multi_speaker,
            "offline_mode": self.supports_offline_mode,
        }
        return feature_map.get(feature.lower(), False)
