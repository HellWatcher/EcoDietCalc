# EcoDietMaker / EcoDietCalc

Small Python project that generates environmentally-conscious diet plans.

## Quick start

1. Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install project (editable)
```bash
pip install -e .
pip install -r requirements.txt  # if present
```

3. Run the CLI
```bash
python main.py
# or
python -m main
```

4. Run tests
```bash
pytest
```

## Project layout
- main.py — entry point
- interface/ — CLI, persistence, prompts, render
- models/ — domain models (food, plan)
- planner.py, calculations.py — core logic
- tests/ — pytest test suite

## Notes & recommendations
- Remove or ignore runtime artifacts stored in repo (food_state.json, tuner_best.json, logs).
- Add CI (GitHub Actions) to run tests and linters on push.
- Consider adding basic linting (ruff/black) and type checks (mypy).

## Contributing
Fork, make a branch, commit, and open a pull request to your fork or upstream.

## License
Add a LICENSE file if you intend to publish this repository.