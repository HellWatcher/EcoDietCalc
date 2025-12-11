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
