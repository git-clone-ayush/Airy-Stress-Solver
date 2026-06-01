import sympy as sp

def apply_biharmonic(phi, x, y) -> list:
    """
    Evaluates the biharmonic operator on phi and collects coefficient constraints
    that must vanish to guarantee kinematic compatibility: ∇⁴φ = 0
    
    Returns list of polynomial coefficients that must equal zero.
    For polynomials of degree < 4, all coefficients are automatically zero.
    """
    # Compute Laplacian
    lap = sp.diff(phi, x, 2) + sp.diff(phi, y, 2)
    
    # Compute Bilaplacian
    bilap = sp.diff(lap, x, 2) + sp.diff(lap, y, 2)
    
    # For low-degree polynomials, biharmonic is automatically satisfied
    # For example, degree-2 polynomial: bilap = 0 identically
    if bilap == 0:
        return []
    
    # Extract coefficient equations from the biharmonic field
    # The biharmonic must vanish, so each coefficient of the polynomial must be zero
    try:
        poly = sp.Poly(bilap, x, y)
        coefficients = poly.coeffs()
        return coefficients if coefficients else []
    except (sp.PolynomialError, TypeError):
        # If can't convert to polynomial, return the expression itself
        return [bilap]
