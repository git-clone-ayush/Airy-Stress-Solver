import sympy as sp

try:
    from .stress_extractor import extract_stresses
    from .biharmonic_check import apply_biharmonic
except ImportError:
    from stress_extractor import extract_stresses
    from biharmonic_check import apply_biharmonic


LOCAL_SYMBOLS = {
    "x": sp.Symbol("x"),
    "y": sp.Symbol("y"),
    "c": sp.Symbol("c", positive=True),
    "L": sp.Symbol("L", positive=True),
    "q": sp.Symbol("q"),
    "P": sp.Symbol("P"),
    "M": sp.Symbol("M"),
    "F": sp.Symbol("F"),
    "V": sp.Symbol("V"),
    "tau_o": sp.Symbol("tau_o"),
    "sigma_o": sp.Symbol("sigma_o"),
}


def _expand_to_scalar_equations(expr, *poly_symbols):
    """Return scalar coefficient equations for any polynomial expression."""
    expanded = sp.expand(expr)
    if not poly_symbols:
        return [expanded]

    try:
        poly = sp.Poly(expanded, *poly_symbols)
    except sp.PolynomialError:
        return [expanded]

    return poly.coeffs()


def _equations_from_relation(lhs, rhs=0, *poly_symbols):
    """Convert a symbolic relation into scalar polynomial equations."""
    return _expand_to_scalar_equations(lhs - rhs, *poly_symbols)


def _scalar_equation(lhs, rhs=0):
    """Convert a scalar relation into a single equation."""
    return [sp.expand(lhs - rhs)]


def _parse_expr(value):
    """Parse a user-supplied boundary expression into a SymPy expression."""
    if value is None:
        return None
    if isinstance(value, sp.Basic):
        return value
    if isinstance(value, (int, float)):
        return sp.sympify(value)

    text = str(value).strip()
    if not text:
        return None

    return sp.sympify(text, locals=LOCAL_SYMBOLS)


def _get_expr(specs, key, default):
    parsed = _parse_expr(specs.get(key))
    return default if parsed is None else parsed


def _reaction_targets(specs, L, total_vertical, total_moment):
    """Return support reactions for the current beam support condition."""
    support_type = str(specs.get("support_type", "cantilever_left"))

    if support_type == "simply_supported":
        # For simply-supported: use moment equilibrium about left support
        # M_left = 0: right_reaction * L - total_moment = 0
        right_reaction = sp.simplify(total_moment / L)
        # Vertical equilibrium: left_reaction + right_reaction = total_vertical
        left_reaction = sp.simplify(total_vertical - right_reaction)
        return {
            "left_shear": left_reaction,
            "left_moment": sp.Integer(0),
            "right_shear": right_reaction,
            "right_moment": sp.Integer(0),
        }

    # Default to cantilever-left behavior.
    return {
        "left_shear": total_vertical,
        "left_moment": total_moment,
        "right_shear": sp.Integer(0),
        "right_moment": sp.Integer(0),
    }

def apply_bcs_and_solve(phi, coeffs, x, y, specs: dict) -> tuple:
    """
    Assembles compatibility and physical boundary constraints to resolve 
    unknown polynomial coefficients.
    """
    sigma_x, sigma_y, tau_xy = extract_stresses(phi, x, y)
    equations = []
    x_boundary = _get_expr(specs, "resultant_x", sp.Integer(0))
    
    # 1. Inject Biharmonic requirements
    for expr in apply_biharmonic(phi, x, y):
        equations.extend(_expand_to_scalar_equations(expr, x, y))
    
    # 2. Establish geometric parameters
    c = sp.Symbol('c', positive=True) # half-height
    L = sp.Symbol('L', positive=True) # beam length
    
    # Parse loads
    q_val = specs.get("distributed_load")
    m_val = specs.get("moment")
    p_val = specs.get("end_load")
    f_val = specs.get("pure_tension")

    top_sigma_target = _parse_expr(specs.get("top_sigma_y"))
    bottom_sigma_target = _parse_expr(specs.get("bottom_sigma_y"))
    top_tau_target = _parse_expr(specs.get("top_tau_xy"))
    bottom_tau_target = _parse_expr(specs.get("bottom_tau_xy"))

    if top_sigma_target is None:
        top_sigma_target = -sp.Symbol("q") if q_val is not None else sp.Integer(0)
    if bottom_sigma_target is None:
        bottom_sigma_target = sp.Integer(0)
    if top_tau_target is None:
        top_tau_target = sp.Integer(0)
    if bottom_tau_target is None:
        bottom_tau_target = sp.Integer(0)
    
    # Top/Bottom Traction Profiles
    # For standard loading with distributed load: σy(x,c) = -q
    # For free surfaces: σy = 0 and τxy = 0 where no load is applied
    equations.extend(_equations_from_relation(sigma_y.subs(y, c), top_sigma_target, x))
    equations.extend(_equations_from_relation(sigma_y.subs(y, -c), bottom_sigma_target, x))
    equations.extend(_equations_from_relation(tau_xy.subs(y, c), top_tau_target, x))
    equations.extend(_equations_from_relation(tau_xy.subs(y, -c), bottom_tau_target, x))
        
    # 3. Handle Cross-Sectional Resultant Integrals
    section_sigma_x = sigma_x.subs(x, x_boundary)
    section_tau_xy = tau_xy.subs(x, x_boundary)

    axial_target = _parse_expr(specs.get("resultant_axial_force"))
    shear_target = _parse_expr(specs.get("resultant_shear_force"))
    moment_target = _parse_expr(specs.get("resultant_moment"))

    support_type = str(specs.get("support_type", "cantilever_left"))

    if q_val is not None and axial_target is None and shear_target is None and moment_target is None:
        q = sp.Symbol('q')
        axial_target = sp.Integer(0)
        shear_target = q * L
        moment_target = q * L**2 / 2

    if p_val is not None and axial_target is None and shear_target is None and moment_target is None:
        P = sp.Symbol('P')
        axial_target = sp.Integer(0)
        shear_target = P
        moment_target = P * L

    if m_val is not None and axial_target is None and shear_target is None and moment_target is None:
        M = sp.Symbol('M')
        axial_target = sp.Integer(0)
        shear_target = sp.Integer(0)
        moment_target = M

    if f_val is not None and axial_target is None and shear_target is None and moment_target is None:
        F = sp.Symbol('F')
        axial_target = F
        shear_target = sp.Integer(0)
        moment_target = sp.Integer(0)

    reactions = _reaction_targets(
        specs,
        L,
        shear_target if shear_target is not None else sp.Integer(0),
        moment_target if moment_target is not None else sp.Integer(0),
    )

    if support_type == "simply_supported":
        left_section_sigma = sigma_x.subs(x, sp.Integer(0))
        left_section_tau = tau_xy.subs(x, sp.Integer(0))
        right_section_sigma = sigma_x.subs(x, L)
        right_section_tau = tau_xy.subs(x, L)

        # Left support: shear and moment equilibrium
        equations.extend(_scalar_equation(sp.integrate(left_section_tau, (y, -c, c)), reactions["left_shear"]))
        equations.extend(_scalar_equation(sp.integrate(left_section_sigma * y, (y, -c, c)), reactions["left_moment"]))
        
        # Right support: moment equilibrium (shear internal = external applied)
        equations.extend(_scalar_equation(sp.integrate(right_section_sigma * y, (y, -c, c)), reactions["right_moment"]))
        
        # Right support: shear equilibrium (ADDED - was missing, critical fix)
        equations.extend(_scalar_equation(sp.integrate(right_section_tau, (y, -c, c)), reactions["right_shear"]))
        
        if axial_target is not None:
            equations.extend(_scalar_equation(sp.integrate(left_section_sigma, (y, -c, c)), axial_target))
    else:
        if axial_target is not None:
            equations.extend(_scalar_equation(sp.integrate(section_sigma_x, (y, -c, c)), axial_target))
        if shear_target is not None:
            equations.extend(_scalar_equation(sp.integrate(section_tau_xy, (y, -c, c)), shear_target))
        if moment_target is not None:
            equations.extend(_scalar_equation(sp.integrate(section_sigma_x * y, (y, -c, c)), moment_target))
        
    # Solve the system linear equations
    sol = sp.solve(equations, coeffs)
    if isinstance(sol, list):
        sol = sol[0] if sol else {}
    if not isinstance(sol, dict):
        sol = dict(sol)

    unresolved = [coeff for coeff in coeffs if coeff not in sol]
    if unresolved:
        print(
            "[WARN] Unresolved polynomial coefficients remain underdetermined: "
            + ", ".join(str(coeff) for coeff in unresolved)
        )
        sol.update({coeff: 0 for coeff in unresolved})
    
    # Substitute back solved elements
    final_phi = phi.subs(sol)
    final_sx, final_sy, final_txy = extract_stresses(final_phi, x, y)
    
    return final_phi, (final_sx, final_sy, final_txy), (c, L)
