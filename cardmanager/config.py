"""Configuration loading for CardManager."""

from dataclasses import dataclass
from pathlib import Path
import tomllib


DEFAULT_CONFIG_PATH = Path("/etc/cardmanager/config.toml")


class ConfigurationError(RuntimeError):
    """Raised when the CardManager configuration is invalid."""


@dataclass(frozen=True, slots=True)
class Pkcs11Config:
    module_path: str


@dataclass(frozen=True, slots=True)
class CardManagerConfig:
    pkcs11: Pkcs11Config


def load_config(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> CardManagerConfig:
    """Load and validate the CardManager TOML configuration."""

    path = Path(config_path)

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise ConfigurationError(
            "CardManager configuration could not be read"
        ) from None

    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        raise ConfigurationError(
            "CardManager configuration contains invalid TOML"
        ) from None

    pkcs11_data = data.get("pkcs11")
    if not isinstance(pkcs11_data, dict):
        raise ConfigurationError(
            "CardManager configuration requires a [pkcs11] section"
        )

    module_path = pkcs11_data.get("module_path")
    if not isinstance(module_path, str) or not module_path.strip():
        raise ConfigurationError(
            "PKCS#11 module_path must be a non-empty string"
        )

    module = Path(module_path)
    if not module.is_absolute():
        raise ConfigurationError(
            "PKCS#11 module_path must be an absolute path"
        )

    if not module.is_file():
        raise ConfigurationError(
            "Configured PKCS#11 module file does not exist"
        )

    return CardManagerConfig(
        pkcs11=Pkcs11Config(module_path=str(module)),
    )
