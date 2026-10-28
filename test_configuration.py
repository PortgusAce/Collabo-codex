import json
from pathlib import Path

import pytest

from configuration import validate_file_config, write_json
from server import LocalFiles


def test_live_grant_and_revocation(tmp_path):
    folder = tmp_path / "authorized"
    folder.mkdir()
    sample = folder / "sample.txt"
    sample.write_text("synthetic", encoding="utf-8")
    config_path = tmp_path / "files.json"
    write_json(config_path, {"roots": []})
    files = LocalFiles({"roots": []}, config_path)
    with pytest.raises(PermissionError):
        files.read(str(sample))
    write_json(config_path, {"roots": [str(folder)]})
    assert files.read(str(sample))["content"] == "synthetic"
    write_json(config_path, {"roots": []})
    with pytest.raises(PermissionError):
        files.read(str(sample))
    write_json(config_path, {"roots": [str(folder)]})
    assert files.read(str(sample))["content"] == "synthetic"
    config_path.write_text("{broken", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        files.read(str(sample))
    assert files.roots == []


@pytest.mark.parametrize("config", [
    {"roots": ["relative"]}, {"roots": ["https://example.com"]},
    {"roots": ["\\\\host\\share"]}, {"roots": "not-list"},
    {"roots": [], "max_file_mb": 0}, {"roots": [], "max_file_mb": True},
    {"roots": [], "conversion_timeout_seconds": 121}])
def test_configuration_validation(config):
    with pytest.raises(ValueError):
        validate_file_config(config)
