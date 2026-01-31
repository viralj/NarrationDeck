from __future__ import annotations

import tkinter as tk
from tkinter import filedialog
from typing import Iterable

from .tts import generate_audio_and_srt
from .config import get_api_key

FRAME_RATES = ["23.976", "24", "25", "29.97", "30", "50", "59.94", "60"]

RESOLUTION_PRESETS = [
    {"group": "Wide", "label": "8K UHD (7680x4320)", "width": 7680, "height": 4320},
    {"group": "Wide", "label": "4K UHD (3840x2160)", "width": 3840, "height": 2160},
    {"group": "Wide", "label": "2K (2560x1440)", "width": 2560, "height": 1440},
    {"group": "Wide", "label": "1080p (1920x1080)", "width": 1920, "height": 1080},
    {"group": "Wide", "label": "720p (1280x720)", "width": 1280, "height": 720},
    {"group": "Shorts 9:16", "label": "8K (4320x7680)", "width": 4320, "height": 7680},
    {"group": "Shorts 9:16", "label": "4K (2160x3840)", "width": 2160, "height": 3840},
    {"group": "Shorts 9:16", "label": "2K (1440x2560)", "width": 1440, "height": 2560},
    {"group": "Shorts 9:16", "label": "1080x1920", "width": 1080, "height": 1920},
    {"group": "Shorts 9:16", "label": "720x1280", "width": 720, "height": 1280},
]


class NarrationDeckGUI:
    def __init__(self, root: tk.Tk, voices: Iterable[dict] | None = None) -> None:
        self.root = root
        self.voices = list(voices or [])

        self.images_dir = tk.StringVar()
        self.narration_text = tk.StringVar()
        self.voice_label = tk.StringVar()
        self.speed = tk.DoubleVar(value=1.0)
        self.volume = tk.DoubleVar(value=100.0)
        self.frame_rate = tk.StringVar(value=FRAME_RATES[4])
        self.resolution_label = tk.StringVar(value=self._resolution_labels()[1])
        self.output_format = tk.StringVar(value="mp3")
        self.project_mode = tk.StringVar(value="create")
        self.allow_missing_anchors = tk.BooleanVar(value=False)

        if self.voices:
            self.voice_label.set(self.voices[0].get("label", ""))
        else:
            self.voice_label.set("No voices found")

    def render(self) -> None:
        self.root.geometry("900x700")
        self.root.minsize(820, 640)

        title = tk.Label(self.root, text="NarrationDeck", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, columnspan=4, sticky="w", padx=12, pady=(12, 6))

        self._project_settings_frame().grid(
            row=1, column=0, columnspan=4, sticky="ew", padx=12, pady=(0, 8)
        )
        self._inputs_frame().grid(row=2, column=0, columnspan=4, sticky="ew", padx=12)
        self._narration_frame().grid(
            row=3, column=0, columnspan=4, sticky="nsew", padx=12, pady=(10, 6)
        )
        self._image_map_frame().grid(
            row=4, column=0, columnspan=4, sticky="nsew", padx=12, pady=(0, 6)
        )
        self._actions_frame().grid(row=5, column=0, columnspan=4, sticky="ew", padx=12)
        self._log_frame().grid(row=6, column=0, columnspan=4, sticky="nsew", padx=12, pady=(6, 12))

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)
        self.root.grid_columnconfigure(3, weight=1)
        self.root.grid_rowconfigure(3, weight=1)
        self.root.grid_rowconfigure(4, weight=1)
        self.root.grid_rowconfigure(6, weight=1)

    def _project_settings_frame(self) -> tk.LabelFrame:
        frame = tk.LabelFrame(self.root, text="Project Settings (Phase 1 Placeholder)")
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(3, weight=1)

        tk.Label(frame, text="Project Mode").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        tk.Radiobutton(
            frame, text="Create new", variable=self.project_mode, value="create"
        ).grid(row=0, column=1, sticky="w", padx=8, pady=6)
        tk.Radiobutton(
            frame, text="Use existing (coming soon)", variable=self.project_mode, value="existing", state="disabled"
        ).grid(row=0, column=2, sticky="w", padx=8, pady=6)

        tk.Label(frame, text="Resolution").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        tk.OptionMenu(frame, self.resolution_label, *self._resolution_labels()).grid(
            row=1, column=1, columnspan=2, sticky="ew", padx=8, pady=6
        )

        tk.Label(frame, text="Frame Rate").grid(row=1, column=3, sticky="w", padx=8, pady=6)
        tk.OptionMenu(frame, self.frame_rate, *FRAME_RATES).grid(
            row=1, column=4, sticky="w", padx=8, pady=6
        )

        return frame

    def _inputs_frame(self) -> tk.LabelFrame:
        frame = tk.LabelFrame(self.root, text="Inputs")
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(3, weight=1)

        tk.Label(frame, text="Images Folder").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        tk.Entry(frame, textvariable=self.images_dir).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        tk.Button(frame, text="Browse", command=self._browse_images).grid(
            row=0, column=2, sticky="w", padx=4, pady=6
        )

        tk.Label(frame, text="Voice").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        tk.OptionMenu(frame, self.voice_label, *self._voice_labels()).grid(
            row=1, column=1, sticky="ew", padx=8, pady=6
        )

        tk.Label(frame, text="Speed (x)").grid(row=1, column=2, sticky="w", padx=8, pady=6)
        tk.Scale(
            frame, variable=self.speed, from_=0.7, to=1.2, resolution=0.05, orient="horizontal", length=160
        ).grid(row=1, column=3, sticky="w", padx=8, pady=6)

        tk.Label(frame, text="Volume (%)").grid(row=2, column=2, sticky="w", padx=8, pady=6)
        tk.Scale(
            frame, variable=self.volume, from_=0, to=200, resolution=1, orient="horizontal", length=160
        ).grid(row=2, column=3, sticky="w", padx=8, pady=6)

        tk.Label(frame, text="Output Format").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        tk.Radiobutton(frame, text="MP3", variable=self.output_format, value="mp3").grid(
            row=2, column=1, sticky="w", padx=8, pady=6
        )
        tk.Radiobutton(frame, text="WAV", variable=self.output_format, value="wav").grid(
            row=2, column=1, sticky="e", padx=8, pady=6
        )

        tk.Checkbutton(
            frame,
            text="Allow missing image anchors (lenient)",
            variable=self.allow_missing_anchors,
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=8, pady=6)

        return frame

    def _narration_frame(self) -> tk.LabelFrame:
        frame = tk.LabelFrame(self.root, text="Narration Text")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self.narration_box = tk.Text(frame, height=10, wrap="word")
        self.narration_box.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        return frame

    def _image_map_frame(self) -> tk.LabelFrame:
        frame = tk.LabelFrame(self.root, text="Image Anchors (optional)")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self.image_map_box = tk.Text(frame, height=6, wrap="word")
        self.image_map_box.insert("end", "Image 01 : first words of the segment\n")
        self.image_map_box.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        return frame

    def _actions_frame(self) -> tk.Frame:
        frame = tk.Frame(self.root)

        tk.Button(
            frame,
            text="Generate Audio + SRT",
            command=self._on_generate_clicked,
            state="normal",
        ).grid(row=0, column=0, padx=6, pady=6)

        tk.Button(
            frame,
            text="Build Resolve Timeline (coming soon)",
            command=self._on_build_clicked,
            state="normal",
        ).grid(row=0, column=1, padx=6, pady=6)

        return frame

    def _log_frame(self) -> tk.LabelFrame:
        frame = tk.LabelFrame(self.root, text="Status Log")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self.log_box = tk.Text(frame, height=8, wrap="word", state="disabled")
        self.log_box.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        return frame

    def _browse_images(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.images_dir.set(path)
            self._log(f"Selected folder: {path}")

    def _on_generate_clicked(self) -> None:
        images_dir = self.images_dir.get().strip()
        if not images_dir:
            self._log("Please select an images folder first.")
            return

        narration_text = self.narration_box.get("1.0", "end").strip()
        if not narration_text:
            self._log("Please paste narration text before generating.")
            return

        voice = self._selected_voice()
        if not voice:
            self._log("Selected voice not found in voices.json.")
            return

        api_key = get_api_key()
        if not api_key:
            self._log("Missing ELEVENLABS_API_KEY in .env or environment.")
            return

        self._log("Generating audio + SRT via ElevenLabs...")
        self._log(f"Voice: {voice.get('label', 'Unknown')} | Speed: {self.speed.get():.2f} | Volume: {self.volume.get():.0f}%")
        self._log("Note: Volume is reserved for Resolve clip gain in later phases.")
        try:
            image_map_text = self.image_map_box.get("1.0", "end").strip()
            result = generate_audio_and_srt(
                output_dir=images_dir,
                text=narration_text,
                voice=voice,
                speed=self.speed.get(),
                output_format=self.output_format.get(),
                api_key=api_key,
                image_map_text=image_map_text,
                allow_missing_image_anchors=self.allow_missing_anchors.get(),
            )
        except Exception as exc:
            self._log(f"Failed: {exc}")
            return

        self._log(f"Audio saved: {result['audio_path']}")
        self._log(f"SRT saved: {result['srt_path']}")
        self._log(f"Timestamps saved: {result['timestamps_path']}")
        if result.get("image_timeline_path"):
            self._log(f"Image timeline saved: {result['image_timeline_path']}")
        if result.get("missing_images"):
            self._log(f"Missing image anchors: {', '.join(result['missing_images'])}")
        if result.get("note"):
            self._log(result["note"])

    def _on_build_clicked(self) -> None:
        self._log("Build Resolve Timeline clicked (not implemented yet).")

    def _resolution_labels(self) -> list[str]:
        return [
            f"{preset['group']} - {preset['label']}"
            for preset in RESOLUTION_PRESETS
        ]

    def _voice_labels(self) -> list[str]:
        labels = [voice.get("label", "Unnamed") for voice in self.voices]
        return labels or ["No voices found"]

    def _selected_voice(self) -> dict | None:
        selected = self.voice_label.get()
        for voice in self.voices:
            if voice.get("label") == selected:
                return voice
        return None

    def _log(self, message: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
