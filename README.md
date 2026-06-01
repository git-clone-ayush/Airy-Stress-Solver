# Airy Solver

Symbolic Airy stress-function solver for 2D Cartesian beam problems.

## Run

CLI:

```bash
python main.py
```

GUI:

```bash
python main.py --gui
```

Module form from the workspace root:

```bash
python -m airy_solver.main --gui
```

## Notes

- The GUI supports multiple standard loads at once.
- Load magnitudes are combined by type before solving.
- The solver uses SymPy for symbolic equations and Matplotlib for stress plots.
