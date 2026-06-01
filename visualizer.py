import numpy as np
import sympy as sp
import matplotlib.pyplot as plt

def visualize_stresses(sx_expr, sy_expr, tau_expr, x_sym, y_sym, c_sym, L_sym, numerical_params: dict, specs: dict | None = None):
    """
    Evaluates exact symbolic expressions numerically over a coordinate grid and plots the output.
    """
    # Ensure any unresolved symbolic coefficients get a numeric fallback (0)
    def prepare_expr(expr):
        # Symbols already assigned numeric values
        assigned = set(numerical_params.keys())
        # Remaining free symbols excluding the spatial variables
        remaining = set(expr.free_symbols) - {x_sym, y_sym} - assigned
        # Build full substitution map: given numeric params + fallback zeros
        subs_map = dict(numerical_params)
        for s in remaining:
            subs_map[s] = 0
        return expr.subs(subs_map)

    sx_num = prepare_expr(sx_expr)
    sy_num = prepare_expr(sy_expr)
    txy_num = prepare_expr(tau_expr)

    sx_func = sp.lambdify((x_sym, y_sym), sx_num, 'numpy')
    sy_func = sp.lambdify((x_sym, y_sym), sy_num, 'numpy')
    txy_func = sp.lambdify((x_sym, y_sym), txy_num, 'numpy')
    
    L_val = float(numerical_params[L_sym])
    c_val = float(numerical_params[c_sym])
    
    # Build structural evaluation grid
    X, Y = np.meshgrid(np.linspace(0, L_val, 150), np.linspace(-c_val, c_val, 80))
    
    # Capture edge cases where expressions evaluate to isolated scalars instead of arrays
    SX = sx_func(X, Y) if not isinstance(sx_func(X, Y), (int, float)) else np.full_like(X, sx_func(X, Y))
    SY = sy_func(X, Y) if not isinstance(sy_func(X, Y), (int, float)) else np.full_like(X, sy_func(X, Y))
    TXY = txy_func(X, Y) if not isinstance(txy_func(X, Y), (int, float)) else np.full_like(X, txy_func(X, Y))
    
    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    plots = [
        (SX, 'coolwarm', r'$\sigma_x$ (Axial Stress)'),
        (SY, 'PiYG', r'$\sigma_y$ (Transverse Stress)'),
        (TXY, 'PuOr', r'$\tau_{xy}$ (Shear Stress)')
    ]
    
    for ax, (data, cmap, title) in zip(axes, plots):
        cf = ax.contourf(X, Y, data, levels=50, cmap=cmap)
        fig.colorbar(cf, ax=ax, orientation='vertical', aspect=12)
        ax.set_title(title, fontsize=11, pad=8)
        ax.set_ylabel('y Coordinate')
        ax.set_aspect('equal')
        
    axes[-1].set_xlabel('x Coordinate')
    plt.tight_layout()
    plt.show()


def plot_sfd_bmd(sx_expr, tau_expr, x_sym, y_sym, c_sym, L_sym, numerical_params: dict, specs: dict | None = None):
    """Plot Shear Force Diagram (SFD) and Bending Moment Diagram (BMD).

    sx_expr: σx(x,y)
    tau_expr: τxy(x,y)
    numerical_params: mapping containing numeric `L` and `c` and optional load values
    specs: optional dict of loads to annotate diagrams
    """
    import numpy as np
    import matplotlib.pyplot as plt

    L_val = float(numerical_params[L_sym])
    c_val = float(numerical_params[c_sym])

    # prepare lambdified functions
    sx_num = sx_expr.subs(numerical_params)
    tau_num = tau_expr.subs(numerical_params)
    sx_func = sp.lambdify((x_sym, y_sym), sx_num, 'numpy')
    tau_func = sp.lambdify((x_sym, y_sym), tau_num, 'numpy')

    xs = np.linspace(0, L_val, 300)
    ys = np.linspace(-c_val, c_val, 201)

    S = np.zeros_like(xs)
    M = np.zeros_like(xs)

    for i, xv in enumerate(xs):
        # evaluate tau and sigma across y
        Y = ys
        XV = np.full_like(ys, xv)
        try:
            tau_vals = tau_func(XV, Y)
            sx_vals = sx_func(XV, Y)
        except Exception:
            # fallback: try scalar evaluation
            tau_vals = np.array([float(tau_num.subs({x_sym: xv, y_sym: yv})) for yv in ys])
            sx_vals = np.array([float(sx_num.subs({x_sym: xv, y_sym: yv})) for yv in ys])

        # shear force is integral of tau over section
        S[i] = np.trapz(tau_vals, ys)
        # bending moment is integral of sigma_x * y over section
        M[i] = np.trapz(sx_vals * ys, ys)

    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    axes[0].plot(xs, S, color='tab:blue')
    axes[0].axhline(0, color='k', linewidth=0.6)
    axes[0].set_ylabel('Shear V(x)')
    axes[0].set_title('Shear Force Diagram')

    axes[1].plot(xs, M, color='tab:orange')
    axes[1].axhline(0, color='k', linewidth=0.6)
    axes[1].set_ylabel('Moment M(x)')
    axes[1].set_xlabel('x')
    axes[1].set_title('Bending Moment Diagram')

    # annotate loads if provided
    if specs:
        # point loads
        loads = []
        for key, info in specs.items():
            # skip the resultant keys
            if key.startswith('resultant_') or key == 'degree' or key == 'case_name':
                continue

        # if GUI provided explicit load_rows it will annotate via GUI canvas; here we only show end/distributed
        q_val = specs.get('distributed_load')
        if q_val is not None:
            axes[0].text(0.02 * L_val, 0.9 * axes[0].get_ylim()[1], f'q={q_val}', color='red')
        P_val = specs.get('end_load')
        if P_val is not None:
            axes[0].annotate('', xy=(L_val, 0.8 * axes[0].get_ylim()[1]), xytext=(L_val, 0.2 * axes[0].get_ylim()[1]), arrowprops=dict(arrowstyle='->', color='green', lw=2))
            axes[0].text(L_val, 0.85 * axes[0].get_ylim()[1], f'P={P_val}', color='green', ha='right')

    plt.tight_layout()
    plt.show()
