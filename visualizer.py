import numpy as np
import sympy as sp
import matplotlib.pyplot as plt


def build_sfd_bmd_figure(sx_expr, tau_expr, x_sym, y_sym, c_sym, L_sym, numerical_params: dict, specs: dict | None = None):
    """Build a Matplotlib figure containing SFD and BMD plots without showing it."""
    L_val = float(numerical_params[L_sym])
    c_val = float(numerical_params[c_sym])

    sx_num = sx_expr.subs(numerical_params)
    tau_num = tau_expr.subs(numerical_params)
    sx_func = sp.lambdify((x_sym, y_sym), sx_num, 'numpy')
    tau_func = sp.lambdify((x_sym, y_sym), tau_num, 'numpy')

    xs = np.linspace(0, L_val, 300)
    ys = np.linspace(-c_val, c_val, 201)

    S = np.zeros_like(xs)
    M = np.zeros_like(xs)

    for i, xv in enumerate(xs):
        Y = ys
        XV = np.full_like(ys, xv)
        try:
            tau_vals = tau_func(XV, Y)
            sx_vals = sx_func(XV, Y)
        except Exception:
            tau_vals = np.array([float(tau_num.subs({x_sym: xv, y_sym: yv})) for yv in ys])
            sx_vals = np.array([float(sx_num.subs({x_sym: xv, y_sym: yv})) for yv in ys])

        S[i] = np.trapz(tau_vals, ys)
        M[i] = np.trapz(sx_vals * ys, ys)

    fig, axes = plt.subplots(2, 1, figsize=(9.5, 4.8), sharex=True)
    fig.patch.set_facecolor("#000000")

    axes[0].plot(xs, S, color='#00FFFF', linewidth=2.2)
    axes[0].axhline(0, color='#FFFFFF', linewidth=0.8)
    axes[0].set_ylabel('SFD', color='#FFFFFF', fontsize=10, fontweight='bold')
    axes[0].set_title('Shear Force Diagram', fontsize=11, weight='bold', color='#FFFFFF')
    axes[0].grid(True, alpha=0.22, linestyle='--', color='#444444')
    axes[0].set_facecolor('#1a1a1a')
    axes[0].tick_params(colors='#FFFFFF')

    axes[1].plot(xs, M, color='#00FF00', linewidth=2.2)
    axes[1].axhline(0, color='#FFFFFF', linewidth=0.8)
    axes[1].set_ylabel('BMD', color='#FFFFFF', fontsize=10, fontweight='bold')
    axes[1].set_xlabel('x', color='#FFFFFF', fontsize=10, fontweight='bold')
    axes[1].set_title('Bending Moment Diagram', fontsize=11, weight='bold', color='#FFFFFF')
    axes[1].grid(True, alpha=0.22, linestyle='--', color='#444444')
    axes[1].set_facecolor('#1a1a1a')
    axes[1].tick_params(colors='#FFFFFF')

    if specs:
        q_val = specs.get('distributed_load')
        if q_val is not None:
            axes[0].annotate(f'q = {q_val:g}', xy=(0.04 * L_val, 0.92 * max(S.max(), 1.0)), xycoords='data', color='#FFFF00', fontweight='bold')
        p_val = specs.get('end_load')
        if p_val is not None:
            axes[0].annotate('', xy=(L_val, 0.82 * max(S.max(), 1.0)), xytext=(L_val, 0.18 * max(S.max(), 1.0)), arrowprops=dict(arrowstyle='->', color='#00FF00', lw=2.2))
            axes[0].text(L_val, 0.86 * max(S.max(), 1.0), f'P = {p_val:g}', color='#00FF00', ha='right', va='bottom', fontweight='bold')

    fig.tight_layout()
    return fig

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
    fig = build_sfd_bmd_figure(sx_expr, tau_expr, x_sym, y_sym, c_sym, L_sym, numerical_params, specs)
    plt.show()
    return fig
