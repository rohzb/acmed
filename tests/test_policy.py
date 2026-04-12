from acmed.config import AllowedDomainEntry, PolicyConfig
from acmed.policy import compile_matcher, policy_matches_dns


def test_exact_matcher():
    matcher = compile_matcher(AllowedDomainEntry(syntax="exact", value="host1.lab.example.org"))
    assert matcher("host1.lab.example.org")
    assert not matcher("host2.lab.example.org")


def test_suffix_matcher_matches_apex_and_child():
    policy = PolicyConfig(
        name="shared",
        authorizers=["subnet"],
        allowed_domains=[AllowedDomainEntry(syntax="suffix", value=".apps.lab.example.org")],
        allowed_issuers=["mock"],
        proof_handler="no-proof",
    )
    assert policy_matches_dns(policy, ["apps.lab.example.org"])
    assert policy_matches_dns(policy, ["a.apps.lab.example.org"])
    assert not policy_matches_dns(policy, ["other.lab.example.org"])
