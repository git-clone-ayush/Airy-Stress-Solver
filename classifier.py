LOAD_CASES = [
    ("distributed_load", 5, "Uniformly Distributed Load"),
    ("end_load", 4, "Cantilever End Point Load"),
    ("moment", 3, "Pure Bending"),
    ("pure_tension", 2, "Pure Tension/Compression"),
]


def classify_loading(specs: dict) -> tuple[int, str]:
    """
    Determine the polynomial degree from all active load types.

    When multiple loads are active, the highest required degree drives the
    polynomial order and the labels are combined for display.
    """
    if specs.get("degree") is not None:
        degree = int(specs["degree"])
        return degree, specs.get("case_name", f"Custom Boundary Expressions ({degree}th Degree)")

    active_cases = []
    max_degree = 0
    for key, degree, label in LOAD_CASES:
        if specs.get(key) is not None:
            active_cases.append(label)
            max_degree = max(max_degree, degree)

    if not active_cases:
        raise ValueError("Invalid boundary specifications. Cannot classify loading scenario.")

    if len(active_cases) == 1:
        return max_degree, f"{active_cases[0]} ({max_degree}th Degree)"

    return max_degree, f"Combined Loads: {' + '.join(active_cases)} ({max_degree}th Degree)"
