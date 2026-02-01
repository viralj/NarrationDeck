from __future__ import annotations

import tkinter as tk
import re
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Iterable
from datetime import datetime

from .tts import generate_audio_and_srt
from .config import get_api_key, get_setting, set_setting
from .payload import build_resolve_payload, write_resolve_payload
from .constants import FRAME_RATES, RESOLUTION_PRESETS


class NarrationDeckGUI:
    def __init__(self, root: tk.Tk, voices: Iterable[dict] | None = None) -> None:
        self.root = root
        self.voices = list(voices or [])

        self.images_dir = tk.StringVar(value=get_setting("last_images_dir", ""))
        self.narration_text = tk.StringVar()
        self.voice_label = tk.StringVar()
        self.speed = tk.DoubleVar(value=1.0)
        self.volume = tk.DoubleVar(value=100.0)
        self.frame_rate = tk.StringVar(value=FRAME_RATES[4])
        self.resolution_label = tk.StringVar(value=self._resolution_labels()[1])
        self.output_format = tk.StringVar(value="mp3")
        self.project_mode = tk.StringVar(value="create")
        self.allow_missing_anchors = tk.BooleanVar(value=False)
        self.project_name = tk.StringVar(value=self._default_project_name())
        self.timeline_name = tk.StringVar(value="NarrationDeck Timeline")
        self.textplus_preset = tk.StringVar(value="NarrationDeck_TextPlus")
        self.output_prefix = tk.StringVar(value="narration")

        self.last_generation: dict | None = None

        if self.voices:
            self.voice_label.set(self.voices[0].get("label", ""))
        else:
            self.voice_label.set("No voices found")

    def render(self) -> None:
        self.root.geometry("900x910")
        self.root.minsize(820, 830)
        self.root.configure(bg="#f5f6f8")

        title = tk.Label(
            self.root,
            text="NarrationDeck",
            font=("Segoe UI", 18, "bold"),
            bg="#f5f6f8",
            fg="#1f2a44",
        )
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
        frame = tk.LabelFrame(
            self.root,
            text="Project Settings (Phase 1 Placeholder)",
            bg="#f5f6f8",
            fg="#1f2a44",
        )
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(3, weight=1)

        tk.Label(frame, text="Project Mode", bg="#f5f6f8").grid(
            row=0, column=0, sticky="w", padx=8, pady=6
        )
        tk.Radiobutton(
            frame,
            text="Create new",
            variable=self.project_mode,
            value="create",
            bg="#f5f6f8",
        ).grid(row=0, column=1, sticky="w", padx=8, pady=6)
        tk.Radiobutton(
            frame,
            text="Use existing (coming soon)",
            variable=self.project_mode,
            value="existing",
            state="disabled",
            bg="#f5f6f8",
        ).grid(row=0, column=1, sticky="e", padx=8, pady=6)

        tk.Label(frame, text="Project Name", bg="#f5f6f8").grid(
            row=0, column=2, sticky="w", padx=8, pady=6
        )
        tk.Entry(frame, textvariable=self.project_name).grid(
            row=0, column=3, sticky="ew", padx=8, pady=6
        )

        tk.Label(frame, text="Resolution", bg="#f5f6f8").grid(
            row=1, column=0, sticky="w", padx=8, pady=6
        )
        tk.OptionMenu(frame, self.resolution_label, *self._resolution_labels()).grid(
            row=1, column=1, sticky="ew", padx=8, pady=6
        )

        tk.Label(frame, text="Frame Rate", bg="#f5f6f8").grid(
            row=1, column=2, sticky="w", padx=8, pady=6
        )
        tk.OptionMenu(frame, self.frame_rate, *FRAME_RATES).grid(
            row=1, column=3, sticky="ew", padx=8, pady=6
        )

        tk.Label(frame, text="Timeline Name", bg="#f5f6f8").grid(
            row=2, column=0, sticky="w", padx=8, pady=6
        )
        tk.Entry(frame, textvariable=self.timeline_name).grid(
            row=2, column=1, sticky="ew", padx=8, pady=6
        )

        tk.Label(frame, text="Text+ Preset", bg="#f5f6f8").grid(
            row=2, column=2, sticky="w", padx=8, pady=6
        )
        tk.Entry(frame, textvariable=self.textplus_preset).grid(
            row=2, column=3, sticky="ew", padx=8, pady=6
        )

        return frame

    def _inputs_frame(self) -> tk.LabelFrame:
        frame = tk.LabelFrame(self.root, text="Inputs", bg="#f5f6f8", fg="#1f2a44")
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(4, weight=1)

        tk.Label(frame, text="Images Folder", bg="#f5f6f8").grid(
            row=0, column=0, sticky="w", padx=8, pady=6
        )
        tk.Entry(frame, textvariable=self.images_dir).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        tk.Button(frame, text="Browse", command=self._browse_images).grid(
            row=0, column=2, sticky="w", padx=4, pady=6
        )

        tk.Label(frame, text="Voice", bg="#f5f6f8").grid(
            row=1, column=0, sticky="w", padx=8, pady=6
        )
        tk.OptionMenu(frame, self.voice_label, *self._voice_labels()).grid(
            row=1, column=1, sticky="ew", padx=8, pady=6
        )

        tk.Label(frame, text="Speed (x)", bg="#f5f6f8").grid(
            row=1, column=3, sticky="w", padx=8, pady=6
        )
        tk.Scale(
            frame, variable=self.speed, from_=0.7, to=1.2, resolution=0.05, orient="horizontal", length=160
        ).grid(row=1, column=4, sticky="w", padx=8, pady=6)

        tk.Label(frame, text="Volume (%)", bg="#f5f6f8").grid(
            row=2, column=3, sticky="w", padx=8, pady=6
        )
        tk.Scale(
            frame, variable=self.volume, from_=0, to=200, resolution=1, orient="horizontal", length=160
        ).grid(row=2, column=4, sticky="w", padx=8, pady=6)

        tk.Label(frame, text="Output Format", bg="#f5f6f8").grid(
            row=2, column=0, sticky="w", padx=8, pady=6
        )
        tk.Radiobutton(frame, text="MP3", variable=self.output_format, value="mp3").grid(
            row=2, column=1, sticky="w", padx=8, pady=6
        )
        tk.Radiobutton(frame, text="WAV", variable=self.output_format, value="wav").grid(
            row=2, column=1, sticky="e", padx=8, pady=6
        )

        tk.Label(frame, text="Output Prefix", bg="#f5f6f8").grid(
            row=3, column=0, sticky="w", padx=8, pady=6
        )
        tk.Entry(frame, textvariable=self.output_prefix).grid(
            row=3, column=1, sticky="ew", padx=8, pady=6
        )

        tk.Checkbutton(
            frame,
            text="Allow missing image anchors (lenient)",
            variable=self.allow_missing_anchors,
            bg="#f5f6f8",
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=8, pady=6)

        return frame

    def _narration_frame(self) -> tk.LabelFrame:
        frame = tk.LabelFrame(self.root, text="Narration Text", bg="#f5f6f8", fg="#1f2a44")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self.narration_box = tk.Text(frame, height=10, wrap="word", bg="white")
        self.narration_box.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        return frame

    def _image_map_frame(self) -> tk.LabelFrame:
        frame = tk.LabelFrame(self.root, text="Image Anchors (optional)", bg="#f5f6f8", fg="#1f2a44")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        help_button = tk.Button(frame, text="Help", command=self._show_image_anchor_help)
        help_button.grid(row=0, column=1, sticky="ne", padx=8, pady=8)

        self.image_map_box = tk.Text(frame, height=6, wrap="word", bg="white")
        self.image_map_box.insert("end", "Image 01 : first words of the segment\n")
        self.image_map_box.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        return frame

    def _actions_frame(self) -> tk.Frame:
        frame = tk.Frame(self.root, bg="#f5f6f8")

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

        tk.Button(
            frame,
            text="Export Resolve Payload",
            command=self._on_export_payload_clicked,
            state="normal",
        ).grid(row=0, column=2, padx=6, pady=6)

        tk.Button(
            frame,
            text="Quick Export (Generate + Payload)",
            command=self._on_quick_export_clicked,
            state="normal",
        ).grid(row=0, column=3, padx=6, pady=6)

        return frame

    def _log_frame(self) -> tk.LabelFrame:
        frame = tk.LabelFrame(self.root, text="Status Log", bg="#f5f6f8", fg="#1f2a44")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self.log_box = tk.Text(frame, height=8, wrap="word", state="disabled", bg="white")
        self.log_box.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        return frame

    def _browse_images(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.images_dir.set(path)
            set_setting("last_images_dir", path)
            self._log(f"Selected folder: {path}")

    def _on_generate_clicked(self) -> None:
        images_dir = self.images_dir.get().strip()
        if not images_dir:
            self._log("Please select an images folder first.")
            return
        self._validate_images(images_dir)

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
                output_prefix=self.output_prefix.get().strip() or "narration",
                image_map_text=image_map_text,
                allow_missing_image_anchors=self.allow_missing_anchors.get(),
            )
        except Exception as exc:
            self._log(f"Failed: {exc}")
            return

        self.last_generation = result
        self._log(f"Audio saved: {result['audio_path']}")
        self._log(f"SRT saved: {result['srt_path']}")
        self._log(f"Timestamps saved: {result['timestamps_path']}")
        if result.get("image_timeline_path"):
            self._log(f"Image timeline saved: {result['image_timeline_path']}")
        if result.get("missing_images"):
            self._log(f"Missing image anchors: {', '.join(result['missing_images'])}")
        if result.get("image_segments"):
            self._log("Image anchor preview:")
            for segment in result["image_segments"]:
                start = segment.get("start", 0.0)
                end = segment.get("end", 0.0)
                image_id = segment.get("image_id", "??")
                snippet = segment.get("snippet", "")
                self._log(f"  {image_id}: {start:.2f}s → {end:.2f}s | {snippet}")
        if result.get("note"):
            self._log(result["note"])

    def _on_build_clicked(self) -> None:
        self._log("Build Resolve Timeline clicked (not implemented yet).")

    def _on_export_payload_clicked(self) -> None:
        images_dir = self.images_dir.get().strip()
        if not images_dir:
            self._log("Please select an images folder before exporting payload.")
            return
        self._validate_images(images_dir)

        image_map_text = self.image_map_box.get("1.0", "end").strip()
        payload = build_resolve_payload(
            images_dir=images_dir,
            resolution_label=self.resolution_label.get(),
            frame_rate=self.frame_rate.get(),
            project_mode=self.project_mode.get(),
            project_name=self.project_name.get().strip(),
            timeline_name=self.timeline_name.get().strip(),
            textplus_preset=self.textplus_preset.get().strip(),
            image_map_text=image_map_text,
            last_generation=self.last_generation,
            allow_missing_image_anchors=self.allow_missing_anchors.get(),
        )

        payload_path = write_resolve_payload(images_dir, payload)
        self._log(f"Resolve payload saved: {payload_path}")
        if not self.last_generation:
            self._log("Note: No audio/SRT artifacts recorded yet. Generate audio first.")

    def _on_quick_export_clicked(self) -> None:
        self._log("Running quick export...")
        self._on_generate_clicked()
        if not self.last_generation:
            self._log("Quick export stopped: audio generation failed.")
            return
        self._on_export_payload_clicked()

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

    def _default_project_name(self) -> str:
        return f"NarrationDeck_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _show_image_anchor_help(self) -> None:
        message = (
            "Image anchor format:\n"
            "  Image 01 : first words of the segment\n"
            "  Image 02 : next words of the segment\n\n"
            "Tips:\n"
            "- The snippet should match the narration text as spoken.\n"
            "- Matching is case-insensitive and ignores punctuation.\n"
            "- Each image starts at the first matched word and ends at the next image start."
        )
        messagebox.showinfo("Image Anchors Help", message)

    def _validate_images(self, images_dir: str) -> None:
        folder = Path(images_dir)
        if not folder.exists():
            self._log("Images folder does not exist.")
            return

        pattern = re.compile(r"^(\d+)\.(png|jpg|jpeg)$", re.IGNORECASE)
        image_numbers = []
        for entry in folder.iterdir():
            if not entry.is_file():
                continue
            match = pattern.match(entry.name)
            if match:
                image_numbers.append(int(match.group(1)))

        if not image_numbers:
            self._log("No numbered images found (expected like 01.png, 02.jpg).")
            return

        image_numbers.sort()
        missing = []
        for num in range(image_numbers[0], image_numbers[-1] + 1):
            if num not in image_numbers:
                missing.append(num)

        if missing:
            missing_str = ", ".join(f"{num:02d}" for num in missing)
            self._log(f"Warning: missing image numbers: {missing_str}")
        else:
            self._log(f"Found {len(image_numbers)} numbered images. Sequence looks complete.")
