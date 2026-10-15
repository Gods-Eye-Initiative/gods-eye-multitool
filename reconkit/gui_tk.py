import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from .gui_common import PALETTE, TOOLS, TOOL_BY_ID, execute_tool


def logo_asset_path():
    """Return the logo location relative to this module, including in PyInstaller builds."""
    return Path(__file__).resolve().with_name("logo_sidebar.png")


class ReconKitDesktop:
    def __init__(self, root):
        self.root = root
        self.root.title("G.E.M. · Console operativa")
        self.root.geometry("1120x760")
        self.root.minsize(860, 620)
        self.root.configure(bg=PALETTE["background"])
        self.results = queue.Queue()
        self.vars = {}
        self.entries = {}
        self.current_tool = TOOLS[0]["id"]
        self.running = False
        self.logo_image = self._load_logo()
        self.logo_label = None
        if self.logo_image is not None:
            try:
                self.root.iconphoto(True, self.logo_image)
            except tk.TclError:
                pass
        self._configure_style()
        self._build_layout()
        self.select_tool(self.current_tool)
        self.root.after(100, self._poll_results)

    def _configure_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=PALETTE["background"], foreground=PALETTE["text"],
                        font=("Segoe UI", 10))
        style.configure("Panel.TFrame", background=PALETTE["panel"])
        style.configure("PanelInner.TFrame", background=PALETTE["panel"])
        style.configure("TLabel", background=PALETTE["panel"], foreground=PALETTE["text"])
        style.configure("Muted.TLabel", background=PALETTE["panel"], foreground=PALETTE["muted"])
        style.configure("Heading.TLabel", background=PALETTE["panel"], foreground=PALETTE["text"],
                        font=("Segoe UI Semibold", 20))
        style.configure("Section.TLabel", background=PALETTE["panel"], foreground=PALETTE["primary"],
                        font=("Segoe UI Semibold", 9))
        style.configure("TEntry", fieldbackground=PALETTE["panel_alt"], foreground=PALETTE["text"],
                        insertcolor=PALETTE["text"], bordercolor="#344555", padding=8)
        style.configure("TCheckbutton", background=PALETTE["panel"], foreground=PALETTE["text"])
        style.map("TCheckbutton", background=[("active", PALETTE["panel"])])
        style.configure("Nav.TButton", background=PALETTE["background"], foreground=PALETTE["muted"],
                        borderwidth=0, anchor="w", padding=(12, 9))
        style.map("Nav.TButton", background=[("active", PALETTE["panel_alt"])],
                  foreground=[("active", PALETTE["text"])])
        style.configure("SelectedNav.TButton", background=PALETTE["panel_alt"],
                        foreground=PALETTE["primary"], borderwidth=0, anchor="w",
                        padding=(12, 9), font=("Segoe UI Semibold", 10))
        style.map("SelectedNav.TButton", background=[("active", PALETTE["panel_alt"])],
                  foreground=[("active", PALETTE["primary"])])
        style.configure("Primary.TButton", background=PALETTE["primary"], foreground="#171222",
                        font=("Segoe UI Semibold", 10), borderwidth=0, padding=(18, 10))
        style.map("Primary.TButton", background=[("active", "#c4b5fd"), ("disabled", "#584a78")])
        style.configure("Secondary.TButton", background=PALETTE["panel_alt"], foreground=PALETTE["text"],
                        borderwidth=0, padding=(12, 9))
        style.map("Secondary.TButton", background=[("active", "#2b3a49")])
        style.configure("TSeparator", background="#2c3946")
        style.map("TEntry", bordercolor=[("focus", PALETTE["primary"])])

    def _load_logo(self):
        try:
            return tk.PhotoImage(file=str(logo_asset_path()))
        except (tk.TclError, OSError):
            return None

    def _build_layout(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(outer, style="Panel.TFrame", padding=(12, 16), width=218)
        sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, 16))
        sidebar.grid_propagate(False)
        if self.logo_image is not None:
            self.logo_label = tk.Label(sidebar, image=self.logo_image, bg=PALETTE["panel"])
            self.logo_label.pack(anchor="w", padx=8, pady=(0, 8))
        ttk.Label(sidebar, text="G.E.M.", foreground=PALETTE["primary"],
                  font=("Segoe UI Semibold", 20)).pack(anchor="w", padx=8)
        ttk.Label(sidebar, text="CONSOLE OPERATIVA", style="Muted.TLabel",
                  font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=8, pady=(2, 16))
        ttk.Separator(sidebar).pack(fill="x", padx=7, pady=(0, 12))
        nav_canvas = tk.Canvas(sidebar, bg=PALETTE["panel"], highlightthickness=0, width=190)
        nav_scroll = ttk.Scrollbar(sidebar, orient="vertical", command=nav_canvas.yview)
        nav_canvas.configure(yscrollcommand=nav_scroll.set)
        nav_canvas.pack(side="left", fill="both", expand=True)
        nav_scroll.pack(side="right", fill="y")
        nav = ttk.Frame(nav_canvas, style="Panel.TFrame")
        nav_window = nav_canvas.create_window((0, 0), window=nav, anchor="nw")
        self.nav_buttons = {}
        nav.bind("<Configure>", lambda _e: nav_canvas.configure(scrollregion=nav_canvas.bbox("all")))
        nav_canvas.bind("<Configure>", lambda e: nav_canvas.itemconfigure(nav_window, width=e.width))
        groups = []
        for spec in TOOLS:
            if spec["group"] not in groups:
                groups.append(spec["group"])
                ttk.Label(nav, text=spec["group"], style="Section.TLabel").pack(
                    anchor="w", padx=10, pady=(12, 3))
            button = ttk.Button(nav, text=spec["title"], style="Nav.TButton",
                                command=lambda tool_id=spec["id"]: self.select_tool(tool_id))
            button.pack(fill="x")
            self.nav_buttons[spec["id"]] = button

        content = ttk.Frame(outer, style="Panel.TFrame", padding=24)
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(4, weight=1)

        top = ttk.Frame(content, style="Panel.TFrame")
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)
        self.title_label = ttk.Label(top, text="", style="Heading.TLabel")
        self.title_label.grid(row=0, column=0, sticky="w")
        self.state_label = tk.Label(top, text="PRONTO", bg="#1d382f", fg=PALETTE["green"],
                                    font=("Segoe UI Semibold", 8), padx=10, pady=5)
        self.state_label.grid(row=0, column=1, sticky="e")
        self.description_label = ttk.Label(content, text="", style="Muted.TLabel",
                                           wraplength=750, justify="left")
        self.description_label.grid(row=1, column=0, sticky="w", pady=(8, 15))

        self.notice = tk.Label(content, text="", bg="#332919", fg=PALETTE["amber"],
                               font=("Segoe UI", 9), justify="left", anchor="w",
                               padx=12, pady=9, wraplength=740)
        self.notice.grid(row=2, column=0, sticky="ew", pady=(0, 18))

        form_view = ttk.Frame(content, style="Panel.TFrame")
        form_view.grid(row=3, column=0, sticky="ew")
        form_view.columnconfigure(0, weight=1)
        self.form_canvas = tk.Canvas(form_view, bg=PALETTE["panel"], height=165,
                                     highlightthickness=0, borderwidth=0)
        self.form_canvas.grid(row=0, column=0, sticky="ew")
        form_scroll = ttk.Scrollbar(form_view, orient="vertical", command=self.form_canvas.yview)
        form_scroll.grid(row=0, column=1, sticky="ns")
        self.form_canvas.configure(yscrollcommand=form_scroll.set)
        self.form = ttk.Frame(self.form_canvas, style="Panel.TFrame")
        self.form_window = self.form_canvas.create_window(
            (0, 0), window=self.form, anchor="nw")
        self.form.bind(
            "<Configure>",
            lambda _event: self.form_canvas.configure(
                scrollregion=self.form_canvas.bbox("all")))
        self.form_canvas.bind(
            "<Configure>",
            lambda event: self.form_canvas.itemconfigure(self.form_window, width=event.width))
        self.form_canvas.bind("<MouseWheel>", self._scroll_form)
        self.form_canvas.bind("<Button-4>", self._scroll_form)
        self.form_canvas.bind("<Button-5>", self._scroll_form)
        self.form.columnconfigure(1, weight=1)

        output_panel = ttk.Frame(content, style="Panel.TFrame")
        output_panel.grid(row=4, column=0, sticky="nsew", pady=(20, 0))
        output_panel.columnconfigure(0, weight=1)
        output_panel.rowconfigure(1, weight=1)
        output_head = ttk.Frame(output_panel, style="Panel.TFrame")
        output_head.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        output_head.columnconfigure(0, weight=1)
        self.output_title = ttk.Label(output_head, text="RISULTATO", style="Section.TLabel")
        self.output_title.grid(row=0, column=0, sticky="w")
        self.status_detail = ttk.Label(output_head, text="Output copiabile · operazioni in background",
                                       style="Muted.TLabel")
        self.status_detail.grid(row=0, column=1, sticky="e")
        output_frame = ttk.Frame(output_panel, style="Panel.TFrame")
        output_frame.grid(row=1, column=0, sticky="nsew")
        output_frame.rowconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        self.output = tk.Text(output_frame, bg="#111922", fg="#d5e1e9", insertbackground="#d5e1e9",
                              selectbackground="#245763", relief="flat", wrap="word",
                              font=("Consolas", 10), padx=14, pady=12, height=6, state="disabled")
        self.output.grid(row=0, column=0, sticky="nsew")
        out_scroll = ttk.Scrollbar(output_frame, command=self.output.yview)
        out_scroll.grid(row=0, column=1, sticky="ns")
        self.output.configure(yscrollcommand=out_scroll.set)

        actions = ttk.Frame(content, style="Panel.TFrame")
        actions.grid(row=5, column=0, sticky="ew", pady=(16, 0))
        self.run_button = ttk.Button(actions, text="Esegui analisi", style="Primary.TButton",
                                     command=self.run_selected)
        self.run_button.pack(side="left")
        ttk.Button(actions, text="Copia risultato", style="Secondary.TButton",
                   command=self.copy_output).pack(side="left", padx=8)
        ttk.Button(actions, text="Pulisci", style="Secondary.TButton",
                   command=lambda: self._set_output("")).pack(side="left")
    def select_tool(self, tool_id):
        if self.running:
            return
        self.current_tool = tool_id
        spec = TOOL_BY_ID[tool_id]
        for button_id, button in self.nav_buttons.items():
            button.configure(style="SelectedNav.TButton" if button_id == tool_id else "Nav.TButton")
        self.title_label.configure(text=spec["title"])
        self.description_label.configure(text=spec["description"])
        if spec.get("active"):
            self.notice.configure(text="ATTENZIONE · Questa funzione effettua scansioni/sonde attive. "
                                       "Usala esclusivamente su sistemi propri o esplicitamente autorizzati.")
            self.notice.grid()
        elif tool_id == "traceroute":
            self.notice.configure(text="PRIVILEGI · ICMP raw richiede permessi amministratore/root.")
            self.notice.grid()
        else:
            self.notice.grid_remove()
        for child in self.form.winfo_children():
            child.destroy()
        self.vars.clear()
        self.entries.clear()
        for row, field in enumerate(spec.get("fields", [])):
            name, label, kind, placeholder, required = field[:5]
            default = field[5] if len(field) > 5 else ""
            if kind == "check":
                value = tk.BooleanVar(value=default)
                self.vars[name] = value
                ttk.Checkbutton(self.form, text=label, variable=value).grid(
                    row=row, column=0, columnspan=2, sticky="w", pady=5)
                continue
            ttk.Label(self.form, text=label).grid(row=row, column=0, sticky="nw", padx=(0, 18), pady=7)
            if kind == "multiline":
                widget = tk.Text(self.form, height=4, wrap="word", bg=PALETTE["panel_alt"],
                                 fg=PALETTE["text"], insertbackground=PALETTE["text"],
                                 relief="flat", padx=8, pady=7, font=("Segoe UI", 10))
                widget.grid(row=row, column=1, sticky="ew", pady=5)
                self.entries[name] = widget
                continue
            value = tk.StringVar(value=str(default))
            self.vars[name] = value
            show = "•" if kind == "password" else ""
            entry = ttk.Entry(self.form, textvariable=value, show=show)
            entry.grid(row=row, column=1, sticky="ew", pady=5, ipady=2)
            self.entries[name] = entry
            if required and kind != "password":
                entry.bind("<Return>", lambda _event: self.run_selected())
        for child in self.form.winfo_children():
            child.bind("<MouseWheel>", self._scroll_form, add="+")
            child.bind("<Button-4>", self._scroll_form, add="+")
            child.bind("<Button-5>", self._scroll_form, add="+")
        self._set_output("")
        self.output_title.configure(text="RISULTATO")
        self.status_detail.configure(text="I risultati provengono dal modulo G.E.M. selezionato.")

    def _collect_values(self):
        values = {}
        for name, value in self.vars.items():
            values[name] = value.get()
        for name, widget in self.entries.items():
            if isinstance(widget, tk.Text):
                values[name] = widget.get("1.0", "end-1c")
        return values

    def run_selected(self):
        if self.running:
            return
        values = self._collect_values()
        spec = TOOL_BY_ID[self.current_tool]
        missing = []
        for field in spec.get("fields", []):
            name, label, kind, _placeholder, required = field[:5]
            if required and kind != "check" and not str(values.get(name, "")).strip():
                missing.append(label)
        if missing:
            messagebox.showwarning("Campo richiesto", "Compila: " + ", ".join(missing), parent=self.root)
            return
        self.running = True
        self._has_live_output = False
        self.run_button.configure(state="disabled")
        self.state_label.configure(text="IN ESECUZIONE", bg="#3a3020", fg=PALETTE["amber"])
        self.status_detail.configure(text="Log in tempo reale · l'interfaccia resta disponibile")
        self.output_title.configure(text="LOG IN TEMPO REALE")
        self._set_output("Avvio analisi...\n")
        threading.Thread(target=self._execute, args=(self.current_tool, values), daemon=True).start()

    def _execute(self, tool_id, values):
        try:
            text = execute_tool(
                tool_id, values,
                on_output=lambda chunk: self.results.put(("log", chunk)),
            )
            self.results.put(("done", True, text))
        except Exception as exc:
            self.results.put(("done", False, str(exc)))

    def _poll_results(self):
        try:
            event = self.results.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_results)
            return
        if event[0] == "log":
            if not self._has_live_output:
                self._set_output("")
                self._has_live_output = True
            self._append_output(event[1])
            self.root.after(100, self._poll_results)
            return
        success, text = event[1], event[2]
        self.running = False
        self.run_button.configure(state="normal")
        color = PALETTE["green"] if success else PALETTE["red"]
        self.state_label.configure(text="COMPLETATO" if success else "ERRORE",
                                   bg="#1d382f" if success else "#3b2529", fg=color)
        self.status_detail.configure(text="Risultato reale del modulo G.E.M.")
        self.output_title.configure(text="RISULTATO")
        self._set_output(text)
        self.root.after(100, self._poll_results)

    def _set_output(self, text):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def _append_output(self, text):
        self.output.configure(state="normal")
        self.output.insert("end", text)
        self.output.see("end")
        self.output.configure(state="disabled")

    def copy_output(self):
        text = self.output.get("1.0", "end-1c")
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_detail.configure(text="Risultato copiato negli appunti.")

    def _scroll_form(self, event):
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1
        self.form_canvas.yview_scroll(delta, "units")
        return "break"


def main():
    root = tk.Tk()
    ReconKitDesktop(root)
    root.mainloop()


if __name__ == "__main__":
    main()
