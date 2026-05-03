# Release checklist

1. Update `pyproject.toml` version.
2. Update `CHANGELOG.md`.
3. Run package validation:

   ```bash
   ruff check .
   mypy src tests
   python -m compileall -q src tests
   pytest -q
   python -m build
   ```

4. Validate the Hermes core patch artifact against a clean Hermes checkout.
5. Confirm `README.md`, `docs/`, and `examples/` match the release behavior.
6. Tag and publish only after the GitHub repository contains the verified commit.
