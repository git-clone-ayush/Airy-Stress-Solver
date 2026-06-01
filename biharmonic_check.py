import sympy as sp

def apply_biharmonic(phi, x, y) -> list:
    """
    Evaluates the biharmonic operator on phi and collects coefficient constraints
    that must vanish to guarantee kinematic compatibility.
    """
    lap = sp.diff(phi, x, 2) + sp.diff(phi, y, 2)
    bilap = sp.diff(lap, x, 2) + sp.diff(lap, y, 2)
    
    if bilap == 0:
        return []
        
    # Extract linear combination expressions from the biharmonic field
    poly = sp.Poly(bilap, x, y)
    return poly.coeffs()
