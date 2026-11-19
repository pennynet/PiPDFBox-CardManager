from pathlib import Path

import pytest

from cardmanager.config import (
    ConfigurationError,
    load_config,
)


def test_loads_valid_configuration(tmp_path: Path):
    module = tmp_path / "opensc-pkcs11.so"
    module.touch()

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        f'[pkcs11]\nmodule_path = "{module}"\n',
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.pkcs11.module_path == str(module)


def test_missing_configuration_file_is_rejected(tmp_path: Path):
    with pytest.raises(ConfigurationError, match="could not be read"):
        load_config(tmp_path / "missing.toml")


def test_invalid_toml_is_rejected(tmp_path: Path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("[pkcs11\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="invalid TOML"):
        load_config(config_file)


def test_missing_pkcs11_section_is_rejected(tmp_path: Path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("[other]\nvalue = 1\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="requires a"):
        load_config(config_file)


@pytest.mark.parametrize("module_path", ["", "   ", "relative/module.so"])
def test_invalid_module_path_is_rejected(
    tmp_path: Path,
    module_path: str,
):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        f'[pkcs11]\nmodule_path = "{module_path}"\n',
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError):
        load_config(config_file)


def test_nonexistent_module_file_is_rejected(tmp_path: Path):
    module = tmp_path / "missing-pkcs11.so"
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        f'[pkcs11]\nmodule_path = "{module}"\n',
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="does not exist"):
        load_config(config_file)
