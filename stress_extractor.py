import sympy as sp

def extract_stresses(phi, x, y) -> tuple:
    """
    Applies the partial differential relationships defining Airy stress fields.
    """
    sigma_x  =  sp.diff(phi, y, 2)
    sigma_y  =  sp.diff(phi, x, 2)
    tau_xy   = -sp.diff(phi, x, 1, y, 1)
    return sigma_x, sigma_y, tau_xy
