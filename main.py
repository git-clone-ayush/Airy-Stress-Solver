import sys

import sympy as sp

try:
    from .classifier import classify_loading
    from .phi_generator import generate_phi
    from .bc_applicator import apply_bcs_and_solve
except ImportError:
    from classifier import classify_loading
    from phi_generator import generate_phi
    from bc_applicator import apply_bcs_and_solve


CASE_OPTIONS = {
    "1": ("distributed_load", "Uniformly Distributed Load", "q (force per unit length, N/m)"),
    "2": ("end_load", "Cantilever End Point Load", "P (point force, Newtons, N)"),
    "3": ("moment", "Pure Bending", "M (bending moment, Newton-meters, N·m)"),
    "4": ("pure_tension", "Pure Tension / Compression", "F (axial force, Newtons, N)"),
    "5": ("custom", "Custom Boundary Expressions", "symbolic expressions in x, c, L, q, P, M, F"),
}

SUPPORT_OPTIONS = {
    "cantilever_left": "Cantilever (fixed at x=0)",
    "simply_supported": "Simply supported (pins/rollers at x=0 and x=L)",
}


STANDARD_LOCAL_SYMBOLS = {
    "x": sp.Symbol("x"),
    "y": sp.Symbol("y"),
    "c": sp.Symbol("c"),
    "L": sp.Symbol("L"),
    "q": sp.Symbol("q"),
    "P": sp.Symbol("P"),
    "M": sp.Symbol("M"),
    "F": sp.Symbol("F"),
    "V": sp.Symbol("V"),
    "tau_o": sp.Symbol("tau_o"),
    "sigma_o": sp.Symbol("sigma_o"),
}


def prompt_float(prompt: str, default: float | None = None) -> float:
    while True:
        raw_value = input(prompt).strip()
        if raw_value == "" and default is not None:
            return default
        try:
            return float(raw_value)
        except ValueError:
            print("Enter a valid number.")


def prompt_int(prompt: str, default: int | None = None) -> int:
    while True:
        raw_value = input(prompt).strip()
        if raw_value == "" and default is not None:
            return default
        try:
            return int(raw_value)
        except ValueError:
            print("Enter a valid integer.")


def prompt_expression(prompt: str, default: str = "0") -> str:
    raw_value = input(prompt).strip()
    return raw_value if raw_value else default


def prompt_case() -> tuple[dict, str]:
    print("\n" + "="*50)
    print("All inputs must be in SI units:")
    print("  • Length: meters (m)")
    print("  • Force: Newtons (N)")
    print("  • Distributed load: N/m")
    print("  • Moment: Newton-meters (N·m)")
    print("="*50 + "\n")
    print("Select a loading case:")
    for key, (_, label, _) in CASE_OPTIONS.items():
        print(f"  {key}. {label}")

    while True:
        choice = input("Enter case number (1-5): ").strip()
        if choice in CASE_OPTIONS:
            spec_key, label, symbol_name = CASE_OPTIONS[choice]
            if spec_key == "custom":
                specs = prompt_custom_case()
                specs["support_type"] = prompt_support_type()
                return specs, label
            value = prompt_float(f"Enter the boundary value for {symbol_name}: ")
            specs = {
                "distributed_load": None,
                "end_load": None,
                "moment": None,
                "pure_tension": None,
            }
            specs[spec_key] = value
            specs["support_type"] = prompt_support_type()
            return specs, label
        print("Choose 1, 2, 3, 4, or 5.")


def prompt_support_type() -> str:
    print("Select the beam support condition:")
    print("  1. Cantilever (fixed at x=0)")
    print("  2. Simply supported (pins/rollers at x=0 and x=L)")
    while True:
        choice = input("Enter support number (1-2): ").strip()
        if choice == "1":
            return "cantilever_left"
        if choice == "2":
            return "simply_supported"
        print("Choose 1 or 2.")


def prompt_custom_case() -> dict:
    print("Custom boundary expressions")
    degree = prompt_int("Polynomial degree to generate: ", default=4)
    print("Enter SymPy expressions. Press Enter to use 0.")

    return {
        "degree": degree,
        "distributed_load": None,
        "end_load": None,
        "moment": None,
        "pure_tension": None,
        "top_sigma_y": prompt_expression("σyy(x, c) = "),
        "bottom_sigma_y": prompt_expression("σyy(x, -c) = "),
        "top_tau_xy": prompt_expression("τxy(x, c) = "),
        "bottom_tau_xy": prompt_expression("τxy(x, -c) = "),
        "resultant_x": prompt_expression("Resultant section x = "),
        "resultant_axial_force": prompt_expression("∫σxx dy = "),
        "resultant_shear_force": prompt_expression("∫τxy dy = "),
        "resultant_moment": prompt_expression("∫σxx·y dy = "),
    }


def prompt_geometry() -> dict:
    print("Enter the beam geometry in SI units (meters, Newtons).")
    print("-" * 50)
    return {
        "L": prompt_float("Beam length L (meters, m): "),
        "c": prompt_float("Half-height c (meters, m): "),
        "P": 0.0,
        "M": 0.0,
        "q": 0.0,
        "F": 0.0,
    }


def prompt_custom_numeric_values(execution_values: dict) -> dict:
    print("Enter optional numeric values for plotting. Press Enter to keep 0.")
    for symbol_name in ["q", "P", "M", "F"]:
        execution_values[symbol_name] = prompt_float(f"{symbol_name} = ", default=0.0)
    return execution_values

def run_solver_pipeline(user_specs: dict, numeric_eval_values: dict, plot_stresses: bool = True):
    
    
    # Step 1: Classify
    if user_specs.get("degree") is not None:
        degree = user_specs["degree"]
        case_name = user_specs.get("case_name", "Custom Boundary Expressions")
    else:
        degree, case_name = classify_loading(user_specs)
    print(f"[STATUS] 1. Classifier: Selected Case -> {case_name}")
    
    # Step 2: Generate base space
    phi, coeffs, (x, y) = generate_phi(degree)
    print(f"[STATUS] 2. Generator: Extracted general polynomial of order {degree}.")
    
    # Step 3, 4, 5: Constraint enforcement and solution execution
    print(f"[STATUS] 3 & 4. Running Biharmonic Checking and BC Integrations...")
    final_phi, (sx, sy, txy), (c, L) = apply_bcs_and_solve(phi, coeffs, x, y, user_specs)
    
    print("\n" + "-"*40 + " ANALYTICAL SOLUTION " + "-"*40)
    print(f" Resolved φ(x, y) = {sp.simplify(final_phi)}")
    print(f" σx(x, y)  = {sp.simplify(sx)}")
    print(f" σy(x, y)  = {sp.simplify(sy)}")
    print(f" τxy(x, y) = {sp.simplify(txy)}")
    print("-" * 101)
    print("\n [UNITS] All stresses are in Pascals (Pa). Substitute L, c, q, P, M, F in SI units.")
    print("-" * 101 + "\n")
    
    # Step 6: Visualize
    print(f"[STATUS] 5. Visualizer: Initializing numerical grid rendering...")
    try:
        from .visualizer import visualize_stresses
    except ImportError:
        from visualizer import visualize_stresses

    # Compile execution variables map
    mapping = {}
    for sym_char in ['M', 'P', 'q', 'F']:
        if sym_char in numeric_eval_values:
            mapping[sp.Symbol(sym_char)] = numeric_eval_values[sym_char]

    mapping[c] = numeric_eval_values['c']
    mapping[L] = numeric_eval_values['L']

    if plot_stresses:
        visualize_stresses(sx, sy, txy, x, y, c, L, mapping, specs=user_specs)

    # Return symbolic results for further processing (GUI calls may use these)
    return final_phi, (sx, sy, txy), (c, L), mapping


def main():
    if any(arg in {"--gui", "-g"} for arg in sys.argv[1:]):
        try:
            from .gui import run_gui
        except ImportError:
            from gui import run_gui

        run_gui()
        return

    print("Airy Stress Function Solver")
    print("="*50)
    print("ALL INPUTS AND OUTPUTS ARE IN SI UNITS:")
    print("  • Lengths (L, c): meters (m)")
    print("  • Forces (P, F): Newtons (N)")
    print("  • Distributed Load (q): N/m")
    print("  • Moments (M): Newton-meters (N·m)")
    print("  • Stresses (σ, τ): Pascals (Pa = N/m²)")
    print("="*50)
    user_specs, _case_name = prompt_case()
    execution_values = prompt_geometry()

    if user_specs.get("degree") is not None:
        execution_values = prompt_custom_numeric_values(execution_values)
        user_specs["case_name"] = "Custom Boundary Expressions"

    if user_specs.get("distributed_load") is not None:
        execution_values["q"] = user_specs["distributed_load"]
    if user_specs.get("end_load") is not None:
        execution_values["P"] = user_specs["end_load"]
    if user_specs.get("moment") is not None:
        execution_values["M"] = user_specs["moment"]
    if user_specs.get("pure_tension") is not None:
        execution_values["F"] = user_specs["pure_tension"]

    run_solver_pipeline(user_specs, execution_values)


if __name__ == "__main__":
    main()
