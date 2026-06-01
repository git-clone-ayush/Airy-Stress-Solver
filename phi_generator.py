import sympy as sp

def generate_phi(degree: int):
    """
    Dynamically constructs a generic polynomial of a specified degree using SymPy.
    """
    x, y = sp.symbols('x y')
    terms = []
    coeffs = []
    k = 0
    
    for n in range(2, degree + 1):
        for i in range(n + 1):
            j = n - i
            c = sp.Symbol(f'A{k}')
            terms.append(c * x**i * y**j)
            coeffs.append(c)
            k += 1
            
    phi = sum(terms)
    return phi, coeffs, (x, y)
