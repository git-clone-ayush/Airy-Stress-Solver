from __future__ import annotations

import io
import sympy as sp
import tkinter as tk
from contextlib import redirect_stdout
from tkinter import messagebox, scrolledtext, ttk

try:
    from .main import run_solver_pipeline
except ImportError:
    from main import run_solver_pipeline


LOAD_TYPES = {
    "distributed_load": {"label": "Uniformly distributed load", "symbol": "q", "default": 0.0, "display": "q"},
    "partial_distributed": {"label": "Partial distributed (span)", "symbol": "q", "default": 0.0, "display": "q over span"},
    "point_load": {"label": "Point load at x", "symbol": "P", "default": 0.0, "display": "P@x"},
    "end_load": {"label": "End point load (x=L)", "symbol": "P", "default": 0.0, "display": "P"},
    "moment": {"label": "End moment (x=L)", "symbol": "M", "default": 0.0, "display": "M"},
    "concentrated_moment": {"label": "Concentrated moment at x", "symbol": "M", "default": 0.0, "display": "M@x"},
    "pure_tension": {"label": "Axial force", "symbol": "F", "default": 0.0, "display": "F"},
}


class AirySolverApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Airy Stress Function Solver")
        self.root.geometry("1280x820")
        self.root.minsize(1120, 720)

        self.beam_length_var = tk.StringVar(value="12")
        self.beam_half_height_var = tk.StringVar(value="1.5")
        self.load_type_var = tk.StringVar(value="distributed_load")
        self.load_value_var = tk.StringVar(value="10")
        self.load_rows: list[dict[str, float | str]] = []
        self.next_load_id = 1
        self.place_mode: str | None = None
        self.partial_start_x: float | None = None
        self.drag_load_id: int | None = None
        self.drag_offset_x: float = 0.0
        self.beam_bounds = (80, 800)

        self._build_styles()
        self._build_layout()
        self._bind_canvas_events()
        self._redraw_beam()

    def _build_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
        style.configure("Section.TLabelframe", padding=10)
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"))

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="Airy Stress Function Solver", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Build a beam, stack multiple loads, then solve the Airy stress field symbolically.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        content = ttk.Frame(outer)
        content.pack(fill="both", expand=True)

        left = ttk.Frame(content)
        left.pack(side="left", fill="both", expand=True)

        right = ttk.Frame(content, width=380)
        right.pack(side="right", fill="y", padx=(14, 0))
        right.pack_propagate(False)

        self.canvas = tk.Canvas(left, bg="#f6f2ea", highlightthickness=0, height=380)
        self.canvas.pack(fill="x", expand=False)

        beam_controls = ttk.LabelFrame(left, text="Beam Parameters", style="Section.TLabelframe")
        beam_controls.pack(fill="x", pady=(12, 0))

        beam_grid = ttk.Frame(beam_controls)
        beam_grid.pack(fill="x")
        beam_grid.columnconfigure(1, weight=1)
        beam_grid.columnconfigure(3, weight=1)

        ttk.Label(beam_grid, text="Length L").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(beam_grid, textvariable=self.beam_length_var, width=12).grid(row=0, column=1, sticky="we", pady=4)
        ttk.Label(beam_grid, text="Half-height c").grid(row=0, column=2, sticky="w", padx=(12, 8), pady=4)
        ttk.Entry(beam_grid, textvariable=self.beam_half_height_var, width=12).grid(row=0, column=3, sticky="we", pady=4)

        load_controls = ttk.LabelFrame(left, text="Loads", style="Section.TLabelframe")
        load_controls.pack(fill="x", pady=(12, 0))

        load_grid = ttk.Frame(load_controls)
        load_grid.pack(fill="x")
        load_grid.columnconfigure(1, weight=1)
        load_grid.columnconfigure(3, weight=1)

        ttk.Label(load_grid, text="Load type").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        load_selector = ttk.Combobox(
            load_grid,
            textvariable=self.load_type_var,
            values=list(LOAD_TYPES.keys()),
            state="readonly",
            width=22,
        )
        load_selector.grid(row=0, column=1, sticky="we", pady=4)
        load_selector.bind("<<ComboboxSelected>>", self._on_load_type_changed)

        ttk.Label(load_grid, text="Magnitude").grid(row=0, column=2, sticky="w", padx=(12, 8), pady=4)
        ttk.Entry(load_grid, textvariable=self.load_value_var, width=12).grid(row=0, column=3, sticky="we", pady=4)

        button_row = ttk.Frame(load_controls)
        button_row.pack(fill="x", pady=(8, 0))
        ttk.Button(button_row, text="Add Load", command=self.add_load).pack(side="left")
        ttk.Button(button_row, text="Place on Beam", command=self.start_place_on_beam).pack(side="left", padx=(8, 0))
        ttk.Button(button_row, text="Remove Selected", command=self.remove_selected_load).pack(side="left", padx=(8, 0))
        ttk.Button(button_row, text="Clear Loads", command=self.clear_loads).pack(side="left", padx=(8, 0))
        ttk.Button(button_row, text="Solve", command=self.solve).pack(side="right")

        list_frame = ttk.LabelFrame(left, text="Active Loads", style="Section.TLabelframe")
        list_frame.pack(fill="both", expand=True, pady=(12, 0))

        self.load_listbox = tk.Listbox(list_frame, height=8, activestyle="dotbox")
        self.load_listbox.pack(side="left", fill="both", expand=True)
        load_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.load_listbox.yview)
        load_scroll.pack(side="right", fill="y")
        self.load_listbox.configure(yscrollcommand=load_scroll.set)

        summary_box = ttk.LabelFrame(right, text="Solver Output", style="Section.TLabelframe")
        summary_box.pack(fill="both", expand=True)

        self.output = scrolledtext.ScrolledText(summary_box, wrap="word", height=32, font=("Consolas", 10))
        self.output.pack(fill="both", expand=True)
        self._append_output("Add one or more loads, then press Solve.\n")

        help_box = ttk.LabelFrame(right, text="Notes", style="Section.TLabelframe")
        help_box.pack(fill="x", pady=(12, 0))
        ttk.Label(
            help_box,
            text=(
                "Click Place on Beam, then click the beam to add a load. "
                "Point loads and moments can be dragged horizontally after placement."
            ),
            wraplength=320,
            justify="left",
        ).pack(anchor="w")

    def _bind_canvas_events(self) -> None:
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

    def _on_load_type_changed(self, _event=None) -> None:
        selected = LOAD_TYPES[self.load_type_var.get()]
        self.load_value_var.set(str(selected["default"]))

    def _append_output(self, text: str) -> None:
        self.output.insert("end", text)
        self.output.see("end")

    def _clear_output(self) -> None:
        self.output.delete("1.0", "end")

    def _parse_float(self, text: str, label: str) -> float:
        try:
            return float(text)
        except ValueError as exc:
            raise ValueError(f"{label} must be a valid number.") from exc

    def add_load(self) -> None:
        load_key = self.load_type_var.get()
        load_info = LOAD_TYPES[load_key]
        try:
            params = self._ask_load_params(load_key, load_info)
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        self.load_rows.append(params)
        display_label = params.get("display", load_info["display"])
        self.load_listbox.insert("end", display_label)
        self._redraw_beam()

    def start_place_on_beam(self) -> None:
        self.place_mode = self.load_type_var.get()
        self.partial_start_x = None
        self._append_output(f"\n[INFO] Placement mode: click the beam to place {LOAD_TYPES[self.place_mode]['label']}.\n")

    def _canvas_to_x(self, event_x: int) -> float:
        left, right = self.beam_bounds
        if right <= left:
            return 0.0
        clamped = max(left, min(right, event_x))
        L = self._parse_float(self.beam_length_var.get(), "Beam length L")
        return (clamped - left) / (right - left) * L

    def _x_to_canvas(self, x_value: float) -> float:
        left, right = self.beam_bounds
        L = self._parse_float(self.beam_length_var.get(), "Beam length L")
        if L <= 0:
            return left
        return left + (x_value / L) * (right - left)

    def _find_load_at_canvas_item(self, item_id: int) -> int | None:
        tags = self.canvas.gettags(item_id)
        for tag in tags:
            if tag.startswith("load_"):
                try:
                    return int(tag.split("_", 1)[1])
                except ValueError:
                    return None
        return None

    def _get_load_by_id(self, load_id: int) -> dict | None:
        for row in self.load_rows:
            if int(row.get("id", -1)) == load_id:
                return row
        return None

    def _on_canvas_click(self, event: tk.Event) -> None:
        x = self._canvas_to_x(event.x)
        hit = self.canvas.find_withtag("current")
        if hit:
            load_id = self._find_load_at_canvas_item(hit[0])
            if load_id is not None:
                row = self._get_load_by_id(load_id)
                if row is not None and row.get("key") in {"point_load", "end_load", "moment", "concentrated_moment"}:
                    self.drag_load_id = load_id
                    self.drag_offset_x = x - float(row.get("x", x))
                    return

        if not self.place_mode:
            return

        load_key = self.place_mode
        magnitude = self._parse_float(self.load_value_var.get(), "Load magnitude")

        if load_key == "partial_distributed":
            if self.partial_start_x is None:
                self.partial_start_x = x
                self._append_output(f"[INFO] Partial distributed load start set at x={x:.3g}. Click again to set the end.\n")
                return
            start_x = min(self.partial_start_x, x)
            end_x = max(self.partial_start_x, x)
            self._add_load_row({
                "key": load_key,
                "magnitude": magnitude,
                "start": start_x,
                "end": end_x,
                "label": LOAD_TYPES[load_key]["label"],
                "display": f'q={magnitude:g} on [{start_x:.3g},{end_x:.3g}]',
            })
            self.partial_start_x = None
            self.place_mode = None
            return

        if load_key == "distributed_load":
            self._add_load_row({
                "key": load_key,
                "magnitude": magnitude,
                "label": LOAD_TYPES[load_key]["label"],
                "display": f'q={magnitude:g} over full span',
            })
        elif load_key in {"point_load", "end_load", "moment", "concentrated_moment"}:
            self._add_load_row({
                "key": load_key,
                "magnitude": magnitude,
                "x": self._beam_x_for_load(load_key, x),
                "label": LOAD_TYPES[load_key]["label"],
                "display": f'{LOAD_TYPES[load_key]["display"]}={magnitude:g}@{x:.3g}',
            })
        elif load_key == "pure_tension":
            self._add_load_row({
                "key": load_key,
                "magnitude": magnitude,
                "label": LOAD_TYPES[load_key]["label"],
                "display": f'F={magnitude:g}',
            })

        self.place_mode = None

    def _on_canvas_drag(self, event: tk.Event) -> None:
        if self.drag_load_id is None:
            return
        row = self._get_load_by_id(self.drag_load_id)
        if row is None:
            return
        if row.get("key") not in {"point_load", "end_load", "moment", "concentrated_moment"}:
            return

        x = self._canvas_to_x(event.x) - self.drag_offset_x
        L = self._parse_float(self.beam_length_var.get(), "Beam length L")
        x = max(0.0, min(L, x))
        row["x"] = x
        row["display"] = self._format_load_display(row)
        self._redraw_beam()

    def _on_canvas_release(self, _event: tk.Event) -> None:
        if self.drag_load_id is not None:
            row = self._get_load_by_id(self.drag_load_id)
            if row is not None:
                self._sync_listbox_from_rows()
            self.drag_load_id = None
            self._redraw_beam()

    def _beam_x_for_load(self, load_key: str, x: float) -> float:
        if load_key == "end_load":
            return self._parse_float(self.beam_length_var.get(), "Beam length L")
        return x

    def _format_load_display(self, row: dict) -> str:
        key = str(row["key"])
        magnitude = float(row["magnitude"])
        if key in {"point_load", "end_load", "moment", "concentrated_moment"}:
            return f'{LOAD_TYPES[key]["display"]}={magnitude:g}@{float(row.get("x", 0.0)):.3g}'
        if key == "distributed_load":
            return f'q={magnitude:g} over full span'
        if key == "partial_distributed":
            return f'q={magnitude:g} on [{float(row.get("start", 0.0)):.3g},{float(row.get("end", 0.0)):.3g}]'
        if key == "pure_tension":
            return f'F={magnitude:g}'
        return row.get("display", LOAD_TYPES[key]["display"])

    def _add_load_row(self, row: dict) -> None:
        row["id"] = self.next_load_id
        self.next_load_id += 1
        self.load_rows.append(row)
        self._sync_listbox_from_rows()
        self._redraw_beam()

    def _sync_listbox_from_rows(self) -> None:
        self.load_listbox.delete(0, "end")
        for row in self.load_rows:
            self.load_listbox.insert("end", self._format_load_display(row))

    def _ask_load_params(self, load_key: str, load_info: dict) -> dict:
        """Open a small dialog to collect additional parameters for richer load types."""
        dlg = tk.Toplevel(self.root)
        dlg.transient(self.root)
        dlg.title("Load Parameters")
        dlg.grab_set()

        mag_var = tk.StringVar(value=self.load_value_var.get())
        pos_var = tk.StringVar(value="0.0")
        start_var = tk.StringVar(value="0.0")
        end_var = tk.StringVar(value="0.0")

        row = 0
        ttk.Label(dlg, text=load_info["label"]).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=8)
        row += 1

        ttk.Label(dlg, text="Magnitude:").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(dlg, textvariable=mag_var).grid(row=row, column=1, sticky="we", padx=8, pady=4)
        row += 1

        if load_key in ("point_load", "concentrated_moment"):
            ttk.Label(dlg, text="Position x (0..L):").grid(row=row, column=0, sticky="w", padx=8, pady=4)
            ttk.Entry(dlg, textvariable=pos_var).grid(row=row, column=1, sticky="we", padx=8, pady=4)
            row += 1

        if load_key == "partial_distributed":
            ttk.Label(dlg, text="Start x (0..L):").grid(row=row, column=0, sticky="w", padx=8, pady=4)
            ttk.Entry(dlg, textvariable=start_var).grid(row=row, column=1, sticky="we", padx=8, pady=4)
            row += 1
            ttk.Label(dlg, text="End x (0..L):").grid(row=row, column=0, sticky="w", padx=8, pady=4)
            ttk.Entry(dlg, textvariable=end_var).grid(row=row, column=1, sticky="we", padx=8, pady=4)
            row += 1

        result = {}

        def on_ok() -> None:
            try:
                mag = float(mag_var.get())
            except ValueError:
                messagebox.showerror("Invalid", "Magnitude must be a number")
                return

            result["key"] = load_key
            result["magnitude"] = mag
            result["label"] = load_info["label"]
            if load_key in ("point_load", "concentrated_moment"):
                try:
                    pos = float(pos_var.get())
                except ValueError:
                    messagebox.showerror("Invalid", "Position must be a number")
                    return
                result["pos"] = pos
                result["display"] = f'{load_info["display"]}={mag:g}@{pos:g}'
            if load_key == "partial_distributed":
                try:
                    a = float(start_var.get())
                    b = float(end_var.get())
                except ValueError:
                    messagebox.showerror("Invalid", "Start and end must be numbers")
                    return
                if b <= a:
                    messagebox.showerror("Invalid", "End must be > start")
                    return
                result["start"] = a
                result["end"] = b
                result["display"] = f'q={mag:g} on [{a:g},{b:g}]'

            dlg.grab_release()
            dlg.destroy()

        def on_cancel() -> None:
            dlg.grab_release()
            dlg.destroy()

        btn_row = ttk.Frame(dlg)
        btn_row.grid(row=row, column=0, columnspan=2, pady=12)
        ttk.Button(btn_row, text="OK", command=on_ok).pack(side="left", padx=6)
        ttk.Button(btn_row, text="Cancel", command=on_cancel).pack(side="left")

        dlg.wait_window()

        if not result:
            raise ValueError("Load dialog cancelled")
        return result

    def remove_selected_load(self) -> None:
        selection = list(self.load_listbox.curselection())
        if not selection:
            return
        for index in reversed(selection):
            del self.load_rows[index]
            self.load_listbox.delete(index)
        self._redraw_beam()

    def clear_loads(self) -> None:
        self.load_rows.clear()
        self.load_listbox.delete(0, "end")
        self._redraw_beam()

    def _combined_specs(self) -> tuple[dict, dict]:
        specs = {
            "distributed_load": None,
            "end_load": None,
            "moment": None,
            "pure_tension": None,
        }
        import sympy as sp

        L = self._parse_float(self.beam_length_var.get(), "Beam length L")
        c = self._parse_float(self.beam_half_height_var.get(), "Half-height c")

        numeric_values = {"L": L, "c": c, "P": 0.0, "M": 0.0, "q": 0.0, "F": 0.0}

        # Build resultant totals (evaluated numerically at left boundary x=0)
        shear_total = 0.0
        moment_total = 0.0
        axial_total = 0.0
        full_q = 0.0

        for row in self.load_rows:
            key = str(row["key"])
            magnitude = float(row["magnitude"])

            if key == "distributed_load":
                full_q += magnitude
                shear_total += magnitude * L
                moment_total += magnitude * L * L / 2.0
                numeric_values["q"] += magnitude
            elif key == "partial_distributed":
                a = float(row["start"])
                b = float(row["end"])
                length = max(0.0, min(b, L) - max(a, 0.0))
                shear_total += magnitude * length
                # moment about x=0: integral q*x dx from a..b = q*(b^2 - a^2)/2
                moment_total += magnitude * (b * b - a * a) / 2.0
            elif key == "point_load":
                x_pos = float(row.get("pos", L))
                shear_total += magnitude
                moment_total += magnitude * x_pos
            elif key == "end_load":
                shear_total += magnitude
                moment_total += magnitude * L
                numeric_values["P"] += magnitude
            elif key == "moment":
                moment_total += magnitude
                numeric_values["M"] += magnitude
            elif key == "concentrated_moment":
                moment_total += magnitude
            elif key == "pure_tension":
                axial_total += magnitude
                numeric_values["F"] += magnitude

        if full_q != 0.0:
            specs["distributed_load"] = full_q

        # If there are simple end loads/moments also present, set them too
        if numeric_values["P"] != 0.0:
            specs["end_load"] = numeric_values["P"]
        if numeric_values["M"] != 0.0:
            specs["moment"] = numeric_values["M"]
        if numeric_values["F"] != 0.0:
            specs["pure_tension"] = numeric_values["F"]

        # Provide resultant scalars to the solver (left-section at x=0)
        specs["resultant_shear_force"] = shear_total
        specs["resultant_moment"] = moment_total
        specs["resultant_axial_force"] = axial_total

        # Infer degree from active load types (choose highest requirement)
        degree_map = {
            "distributed_load": 5,
            "partial_distributed": 5,
            "point_load": 4,
            "end_load": 4,
            "moment": 3,
            "concentrated_moment": 3,
            "pure_tension": 2,
        }
        max_degree = 0
        for row in self.load_rows:
            key = row.get("key")
            max_degree = max(max_degree, degree_map.get(key, 0))
        if max_degree > 0:
            specs["degree"] = max_degree

        return specs, numeric_values

    def solve(self) -> None:
        if not self.load_rows:
            messagebox.showwarning("No loads", "Add at least one load before solving.")
            return

        try:
            specs, numeric_values = self._combined_specs()
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        self._clear_output()
        buffer = io.StringIO()
        try:
            with redirect_stdout(buffer):
                result = run_solver_pipeline(specs, numeric_values, plot_stresses=False)
        except Exception as exc:  # noqa: BLE001
            self._append_output(buffer.getvalue())
            self._append_output(f"\n[ERROR] {exc}\n")
            messagebox.showerror("Solve failed", str(exc))
            return

        self._append_output(buffer.getvalue())

        self._redraw_beam()

        # result contains final_phi, (sx, sy, txy), (c, L), mapping
        try:
            _, stresses, geom, mapping = result
            sx_sym, _, txy_sym = stresses
            c_sym, L_sym = geom
            try:
                from visualizer import plot_sfd_bmd
            except Exception:
                from .visualizer import plot_sfd_bmd

            plot_sfd_bmd(sx_sym, txy_sym, sp.Symbol('x'), sp.Symbol('y'), c_sym, L_sym, mapping, specs)
            self._draw_reactions(specs, numeric_values)
        except Exception:
            # if unpack fails, ignore extended plotting
            pass

    def _draw_reactions(self, specs: dict, numeric_values: dict) -> None:
        # overlay simple reaction arrows at x=0 based on resultant_shear_force and resultant_moment
        try:
            shear = float(specs.get('resultant_shear_force', 0.0))
            moment = float(specs.get('resultant_moment', 0.0))
        except Exception:
            shear = 0.0
            moment = 0.0

        # draw on canvas: arrow upward/downward at left end
        width = max(self.canvas.winfo_width(), 800)
        margin_x = 80
        beam_left = margin_x
        beam_top = self.canvas.winfo_height() // 2 - 20
        if abs(shear) > 1e-6:
            dir_sign = -1 if shear > 0 else 1
            self.canvas.create_line(beam_left + 6, beam_top - 12, beam_left + 6, beam_top - 48 * dir_sign, arrow=tk.LAST, width=3, fill='#ff4500')
            self.canvas.create_text(beam_left + 26, beam_top - 48 * dir_sign - 8, text=f'V0={shear:.2f}', fill='#ff4500', anchor='w')
        if abs(moment) > 1e-6:
            x_pos = beam_left + 24
            self.canvas.create_arc(x_pos - 36, beam_top - 64, x_pos + 36, beam_top + 12, start=35, extent=260, style='arc', width=2, outline='#8b0000')
            self.canvas.create_text(x_pos + 48, beam_top - 36, text=f'M0={moment:.2f}', fill='#8b0000', anchor='w')

    def _redraw_beam(self) -> None:
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 800)
        height = max(self.canvas.winfo_height(), 320)

        margin_x = 80
        beam_y = height // 2
        beam_left = margin_x
        beam_right = width - margin_x
        self.beam_bounds = (beam_left, beam_right)
        beam_top = beam_y - 20
        beam_bottom = beam_y + 20

        self.canvas.create_rectangle(beam_left, beam_top, beam_right, beam_bottom, fill="#3d4f6b", outline="#1d2430")
        self.canvas.create_text(width // 2, beam_top - 28, text="Beam", fill="#333", font=("Segoe UI", 11, "bold"))
        self.canvas.create_text(beam_left, beam_bottom + 24, text="x = 0", fill="#555", font=("Segoe UI", 9))
        self.canvas.create_text(beam_right, beam_bottom + 24, text="x = L", fill="#555", font=("Segoe UI", 9))

        for index, row in enumerate(self.load_rows):
            self._draw_load(beam_left, beam_right, beam_top, beam_bottom, beam_y, index, row)

    def _draw_load(self, beam_left: int, beam_right: int, beam_top: int, beam_bottom: int, beam_y: int, index: int, row: dict) -> None:
        key = str(row["key"])
        magnitude = float(row["magnitude"])
        label = f'{LOAD_TYPES[key]["display"]} = {magnitude:g}'
        offset = 34 + index * 18
        load_id = int(row.get("id", index + 1))
        tags = (f"load_{load_id}", "load_item")

        if key == "distributed_load":
            start_x = beam_left + 20
            end_x = beam_right - 20
            for x_pos in range(start_x, end_x, 36):
                self.canvas.create_line(x_pos, beam_top - 12, x_pos, beam_top - 46, arrow=tk.LAST, width=2, fill="#b5432d", tags=tags)
            self.canvas.create_text((beam_left + beam_right) // 2, beam_top - 58, text=label, fill="#b5432d", font=("Segoe UI", 9, "bold"), tags=tags)
        elif key == "point_load":
            x_pos = self._x_to_canvas(float(row.get("x", self._parse_float(self.beam_length_var.get(), "Beam length L"))))
            self.canvas.create_line(x_pos, beam_top - 12, x_pos, beam_top - 68, arrow=tk.LAST, width=3, fill="#b5432d", tags=tags)
            self.canvas.create_oval(x_pos - 5, beam_top - 72, x_pos + 5, beam_top - 62, fill="#b5432d", outline="", tags=tags)
            self.canvas.create_text(x_pos, beam_top - 80, text=label, fill="#b5432d", font=("Segoe UI", 9, "bold"), tags=tags)
        elif key == "end_load":
            x_pos = self._x_to_canvas(float(row.get("x", self._parse_float(self.beam_length_var.get(), "Beam length L"))))
            self.canvas.create_line(x_pos, beam_top - 12, x_pos, beam_top - 68, arrow=tk.LAST, width=3, fill="#2d6b9f", tags=tags)
            self.canvas.create_text(x_pos - 48, beam_top - 76, text=label, fill="#2d6b9f", font=("Segoe UI", 9, "bold"), tags=tags)
        elif key == "moment":
            x_pos = self._x_to_canvas(float(row.get("x", self._parse_float(self.beam_length_var.get(), "Beam length L"))))
            self.canvas.create_arc(x_pos - 42, beam_top - 74, x_pos + 42, beam_top + 10, start=35, extent=260, style="arc", width=3, outline="#7a3db5", tags=tags)
            self.canvas.create_line(x_pos + 34, beam_top - 18, x_pos + 46, beam_top - 32, arrow=tk.LAST, width=2, fill="#7a3db5", tags=tags)
            self.canvas.create_text(x_pos - 30, beam_top - 82, text=label, fill="#7a3db5", font=("Segoe UI", 9, "bold"), tags=tags)
            # add a small center handle for dragging
            self.canvas.create_oval(x_pos - 5, beam_top - 5, x_pos + 5, beam_top + 5, fill="#7a3db5", outline="", tags=tags)
        elif key == "concentrated_moment":
            x_pos = self._x_to_canvas(float(row.get("x", self._parse_float(self.beam_length_var.get(), "Beam length L"))))
            self.canvas.create_arc(x_pos - 42, beam_top - 74, x_pos + 42, beam_top + 10, start=35, extent=260, style="arc", width=3, outline="#7a3db5", tags=tags)
            self.canvas.create_line(x_pos + 34, beam_top - 18, x_pos + 46, beam_top - 32, arrow=tk.LAST, width=2, fill="#7a3db5", tags=tags)
            self.canvas.create_text(x_pos - 30, beam_top - 82, text=label, fill="#7a3db5", font=("Segoe UI", 9, "bold"), tags=tags)
            self.canvas.create_oval(x_pos - 5, beam_top - 5, x_pos + 5, beam_top + 5, fill="#7a3db5", outline="", tags=tags)
        elif key == "pure_tension":
            self.canvas.create_line(beam_left - 46, beam_y, beam_left - 8, beam_y, arrow=tk.LAST, width=3, fill="#2e8b57", tags=tags)
            self.canvas.create_line(beam_right + 8, beam_y, beam_right + 46, beam_y, arrow=tk.LAST, width=3, fill="#2e8b57", tags=tags)
            self.canvas.create_text(width // 2, beam_bottom + 42, text=label, fill="#2e8b57", font=("Segoe UI", 9, "bold"), tags=tags)
        elif key == "partial_distributed":
            start_x = self._x_to_canvas(float(row.get("start", 0.0)))
            end_x = self._x_to_canvas(float(row.get("end", self._parse_float(self.beam_length_var.get(), "Beam length L"))))
            if end_x < start_x:
                start_x, end_x = end_x, start_x
            for x_pos in range(int(start_x), int(end_x) + 1, 36):
                self.canvas.create_line(x_pos, beam_top - 12, x_pos, beam_top - 46, arrow=tk.LAST, width=2, fill="#b5432d", tags=tags)
            self.canvas.create_line(start_x, beam_top - 10, end_x, beam_top - 10, fill="#b5432d", width=3, tags=tags)
            self.canvas.create_oval(start_x - 5, beam_top - 15, start_x + 5, beam_top - 5, fill="#b5432d", outline="", tags=tags)
            self.canvas.create_oval(end_x - 5, beam_top - 15, end_x + 5, beam_top - 5, fill="#b5432d", outline="", tags=tags)
            self.canvas.create_text((start_x + end_x) / 2, beam_top - 58, text=label, fill="#b5432d", font=("Segoe UI", 9, "bold"), tags=tags)

        self.canvas.create_text(beam_left + 110, beam_top - offset, text=f"Load {index + 1}: {label}", fill="#333", anchor="w", font=("Segoe UI", 8), tags=tags)


def run_gui() -> None:
    app = AirySolverApp()
    app.root.mainloop()


if __name__ == "__main__":
    run_gui()
