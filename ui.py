"""
User interface and interaction handling for Smart Evac using CustomTkinter.
"""

import tkinter as tk
import customtkinter as ctk

from constants import (
    GRID_ROWS,
    GRID_COLS,
    CELL_SIZE,
    GRID_PADDING,
    EMPTY,
    WALL,
    EXIT,
    START,
    VISITED,
    PATH,
    COLOUR,
    GRID_LINE_COLOUR,
    CANVAS_BG,
    PANEL_BG,
    SPEED_OPTIONS,
    STAGE_WALLS,
    STAGE_EXITS,
    STAGE_START,
    STAGE_RUNNING,
    STAGE_DONE,
    STEP_INFO,
)
from bfs import bfs


class SmartEvac:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("SMART EVAC | Emergency Route Planner")
        self.root.resizable(False, False)
        self.root.configure(fg_color="#242424")

        # Grid state
        self.grid         = self._create_grid()
        self.canvas_items = {}              # (row, col) → canvas rectangle id

        # App state
        self.stage = STAGE_WALLS
        self.exits = set()                 # set of (row, col)
        self.start_pos = None              # (row, col) or None
        self.is_dragging = False
        self.drag_action = None            # "place" or "erase"
        self.anim_job_id = None            # handle for after() cancellation

        # Build UI then draw grid
        self._build_layout()
        self._draw_grid()
        self._refresh_panel()

    # GRID CREATION

    def _create_grid(self):
        """Return a fresh GRID_ROWS × GRID_COLS grid filled with EMPTY."""
        return [[EMPTY] * GRID_COLS for _ in range(GRID_ROWS)]

    # UI CONSTRUCTION

    def _build_layout(self):
        outer = ctk.CTkFrame(self.root, fg_color="#242424")
        outer.pack(fill="both", expand=True, padx=8, pady=8)

        # LEFT: grid canvas
        canvas_frame = ctk.CTkFrame(
            outer, fg_color="#1a1a1a",
            corner_radius=10, border_width=1, border_color="#333333",
        )
        canvas_frame.pack(side="left", padx=(0, 8))

        cw = GRID_COLS * CELL_SIZE + 2 * GRID_PADDING
        ch = GRID_ROWS * CELL_SIZE + 2 * GRID_PADDING

        self.canvas = tk.Canvas(
            canvas_frame, width=cw, height=ch,
            bg=CANVAS_BG, highlightthickness=0,
        )
        self.canvas.pack(padx=8, pady=8)

        self.canvas.bind("<Button-1>",        self._on_press)
        self.canvas.bind("<B1-Motion>",       self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        # RIGHT: scrollable control panel
        panel_height = ch + 16          # match the canvas frame height
        self.panel = ctk.CTkScrollableFrame(
            outer,
            width=272,
            height=panel_height,
            fg_color=PANEL_BG,
            corner_radius=10,
            border_width=1,
            border_color="#333333",
            scrollbar_button_color="#444444",
            scrollbar_button_hover_color="#555555",
        )
        self.panel.pack(side="left", fill="y")

        self._build_panel_content()

    def _build_panel_content(self):
        """Populate the right-hand control panel with static and dynamic widgets."""
        p = self.panel

        # Title
        ctk.CTkLabel(
            p, text="SMART EVAC",
            font=ctk.CTkFont("Segoe UI", 20, "bold"),
            text_color="#FF5252",
        ).pack(pady=(14, 1))

        ctk.CTkLabel(
            p, text="Emergency Route Planner",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color="#777777",
        ).pack(pady=(0, 8))

        ctk.CTkFrame(p, height=1, fg_color="#333333").pack(fill="x", padx=12, pady=(0, 8))

        # Current step box
        step_box = ctk.CTkFrame(p, fg_color="#252525", corner_radius=8)
        step_box.pack(fill="x", padx=10, pady=(0, 6))

        ctk.CTkLabel(
            step_box, text="▶  CURRENT STEP",
            font=ctk.CTkFont("Segoe UI", 8, "bold"),
            text_color="#666666",
        ).pack(anchor="w", padx=10, pady=(7, 1))

        self.lbl_stage = ctk.CTkLabel(
            step_box, text="",
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color="#FFD54F",
            wraplength=230, justify="left",
        )
        self.lbl_stage.pack(anchor="w", padx=10, pady=(0, 2))

        self.lbl_instr = ctk.CTkLabel(
            step_box, text="",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color="#BBBBBB",
            wraplength=230, justify="left",
        )
        self.lbl_instr.pack(anchor="w", padx=10, pady=(0, 8))

        # Configuration status
        cfg_box = ctk.CTkFrame(p, fg_color="#252525", corner_radius=8)
        cfg_box.pack(fill="x", padx=10, pady=(0, 6))

        ctk.CTkLabel(
            cfg_box, text="CONFIGURATION",
            font=ctk.CTkFont("Segoe UI", 8, "bold"),
            text_color="#666666",
        ).pack(anchor="w", padx=10, pady=(7, 3))

        self.lbl_walls = self._status_row(cfg_box, "Walls")
        self.lbl_exits = self._status_row(cfg_box, "Exits")
        self.lbl_start = self._status_row(cfg_box, "Start")
        ctk.CTkLabel(cfg_box, text="").pack(pady=2)

        # Legend
        leg_box = ctk.CTkFrame(p, fg_color="#252525", corner_radius=8)
        leg_box.pack(fill="x", padx=10, pady=(0, 6))

        ctk.CTkLabel(
            leg_box, text="LEGEND",
            font=ctk.CTkFont("Segoe UI", 8, "bold"),
            text_color="#666666",
        ).pack(anchor="w", padx=10, pady=(7, 3))

        for colour, label in [
            (COLOUR[EMPTY],   "Empty / Walkable"),
            (COLOUR[WALL],    "Wall / Obstacle"),
            (COLOUR[EXIT],    "Emergency Exit"),
            (COLOUR[START],   "Starting Position"),
            (COLOUR[VISITED], "BFS Explored"),
            (COLOUR[PATH],    "Evacuation Route"),
        ]:
            self._legend_row(leg_box, colour, label)
        ctk.CTkLabel(leg_box, text="").pack(pady=2)

        # Speed selector
        spd_box = ctk.CTkFrame(p, fg_color="#252525", corner_radius=8)
        spd_box.pack(fill="x", padx=10, pady=(0, 6))

        ctk.CTkLabel(
            spd_box, text="⚡  ANIMATION SPEED",
            font=ctk.CTkFont("Segoe UI", 8, "bold"),
            text_color="#666666",
        ).pack(anchor="w", padx=10, pady=(7, 3))

        self.speed_var = ctk.StringVar(value="Normal")
        ctk.CTkSegmentedButton(
            spd_box,
            values=["Slow", "Normal", "Fast"],
            variable=self.speed_var,
            font=ctk.CTkFont("Segoe UI", 10),
            fg_color="#1e1e1e",
            selected_color="#37474F",
            selected_hover_color="#455A64",
            unselected_color="#2a2a2a",
        ).pack(fill="x", padx=10, pady=(0, 10))

        # Navigation buttons (Back / Next)
        nav_box = ctk.CTkFrame(p, fg_color="transparent")
        nav_box.pack(fill="x", padx=10, pady=(0, 4))

        self._nav_row = ctk.CTkFrame(nav_box, fg_color="transparent")
        self._nav_row.pack(fill="x")

        self.btn_back = ctk.CTkButton(
            self._nav_row, text="◀  Back",
            font=ctk.CTkFont("Segoe UI", 11),
            fg_color="#37474F", hover_color="#455A64",
            height=34, corner_radius=8,
            command=self._go_back,
        )
        self.btn_next = ctk.CTkButton(
            self._nav_row, text="Next  ▶",
            font=ctk.CTkFont("Segoe UI", 11),
            fg_color="#1565C0", hover_color="#1976D2",
            height=34, corner_radius=8,
            command=self._go_next,
        )

        # Action buttons
        act_box = ctk.CTkFrame(p, fg_color="transparent")
        act_box.pack(fill="x", padx=10, pady=(0, 6))

        self.btn_start = ctk.CTkButton(
            act_box, text="▶  Start Simulation",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color="#B71C1C", hover_color="#C62828",
            height=40, corner_radius=8,
            command=self._start_simulation,
        )
        self.btn_start.pack(fill="x", pady=(0, 5))

        self.btn_reset = ctk.CTkButton(
            act_box, text="↺  Reset Simulation",
            font=ctk.CTkFont("Segoe UI", 11),
            fg_color="#37474F", hover_color="#455A64",
            height=34, corner_radius=8,
            command=self._reset_simulation,
        )
        self.btn_reset.pack(fill="x", pady=(0, 5))

        self.btn_clear = ctk.CTkButton(
            act_box, text="✕  Clear All",
            font=ctk.CTkFont("Segoe UI", 11),
            fg_color="#4a1942", hover_color="#6a2d62",
            height=34, corner_radius=8,
            command=self._clear_all,
        )
        self.btn_clear.pack(fill="x")

        # Result box
        res_box = ctk.CTkFrame(p, fg_color="#252525", corner_radius=8)
        res_box.pack(fill="x", padx=10, pady=(6, 14))

        ctk.CTkLabel(
            res_box, text="RESULT",
            font=ctk.CTkFont("Segoe UI", 8, "bold"),
            text_color="#666666",
        ).pack(anchor="w", padx=10, pady=(7, 2))

        self.lbl_result = ctk.CTkLabel(
            res_box, text="Awaiting simulation…",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color="#888888",
            wraplength=230, justify="left",
        )
        self.lbl_result.pack(anchor="w", padx=10, pady=(0, 10))

    # WIDGET HELPERS

    def _status_row(self, parent, label_text):
        """Return the value CTkLabel for a key:value status row."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=1)
        ctk.CTkLabel(
            row, text=f"{label_text}:",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color="#999999", width=52, anchor="w",
        ).pack(side="left")
        val = ctk.CTkLabel(
            row, text="—",
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color="#888888", anchor="w",
        )
        val.pack(side="left")
        return val

    def _legend_row(self, parent, colour, text):
        """Create a colour swatch + label row."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=1)
        sw = tk.Canvas(row, width=12, height=12, bg=colour,
                       highlightthickness=1, highlightbackground="#555555")
        sw.pack(side="left", padx=(0, 7))
        ctk.CTkLabel(
            row, text=text,
            font=ctk.CTkFont("Segoe UI", 10),
            text_color="#CCCCCC",
        ).pack(side="left")

    # GRID DRAWING

    def _draw_grid(self):
        """Full redraw of every cell and all grid lines."""
        self.canvas.delete("all")
        self.canvas_items.clear()

        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                self._draw_cell(r, c)

        self._draw_lines()

    def _draw_cell(self, row, col):
        """Create the canvas rectangle for one cell."""
        x1 = GRID_PADDING + col * CELL_SIZE
        y1 = GRID_PADDING + row * CELL_SIZE
        item = self.canvas.create_rectangle(
            x1, y1, x1 + CELL_SIZE, y1 + CELL_SIZE,
            fill=COLOUR.get(self.grid[row][col], COLOUR[EMPTY]),
            outline="",
        )
        self.canvas_items[(row, col)] = item

    def _draw_lines(self):
        """Draw the thin grid lines on top of all cells."""
        tw = GRID_COLS * CELL_SIZE
        th = GRID_ROWS * CELL_SIZE
        for c in range(GRID_COLS + 1):
            x = GRID_PADDING + c * CELL_SIZE
            self.canvas.create_line(x, GRID_PADDING, x, GRID_PADDING + th,
                                    fill=GRID_LINE_COLOUR)
        for r in range(GRID_ROWS + 1):
            y = GRID_PADDING + r * CELL_SIZE
            self.canvas.create_line(GRID_PADDING, y, GRID_PADDING + tw, y,
                                    fill=GRID_LINE_COLOUR)

    def _refresh_cell(self, row, col):
        """Update just the colour of an existing canvas rectangle."""
        item = self.canvas_items.get((row, col))
        if item:
            self.canvas.itemconfig(
                item, fill=COLOUR.get(self.grid[row][col], COLOUR[EMPTY])
            )

    # MOUSE EVENTS

    def _pixel_to_cell(self, ex, ey):
        """Convert canvas pixel coords to (row, col), or None if outside grid."""
        col = (ex - GRID_PADDING) // CELL_SIZE
        row = (ey - GRID_PADDING) // CELL_SIZE
        if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
            return (int(row), int(col))
        return None

    def _on_press(self, event):
        if self.stage in (STAGE_RUNNING, STAGE_DONE):
            return
        cell = self._pixel_to_cell(event.x, event.y)
        if cell is None:
            return
        self.is_dragging = True
        if self.stage == STAGE_WALLS:
            if self.grid[cell[0]][cell[1]] == WALL:
                self.drag_action = "erase"
                self._remove_wall(cell)
            else:
                self.drag_action = "place"
                self._place_wall(cell)
        elif self.stage == STAGE_EXITS:
            self._toggle_exit(cell)
        elif self.stage == STAGE_START:
            self._place_start(cell)

    def _on_drag(self, event):
        if not self.is_dragging or self.stage != STAGE_WALLS:
            return
        cell = self._pixel_to_cell(event.x, event.y)
        if cell is None:
            return
        if self.drag_action == "place":
            self._place_wall(cell)
        else:
            self._remove_wall(cell)

    def _on_release(self, event):
        self.is_dragging = False
        self.drag_action = None

    # GRID EDITING

    def _place_wall(self, cell):
        r, c = cell
        if self.grid[r][c] == EMPTY:
            self.grid[r][c] = WALL
            self._refresh_cell(r, c)

    def _remove_wall(self, cell):
        r, c = cell
        if self.grid[r][c] == WALL:
            self.grid[r][c] = EMPTY
            self._refresh_cell(r, c)

    def _toggle_exit(self, cell):
        r, c = cell
        if self.grid[r][c] == WALL:
            self._set_result("⚠ Cannot place an exit on a wall.", "#FF8A65")
            return
        if self.grid[r][c] == EXIT:
            self.exits.discard(cell)
            self.grid[r][c] = EMPTY
        else:
            self.exits.add(cell)
            self.grid[r][c] = EXIT
        self._refresh_cell(r, c)
        self._refresh_panel()

    def _place_start(self, cell):
        r, c = cell
        if self.grid[r][c] == WALL:
            self._set_result("⚠ Cannot start on a wall.", "#FF8A65")
            return
        if self.grid[r][c] == EXIT:
            self._set_result("⚠ Cannot start on an exit.", "#FF8A65")
            return
        # Remove old start
        if self.start_pos is not None:
            pr, pc = self.start_pos
            self.grid[pr][pc] = EMPTY
            self._refresh_cell(pr, pc)
        self.start_pos = cell
        self.grid[r][c] = START
        self._refresh_cell(r, c)
        self._refresh_panel()

    # WORKFLOW NAVIGATION

    def _go_next(self):
        if self.stage == STAGE_WALLS:
            self.stage = STAGE_EXITS
            self._refresh_panel()
        elif self.stage == STAGE_EXITS:
            if not self.exits:
                self._set_result("⚠ Place at least one emergency exit first.", "#FF8A65")
                return
            self.stage = STAGE_START
            self._refresh_panel()

    def _go_back(self):
        if self.stage == STAGE_EXITS:
            self.stage = STAGE_WALLS
            self._refresh_panel()
        elif self.stage == STAGE_START:
            self.stage = STAGE_EXITS
            self._refresh_panel()

    # PANEL REFRESH — called whenever stage or config changes

    def _refresh_panel(self):
        """Synchronise every dynamic widget with the current app state."""
        sh, si = STEP_INFO.get(self.stage, ("", ""))
        self.lbl_stage.configure(text=sh)
        self.lbl_instr.configure(text=si)

        # Config status badges
        wall_count = sum(
            1 for r in range(GRID_ROWS) for c in range(GRID_COLS)
            if self.grid[r][c] == WALL
        )
        self.lbl_walls.configure(
            text=f"{wall_count} cell(s)",
            text_color="#81C784" if wall_count else "#888888",
        )
        self.lbl_exits.configure(
            text=f"{len(self.exits)} exit(s)",
            text_color="#81C784" if self.exits else "#888888",
        )
        self.lbl_start.configure(
            text=str(self.start_pos) if self.start_pos else "Not set",
            text_color="#81C784" if self.start_pos else "#888888",
        )

        # Navigation buttons
        for widget in self._nav_row.winfo_children():
            widget.pack_forget()

        if self.stage == STAGE_WALLS:
            self.btn_next.configure(text="Next: Select Exits  ▶")
            self.btn_next.pack(in_=self._nav_row, fill="x", pady=(0, 4))

        elif self.stage == STAGE_EXITS:
            self.btn_back.pack(in_=self._nav_row, side="left",
                               fill="x", expand=True, padx=(0, 3), pady=(0, 4))
            self.btn_next.configure(text="Next: Set Start  ▶")
            self.btn_next.pack(in_=self._nav_row, side="left",
                               fill="x", expand=True, pady=(0, 4))

        elif self.stage == STAGE_START:
            self.btn_back.pack(in_=self._nav_row, fill="x", pady=(0, 4))

        # Action button states
        can_simulate = (
            self.stage == STAGE_START
            and self.start_pos is not None
            and bool(self.exits)
        )

        self.btn_start.configure(
            state="normal" if can_simulate else "disabled",
            fg_color="#B71C1C" if can_simulate else "#37474F",
        )
        self.btn_reset.configure(
            state="normal" if self.stage in (STAGE_RUNNING, STAGE_DONE) else "disabled"
        )
        self.btn_clear.configure(
            state="disabled" if self.stage == STAGE_RUNNING else "normal"
        )

    # SIMULATION

    def _start_simulation(self):
        """Validate, run BFS, and kick off the animation."""
        if not self.exits:
            self._set_result("⚠ No emergency exits placed.", "#FF8A65")
            return
        if self.start_pos is None:
            self._set_result("⚠ No starting position set.", "#FF8A65")
            return

        self.stage = STAGE_RUNNING
        self._refresh_panel()
        self._set_result("BFS in progress…", "#F9A825")
        self.root.update_idletasks()

        # Run pure BFS — no GUI involved
        explored, path = bfs(self.start_pos, self.exits, self.grid)

        # Start animation
        delay = SPEED_OPTIONS.get(self.speed_var.get(), 60)
        self._animate_exploration(explored, path, delay, 0)

    def _reset_simulation(self):
        """Clear BFS colours; keep walls, exits and start unchanged."""
        if self.anim_job_id is not None:
            self.root.after_cancel(self.anim_job_id)
            self.anim_job_id = None

        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.grid[r][c] in (VISITED, PATH):
                    self.grid[r][c] = EMPTY
                    self._refresh_cell(r, c)

        # Restore exit and start cells (animation may have read them as VISITED)
        for (er, ec) in self.exits:
            self.grid[er][ec] = EXIT
            self._refresh_cell(er, ec)
        if self.start_pos:
            sr, sc = self.start_pos
            self.grid[sr][sc] = START
            self._refresh_cell(sr, sc)

        self.stage = STAGE_START
        self._set_result("Reset done — ready to simulate again.", "#888888")
        self._refresh_panel()

    # ANIMATION (after()-based, non-blocking)

    def _animate_exploration(self, explored, path, delay, idx):
        """
        Colour one explored cell per after() call (amber wave).
        When done, hand off to _animate_path().
        """
        if idx < len(explored):
            r, c = explored[idx]
            # Keep start and exit cells visually intact
            if self.grid[r][c] not in (START, EXIT):
                self.grid[r][c] = VISITED
                self._refresh_cell(r, c)
            # Schedule the next frame — default-argument captures current idx
            next_idx = idx + 1
            self.anim_job_id = self.root.after(
                delay,
                lambda ni=next_idx: self._animate_exploration(explored, path, delay, ni),
            )
        else:
            # Exploration animation finished
            if path:
                self._animate_path(path, delay, 0)
            else:
                self.stage = STAGE_DONE
                self._set_result(
                    f"NO ACCESSIBLE EXIT FOUND\n\nCells explored: {len(explored)}",
                    "#FF5252",
                )
                self._refresh_panel()

    def _animate_path(self, path, delay, idx):
        """
        Colour one path cell per after() call (cyan trail).
        Start cell stays blue; exit cell stays green.
        """
        if idx < len(path):
            r, c = path[idx]
            if self.grid[r][c] not in (START, EXIT):
                self.grid[r][c] = PATH
                self._refresh_cell(r, c)
            next_idx = idx + 1
            self.anim_job_id = self.root.after(
                delay,
                lambda ni=next_idx: self._animate_path(path, delay, ni),
            )
        else:
            # Path animation finished — show results
            self.stage = STAGE_DONE
            exit_cell = path[-1]
            steps     = len(path) - 1
            explored_count = sum(
                1 for r in range(GRID_ROWS) for c in range(GRID_COLS)
                if self.grid[r][c] in (VISITED, PATH, EXIT)
            )
            self._set_result(
                f"✅  EVACUATION ROUTE FOUND!\n\n"
                f"Nearest exit:    {exit_cell}\n"
                f"Path length:     {steps} step(s)\n"
                f"Cells explored:  {explored_count}",
                "#00C853",
            )
            self._refresh_panel()

    def _clear_all(self):
        """Reset everything to initial state."""
        if self.anim_job_id is not None:
            self.root.after_cancel(self.anim_job_id)
            self.anim_job_id = None

        self.grid      = self._create_grid()
        self.exits     = set()
        self.start_pos = None
        self.stage     = STAGE_WALLS

        self._draw_grid()
        self._set_result("Awaiting simulation…", "#888888")
        self._refresh_panel()

    # HELPERS

    def _set_result(self, text, colour="#CCCCCC"):
        self.lbl_result.configure(text=text, text_color=colour)
