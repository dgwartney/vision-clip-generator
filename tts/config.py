"""Configuration manager for TTS providers.

Implements hybrid configuration with precedence:
1. Constructor arguments (highest priority)
2. Environment variables
3. Configuration file (tts_config.yaml)
4. Defaults (lowest priority)
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class TTSConfig:
    """
    Manages TTS provider configuration with multiple sources.

    Configuration precedence (highest to lowest):
    1. Constructor arguments
    2. Environment variables
    3. Configuration file
    4. Built-in defaults
    """

    # Default configuration values
    DEFAULTS = {
        "provider": "google",
        "google": {
            "api_key": None,
            "va_voice": "en-US-Journey-O",
            "va_locale": "en-US",
            "caller_voice": "en-US-Journey-D",
            "caller_locale": "en-US",
        },
        "azure": {
            "subscription_key": None,
            "region": "eastus",
            "va_voice": "en-US-JennyNeural",
            "va_locale": "en-US",
            "caller_voice": "en-US-GuyNeural",
            "caller_locale": "en-US",
        },
        "elevenlabs": {
            "api_key": None,
            "va_voice": None,  # Voice ID required
            "caller_voice": None,  # Voice ID required
            "model": "eleven_monolingual_v1",
        },
        "aws": {
            "access_key_id": None,
            "secret_access_key": None,
            "region": "us-east-1",
            "va_voice": "Joanna",
            "caller_voice": "Matthew",
            "va_locale": "en-US",
            "caller_locale": "en-US",
        },
    }

    # Environment variable mappings
    ENV_VAR_MAP = {
        "provider": "TTS_PROVIDER",
        "google.api_key": "GOOGLE_API_KEY",
        "google.va_voice": "VA_VOICE",
        "google.va_locale": "VA_LOCALE",
        "google.caller_voice": "CALLER_VOICE",
        "google.caller_locale": "CALLER_LOCALE",
        "azure.subscription_key": "AZURE_SUBSCRIPTION_KEY",
        "azure.region": "AZURE_REGION",
        "azure.va_voice": "AZURE_VA_VOICE",
        "azure.caller_voice": "AZURE_CALLER_VOICE",
        "elevenlabs.api_key": "ELEVENLABS_API_KEY",
        "elevenlabs.va_voice": "ELEVENLABS_VA_VOICE",
        "elevenlabs.caller_voice": "ELEVENLABS_CALLER_VOICE",
        "elevenlabs.model": "ELEVENLABS_MODEL",
        "aws.access_key_id": "AWS_ACCESS_KEY_ID",
        "aws.secret_access_key": "AWS_SECRET_ACCESS_KEY",
        "aws.region": "AWS_REGION",
        "aws.va_voice": "AWS_VA_VOICE",
        "aws.caller_voice": "AWS_CALLER_VOICE",
    }

    def __init__(
        self,
        config_file: Optional[str] = None,
        **overrides
    ):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to YAML config file (optional)
            **overrides: Direct configuration overrides (highest priority)
        """
        self.config_file = config_file
        self.overrides = overrides
        self._config = None

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value with precedence resolution.

        Args:
            key: Configuration key (supports dot notation, e.g., 'google.api_key')
            default: Default value if not found

        Returns:
            Configuration value with precedence applied
        """
        if self._config is None:
            self._config = self._build_config()

        # Navigate nested keys
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value if value is not None else default

    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """
        Get all configuration for a specific provider.

        Args:
            provider: Provider name (e.g., 'google', 'azure')

        Returns:
            Dictionary of provider configuration
        """
        if self._config is None:
            self._config = self._build_config()

        return self._config.get(provider, {})

    def _build_config(self) -> Dict[str, Any]:
        """
        Build the final configuration by merging all sources.

        Returns:
            Merged configuration dictionary
        """
        # Start with defaults
        config = self._deep_copy(self.DEFAULTS)

        # Merge config file
        if self.config_file:
            file_config = self._load_config_file(self.config_file)
            config = self._deep_merge(config, file_config)

        # Merge environment variables
        env_config = self._load_env_config()
        config = self._deep_merge(config, env_config)

        # Merge constructor overrides (highest priority)
        config = self._deep_merge(config, self.overrides)

        return config

    def _load_config_file(self, config_file: str) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Args:
            config_file: Path to config file

        Returns:
            Configuration dictionary from file
        """
        path = Path(config_file)
        if not path.exists():
            return {}

        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
                return config if config else {}
        except Exception as e:
            print(f"Warning: Failed to load config file {config_file}: {e}")
            return {}

    def _load_env_config(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables.

        Returns:
            Configuration dictionary from environment
        """
        config = {}

        for config_key, env_var in self.ENV_VAR_MAP.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Handle nested keys (e.g., 'google.api_key')
                keys = config_key.split(".")
                current = config
                for i, key in enumerate(keys[:-1]):
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[keys[-1]] = value

        return config

    def _deep_copy(self, d: Dict) -> Dict:
        """Create a deep copy of a dictionary."""
        result = {}
        for key, value in d.items():
            if isinstance(value, dict):
                result[key] = self._deep_copy(value)
            else:
                result[key] = value
        return result

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        Deep merge two dictionaries, with override taking precedence.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = self._deep_copy(base)

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                if value is not None:  # Only override if not None
                    result[key] = value

        return result

    def to_dict(self) -> Dict[str, Any]:
        """
        Get the complete configuration as a dictionary.

        Returns:
            Full configuration dictionary
        """
        if self._config is None:
            self._config = self._build_config()
        return self._deep_copy(self._config)


# Global configuration instance
_global_config: Optional[TTSConfig] = None


def get_config(**overrides) -> TTSConfig:
    """
    Get the global configuration instance.

    Args:
        **overrides: Configuration overrides

    Returns:
        Global TTSConfig instance
    """
    global _global_config
    if _global_config is None or overrides:
        _global_config = TTSConfig(**overrides)
    return _global_config


def reset_config():
    """Reset the global configuration (mainly for testing)."""
    global _global_config
    _global_config = None
