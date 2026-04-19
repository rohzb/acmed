import os
from pathlib import Path

import pytest

from acmed.config import ConfigError, load_config


def _base_config(tmp_path: Path) -> str:
    return f"""
server:
  host: 127.0.0.1
  port: 8443
  tls_enabled: false
  development_mode: true

identity:
  api_tokens:
    enabled: true
    tokens:
      - token_id: t1
        subject: acmed-admin
        secret_env: ACMED_TEST_TOKEN
        roles: [requester]
  mtls:
    enabled: false

access:
  admin_subjects: [acmed-admin]

acme:
  require_eab: false

storage:
  sqlite_path: {tmp_path / 'acmed.db'}
  artifacts_root: {tmp_path / 'orders'}

issuers:
  - name: mock
    type: mock

proof_handlers:
  - name: no-proof
    type: none

authorizers:
  - name: subnet-lab
    type: source_subnet
    source_subnets: [10.0.0.0/24]

policies:
  - name: p1
    requester_match:
      authorizers: [subnet-lab]
    allowed_domains:
      - syntax: exact
        value: host1.lab.example.org
    allowed_issuers: [mock]
    proof_handler: no-proof
"""


def test_load_config_requires_secret_env_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ACMED_TEST_TOKEN", raising=False)
    path = tmp_path / "cfg.yml"
    path.write_text(_base_config(tmp_path), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_load_config_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ACMED_TEST_TOKEN", "secret")
    path = tmp_path / "cfg.yml"
    path.write_text(_base_config(tmp_path), encoding="utf-8")
    cfg = load_config(path)
    assert cfg.issuers[0].name == "mock"
    assert cfg.policies[0].allowed_domains[0].syntax == "exact"


def test_trusted_bypass_requires_development_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ACMED_TEST_TOKEN", "secret")
    cert_path = tmp_path / "server.crt"
    key_path = tmp_path / "server.key"
    cert_path.write_text("dummy", encoding="utf-8")
    key_path.write_text("dummy", encoding="utf-8")
    base = _base_config(tmp_path).replace(
        "  tls_enabled: false\n  development_mode: true",
        (
            "  tls_enabled: true\n"
            f"  tls_cert_file: {cert_path}\n"
            f"  tls_key_file: {key_path}\n"
            "  development_mode: false"
        ),
    )
    cfg_text = base + "    challenge_validation_mode: trusted_bypass\n"
    path = tmp_path / "cfg.yml"
    path.write_text(cfg_text, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_trusted_bypass_allowed_in_development_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ACMED_TEST_TOKEN", "secret")
    base = _base_config(tmp_path)
    cfg_text = base + "    challenge_validation_mode: trusted_bypass\n"
    path = tmp_path / "cfg.yml"
    path.write_text(cfg_text, encoding="utf-8")
    cfg = load_config(path)
    assert cfg.policies[0].challenge_validation_mode == "trusted_bypass"


def test_forwarded_headers_require_trusted_proxy_cidrs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ACMED_TEST_TOKEN", "secret")
    base = _base_config(tmp_path).replace(
        "  tls_enabled: false\n  development_mode: true",
        "  tls_enabled: false\n  development_mode: true\n  trust_forwarded_headers: true",
    )
    path = tmp_path / "cfg.yml"
    path.write_text(base, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_forwarded_headers_reject_invalid_proxy_cidr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ACMED_TEST_TOKEN", "secret")
    base = _base_config(tmp_path).replace(
        "  tls_enabled: false\n  development_mode: true",
        "  tls_enabled: false\n  development_mode: true\n  trust_forwarded_headers: true\n  trusted_proxy_cidrs: [invalid-cidr]",
    )
    path = tmp_path / "cfg.yml"
    path.write_text(base, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_tls_enabled_requires_cert_and_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ACMED_TEST_TOKEN", "secret")
    base = _base_config(tmp_path).replace(
        "  tls_enabled: false\n  development_mode: true",
        "  tls_enabled: true\n  development_mode: false",
    )
    path = tmp_path / "cfg.yml"
    path.write_text(base, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)
