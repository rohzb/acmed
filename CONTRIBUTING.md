# Contributing

## Project Links

- Main repository: <https://github.com/rohzb/acmed>
- Issue tracker: <https://github.com/rohzb/acmed/issues>
- Pull requests: <https://github.com/rohzb/acmed/pulls>

## Workflow

1. Read [`README.md`](README.md) and [`docs/README.md`](docs/README.md).
2. Confirm which document owns the behavior you are changing.
3. Implement changes in small, testable increments.
4. Run local tests before opening a pull request.
5. Update docs and links when behavior or structure changes.

## Local Setup

Clone and enter the repository:

```bash
git clone https://github.com/rohzb/acmed.git
cd acmed
```

Then set up Python:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Test

```bash
pytest
```

## Documentation Requirements

- Keep `README.md` high-level and link to deeper docs.
- Keep `docs/README.md` current when files move.
- Do not duplicate the same rule in multiple places.
- Keep examples aligned with real config and behavior.
- Keep human-facing explanations in guides/reference/tutorial docs.
- Put strict machine-oriented schemas and constraints in `docs/models/`.

## Pull Request Checklist

- [ ] Tests pass locally.
- [ ] Docs are updated for behavior or structure changes.
- [ ] New links resolve correctly.
- [ ] Security-sensitive behavior remains fail-closed.
