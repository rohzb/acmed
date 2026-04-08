# acmed Iteration Log

> [!TIP]
> **TL;DR**
> This log records the review-and-improvement passes used to turn the original rough prompt into a cleaner spec set with stronger architecture, implementation guidance, clearer scope control, and a much leaner MVP shape.

## Pass 1: Separate concept from prompt framing

Review focus:

- identify useful project requirements
- remove prompt-oriented wording that does not belong in a design brief

Improvements:

- converted the original file from a prompt-heavy draft into a project brief
- preserved the core idea of a certificate broker with an optional ACME facade
- removed wording that treated the document as instructions to a model instead of a reader-facing design artifact

## Pass 2: Clarify the product boundary

Review focus:

- decide what `acmed` is and is not
- make the broker-first stance explicit

Improvements:

- stated that `acmed` is not primarily a CA and not a naive ACME proxy
- elevated the broker API as the primary interface and ACME as an adapter
- reinforced the distinction between internal authorization policy and ACME challenge validation

## Pass 3: Normalize the architecture vocabulary

Review focus:

- stabilize terminology so later docs can use consistent names
- reduce ambiguity between policy, validation, and issuance

Improvements:

- introduced canonical terms such as order, authorizer, challenge provider, issuer, runtime state, and artifact storage
- aligned component names with the intended Python package layout
- made plugin boundaries more explicit

## Pass 4: Strengthen the lifecycle model

Review focus:

- make the request lifecycle enforceable
- identify terminal and non-terminal states

Improvements:

- documented the required order states
- added recommended transition rules
- clarified which states should be terminal in the MVP

## Pass 5: Expand the operational design

Review focus:

- describe how the system runs, not only what modules exist
- make async processing concrete

Improvements:

- added a primary request sequence diagram
- documented the API-plus-worker runtime model
- defined startup expectations, worker responsibilities, and restart handling considerations

## Pass 6: Detail storage, security, and failure handling

Review focus:

- ensure the design is operationally credible
- cover the main data paths and trust boundaries

Improvements:

- separated YAML configuration, SQLite runtime state, and filesystem artifacts
- added a security section for identity, secret handling, and subprocess control
- documented expected failure modes and handling strategies

## Pass 7: Convert architecture into implementation guidance

Review focus:

- turn the design into actionable build instructions
- keep the MVP delivery sequence realistic

Improvements:

- created a dedicated implementation guide
- defined phased build order, package responsibilities, and acceptance criteria
- added explicit testing and documentation requirements

## Pass 8: Restructure into a doc set and tighten navigation

Review focus:

- choose whether one file or several files better serve the work
- improve usability for future implementation passes

Improvements:

- kept `description.md` as the entry point
- split detailed architecture and implementation instructions into dedicated docs
- added this iteration log so the refinement work remains inspectable and reusable

## Pass 9: Add explicit documentation and code-quality rules

Review focus:

- make documentation expectations enforceable during code generation
- ensure source code quality rules are part of the spec, not implied

Improvements:

- added a hard requirement for fully documented code to the project brief
- expanded the implementation guide with explicit rules for file banners, Python type hints, and complete docstrings
- added acceptance criteria and checks so documentation quality is part of the MVP definition

## Pass 10: Re-evaluate the architecture for MVP simplicity

Review focus:

- identify abstractions that were technically clean but heavier than needed
- reframe the design around elegance, speed, and low code volume

Improvements:

- shifted the brief toward a lean single-service implementation style
- made simplicity a first-class architectural requirement
- added explicit guidance to avoid extra moving parts unless they solve a real problem

## Pass 11: Remove queue-oriented thinking

Review focus:

- decide whether the MVP needs a separate queue abstraction
- reduce coordination complexity

Improvements:

- replaced the queue concept with a SQLite-backed polling worker loop
- simplified the runtime story to one database and one worker path
- reduced the number of distinct failure domains in the design

## Pass 12: Shrink the package layout

Review focus:

- reduce file and package fragmentation
- improve readability for early implementation

Improvements:

- replaced the more segmented package tree with a leaner starting layout
- recommended coarse-grained modules such as `api.py`, `models.py`, `storage.py`, and `worker.py`
- clarified that modules should be split only when they actually become too large

## Pass 13: Simplify the persistence model

Review focus:

- trim the data model to what the MVP truly needs
- keep auditability without excessive schema design

Improvements:

- recommended starting with `orders`, `issuance_attempts`, and `audit_events`
- moved authorization details toward audit metadata unless richer queries prove necessary
- aligned persistence with the modular monolith approach

## Pass 14: Narrow the API surface

Review focus:

- keep the external API centered on the core value of the service
- avoid designing management endpoints too early

Improvements:

- reduced the initial admin and retry surface
- kept the broker API focused on creating and inspecting orders
- delayed broader API ambitions until real operational needs appear

## Pass 15: Simplify plugin strategy

Review focus:

- preserve extensibility without building a framework
- keep plugin code easy to understand

Improvements:

- recommended static implementation mappings instead of plugin discovery machinery
- kept plugin contracts small and synchronous at the boundary
- reduced the likelihood of architecture-driven boilerplate

## Pass 16: Adjust testing strategy toward realism

Review focus:

- improve confidence without creating a large mock-heavy test suite
- support speed and maintainability

Improvements:

- favored service-level and end-to-end flows over excessive unit isolation
- added guidance to keep test helpers small and local
- aligned the test plan with the simplified runtime shape

## Pass 17: Reconcile implementation guidance with the simpler architecture

Review focus:

- make sure the implementation guide and brief match the simplified design
- ensure elegance remains an explicit acceptance criterion

Improvements:

- updated the implementation guide to prefer compact modules and fewer abstractions
- added acceptance and avoidance rules tied to simplicity
- made “easy to read in a handful of files” part of the desired outcome

## Pass 18: Add security-by-default guidance

Review focus:

- make sure future code generation starts from safe defaults instead of postponing security hardening
- integrate cybersecurity practices without pushing the design back into over-engineering

Improvements:

- added security-by-default as a first-class design directive
- expanded the architecture with transport, identity, authorization, secret handling, subprocess, audit, and abuse-control rules
- updated the implementation guide so secure behavior is part of phases, testing, acceptance criteria, and generation constraints

## Pass 19: Tighten ACME client compatibility

Review focus:

- make the ACME adapter compatible with common clients such as `certbot` and `acme.sh`
- fix places where the broker-first design was too vague at the protocol boundary

Improvements:

- upgraded the ACME section from a vague minimal adapter to a concrete RFC 8555-compatible feature baseline
- added explicit requirements for directory, nonce, account, order, authorization, challenge, finalize, and certificate flows
- clarified that ACME clients fulfill challenges while the server validates them, and that only truly supported challenge types should be advertised

## Pass 20: Add explicit ACME endpoint reference

Review focus:

- avoid leaving endpoint details scattered across the architecture text
- give future implementation work a clear ACME endpoint contract

Improvements:

- added a dedicated ACME API reference document with endpoint-by-endpoint descriptions
- linked that reference from the project brief and architecture
- made explicit endpoint documentation part of the implementation deliverables

## Pass 21: Tighten the remaining ACME contract details

Review focus:

- remove remaining ambiguity that could still lead to “mostly compatible” ACME behavior
- make generator-facing protocol choices explicit

Improvements:

- added identifier support and wildcard rules
- added ACME signing and key-authorization guidance
- added a minimum ACME error contract and object-shape expectations
- added explicit ownership rules for account-scoped ACME resources

## Pass 22: Close the remaining compatibility polish gaps

Review focus:

- resolve small contradictions that could still mislead implementation work
- turn protocol compatibility claims into more testable requirements

Improvements:

- made revocation advertisement conditional on actual implementation
- fixed the v1 certificate response format expectation
- added HTTP status guidance for core ACME endpoints
- required at least one real-client smoke test before claiming practical compatibility
- updated the brief so the iteration log is treated as a running improvement log rather than a fixed-count list

## Pass 23: Close the remaining protocol-precision gaps

Review focus:

- address the last ambiguous ACME resource and compatibility details
- make compatibility claims match concrete test expectations

Improvements:

- added the account-orders resource referenced by the account object
- tightened named-client compatibility claims to require testing with both `certbot` and `acme.sh`
- added DNS identifier normalization guidance
- made the v1 External Account Binding posture explicit

## Pass 24: Add the final configuration and support-summary refinements

Review focus:

- make sure the configuration model exposes the ACME behaviors already required elsewhere
- provide one compact support summary so claims stay truthful

Improvements:

- added explicit ACME adapter configuration settings to the architecture and implementation guide
- added a concise ACME v1 support matrix to centralize required, optional, and unsupported features

## Pass 25: Restructure the document set for cleaner implementation use

Review focus:

- reduce overlap between brief, architecture, implementation, and ACME protocol docs
- make the set easier for both a human reader and a code generator to consume

Improvements:

- rewrote the brief as a true entry-point document with a clearer reading order
- trimmed architecture back to system design and removed protocol-detail duplication
- rewrote the implementation guide around build order, runtime contracts, config, tests, and acceptance
- made the ACME reference the authoritative source for protocol-visible behavior, support matrix, endpoint details, and client smoke-test examples

## Result

The design now exists as a small document set with:

- a concise project brief
- a full architecture description
- a practical implementation guide
- an explicit refinement record

This structure should support both future human review and code generation work more effectively than a single mixed-purpose prompt.
