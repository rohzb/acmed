"""Policy resolution and matcher compilation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .config import AllowedDomainEntry, AppConfig, PolicyConfig
from .errors import AuthorizationError, ValidationError
from .models import CsrSource
from .utils import normalize_dns_names

Matcher = Callable[[str], bool]


@dataclass(slots=True)
class ResolvedPolicy:
    """Resolved runtime policy selection for an order request.

    Attributes:
        policy: Selected full policy definition.
        issuer_name: Effective issuer profile name to use.
        proof_handler_name: Effective proof handler name to use.
    """

    policy: PolicyConfig
    issuer_name: str
    proof_handler_name: str


def compile_matcher(entry: AllowedDomainEntry) -> Matcher:
    """Compile one YAML allowed-domain entry into an executable matcher.

    Args:
        entry: Allowed domain matcher entry.

    Returns:
        Predicate that returns `True` when a normalized DNS name matches.

    Raises:
        ValidationError: If matcher syntax is unsupported.
    """

    if entry.syntax == "exact":
        expected = entry.value
        return lambda value: value == expected
    if entry.syntax == "suffix":
        suffix = entry.value
        zone = suffix[1:]
        return lambda value: value == zone or value.endswith(suffix)
    raise ValidationError(f"unsupported matcher syntax at runtime: {entry.syntax}")


def policy_matches_dns(policy: PolicyConfig, dns_names: list[str]) -> bool:
    """Check whether all DNS names are allowed by the policy.

    Args:
        policy: Candidate policy definition.
        dns_names: Normalized requested DNS names.

    Returns:
        `True` when every requested DNS name matches at least one policy matcher.
    """

    compiled = [compile_matcher(entry) for entry in policy.allowed_domains]
    for name in dns_names:
        if not any(match(name) for match in compiled):
            return False
    return True


def _policy_specificity(policy: PolicyConfig) -> tuple[int, int]:
    """Return sort key where larger values are more specific."""
    exact_count = sum(1 for item in policy.allowed_domains if item.syntax == "exact")
    total_len = sum(len(item.value) for item in policy.allowed_domains)
    return exact_count, total_len


def _is_authorized_by_matchers(policy: PolicyConfig, authorized_names: set[str]) -> bool:
    """Check if requester satisfied all authorizers required by policy."""

    for name in policy.authorizers:
        if name not in authorized_names:
            return False
    return True


def resolve_policy(
    config: AppConfig,
    requester_authorizers: set[str],
    dns_names: list[str],
    requested_issuer: str | None,
    csr_source: CsrSource,
    enforce_authorizers: bool = True,
) -> ResolvedPolicy:
    """Resolve the effective policy and runtime plugins for an order request.

    Args:
        config: Loaded application configuration.
        requester_authorizers: Authorizer names satisfied by request context.
        dns_names: Requested DNS names.
        requested_issuer: Optional explicitly requested issuer profile.
        csr_source: Whether CSR was client-provided or service-generated.
        enforce_authorizers: Whether authorizer constraints must be enforced.

    Returns:
        Resolved runtime policy and selected plugin names.

    Raises:
        AuthorizationError: If no policy matches or matching policies are ambiguous.
    """

    normalized_names = normalize_dns_names(dns_names)
    matching: list[PolicyConfig] = []
    for policy in config.policies:
        if enforce_authorizers and not _is_authorized_by_matchers(policy, requester_authorizers):
            continue
        if not policy_matches_dns(policy, normalized_names):
            continue
        if requested_issuer and requested_issuer not in policy.allowed_issuers:
            continue
        if policy.csr_mode == "client_provided" and csr_source != CsrSource.CLIENT_PROVIDED:
            continue
        if policy.csr_mode == "service_generated" and csr_source != CsrSource.SERVICE_GENERATED:
            continue
        matching.append(policy)

    if not matching:
        raise AuthorizationError("no matching policy")

    if len(matching) == 1:
        selected = matching[0]
        issuer_name = requested_issuer or selected.allowed_issuers[0]
        return ResolvedPolicy(selected, issuer_name=issuer_name, proof_handler_name=selected.proof_handler)

    # Ambiguity handling: permit deterministic choice only if runtime options are equal.
    runtime_choices = {
        (
            tuple(policy.allowed_issuers),
            policy.proof_handler,
            policy.csr_mode,
            policy.challenge_validation_mode,
        )
        for policy in matching
    }
    if len(runtime_choices) != 1:
        raise AuthorizationError("ambiguous policy configuration; matches disagree on runtime choices")

    selected = sorted(matching, key=_policy_specificity, reverse=True)[0]
    issuer_name = requested_issuer or selected.allowed_issuers[0]
    return ResolvedPolicy(selected, issuer_name=issuer_name, proof_handler_name=selected.proof_handler)
