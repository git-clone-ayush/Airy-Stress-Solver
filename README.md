# Airy Stress Function Solver

A symbolic solver for 2D Cartesian beam problems using the Airy stress function method. Automatically computes analytical stress fields (σx, σy, τxy) and generates shear force & bending moment diagrams.

## Features

- **Symbolic computation** using SymPy for exact closed-form Airy stress functions
- **Multiple load types**: distributed, point, partial distributed, moments, and axial forces
- **Interactive GUI** with drag-and-drop load placement on the beam canvas
- **Real-time diagrams**: embedded SFD/BMD plots and stress field contours
- **Support conditions**: Cantilever and simply supported beams (fully determined equations)
- **CLI & GUI modes**: Choose between interactive or batch solving
- **SI Units**: All inputs and outputs in SI units (meters, Newtons, Pascals)
- **Fully determined system**: Fixed boundary condition handling ensures no underdetermined coefficients

## Installation

```bash
# From the workspace root
python -m pip install -r requirements.txt  # if a requirements file exists
```

## Usage

### Units: All inputs and outputs are in **SI units**

| Quantity | Unit | Symbol |
|----------|------|--------|
| Length (L, c) | meters | m |
| Point Force (P, F) | Newtons | N |
| Distributed Load (q) | force per length | N/m |
| Moment (M) | Newton-meters | N·m |
| **Stress (σ, τ)** | **Pascals** | **Pa (N/m²)** |

### GUI (Interactive)

```bash
python main.py --gui
# or
python -m airy_solver.main --gui
```

**Workflow:**
1. Set beam length (L) in meters and half-height (c) in meters
2. Select support type (Cantilever or Simply Supported)
3. Choose a load type and enter magnitude in appropriate SI units (N, N/m, or N·m)
4. Click "Place on Beam" to add the load to the canvas
5. Drag placed loads horizontally to adjust their position
6. Click "Solve" to compute the symbolic Airy stress function
7. View the analytical solution and embedded SFD/BMD diagrams

### CLI (Batch)

```bash
python main.py
```

Follow the interactive prompts to:
1. Select a loading case (distributed, end point, moment, tension, or custom)
2. Enter load magnitude and beam geometry **in SI units**
3. View the resolved Airy function φ(x,y) and all stress components
4. Stresses are computed in Pascals (Pa)

## Load Types

| Load Type | Symbol | Description | Position |
|-----------|--------|-------------|----------|
| Distributed Load | `q` | Uniform load over full span | Full span |
| Point Load | `P` | Concentrated force at arbitrary x | Anywhere on beam |
| End Load | `P` | Point load at x = L | Right end |
| Moment | `M` | End moment (x = L) | Right end |
| Concentrated Moment | `M` | Moment at arbitrary x | Anywhere on beam |
| Partial Distributed | `q` | Uniform load over [a, b] span | Custom range |
| Axial Force | `F` | Pure tension/compression | Whole section |

## Support Conditions

- **Cantilever (fixed at x=0)**: All reactions at the left support
- **Simply Supported (pins/rollers at x=0 and x=L)**: Distributed reactions at both ends

## Architecture & Workflow

The solver follows a 5-step pipeline:

```
1. Load Classification    → Determine polynomial degree from load types
2. Phi Generation        → Create symbolic Airy polynomial basis
3. Biharmonic Check      → Extract kinematic compatibility constraints (∇⁴Φ = 0)
4. Boundary Conditions   → Apply traction, resultant, and reaction constraints
5. Coefficient Solution  → Solve linear system for polynomial coefficients
6. Stress Field Output   → Extract σx, σy, τxy and generate SFD/BMD diagrams
```

**Key Features:**
- Biharmonic constraints provide ~40% of equations
- Traction boundary conditions (σy, τxy at top/bottom) provide ~40%
- Sectional resultants (axial, shear, moment) and support reactions complete the system
- Result: Fully determined square system with unique solution

## Core Modules

- **`main.py`**: Entry point, CLI interface, and solver pipeline orchestration
- **`gui.py`**: Tkinter-based interactive beam editor with drag-and-drop load placement and embedded Matplotlib diagrams
- **`classifier.py`**: Classifies loading cases and determines required polynomial degree
- **`phi_generator.py`**: Generates symbolic Airy stress function polynomial basis of specified degree
- **`stress_extractor.py`**: Computes stress components (σx, σy, τxy) from Airy function using PDEs
- **`bc_applicator.py`**: Assembles and solves the complete boundary condition system; handles support-specific reaction calculations
- **`biharmonic_check.py`**: Extracts kinematic compatibility constraints from biharmonic equation (∇⁴Φ = 0)
- **`visualizer.py`**: Generates Shear Force Diagrams (SFD), Bending Moment Diagrams (BMD), and stress field contours

## Example: Cantilever Beam with Distributed Load

**Input (SI units):**
- Length: L = 12 m
- Half-height: c = 1.5 m  
- Support: Cantilever (fixed at x=0)
- Load: q = 1000 N/m (uniform over full span)

**Output:**
```
Resolved φ(x, y) = ... (Airy stress function)
σx(x, y) = ... (longitudinal stress in Pa)
σy(x, y) = ... (transverse stress in Pa)
τxy(x, y) = ... (shear stress in Pa)
```

**Diagrams:**
- Shear Force Diagram (SFD): Varies linearly from -12,000 N at x=0 to 0 at x=L
- Bending Moment Diagram (BMD): Parabolic, peak 72,000 N·m at x=0
- Stress contours: Show stress distribution across cross-section (in Pascals)

## Notes & Limitations

- **Fully determined system** (as of June 2026): All critical boundary condition issues have been resolved
  - Simply-supported reaction formulas corrected
  - Right shear constraint properly applied
  - Biharmonic constraint handling improved
  - Both cantilever and simply-supported modes produce fully resolved polynomial coefficients
  
- **Cantilever beams** solve exactly with high polynomial degrees
- **Simply supported beams** now properly constrained and fully determined
- **Custom expressions** can be entered via CLI for non-standard boundary conditions
- **Multiple loads** are automatically aggregated into resultant forces and moments

## Recent Improvements (June 2026)

- ✅ **Fixed boundary condition solver**: Eliminated underdetermined systems
  - Corrected reaction calculations for simply-supported beams
  - Added missing right support shear constraint
  - Improved biharmonic constraint extraction
  
- ✅ **Explicit SI unit labeling**: All prompts and input fields now show units clearly
  - GUI displays units next to each parameter (m, N, N/m, N·m)
  - CLI prompts emphasize SI system at startup
  - Output reminds users that stresses are in Pascals

## Requirements

- **Python** 3.9 or higher
- **SymPy** - Symbolic mathematics and equation solving
- **NumPy** - Numerical operations and array handling
- **Matplotlib** - Stress field visualization and diagram plotting
- **Tkinter** - GUI framework (typically bundled with Python)

**Optional:**
- **Jupyter** - For interactive notebook-based analysis

## Installation

```bash
# Clone or download the airy_solver directory
cd airy_solver

# Install dependencies
pip install sympy numpy matplotlib

# Run the GUI
python main.py --gui

# Or run CLI
python main.py
```

## Troubleshooting

- **"No module named 'tkinter'"**: On Linux, run `sudo apt-get install python3-tk`
- **"Underdetermined coefficients" warning**: Ensure all load parameters are set correctly; check that beam geometry (L, c) is positive
- **GUI doesn't appear**: Verify your display/environment supports Tkinter; try CLI mode instead

## Contributing

Extend the solver by:

1. **Adding new load types**: Modify `LOAD_TYPES` in `gui.py` and `CASE_OPTIONS` in `main.py`
2. **Custom boundary conditions**: Use the "Custom" option in CLI to enter symbolic expressions
3. **New support types**: Add cases to `_reaction_targets()` in `bc_applicator.py`
4. **Enhanced visualization**: Extend `visualizer.py` with additional plots or animations

## License

This project is provided as-is for educational and research purposes.
