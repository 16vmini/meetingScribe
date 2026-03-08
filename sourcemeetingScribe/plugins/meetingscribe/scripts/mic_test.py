"""
MIC DEBUG TEST - tries 5 different ways to read mic level
Run: py -3 mic_test.py
"""
import tkinter as tk
import threading
import time
import numpy as np

BG = "#1e1e1e"
BG2 = "#252526"
FG = "#d4d4d4"
GREEN = "#27ae60"
RED = "#c0392b"
ACCENT = "#007acc"
GREY = "#2a2a2a"

SEGS = 30


def make_bar(parent):
    canvas = tk.Canvas(parent, height=16, bg="#111", highlightthickness=0)
    canvas.pack(fill="x", expand=True, padx=4)
    ids = []

    def draw(level):
        w = canvas.winfo_width()
        if w < 10:
            return
        if not ids:
            sw = max(1, (w - SEGS) // SEGS)
            for i in range(SEGS):
                x = i * (sw + 1)
                ids.append(canvas.create_rectangle(x, 1, x + sw, 15,
                                                    fill=GREY, outline=""))
        lit = int(min(level, 1.0) * SEGS)
        for i, rid in enumerate(ids):
            f = i / SEGS
            color = GREEN if f < 0.6 else ("#f39c12" if f < 0.8 else RED) if i < lit else GREY
            canvas.itemconfig(rid, fill=color)

    return draw


class MethodRow:
    def __init__(self, parent, row, label, start_fn):
        self.root = parent
        self.level = 0.0
        self.active = False
        self.error = None
        self._stop_event = threading.Event()

        frame = tk.Frame(parent, bg=BG2, pady=6, padx=8)
        frame.grid(row=row, column=0, sticky="ew", padx=8, pady=4)
        parent.columnconfigure(0, weight=1)

        top = tk.Frame(frame, bg=BG2)
        top.pack(fill="x")
        tk.Label(top, text=label, bg=BG2, fg=FG,
                 font=("Consolas", 9, "bold"), width=42, anchor="w").pack(side="left")

        self._rms_lbl = tk.Label(top, text="  ---  ", bg=BG2, fg="#aaa",
                                  font=("Consolas", 9), width=8)
        self._rms_lbl.pack(side="left", padx=4)

        self._status_lbl = tk.Label(top, text="idle", bg=BG2, fg="#555",
                                     font=("Segoe UI", 8))
        self._status_lbl.pack(side="left", padx=8)

        self._btn = tk.Button(top, text="Start", bg=ACCENT, fg="white",
                               font=("Segoe UI", 8), relief="flat", width=6,
                               command=self._toggle)
        self._btn.pack(side="right")

        self._bar_fn = make_bar(frame)

        self._start_fn = start_fn
        self._thread = None

    def _toggle(self):
        if self.active:
            self._stop()
        else:
            self._start()

    def _start(self):
        self._stop_event.clear()
        self.active = True
        self._btn.config(text="Stop", bg=RED)
        self._status_lbl.config(text="starting...", fg=ACCENT)
        self._thread = threading.Thread(
            target=self._run, daemon=True)
        self._thread.start()
        self._tick()

    def _stop(self):
        self._stop_event.set()
        self.active = False
        self._btn.config(text="Start", bg=ACCENT)
        self._status_lbl.config(text="stopped", fg="#555")

    def _run(self):
        try:
            self._start_fn(
                self._stop_event,
                self._set_level,
                self._set_status,
            )
        except Exception as e:
            self._set_status(f"ERROR: {e}", error=True)
            self.active = False

    def _set_level(self, rms):
        self.level = rms

    def _set_status(self, msg, error=False):
        self.root.after(0, lambda: self._status_lbl.config(
            text=msg, fg=RED if error else GREEN))

    def _tick(self):
        if not self.root.winfo_exists():
            return
        self._bar_fn(self.level)
        self._rms_lbl.config(text=f"{self.level:.4f}")
        if self.active:
            self.root.after(80, self._tick)
        else:
            self.level = 0.0
            self._bar_fn(0.0)
            self._rms_lbl.config(text="  ---  ")


# ── The 5 methods ─────────────────────────────────────────────────────────────

def method1_sd_default(stop, set_level, set_status):
    """sounddevice InputStream — device=None (system default)"""
    import sounddevice as sd
    buf = []

    def cb(indata, frames, t, status):
        rms = float(np.sqrt(np.mean(indata ** 2)))
        set_level(min(rms * 30, 1.0))
        buf.append(rms)

    set_status("opened stream", error=False)
    with sd.InputStream(channels=1, callback=cb, blocksize=2048):
        set_status("streaming ✓")
        while not stop.is_set():
            time.sleep(0.1)
    set_status("stopped")


def method2_sd_device1(stop, set_level, set_status):
    """sounddevice InputStream — device=1 (SoundWire D)"""
    import sounddevice as sd

    def cb(indata, frames, t, status):
        rms = float(np.sqrt(np.mean(indata ** 2)))
        set_level(min(rms * 30, 1.0))

    with sd.InputStream(device=1, channels=1, callback=cb, blocksize=2048):
        set_status("streaming ✓")
        while not stop.is_set():
            time.sleep(0.1)
    set_status("stopped")


def method3_sd_raw(stop, set_level, set_status):
    """sounddevice RawInputStream — default device, raw bytes"""
    import sounddevice as sd

    def cb(indata, frames, t, status):
        arr = np.frombuffer(indata, dtype=np.int16).astype(np.float32) / 32768.0
        rms = float(np.sqrt(np.mean(arr ** 2)))
        set_level(min(rms * 30, 1.0))

    with sd.RawInputStream(channels=1, dtype="int16", callback=cb, blocksize=2048):
        set_status("streaming ✓")
        while not stop.is_set():
            time.sleep(0.1)
    set_status("stopped")


def method4_sd_blockread(stop, set_level, set_status):
    """sounddevice blocking rec() in loop — no callback"""
    import sounddevice as sd
    set_status("loop recording ✓")
    while not stop.is_set():
        chunk = sd.rec(2048, samplerate=16000, channels=1, dtype="float32")
        sd.wait()
        if stop.is_set():
            break
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        set_level(min(rms * 30, 1.0))
    set_status("stopped")


def method6_sd_44100(stop, set_level, set_status):
    """sounddevice InputStream — samplerate=44100, blocksize=4410 (same as main app)"""
    import sounddevice as sd

    def cb(indata, frames, t, status):
        if status:
            set_status(f"status: {status}", error=True)
        rms = float(np.sqrt(np.mean(indata ** 2)))
        set_level(min(rms * 30, 1.0))

    try:
        with sd.InputStream(channels=1, samplerate=44100, blocksize=4410, callback=cb):
            set_status("streaming ✓  (44100 Hz)")
            while not stop.is_set():
                time.sleep(0.1)
    except Exception as e:
        set_status(f"FAILED: {e}", error=True)
        return
    set_status("stopped")


def method7_sd_16000(stop, set_level, set_status):
    """sounddevice InputStream — samplerate=16000, blocksize=1600 (speech rate)"""
    import sounddevice as sd

    def cb(indata, frames, t, status):
        if status:
            set_status(f"status: {status}", error=True)
        rms = float(np.sqrt(np.mean(indata ** 2)))
        set_level(min(rms * 30, 1.0))

    try:
        with sd.InputStream(channels=1, samplerate=16000, blocksize=1600, callback=cb):
            set_status("streaming ✓  (16000 Hz)")
            while not stop.is_set():
                time.sleep(0.1)
    except Exception as e:
        set_status(f"FAILED: {e}", error=True)
        return
    set_status("stopped")


def method5_pyaudio(stop, set_level, set_status):
    """PyAudio — default input device"""
    try:
        import pyaudio
    except ImportError:
        set_status("PyAudio not installed", error=True)
        return

    pa = pyaudio.PyAudio()
    try:
        stream = pa.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=2048,
        )
        set_status("streaming ✓")
        while not stop.is_set():
            try:
                data = stream.read(2048, exception_on_overflow=False)
                arr = np.frombuffer(data, dtype=np.float32)
                rms = float(np.sqrt(np.mean(arr ** 2)))
                set_level(min(rms * 30, 1.0))
            except Exception as e:
                set_status(f"read error: {e}", error=True)
                break
        stream.stop_stream()
        stream.close()
    finally:
        pa.terminate()
    set_status("stopped")


# ── Also enumerate all input devices ──────────────────────────────────────────

def list_devices():
    try:
        import sounddevice as sd
        devs = sd.query_devices()
        lines = []
        default_in = sd.default.device[0]
        for i, d in enumerate(devs):
            if d['max_input_channels'] > 0:
                marker = " ◄ DEFAULT" if i == default_in else ""
                lines.append(f"  [{i}] {d['name']} (ch={d['max_input_channels']}){marker}")
        return "\n".join(lines) if lines else "  (no input devices found)"
    except Exception as e:
        return f"  ERROR: {e}"


# ── Main window ───────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    root.title("Mic Debug Test — 5 Methods")
    root.configure(bg=BG)
    root.resizable(True, False)

    tk.Label(root, text="MIC DEBUG TEST", bg=BG, fg=FG,
             font=("Segoe UI", 13, "bold")).pack(pady=(16, 2))
    tk.Label(root, text="Start each method and watch the RMS / bar react to your voice.",
             bg=BG, fg="#777", font=("Segoe UI", 8)).pack(pady=(0, 6))

    # Device list
    dev_frame = tk.Frame(root, bg="#111", pady=4)
    dev_frame.pack(fill="x", padx=8, pady=(0, 8))
    tk.Label(dev_frame, text="Input devices detected:", bg="#111", fg="#555",
             font=("Consolas", 7)).pack(anchor="w", padx=6)
    dev_text = tk.Text(dev_frame, height=5, bg="#111", fg="#888",
                       font=("Consolas", 8), relief="flat", state="normal")
    dev_text.pack(fill="x", padx=6)
    dev_text.insert("1.0", list_devices())
    dev_text.config(state="disabled")

    # Method rows
    grid = tk.Frame(root, bg=BG)
    grid.pack(fill="x", padx=0, pady=4)

    methods = [
        ("1. sounddevice InputStream  — device=None (auto default)", method1_sd_default),
        ("2. sounddevice InputStream  — device=1  (SoundWire D)",     method2_sd_device1),
        ("3. sounddevice RawInputStream — device=None, int16 bytes",  method3_sd_raw),
        ("4. sounddevice blocking rec() loop — no callback",           method4_sd_blockread),
        ("5. PyAudio paFloat32 — default input device",               method5_pyaudio),
        ("6. sounddevice InputStream  — samplerate=44100 (main app)", method6_sd_44100),
        ("7. sounddevice InputStream  — samplerate=16000 (speech)",   method7_sd_16000),
    ]

    rows = []
    for i, (label, fn) in enumerate(methods):
        rows.append(MethodRow(grid, i, label, fn))

    tk.Label(root, text="If RMS moves when you speak → that method works in your environment.",
             bg=BG, fg="#555", font=("Segoe UI", 8)).pack(pady=(8, 16))

    root.mainloop()

    # Stop all on exit
    for r in rows:
        r._stop_event.set()


if __name__ == "__main__":
    main()
