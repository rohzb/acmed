from acmed.config import IssuerProfile
from acmed.errors import WorkerError
from acmed.issuers import IssueRequest
from acmed.issuers.acme_sh import AcmeShIssuerBackend
from acmed.issuers.base import IssueResult
from acmed.issuers.certbot import CertbotIssuerBackend
from acmed.issuers.subprocess_backend import SubprocessResult


def test_acme_sh_uses_dns_plugin_and_exports_expected_artifacts(monkeypatch, tmp_path):
    backend = AcmeShIssuerBackend()
    calls = []

    def fake_run(argv, profile, cwd):  # noqa: ANN001
        calls.append(argv)
        if "--install-cert" in argv:
            (tmp_path / "certificate.pem").write_text("CERT", encoding="utf-8")
            (tmp_path / "chain.pem").write_text("CHAIN", encoding="utf-8")
            (tmp_path / "fullchain.pem").write_text("FULLCHAIN", encoding="utf-8")
            (tmp_path / "private.key").write_text("KEY", encoding="utf-8")
        return SubprocessResult(command=argv, exit_code=0, stdout="ok", stderr="")

    monkeypatch.setattr(backend, "_run", fake_run)

    result = backend.issue(
        profile=IssuerProfile(
            name="acmesh-dns",
            type="acme_sh",
            executable="/usr/local/bin/acme.sh",
            ca_directory_url="https://acme-staging-v02.api.letsencrypt.org/directory",
            challenge_mode="dns-01",
            plugin_name="dns_hetzner",
        ),
        request=IssueRequest(
            order_id="order-1",
            dns_names=["host1.example.org", "host2.example.org"],
            common_name="host1.example.org",
            csr_pem=None,
            artifacts_dir=str(tmp_path),
        ),
    )

    assert result.success is True
    assert result.certificate_pem == "CERT"
    assert result.chain_pem == "CHAIN"
    assert result.fullchain_pem == "FULLCHAIN"
    assert result.private_key_pem == "KEY"

    issue_call = calls[0]
    assert "--challenge-alias" not in issue_call
    assert "--force" not in issue_call
    assert "--dns" in issue_call
    assert issue_call[issue_call.index("--dns") + 1] == "dns_hetzner"

    install_call = calls[1]
    assert "--cert-file" in install_call
    assert "--key-file" in install_call
    assert "--ca-file" in install_call
    assert "--fullchain-file" in install_call


def test_certbot_sets_explicit_output_paths(monkeypatch, tmp_path):
    backend = CertbotIssuerBackend()
    captured = {}

    def fake_issue_by_subprocess(argv, profile, request):  # noqa: ANN001
        captured["argv"] = argv
        return IssueResult(
            success=True,
            result_code="issued",
            command=" ".join(argv),
            exit_code=0,
            stdout="ok",
            stderr="",
            certificate_pem="CERT",
            chain_pem="CHAIN",
            fullchain_pem="FULLCHAIN",
            private_key_pem="KEY",
        )

    monkeypatch.setattr(backend, "_issue_by_subprocess", fake_issue_by_subprocess)

    result = backend.issue(
        profile=IssuerProfile(
            name="certbot-dns",
            type="certbot",
            executable="/usr/bin/certbot",
            ca_directory_url="https://acme-staging-v02.api.letsencrypt.org/directory",
            challenge_mode="dns-01",
            plugin_name="dns-route53",
        ),
        request=IssueRequest(
            order_id="order-2",
            dns_names=["host1.example.org"],
            common_name="host1.example.org",
            csr_pem=None,
            artifacts_dir=str(tmp_path),
        ),
    )

    assert result.success is True
    argv = captured["argv"]
    assert "--cert-path" in argv
    assert "--chain-path" in argv
    assert "--fullchain-path" in argv
    assert "--key-path" in argv
    assert argv[argv.index("--cert-path") + 1].endswith("/certificate.pem")
    assert argv[argv.index("--key-path") + 1].endswith("/private.key")


def test_acme_sh_fails_fast_when_dns_plugin_missing(tmp_path):
    backend = AcmeShIssuerBackend()

    result = backend.issue(
        profile=IssuerProfile(
            name="acmesh-dns",
            type="acme_sh",
            executable="/usr/local/bin/acme.sh",
            challenge_mode="dns-01",
            plugin_name=None,
        ),
        request=IssueRequest(
            order_id="order-3",
            dns_names=["host1.example.org"],
            common_name="host1.example.org",
            csr_pem=None,
            artifacts_dir=str(tmp_path),
        ),
    )

    assert result.success is False
    assert result.exit_code == 64
    assert "plugin_name" in result.stderr


def test_certbot_fails_fast_when_dns_plugin_missing(tmp_path):
    backend = CertbotIssuerBackend()

    result = backend.issue(
        profile=IssuerProfile(
            name="certbot-dns",
            type="certbot",
            executable="/usr/bin/certbot",
            challenge_mode="dns-01",
            plugin_name=None,
        ),
        request=IssueRequest(
            order_id="order-4",
            dns_names=["host1.example.org"],
            common_name="host1.example.org",
            csr_pem=None,
            artifacts_dir=str(tmp_path),
        ),
    )

    assert result.success is False
    assert result.exit_code == 64
    assert "plugin_name" in result.stderr


def test_acme_sh_marks_missing_required_artifacts_as_error(monkeypatch, tmp_path):
    backend = AcmeShIssuerBackend()

    def fake_run(argv, profile, cwd):  # noqa: ANN001
        return SubprocessResult(command=argv, exit_code=0, stdout="ok", stderr="")

    monkeypatch.setattr(backend, "_run", fake_run)

    result = backend.issue(
        profile=IssuerProfile(
            name="acmesh-dns",
            type="acme_sh",
            executable="/usr/local/bin/acme.sh",
            challenge_mode="dns-01",
            plugin_name="dns_hetzner",
        ),
        request=IssueRequest(
            order_id="order-5",
            dns_names=["host1.example.org"],
            common_name="host1.example.org",
            csr_pem=None,
            artifacts_dir=str(tmp_path),
        ),
    )

    assert result.success is False
    assert result.exit_code == 65
    assert "missing required artifacts" in result.stderr


def test_acme_sh_reuses_existing_cert_without_forced_renew(monkeypatch, tmp_path):
    backend = AcmeShIssuerBackend()
    calls = []

    def fake_run(argv, profile, cwd):  # noqa: ANN001
        calls.append(argv)
        if "--issue" in argv:
            return SubprocessResult(
                command=argv,
                exit_code=2,
                stdout="",
                stderr="[Sun Apr 26 17:17:11 UTC 2026] Add '--force' to force to renew.",
            )
        (tmp_path / "certificate.pem").write_text("CERT", encoding="utf-8")
        (tmp_path / "chain.pem").write_text("CHAIN", encoding="utf-8")
        (tmp_path / "fullchain.pem").write_text("FULLCHAIN", encoding="utf-8")
        (tmp_path / "private.key").write_text("KEY", encoding="utf-8")
        return SubprocessResult(command=argv, exit_code=0, stdout="installed", stderr="")

    monkeypatch.setattr(backend, "_run", fake_run)

    result = backend.issue(
        profile=IssuerProfile(
            name="acmesh-dns",
            type="acme_sh",
            executable="/usr/local/bin/acme.sh",
            challenge_mode="dns-01",
            plugin_name="dns_hetznercloud",
        ),
        request=IssueRequest(
            order_id="order-reuse-1",
            dns_names=["testme.amgro.de"],
            common_name="testme.amgro.de",
            csr_pem=None,
            artifacts_dir=str(tmp_path),
        ),
    )

    assert result.success is True
    assert len(calls) == 2
    assert "--install-cert" in calls[1]


def test_certbot_marks_missing_required_artifacts_as_error(monkeypatch, tmp_path):
    backend = CertbotIssuerBackend()

    def fake_issue_by_subprocess(argv, profile, request):  # noqa: ANN001
        return IssueResult(
            success=True,
            result_code="issued",
            command=" ".join(argv),
            exit_code=0,
            stdout="ok",
            stderr="",
            certificate_pem=None,
            chain_pem=None,
            fullchain_pem=None,
            private_key_pem=None,
        )

    monkeypatch.setattr(backend, "_issue_by_subprocess", fake_issue_by_subprocess)

    result = backend.issue(
        profile=IssuerProfile(
            name="certbot-dns",
            type="certbot",
            executable="/usr/bin/certbot",
            challenge_mode="dns-01",
            plugin_name="dns-route53",
        ),
        request=IssueRequest(
            order_id="order-6",
            dns_names=["host1.example.org"],
            common_name="host1.example.org",
            csr_pem=None,
            artifacts_dir=str(tmp_path),
        ),
    )

    assert result.success is False
    assert result.exit_code == 65
    assert "missing required artifacts" in result.stderr


def test_filtered_env_preserves_home_and_includes_only_required_credentials(monkeypatch):
    backend = CertbotIssuerBackend()
    monkeypatch.setenv("PATH", "/usr/local/bin:/usr/bin")
    monkeypatch.setenv("HOME", "/home/acmed")
    monkeypatch.setenv("REQUIRED_TOKEN", "secret")
    monkeypatch.setenv("UNUSED_TOKEN", "should-not-pass")

    profile = IssuerProfile(
        name="certbot-dns",
        type="certbot",
        executable="/usr/bin/certbot",
        challenge_mode="dns-01",
        plugin_name="dns-route53",
        credential_env=["REQUIRED_TOKEN"],
    )

    env = backend._filtered_env(profile)

    assert env["PATH"] == "/usr/local/bin:/usr/bin"
    assert env["HOME"] == "/home/acmed"
    assert env["REQUIRED_TOKEN"] == "secret"
    assert "UNUSED_TOKEN" not in env


def test_filtered_env_raises_when_required_credential_missing(monkeypatch):
    backend = CertbotIssuerBackend()
    monkeypatch.delenv("MISSING_TOKEN", raising=False)

    profile = IssuerProfile(
        name="certbot-dns",
        type="certbot",
        executable="/usr/bin/certbot",
        challenge_mode="dns-01",
        plugin_name="dns-route53",
        credential_env=["MISSING_TOKEN"],
    )

    try:
        backend._filtered_env(profile)
    except WorkerError as exc:
        assert "MISSING_TOKEN" in str(exc)
        return

    raise AssertionError("expected WorkerError for missing credential env var")
