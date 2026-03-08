"""
MeetingScribe - Single Window App
"""
import sys
import os
import json
import threading
import time
import logging
import tempfile
import ctypes
import tkinter as tk
from tkinter import filedialog, simpledialog, scrolledtext, ttk, messagebox
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip install pillow")
    sys.exit(1)

from PIL import ImageTk

CONFIG_PATH = Path.home() / ".meetingscribe" / "config.json"

BG      = "#1e1e1e"
BG2     = "#252526"
BG3     = "#2d2d2d"
FG      = "#d4d4d4"
FG_DIM  = "#888888"
ACCENT  = "#007acc"
GREEN   = "#27ae60"
RED     = "#c0392b"
TEAL    = "#4ec9b0"

IDLE_W, IDLE_H = 440, 580
REC_W,  REC_H  = 960, 640


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"openai_api_key": "", "monitor": 0}


def save_config(cfg: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def apply_config(cfg: dict):
    if cfg.get("openai_api_key"):
        os.environ["OPENAI_API_KEY"] = cfg["openai_api_key"]
    if cfg.get("screenshot_triggers"):
        import utils
        utils.SCREENSHOT_TRIGGERS = [
            t.strip().lower() for t in cfg["screenshot_triggers"].split(",") if t.strip()
        ]


# ── Settings window ───────────────────────────────────────────────────────────

class SettingsWindow:
    def __init__(self, parent, cfg: dict, on_save):
        self.on_save = on_save
        self.win = tk.Toplevel(parent)
        self.win.title("Settings")
        self.win.resizable(False, False)
        self.win.configure(bg=BG)
        self.win.attributes("-topmost", True)
        self._build(cfg)
        self.win.grab_set()

    def _build(self, cfg):
        pad = {"padx": 12, "pady": 7}

        tk.Label(self.win, text="OpenAI API Key:", bg=BG, fg=FG).grid(
            row=0, column=0, sticky="w", **pad)
        self._api_var = tk.StringVar(value=cfg.get("openai_api_key", ""))
        api_entry = tk.Entry(self.win, textvariable=self._api_var, width=46,
                             show="*", bg=BG2, fg=FG, insertbackground=FG,
                             relief="flat")
        api_entry.grid(row=0, column=1, **pad)

        self._show_key = tk.BooleanVar()
        tk.Checkbutton(self.win, text="Show", variable=self._show_key, bg=BG, fg=FG,
                       selectcolor=BG2, activebackground=BG,
                       command=lambda: api_entry.config(
                           show="" if self._show_key.get() else "*"
                       )).grid(row=0, column=2, padx=(0, 10))

        # Anthropic API Key (for AI Assistant)
        tk.Label(self.win, text="Anthropic API Key:", bg=BG, fg=FG).grid(
            row=1, column=0, sticky="w", **pad)
        self._anthropic_var = tk.StringVar(value=cfg.get("anthropic_api_key", ""))
        anth_entry = tk.Entry(self.win, textvariable=self._anthropic_var, width=46,
                              show="*", bg=BG2, fg=FG, insertbackground=FG,
                              relief="flat")
        anth_entry.grid(row=1, column=1, **pad)
        self._show_anth = tk.BooleanVar()
        tk.Checkbutton(self.win, text="Show", variable=self._show_anth, bg=BG, fg=FG,
                       selectcolor=BG2, activebackground=BG,
                       command=lambda: anth_entry.config(
                           show="" if self._show_anth.get() else "*"
                       )).grid(row=1, column=2, padx=(0, 10))

        # Assistant project root
        tk.Label(self.win, text="Assistant project root:", bg=BG, fg=FG).grid(
            row=2, column=0, sticky="w", **pad)
        self._asst_root_var = tk.StringVar(value=cfg.get("assistant_project_root", ""))
        tk.Entry(self.win, textvariable=self._asst_root_var, width=46,
                 bg=BG2, fg=FG, insertbackground=FG,
                 relief="flat").grid(row=2, column=1, columnspan=2, sticky="w", **pad)

        tk.Label(self.win, text="Monitor (0 = primary):", bg=BG, fg=FG).grid(
            row=3, column=0, sticky="w", **pad)
        self._monitor_var = tk.IntVar(value=cfg.get("monitor", 0))
        tk.Spinbox(self.win, from_=0, to=10, textvariable=self._monitor_var,
                   width=5, bg=BG2, fg=FG, buttonbackground=BG3,
                   relief="flat").grid(row=3, column=1, sticky="w", **pad)

        tk.Label(self.win, text="Screenshot triggers:", bg=BG, fg=FG).grid(
            row=4, column=0, sticky="w", **pad)
        import utils as _utils
        default_triggers = ", ".join(_utils.SCREENSHOT_TRIGGERS)
        self._triggers_var = tk.StringVar(value=cfg.get("screenshot_triggers", default_triggers))
        tk.Entry(self.win, textvariable=self._triggers_var, width=46,
                 bg=BG2, fg=FG, insertbackground=FG,
                 relief="flat").grid(row=4, column=1, columnspan=2, sticky="w", **pad)
        tk.Label(self.win, text="(comma-separated words/phrases)",
                 bg=BG, fg=FG_DIM, font=("Segoe UI", 7)).grid(
            row=5, column=1, sticky="w", padx=12, pady=(0, 4))

        tk.Label(self.win, text="Mic Input:", bg=BG, fg=FG).grid(
            row=6, column=0, sticky="w", **pad)
        self._mic_options, self._mic_indices = self._get_mic_devices()
        saved_mic = cfg.get("mic_device", -1)
        saved_label = "Auto (default)"
        for idx, lbl in zip(self._mic_indices, self._mic_options):
            if idx == saved_mic:
                saved_label = lbl
                break
        self._mic_var = tk.StringVar(value=saved_label)
        ttk.Combobox(self.win, textvariable=self._mic_var,
                     values=self._mic_options, state="readonly",
                     width=43).grid(row=6, column=1, columnspan=2,
                                    sticky="w", **pad)

        btn_frame = tk.Frame(self.win, bg=BG)
        btn_frame.grid(row=7, column=0, columnspan=3, pady=(4, 12))
        tk.Button(btn_frame, text="Save", width=10, bg=ACCENT, fg="white",
                  relief="flat", command=self._save).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Cancel", width=10, bg=BG3, fg=FG,
                  relief="flat", command=self.win.destroy).pack(side="left", padx=6)

    @staticmethod
    def _get_mic_devices():
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            labels = ["Auto (default)"]
            indices = [-1]
            for i, d in enumerate(devices):
                if d['max_input_channels'] > 0:
                    labels.append(f"{i}: {d['name']}")
                    indices.append(i)
            return labels, indices
        except Exception:
            return ["Auto (default)"], [-1]

    def _save(self):
        sel_label = self._mic_var.get()
        mic_idx = -1
        for idx, lbl in zip(self._mic_indices, self._mic_options):
            if lbl == sel_label:
                mic_idx = idx
                break
        new_cfg = {
            "openai_api_key": self._api_var.get().strip(),
            "anthropic_api_key": self._anthropic_var.get().strip(),
            "assistant_project_root": self._asst_root_var.get().strip(),
            "monitor": self._monitor_var.get(),
            "mic_device": mic_idx,
            "screenshot_triggers": self._triggers_var.get().strip(),
        }
        save_config(new_cfg)
        apply_config(new_cfg)
        self.on_save(new_cfg)
        self.win.destroy()


# ── Thread-safe log handler ───────────────────────────────────────────────────

class _TkLogHandler(logging.Handler):
    def __init__(self, get_widget_fn):
        super().__init__()
        self._get_widget = get_widget_fn
        self.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))

    def emit(self, record):
        try:
            msg = self.format(record)
            w = self._get_widget()
            if w and w.winfo_exists():
                w.after(0, lambda m=msg: self._write(m))
        except Exception:
            pass

    def _write(self, msg):
        try:
            w = self._get_widget()
            if not w or not w.winfo_exists():
                return
            w.config(state="normal")
            w.insert("end", msg + "\n")
            w.see("end")
            lines = int(w.index("end-1c").split(".")[0])
            if lines > 200:
                w.delete("1.0", f"{lines - 200}.0")
            w.config(state="disabled")
        except Exception:
            pass


# ── Main App ──────────────────────────────────────────────────────────────────

class MeetingScribeApp:
    _METER_SEGS  = 24
    _SS_THUMB_W  = 200

    def __init__(self, auto_start: bool = False,
                 auto_project: str = None, auto_name: str = None):
        self.cfg = load_config()
        apply_config(self.cfg)

        self.recording       = False
        self.live_session    = None
        self.meeting_session = None

        # Recording UI state
        self._ticking         = False
        self._current_level   = 0.0
        self._current_sys_level = 0.0
        self._n_transcripts   = 0
        self._n_screenshots   = 0
        self._rec_start       = 0.0
        self._photo_refs      = []
        self._meter_segs_ids  = []
        self._sys_meter_segs_ids = []
        self._log_handler     = None

        # Set AppUserModelID so Windows taskbar groups this app correctly
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "MeetingScribe.App")
        except Exception:
            pass

        self.root = tk.Tk()
        self.root.title("MeetingScribe")
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._set_window_icon()
        self._build()
        self._show_idle()

        if auto_start:
            self._auto_start_pending = True
            if auto_project:
                self._project_var.set(auto_project)
            if auto_name:
                self._name_var.set(auto_name)
            self.root.after(500, self._auto_start)
        else:
            self._auto_start_pending = False

        self.root.mainloop()

    def _set_window_icon(self):
        """Set a custom taskbar/window icon using a .ico file for Windows."""
        sizes = [16, 32, 48, 64]
        images = []
        for size in sizes:
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            s = size  # shorthand
            # Teal microphone on dark circle — scaled to each size
            pad = max(1, s // 16)
            draw.ellipse([pad, pad, s - pad, s - pad], fill="#1e1e1e")
            # Mic body (rounded rect)
            bx0 = int(s * 0.34)
            bx1 = int(s * 0.66)
            by0 = int(s * 0.16)
            by1 = int(s * 0.59)
            radius = max(2, s // 6)
            draw.rounded_rectangle([bx0, by0, bx1, by1], radius=radius,
                                   fill="#4ec9b0")
            # Arc under mic
            ax0 = int(s * 0.25)
            ax1 = int(s * 0.75)
            ay0 = int(s * 0.31)
            ay1 = int(s * 0.75)
            arc_w = max(1, s // 20)
            draw.arc([ax0, ay0, ax1, ay1], start=0, end=180,
                     fill="#4ec9b0", width=arc_w)
            # Stand
            cx = s // 2
            stand_top = int(s * 0.75)
            stand_bot = int(s * 0.87)
            draw.line([cx, stand_top, cx, stand_bot], fill="#4ec9b0",
                      width=max(1, s // 20))
            # Base
            base_half = int(s * 0.12)
            draw.line([cx - base_half, stand_bot, cx + base_half, stand_bot],
                      fill="#4ec9b0", width=max(1, s // 20))
            images.append(img)

        # Save as .ico with multiple sizes
        ico_dir = Path(tempfile.gettempdir())
        ico_path = ico_dir / "meetingscribe_icon.ico"
        images[0].save(str(ico_path), format="ICO",
                       sizes=[(s, s) for s in sizes],
                       append_images=images[1:])
        self._ico_path = str(ico_path)
        self.root.wm_iconbitmap(self._ico_path)

    # ── Build frames ──────────────────────────────────────────────────────────

    def _build(self):
        self._idle_frame = tk.Frame(self.root, bg=BG)
        self._rec_frame  = tk.Frame(self.root, bg=BG)
        self._build_idle()
        self._build_recording()

    def _build_idle(self):
        f = self._idle_frame

        # Header
        hdr = tk.Frame(f, bg=BG3, pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="MeetingScribe", bg=BG3, fg=FG,
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=14)
        tk.Label(hdr, text="AI Meeting Recorder", bg=BG3, fg=FG_DIM,
                 font=("Segoe UI", 8)).pack(side="left", padx=(0, 6))
        tk.Button(hdr, text="Settings", bg=BG3, fg=FG_DIM, relief="flat",
                  font=("Segoe UI", 8), cursor="hand2",
                  command=self._on_settings).pack(side="right", padx=10)

        # Project row
        proj_row = tk.Frame(f, bg=BG)
        proj_row.pack(fill="x", padx=14, pady=(14, 4))
        tk.Label(proj_row, text="Project:", bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 9)).pack(side="left")
        self._project_var = tk.StringVar()
        self._project_combo = ttk.Combobox(
            proj_row, textvariable=self._project_var,
            width=22, font=("Segoe UI", 9), state="normal")
        self._project_combo.pack(side="left", padx=(6, 4))
        self._project_combo.bind("<<ComboboxSelected>>",
                                  lambda e: self._refresh_meetings())
        self._project_var.trace_add("write", lambda *_: self.root.after(50, self._refresh_meetings))
        tk.Button(proj_row, text="📁 Browse", bg=BG2, fg=FG,
                  relief="flat", font=("Segoe UI", 8), cursor="hand2",
                  command=self._browse_project).pack(side="left", padx=2)

        # Meeting name
        name_row = tk.Frame(f, bg=BG)
        name_row.pack(fill="x", padx=14, pady=(6, 0))
        tk.Label(name_row, text="Meeting name (optional):", bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 8)).pack(anchor="w")
        self._name_var = tk.StringVar()
        tk.Entry(name_row, textvariable=self._name_var, bg=BG2, fg=FG,
                 insertbackground=FG, relief="flat", font=("Segoe UI", 10),
                 width=36).pack(fill="x", ipady=5)

        # New Meeting button
        self._start_btn = tk.Button(
            f, text="Start",
            bg=GREEN, fg="white", activebackground="#1e8449",
            activeforeground="white", font=("Segoe UI", 13, "bold"),
            relief="flat", cursor="hand2", pady=10,
            command=self._start,
        )
        self._start_btn.pack(fill="x", padx=14, pady=12)

        self._idle_status_var = tk.StringVar()
        tk.Label(f, textvariable=self._idle_status_var, bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 8)).pack()

        tk.Frame(f, bg=BG3, height=1).pack(fill="x", padx=14, pady=(6, 4))

        # Recent meetings list
        tk.Label(f, text="Recent Meetings", bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14)

        list_outer = tk.Frame(f, bg=BG)
        list_outer.pack(fill="both", expand=True, padx=14, pady=(4, 4))

        self._mtg_canvas = tk.Canvas(list_outer, bg=BG, highlightthickness=0)
        mtg_scroll = tk.Scrollbar(list_outer, orient="vertical",
                                   command=self._mtg_canvas.yview)
        self._mtg_canvas.configure(yscrollcommand=mtg_scroll.set)
        mtg_scroll.pack(side="right", fill="y")
        self._mtg_canvas.pack(fill="both", expand=True)
        self._mtg_inner = tk.Frame(self._mtg_canvas, bg=BG)
        self._mtg_fid = self._mtg_canvas.create_window(
            (0, 0), window=self._mtg_inner, anchor="nw")
        self._mtg_inner.bind("<Configure>", lambda e: self._mtg_canvas.configure(
            scrollregion=self._mtg_canvas.bbox("all")))
        self._mtg_canvas.bind("<Configure>", lambda e: self._mtg_canvas.itemconfig(
            self._mtg_fid, width=e.width))

        # Bottom actions
        bot = tk.Frame(f, bg=BG)
        bot.pack(padx=14, pady=(4, 12))
        for text, cmd in [("Process MP4...", self._on_process_mp4),
                           ("Open Folder",    self._on_open_folder)]:
            tk.Button(bot, text=text, bg=BG2, fg=FG, relief="flat",
                      font=("Segoe UI", 8), cursor="hand2",
                      command=cmd, pady=4, padx=8).pack(side="left", padx=3)

        if not self.cfg.get("openai_api_key"):
            tk.Label(f, text="No API key set — open Settings",
                     bg=BG, fg=RED, font=("Segoe UI", 8)).pack(pady=(0, 6))

    def _build_recording(self):
        f = self._rec_frame

        # Header
        hdr = tk.Frame(f, bg=BG3, pady=4)
        hdr.pack(fill="x")

        self._rec_status_lbl = tk.Label(
            hdr, text="  Recording...", fg=RED, bg=BG3,
            font=("Segoe UI", 10, "bold"))
        self._rec_status_lbl.pack(side="left")

        self._stop_btn = tk.Button(
            hdr, text="  Stop  ", bg=RED, fg="white",
            activebackground="#922b21", font=("Segoe UI", 9, "bold"),
            relief="flat", cursor="hand2", command=self._stop)
        self._stop_btn.pack(side="left", padx=(10, 0), pady=3)

        self._session_lbl = tk.Label(hdr, text="", bg=BG3, fg=FG_DIM,
                                      font=("Segoe UI", 8))
        self._session_lbl.pack(side="left", padx=10)

        self._timer_lbl = tk.Label(hdr, text="00:00",
                                    font=("Segoe UI", 10), bg=BG3, fg=FG)
        self._timer_lbl.pack(side="right", padx=10)

        self._stats_lbl = tk.Label(
            hdr, text="Transcripts: 0  |  Screenshots: 0",
            font=("Segoe UI", 9), bg=BG3, fg=FG_DIM)
        self._stats_lbl.pack(side="right", padx=10)

        # VU meters container
        meters_frame = tk.Frame(f, bg="#1a1a1a")
        meters_frame.pack(fill="x")

        # MIC meter row
        mic_row = tk.Frame(meters_frame, bg="#1a1a1a", pady=2)
        mic_row.pack(fill="x")
        tk.Label(mic_row, text="MIC", bg="#1a1a1a", fg="#555",
                 font=("Segoe UI", 7), width=4, anchor="e").pack(side="left", padx=(8, 4))
        self._meter_canvas = tk.Canvas(mic_row, height=14, bg="#1a1a1a",
                                        highlightthickness=0)
        self._meter_canvas.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._rms_lbl = tk.Label(mic_row, text="0.000", bg="#1a1a1a",
                                  fg="#444", font=("Consolas", 7), width=6)
        self._rms_lbl.pack(side="right", padx=(0, 8))
        tk.Label(mic_row, text="Next chunk in:", bg="#1a1a1a", fg="#444",
                 font=("Segoe UI", 7)).pack(side="right", padx=(0, 4))
        self._chunk_lbl = tk.Label(mic_row, text="10s", bg="#1a1a1a",
                                    fg=ACCENT, font=("Segoe UI", 7, "bold"))
        self._chunk_lbl.pack(side="right")

        # SYS (system/desktop audio) meter row
        sys_row = tk.Frame(meters_frame, bg="#1a1a1a", pady=2)
        sys_row.pack(fill="x")
        tk.Label(sys_row, text="SYS", bg="#1a1a1a", fg="#555",
                 font=("Segoe UI", 7), width=4, anchor="e").pack(side="left", padx=(8, 4))
        self._sys_meter_canvas = tk.Canvas(sys_row, height=14, bg="#1a1a1a",
                                            highlightthickness=0)
        self._sys_meter_canvas.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._sys_rms_lbl = tk.Label(sys_row, text="0.000", bg="#1a1a1a",
                                      fg="#444", font=("Consolas", 7), width=6)
        self._sys_rms_lbl.pack(side="right", padx=(0, 8))

        # Split pane: transcript | screenshots
        pane = tk.PanedWindow(f, orient="horizontal", sashwidth=5,
                               bg=BG, relief="flat")
        pane.pack(fill="both", expand=True)

        left = tk.Frame(pane, bg=BG)
        pane.add(left, minsize=400, stretch="always")
        tk.Label(left, text="Transcript", bg=BG, fg="#555",
                 font=("Segoe UI", 8)).pack(anchor="w", padx=6, pady=(4, 0))
        self._text = scrolledtext.ScrolledText(
            left, wrap="word", state="disabled", font=("Segoe UI", 10),
            bg=BG, fg=FG, insertbackground=FG, relief="flat",
            padx=8, pady=6, borderwidth=0)
        self._text.pack(fill="both", expand=True)

        right = tk.Frame(pane, bg=BG2)
        pane.add(right, minsize=200, stretch="never")
        tk.Label(right, text="Screenshots", bg=BG2, fg="#555",
                 font=("Segoe UI", 8)).pack(anchor="w", padx=6, pady=(4, 0))
        self._ss_canvas = tk.Canvas(right, bg=BG2, highlightthickness=0)
        ss_scroll = tk.Scrollbar(right, orient="vertical",
                                  command=self._ss_canvas.yview)
        self._ss_canvas.configure(yscrollcommand=ss_scroll.set)
        ss_scroll.pack(side="right", fill="y")
        self._ss_canvas.pack(fill="both", expand=True)
        self._ss_frame = tk.Frame(self._ss_canvas, bg=BG2)
        self._ss_fid = self._ss_canvas.create_window(
            (0, 0), window=self._ss_frame, anchor="nw")
        self._ss_frame.bind("<Configure>", lambda e: self._ss_canvas.configure(
            scrollregion=self._ss_canvas.bbox("all")))
        self._ss_canvas.bind("<Configure>", lambda e: self._ss_canvas.itemconfig(
            self._ss_fid, width=e.width))

        # AI Assistant panel
        asst_frame = tk.Frame(f, bg="#1a1a2e", pady=2)
        asst_frame.pack(fill="x", side="bottom")
        tk.Label(asst_frame, text="AI Assistant", bg="#1a1a2e", fg="#555",
                 font=("Segoe UI", 8)).pack(anchor="w", padx=6, pady=(2, 0))
        self._asst_text = tk.Text(asst_frame, height=3, bg="#1a1a2e", fg="#b0b0e0",
                                   font=("Segoe UI", 9), relief="flat",
                                   state="disabled", wrap="word", padx=6, pady=4)
        self._asst_text.pack(fill="x", expand=False, padx=(0, 6))
        self._asst_text.tag_config("time", foreground=ACCENT, font=("Segoe UI", 8))
        self._asst_text.tag_config("question", foreground="#e6c07b")
        self._asst_text.tag_config("answer", foreground="#98c379")
        self._asst_text.tag_config("insight", foreground="#c678dd")
        self._suggestions: list = []

        # Debug log
        log_frame = tk.Frame(f, bg="#111", pady=2)
        log_frame.pack(fill="x", side="bottom")
        tk.Label(log_frame, text="LOG", bg="#111", fg="#444",
                 font=("Consolas", 7)).pack(side="left", padx=(6, 4))
        self._log_text = tk.Text(log_frame, height=4, bg="#111", fg="#666",
                                  font=("Consolas", 8), relief="flat",
                                  state="disabled", wrap="word")
        self._log_text.pack(fill="x", expand=True, padx=(0, 6))

    # ── Idle mode helpers ──────────────────────────────────────────────────────

    def _show_idle(self):
        self._rec_frame.pack_forget()
        self._idle_frame.pack(fill="both", expand=True)
        self.root.resizable(False, False)
        self.root.geometry(f"{IDLE_W}x{IDLE_H}")
        # Pre-fill meeting name with current date/time
        import datetime
        self._name_var.set(datetime.datetime.now().strftime("%Y-%m-%d %H%M"))
        self._load_projects()
        self._refresh_meetings()

    def _load_projects(self):
        from utils import list_projects
        projects = list_projects()
        cur = self._project_var.get().strip()
        # Always include the currently selected project in the dropdown
        if cur and cur not in projects:
            projects = sorted(set(projects + [cur]))
        self._project_combo["values"] = projects
        if not cur:
            last = self.cfg.get("last_project", "")
            self._project_var.set(last if last in projects else (projects[0] if projects else ""))

    def _browse_project(self):
        from utils import MEETINGS_DIR
        folder = filedialog.askdirectory(
            title="Select project folder",
            initialdir=str(MEETINGS_DIR),
            parent=self.root)
        if not folder:
            return
        folder = Path(folder)
        # Always create/use a project folder inside MEETINGS_DIR
        try:
            folder.relative_to(MEETINGS_DIR)
            project_key = folder.name
        except ValueError:
            # Selected folder is outside MEETINGS_DIR — create a matching folder inside
            project_key = folder.name
        project_dir = MEETINGS_DIR / project_key
        project_dir.mkdir(parents=True, exist_ok=True)
        self._project_var.set(project_key)
        self.cfg["last_project"] = project_key
        save_config(self.cfg)
        self._load_projects()

    def _refresh_meetings(self):
        from utils import list_meetings
        for w in self._mtg_inner.winfo_children():
            w.destroy()
        project = self._project_var.get().strip() or None
        meetings = list_meetings(project)
        if not meetings:
            tk.Label(self._mtg_inner, text="No meetings yet",
                     bg=BG, fg=FG_DIM, font=("Segoe UI", 9)).pack(pady=10)
            return
        for m in meetings[:25]:
            self._make_meeting_row(m)

    def _make_meeting_row(self, m: dict):
        path   = Path(m["session_path"])
        start  = m.get("start_time", "")[:16].replace("T", "  ")
        name   = m.get("session_name", path.name)

        row = tk.Frame(self._mtg_inner, bg=BG2, pady=5)
        row.pack(fill="x", pady=2, padx=2)

        info = tk.Frame(row, bg=BG2)
        info.pack(side="left", fill="x", expand=True, padx=6)
        tk.Label(info, text=name, bg=BG2, fg=FG,
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(anchor="w")
        tk.Label(info, text=start, bg=BG2, fg=FG_DIM,
                 font=("Segoe UI", 7), anchor="w").pack(anchor="w")

        btns = tk.Frame(row, bg=BG2)
        btns.pack(side="right", padx=6)
        tk.Button(btns, text="Open", bg=BG3, fg=FG, relief="flat",
                  font=("Segoe UI", 7), pady=2, padx=6,
                  cursor="hand2",
                  command=lambda p=str(path): os.startfile(p)
                  ).pack(side="left", padx=2)

    # ── Recording mode ─────────────────────────────────────────────────────────

    def _show_recording(self, session_name: str, project: str = None):
        # Reset recording UI
        self._n_transcripts  = 0
        self._n_screenshots  = 0
        self._photo_refs.clear()
        self._meter_segs_ids.clear()
        self._sys_meter_segs_ids.clear()
        self._meter_canvas.delete("all")
        self._sys_meter_canvas.delete("all")
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        self._text.config(state="disabled")
        for w in self._ss_frame.winfo_children():
            w.destroy()
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")
        self._asst_text.config(state="normal")
        self._asst_text.delete("1.0", "end")
        self._asst_text.config(state="disabled")
        self._suggestions = []

        proj_prefix = f"{project} / " if project else ""
        self._session_lbl.config(text=f"  {proj_prefix}{session_name}")
        self._rec_status_lbl.config(text="  Recording...", fg=RED)
        self._stop_btn.config(state="normal", text="  Stop  ", bg=RED,
                               command=self._stop)
        self._stats_lbl.config(text="Transcripts: 0  |  Screenshots: 0")
        self._timer_lbl.config(text="00:00")

        # Install log handler
        self._log_handler = _TkLogHandler(lambda: self._log_text)
        logging.getLogger().addHandler(self._log_handler)

        # Switch frames
        self._idle_frame.pack_forget()
        self._rec_frame.pack(fill="both", expand=True)
        self.root.resizable(True, True)
        self.root.geometry(f"{REC_W}x{REC_H}")

        # Start ticks
        self._ticking   = True
        self._rec_start = time.time()
        self._tick()
        self._meter_tick()

    def _set_recording_done(self):
        self._ticking = False
        self.recording = False
        self._rec_status_lbl.config(text="  Processing complete...", fg=TEAL)
        self._stop_btn.config(state="normal", text=" Back to Projects ",
                               bg=ACCENT, activebackground="#005f9e",
                               command=self._back_to_idle)
        if self._log_handler:
            logging.getLogger().removeHandler(self._log_handler)
            self._log_handler = None

    def _back_to_idle(self):
        self._show_idle()

    # ── Timer / meter ticks ────────────────────────────────────────────────────

    def _tick(self):
        if not self.root.winfo_exists() or not self._ticking:
            return
        e = int(time.time() - self._rec_start)
        self._timer_lbl.config(text=f"{e // 60:02d}:{e % 60:02d}")
        self.root.after(1000, self._tick)

    def _meter_tick(self):
        if not self.root.winfo_exists():
            return

        # Update MIC meter
        w = self._meter_canvas.winfo_width()
        if w > 2:
            if not self._meter_segs_ids:
                sw = max(1, (w - self._METER_SEGS) // self._METER_SEGS)
                for i in range(self._METER_SEGS):
                    x = i * (sw + 1)
                    self._meter_segs_ids.append(
                        self._meter_canvas.create_rectangle(
                            x, 1, x + sw, 13, fill="#2a2a2a", outline=""))
            lit = int(self._current_level * self._METER_SEGS)
            for i, rid in enumerate(self._meter_segs_ids):
                f = i / self._METER_SEGS
                color = (GREEN if f < 0.6 else ("#f39c12" if f < 0.8 else RED)) \
                    if i < lit else "#2a2a2a"
                self._meter_canvas.itemconfig(rid, fill=color)

        # Update SYS meter
        sw2 = self._sys_meter_canvas.winfo_width()
        if sw2 > 2:
            if not self._sys_meter_segs_ids:
                seg_w = max(1, (sw2 - self._METER_SEGS) // self._METER_SEGS)
                for i in range(self._METER_SEGS):
                    x = i * (seg_w + 1)
                    self._sys_meter_segs_ids.append(
                        self._sys_meter_canvas.create_rectangle(
                            x, 1, x + seg_w, 13, fill="#2a2a2a", outline=""))
            sys_lit = int(self._current_sys_level * self._METER_SEGS)
            for i, rid in enumerate(self._sys_meter_segs_ids):
                f = i / self._METER_SEGS
                color = (GREEN if f < 0.6 else ("#f39c12" if f < 0.8 else RED)) \
                    if i < sys_lit else "#2a2a2a"
                self._sys_meter_canvas.itemconfig(rid, fill=color)

        from utils import CHUNK_DURATION_SECONDS
        remaining = int(CHUNK_DURATION_SECONDS -
                        (time.time() - self._rec_start) % CHUNK_DURATION_SECONDS)
        self._chunk_lbl.config(text=f"{remaining}s")
        self._rms_lbl.config(text=f"{self._current_level:.3f}")
        self._sys_rms_lbl.config(text=f"{self._current_sys_level:.3f}")
        self.root.after(100, self._meter_tick)

    # ── Recording callbacks ────────────────────────────────────────────────────

    def _on_mic_level(self, rms: float):
        self._current_level = min(rms, 1.0)

    def _on_sys_level(self, rms: float):
        self._current_sys_level = min(rms, 1.0)

    def _on_suggestion(self, text: str, suggestion_type: str):
        """Called from MeetingAssistant background thread."""
        self.root.after(0, lambda t=text, st=suggestion_type:
                        self._append_suggestion(t, st))

    def _append_suggestion(self, text: str, suggestion_type: str):
        from utils import format_timestamp
        elapsed = time.time() - self._rec_start if self._rec_start else 0
        ts = format_timestamp(elapsed)
        self._suggestions.append((ts, text, suggestion_type))
        # Keep only last 3
        if len(self._suggestions) > 3:
            self._suggestions = self._suggestions[-3:]
        # Redraw the panel
        self._asst_text.config(state="normal")
        self._asst_text.delete("1.0", "end")
        for s_ts, s_text, s_type in self._suggestions:
            self._asst_text.insert("end", f"[{s_ts}] ", "time")
            self._asst_text.insert("end", f"{s_text}\n", s_type)
        self._asst_text.see("end")
        self._asst_text.config(state="disabled")

    def _on_transcript(self, text: str, timestamp: float):
        self.root.after(0, lambda t=text, ts=timestamp:
                        self._append_transcript(t, ts))

    def _append_transcript(self, text: str, timestamp: float):
        from utils import format_timestamp
        ts = format_timestamp(timestamp)
        self._n_transcripts += 1
        self._text.config(state="normal")
        self._text.insert("end", f"[{ts}]\n", "ts")
        self._text.insert("end", f"{text}\n\n")
        self._text.tag_config("ts", foreground=ACCENT, font=("Segoe UI", 9))
        self._text.see("end")
        self._text.config(state="disabled")
        self._stats_lbl.config(
            text=f"Transcripts: {self._n_transcripts}  |  Screenshots: {self._n_screenshots}")

    def _on_screenshot(self, path: str, reason: str, timestamp: float):
        self.root.after(0, lambda p=path, r=reason, ts=timestamp:
                        self._append_screenshot(p, r, ts))

    def _append_screenshot(self, image_path: str, reason: str, timestamp: float):
        from utils import format_timestamp
        ts = format_timestamp(timestamp)
        try:
            from PIL import Image as PILImage, ImageTk
            img = PILImage.open(image_path)
            ratio = self._SS_THUMB_W / img.width
            thumb = img.resize((self._SS_THUMB_W, int(img.height * ratio)),
                                PILImage.LANCZOS)
            photo = ImageTk.PhotoImage(thumb)
            self._photo_refs.append(photo)
            card = tk.Frame(self._ss_frame, bg=BG3, pady=4)
            card.pack(fill="x", padx=4, pady=4)
            tk.Label(card, image=photo, bg=BG3).pack()
            tk.Label(card, text=f"[{ts}] {reason}", bg=BG3, fg=FG_DIM,
                     font=("Segoe UI", 8),
                     wraplength=self._SS_THUMB_W).pack()
            self._ss_canvas.yview_moveto(1.0)
        except Exception:
            tk.Label(self._ss_frame, text=f"[{ts}] {reason}",
                     bg=BG2, fg=FG_DIM, font=("Segoe UI", 8),
                     wraplength=self._SS_THUMB_W).pack(anchor="w", padx=6, pady=2)
        self._n_screenshots += 1
        self._stats_lbl.config(
            text=f"Transcripts: {self._n_transcripts}  |  Screenshots: {self._n_screenshots}")

    # ── Start / Stop ───────────────────────────────────────────────────────────

    def _auto_start(self):
        """One-shot auto-start — won't retry on failure."""
        self._auto_start_pending = False
        self._start()

    def _start(self):
        if not os.environ.get("OPENAI_API_KEY"):
            self._idle_status_var.set("No API key — open Settings first")
            print("[MeetingScribe] No API key set — cannot auto-start")
            SettingsWindow(self.root, self.cfg, self._on_cfg_saved)
            return
        print(f"[MeetingScribe] Starting recording...")
        project = self._project_var.get().strip() or None
        name    = self._name_var.get().strip() or None
        # Remember last project
        if project:
            self.cfg["last_project"] = project
            save_config(self.cfg)
        threading.Thread(target=self._record_worker,
                         args=(name, project), daemon=True).start()

    def _stop(self):
        self.recording = False
        self._ticking = False
        self._stop_btn.config(state="disabled")
        self._rec_status_lbl.config(text="  Stopping...", fg="#f39c12")
        threading.Thread(target=self._stop_worker, daemon=True).start()

    def _record_worker(self, name, project):
        try:
            from utils import MeetingSession
            from live_session import LiveSession

            self.meeting_session = MeetingSession(name=name, project=project)
            self.meeting_session.create_directories()

            self.root.after(0, lambda: self._show_recording(
                self.meeting_session.name, project))
            time.sleep(0.3)

            mic_idx    = self.cfg.get("mic_device", -1)
            mic_device = mic_idx if isinstance(mic_idx, int) and mic_idx >= 0 else None

            self.live_session = LiveSession(
                self.meeting_session,
                monitor=self.cfg.get("monitor", 0),
                mic_device=mic_device,
                transcript_callback=self._on_transcript,
                screenshot_callback=self._on_screenshot,
                suggestion_callback=self._on_suggestion,
            )
            self.live_session.set_level_callback(self._on_mic_level)
            self.live_session.set_system_level_callback(self._on_sys_level)

            self.recording = True

            started = self.live_session.start()
            if not started:
                self.root.after(0, lambda: self._idle_status_var.set(
                    "Failed to start recording"))
                self.recording = False
                self.root.after(0, self._show_idle)
                return

            while self.recording:
                time.sleep(0.5)

        except Exception as e:
            print(f"[MeetingScribe] Record worker error: {e}")
            self.root.after(0, lambda err=e: self._idle_status_var.set(
                f"Error: {err}"))
            self.recording = False
            self.root.after(0, self._show_idle)

    def _stop_worker(self):
        try:
            if self.live_session:
                self.live_session.stop()
            if self.meeting_session:
                self.root.after(0, lambda: self._rec_status_lbl.config(
                    text="  Processing...", fg="#f39c12"))
                self._run_post_processing(self.meeting_session)
                folder = self.meeting_session.session_path
                saved_name = self.meeting_session.session_folder
                self.root.after(0, lambda: self._idle_status_var.set(
                    f"Saved: {saved_name}"))
                # Write latest session path for external tools (e.g. Claude Code)
                from utils import MEETINGS_DIR
                marker = MEETINGS_DIR / ".latest_session"
                marker.write_text(str(folder), encoding="utf-8")
                os.startfile(str(folder))
            self.root.after(0, self._set_recording_done)
        except Exception as e:
            self.root.after(0, lambda err=e: self._idle_status_var.set(
                f"Error: {err}"))
            self.root.after(0, self._set_recording_done)
        finally:
            self.live_session    = None
            self.meeting_session = None

    # ── Other actions ──────────────────────────────────────────────────────────

    def _on_settings(self):
        SettingsWindow(self.root, self.cfg, self._on_cfg_saved)

    def _on_cfg_saved(self, new_cfg):
        self.cfg = new_cfg

    def _on_process_mp4(self):
        path = filedialog.askopenfilename(
            title="Select MP4", parent=self.root,
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")])
        if not path:
            return
        threading.Thread(target=self._process_mp4_worker,
                         args=(path,), daemon=True).start()

    def _process_mp4_worker(self, path):
        try:
            from utils import MeetingSession
            from video_processor import VideoProcessor
            project = self._project_var.get().strip() or None
            session = MeetingSession(project=project)
            session.create_directories()
            VideoProcessor(session).process_mp4(path)
            self._run_post_processing(session)
            self.root.after(0, lambda: self._idle_status_var.set("Done!"))
            os.startfile(str(session.session_path))
        except Exception as e:
            self.root.after(0, lambda err=e: self._idle_status_var.set(
                f"Error: {err}"))

    def _on_open_folder(self):
        from utils import MEETINGS_DIR
        project = self._project_var.get().strip()
        target  = (MEETINGS_DIR / project) if project else MEETINGS_DIR
        target.mkdir(parents=True, exist_ok=True)
        os.startfile(str(target))

    def _on_close(self):
        if self.recording:
            self._stop()
            time.sleep(1)
        self.root.destroy()

    @staticmethod
    def _run_post_processing(session):
        logger = logging.getLogger("post_process")

        # Generate work items
        try:
            from work_items import WorkItemsGenerator
            WorkItemsGenerator(session.session_path).generate_work_items()
            logger.info("Work items generated")
        except Exception as e:
            logger.error(f"Work items failed: {e}")

        # Generate AI summary / minutes
        try:
            from summarizer import MeetingSummarizer
            summarizer = MeetingSummarizer(session)
            summarizer.generate_minutes()
            summarizer.generate_html_report()
            logger.info("Minutes & HTML report generated")
        except Exception as e:
            logger.error(f"Summarizer failed: {e}")

        # Generate final report
        try:
            from report_generator import ReportGenerator
            ReportGenerator(session).generate()
            logger.info("Report generated")
        except Exception as e:
            logger.error(f"Report generator failed: {e}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MeetingScribe AI Meeting Recorder")
    parser.add_argument("--start",   action="store_true", help="Start recording immediately")
    parser.add_argument("--project", default=None,        help="Project folder name")
    parser.add_argument("--name",    default=None,        help="Meeting name")
    args = parser.parse_args()
    MeetingScribeApp(auto_start=args.start, auto_project=args.project, auto_name=args.name)
