"""YAML-driven configuration loading and validation for acmed."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from .errors import ConfigError
from .utils import normalize_dns_name

MatcherSyntax = Literal["exact", "suffix", "regex"]
IssuerType = Literal["acme_sh", "certbot", "mock"]


@dataclass(slots=True)
class ServerConfig:
    """HTTP listener configuration."""
    host: str = "0.0.0.0"
    port: int = 8443
    tls_enabled: bool = True
    development_mode: bool = False


@dataclass(slots=True)
class ApiTokenConfig:
    """One configured API-token identity."""
    token_id: str
    subject: str
    secret_env: str
    roles: list[str]


@dataclass(slots=True)
class MtlsConfig:
    """mTLS trust-anchor and subject-mapping settings."""
    enabled: bool = False
    trusted_client_ca_file: str | None = None
    subject_mappings: list[dict[str, str]] | None = None


@dataclass(slots=True)
class IdentityConfig:
    """Identity provider settings used by admin/broker paths."""
    api_tokens_enabled: bool
    api_tokens: list[ApiTokenConfig]
    mtls: MtlsConfig


@dataclass(slots=True)
class LimitsConfig:
    """Request size and rate limiting settings."""
    max_dns_names_per_order: int = 25
    max_csr_bytes: int = 32768
    max_request_body_bytes: int = 65536
    create_order_rate_limit_per_minute: int = 30


@dataclass(slots=True)
class OrdersConfig:
    """Order TTL, claim lease, and retry settings."""
    default_ttl_seconds: int = 3600
    claim_ttl_seconds: int = 300
    max_retries: int = 3


@dataclass(slots=True)
class StorageConfig:
    """Database and artifact root paths."""
    sqlite_path: Path
    artifacts_root: Path


@dataclass(slots=True)
class WorkerConfig:
    """Worker polling and concurrency settings."""
    poll_interval_seconds: int = 2
    max_parallel_orders: int = 4


@dataclass(slots=True)
class AllowedDomainEntry:
    """One policy matcher entry with explicit syntax."""
    syntax: MatcherSyntax
    value: str


@dataclass(slots=True)
class IssuerProfile:
    """Named issuer backend profile and execution settings."""
    name: str
    type: IssuerType
    executable: str | None = None
    ca_directory_url: str | None = None
    challenge_mode: str | None = None
    plugin_name: str | None = None
    credential_env: list[str] | None = None
    capability_scope: list[AllowedDomainEntry] | None = None
    timeout_seconds: int = 120


@dataclass(slots=True)
class ProofHandlerConfig:
    """One configured proof-handler plugin instance."""
    name: str
    type: str
    inventory_source: str | None = None


@dataclass(slots=True)
class AuthorizerConfig:
    """One configured authorizer plugin instance."""
    name: str
    type: str
    source_subnets: list[str] | None = None


@dataclass(slots=True)
class EabCredentialConfig:
    """External Account Binding credential reference."""
    kid: str
    secret_env: str


@dataclass(slots=True)
class PolicyConfig:
    """Resolved policy configuration used for request authorization."""
    name: str
    authorizers: list[str]
    allowed_domains: list[AllowedDomainEntry]
    allowed_issuers: list[str]
    proof_handler: str
    csr_mode: Literal["client_provided", "service_generated", "either"] = "either"
    challenge_validation_mode: Literal["strict", "trusted_bypass"] = "strict"


@dataclass(slots=True)
class AcmeConfig:
    """ACME feature toggles and enrollment settings."""
    enabled: bool = True
    directory_path: str = "/acme/directory"
    require_eab: bool = True
    allow_wildcards: bool = False
    supported_challenge_types: list[str] | None = None
    eab_credentials: list[EabCredentialConfig] | None = None


@dataclass(slots=True)
class AccessConfig:
    """Admin authorization settings."""
    admin_subjects: list[str]


@dataclass(slots=True)
class AppConfig:
    """Top-level validated runtime configuration."""
    server: ServerConfig
    identity: IdentityConfig
    access: AccessConfig
    limits: LimitsConfig
    orders: OrdersConfig
    acme: AcmeConfig
    storage: StorageConfig
    workers: WorkerConfig
    issuers: list[IssuerProfile]
    proof_handlers: list[ProofHandlerConfig]
    authorizers: list[AuthorizerConfig]
    policies: list[PolicyConfig]
    regex_policy_mode_enabled: bool = False


def _must_be_positive(name: str, value: int) -> None:
    """Require positive numeric config value."""
    if value <= 0:
        raise ConfigError(f"{name} must be positive")


def _normalize_subject(value: str) -> str:
    """Normalize configured identity subject string."""
    norm = value.strip().lower()
    if not norm:
        raise ConfigError("subject must not be empty")
    return norm


def _validate_matcher(entry: AllowedDomainEntry, regex_enabled: bool) -> AllowedDomainEntry:
    """Validate and normalize one policy matcher entry."""
    syntax = entry.syntax
    value = entry.value.strip().lower()
    if syntax not in {"exact", "suffix", "regex"}:
        raise ConfigError(f"unsupported matcher syntax: {syntax}")
    if syntax == "regex":
        if not regex_enabled:
            raise ConfigError("regex policy mode is not enabled")
        if not value:
            raise ConfigError("regex matcher value must not be empty")
        return AllowedDomainEntry(syntax="regex", value=value)

    if syntax == "exact":
        normalized = normalize_dns_name(value)
        if normalized.startswith("*."):
            raise ConfigError("wildcard exact matchers are not supported")
        return AllowedDomainEntry(syntax="exact", value=normalized)

    if not value.startswith("."):
        raise ConfigError("suffix matcher must start with '.'")
    normalized_suffix = normalize_dns_name(f"z{value}")
    return AllowedDomainEntry(syntax="suffix", value=f".{normalized_suffix.split('.', 1)[1]}")


def _load_matchers(raw_entries: list[dict[str, Any]], regex_enabled: bool) -> list[AllowedDomainEntry]:
    """Load, validate, and deduplicate matcher entries."""
    if not raw_entries:
        raise ConfigError("allowed_domains must not be empty")
    normalized = [_validate_matcher(AllowedDomainEntry(**entry), regex_enabled) for entry in raw_entries]
    dedupe = {(entry.syntax, entry.value) for entry in normalized}
    if len(dedupe) != len(normalized):
        raise ConfigError("duplicate allowed_domains entries are not allowed")
    return normalized


def _load_issuers(raw_issuers: list[dict[str, Any]], regex_enabled: bool) -> list[IssuerProfile]:
    """Load and validate issuer profile configuration."""
    if not raw_issuers:
        raise ConfigError("at least one issuer profile is required")
    issuers = [IssuerProfile(**raw) for raw in raw_issuers]
    names = [issuer.name for issuer in issuers]
    if len(set(names)) != len(names):
        raise ConfigError("duplicate issuer profile names are not allowed")

    for issuer in issuers:
        if not issuer.name.strip():
            raise ConfigError("issuer name must not be empty")
        if issuer.type not in {"acme_sh", "certbot", "mock"}:
            raise ConfigError(f"unsupported issuer adapter type: {issuer.type}")
        if issuer.type != "mock" and not issuer.executable:
            raise ConfigError(f"issuer {issuer.name} requires executable")
        if issuer.executable and not Path(issuer.executable).exists():
            raise ConfigError(f"issuer executable not found: {issuer.executable}")
        if issuer.capability_scope:
            issuer.capability_scope = _load_matchers(
                [entry.__dict__ if isinstance(entry, AllowedDomainEntry) else entry for entry in issuer.capability_scope],
                regex_enabled=regex_enabled,
            )
    return issuers


def _load_tokens(raw_identity: dict[str, Any]) -> IdentityConfig:
    """Load and validate token and mTLS identity settings."""
    api_tokens = raw_identity.get("api_tokens", {})
    raw_tokens = api_tokens.get("tokens", [])
    parsed_tokens = [ApiTokenConfig(**token) for token in raw_tokens]
    seen_token_ids: set[str] = set()
    seen_subjects: set[str] = set()
    for token in parsed_tokens:
        token_id = token.token_id.strip().lower()
        subject = _normalize_subject(token.subject)
        if token_id in seen_token_ids:
            raise ConfigError("duplicate API token token_id after normalization")
        if subject in seen_subjects:
            raise ConfigError("duplicate API token subject after normalization")
        if not token.secret_env:
            raise ConfigError("api token secret_env must not be empty")
        seen_token_ids.add(token_id)
        seen_subjects.add(subject)

    raw_mtls = raw_identity.get("mtls", {})
    mtls = MtlsConfig(
        enabled=bool(raw_mtls.get("enabled", False)),
        trusted_client_ca_file=raw_mtls.get("trusted_client_ca_file"),
        subject_mappings=raw_mtls.get("subject_mappings", []),
    )

    if mtls.enabled and not mtls.trusted_client_ca_file:
        raise ConfigError("mTLS enabled requires trusted_client_ca_file")

    if mtls.subject_mappings:
        mapped_subjects: set[str] = set()
        for mapping in mtls.subject_mappings:
            to_subject = _normalize_subject(mapping.get("to_subject", ""))
            if to_subject in mapped_subjects:
                raise ConfigError("duplicate mTLS mapped subject")
            mapped_subjects.add(to_subject)

    return IdentityConfig(
        api_tokens_enabled=bool(api_tokens.get("enabled", True)),
        api_tokens=parsed_tokens,
        mtls=mtls,
    )


def _validate_admin_subjects(subjects: list[str]) -> list[str]:
    """Normalize and deduplicate configured admin subjects."""
    normalized = [_normalize_subject(subject) for subject in subjects]
    if len(set(normalized)) != len(normalized):
        raise ConfigError("duplicate admin subjects after normalization")
    return normalized


def _fail_if_inline_token_secret(raw: dict[str, Any]) -> None:
    """Reject inline token secrets in YAML configuration."""
    identity = raw.get("identity", {})
    api_tokens = identity.get("api_tokens", {})
    for token in api_tokens.get("tokens", []):
        if "secret" in token:
            raise ConfigError("inline token secrets are not allowed; use secret_env")


def load_config(path: str | Path) -> AppConfig:
    """Load and validate application configuration from YAML."""
    cfg_path = Path(path)
    try:
        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {cfg_path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid yaml: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("configuration root must be a mapping")

    _fail_if_inline_token_secret(raw)

    regex_enabled = bool(raw.get("features", {}).get("regex_policy_mode_enabled", False))

    server = ServerConfig(**raw.get("server", {}))
    if not server.tls_enabled and not server.development_mode:
        raise ConfigError("TLS must be enabled outside development mode")

    identity = _load_tokens(raw.get("identity", {}))
    access = AccessConfig(admin_subjects=_validate_admin_subjects(raw.get("access", {}).get("admin_subjects", [])))

    limits = LimitsConfig(**raw.get("limits", {}))
    _must_be_positive("limits.max_dns_names_per_order", limits.max_dns_names_per_order)
    _must_be_positive("limits.max_csr_bytes", limits.max_csr_bytes)
    _must_be_positive("limits.max_request_body_bytes", limits.max_request_body_bytes)
    _must_be_positive("limits.create_order_rate_limit_per_minute", limits.create_order_rate_limit_per_minute)

    orders = OrdersConfig(**raw.get("orders", {}))
    _must_be_positive("orders.default_ttl_seconds", orders.default_ttl_seconds)
    _must_be_positive("orders.claim_ttl_seconds", orders.claim_ttl_seconds)
    _must_be_positive("orders.max_retries", orders.max_retries)

    storage_raw = raw.get("storage", {})
    sqlite_path = Path(storage_raw.get("sqlite_path", "data/acmed.db"))
    artifacts_root = Path(storage_raw.get("artifacts_root", "data/orders"))
    storage = StorageConfig(sqlite_path=sqlite_path, artifacts_root=artifacts_root)

    for parent in {sqlite_path.parent, artifacts_root}:
        parent.mkdir(parents=True, exist_ok=True)

    workers = WorkerConfig(**raw.get("workers", {}))
    _must_be_positive("workers.poll_interval_seconds", workers.poll_interval_seconds)
    _must_be_positive("workers.max_parallel_orders", workers.max_parallel_orders)

    acme = AcmeConfig(**raw.get("acme", {}))
    if acme.supported_challenge_types is None:
        acme.supported_challenge_types = ["http-01"]
    allowed_challenges = {"http-01", "dns-01", "tls-alpn-01"}
    if not acme.supported_challenge_types:
        raise ConfigError("acme.supported_challenge_types must not be empty")
    for challenge in acme.supported_challenge_types:
        if challenge not in allowed_challenges:
            raise ConfigError(f"unsupported ACME challenge type: {challenge}")
    if acme.eab_credentials is None:
        acme.eab_credentials = []
    else:
        acme.eab_credentials = [EabCredentialConfig(**item) for item in acme.eab_credentials]
    if acme.require_eab and not acme.eab_credentials:
        raise ConfigError("acme.require_eab=true requires acme.eab_credentials")
    seen_eab: set[str] = set()
    for credential in acme.eab_credentials:
        if not credential.kid.strip():
            raise ConfigError("acme eab credential kid must not be empty")
        if credential.kid in seen_eab:
            raise ConfigError("duplicate acme eab credential kid")
        if not credential.secret_env:
            raise ConfigError("acme eab credential secret_env must not be empty")
        if credential.secret_env not in os.environ:
            raise ConfigError(f"missing acme eab secret env: {credential.secret_env}")
        seen_eab.add(credential.kid)

    issuers = _load_issuers(raw.get("issuers", []), regex_enabled=regex_enabled)

    proof_handlers = [ProofHandlerConfig(**handler) for handler in raw.get("proof_handlers", [])]
    if not proof_handlers:
        raise ConfigError("at least one proof_handler is required")
    proof_names = [handler.name for handler in proof_handlers]
    if len(set(proof_names)) != len(proof_names):
        raise ConfigError("duplicate proof handler names")

    authorizers = [AuthorizerConfig(**authorizer) for authorizer in raw.get("authorizers", [])]
    if not authorizers:
        raise ConfigError("at least one authorizer is required")
    authorizer_names = [authorizer.name for authorizer in authorizers]
    if len(set(authorizer_names)) != len(authorizer_names):
        raise ConfigError("duplicate authorizer names")
    for authorizer in authorizers:
        if authorizer.type not in {"source_subnet", "allow_all"}:
            raise ConfigError(f"unsupported authorizer type: {authorizer.type}")

    policies: list[PolicyConfig] = []
    for raw_policy in raw.get("policies", []):
        name = raw_policy.get("name", "").strip()
        if not name:
            raise ConfigError("policy name must not be empty")

        requester_match = raw_policy.get("requester_match", {})
        selected_authorizers = requester_match.get("authorizers", [])
        if not selected_authorizers:
            raise ConfigError(f"policy {name} must include at least one authorizer")

        allowed_domains = _load_matchers(raw_policy.get("allowed_domains", []), regex_enabled=regex_enabled)
        allowed_issuers = raw_policy.get("allowed_issuers", [])
        proof_handler = raw_policy.get("proof_handler")

        if not allowed_domains:
            raise ConfigError(f"policy {name} must include allowed_domains")
        if not allowed_issuers:
            raise ConfigError(f"policy {name} must include allowed_issuers")
        if not proof_handler:
            raise ConfigError(f"policy {name} must include proof_handler")

        unknown_issuers = set(allowed_issuers) - {issuer.name for issuer in issuers}
        if unknown_issuers:
            raise ConfigError(f"policy {name} references unknown issuers: {sorted(unknown_issuers)}")

        if proof_handler not in set(proof_names):
            raise ConfigError(f"policy {name} references unknown proof_handler: {proof_handler}")

        unknown_authorizers = set(selected_authorizers) - set(authorizer_names)
        if unknown_authorizers:
            raise ConfigError(
                f"policy {name} references unknown authorizers: {sorted(unknown_authorizers)}"
            )

        csr_mode = raw_policy.get("csr_mode", "either")
        if csr_mode not in {"client_provided", "service_generated", "either"}:
            raise ConfigError(f"policy {name} has unsupported csr_mode")
        challenge_validation_mode = raw_policy.get("challenge_validation_mode", "strict")
        if challenge_validation_mode not in {"strict", "trusted_bypass"}:
            raise ConfigError(f"policy {name} has unsupported challenge_validation_mode")
        if challenge_validation_mode == "trusted_bypass" and not server.development_mode:
            raise ConfigError(
                f"policy {name} uses trusted_bypass but server.development_mode is false"
            )

        policies.append(
            PolicyConfig(
                name=name,
                authorizers=list(selected_authorizers),
                allowed_domains=allowed_domains,
                allowed_issuers=list(allowed_issuers),
                proof_handler=proof_handler,
                csr_mode=csr_mode,
                challenge_validation_mode=challenge_validation_mode,
            )
        )

    if not policies:
        raise ConfigError("at least one policy is required")

    for token in identity.api_tokens:
        if token.secret_env not in os.environ:
            raise ConfigError(f"missing token secret env: {token.secret_env}")

    return AppConfig(
        server=server,
        identity=identity,
        access=access,
        limits=limits,
        orders=orders,
        acme=acme,
        storage=storage,
        workers=workers,
        issuers=issuers,
        proof_handlers=proof_handlers,
        authorizers=authorizers,
        policies=policies,
        regex_policy_mode_enabled=regex_enabled,
    )
