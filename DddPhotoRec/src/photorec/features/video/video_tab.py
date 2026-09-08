from typing import Optional

import flet as ft

from photorec.features.video.ffmpeg_runner import FFMPEG_AVAILABLE
from photorec.features.video.service import CRF_BY_QUALITY, VideoCompressorService
from photorec.shared.file_picker import select_folder
from photorec.shared.folder_card import create_folder_card


_QUALITY_OPTIONS = ["High", "Medium", "Strong"]
_DEFAULT_QUALITY = "Medium"

# (label, threshold in MB)
_THRESHOLD_OPTIONS = [
    ("100 MB", 100.0),
    ("200 MB", 200.0),
    ("500 MB", 500.0),
    ("1 GB", 1024.0),
    ("2 GB", 2048.0),
]
_DEFAULT_THRESHOLD_LABEL = "500 MB"


class VideoCompressorTab:
    def __init__(self, page: ft.Page) -> None:
        self._page = page

        self._cancel_requested = False
        self._running = False

        self._input_folder: Optional[str] = None

        self._create_controls()

    # ==================================================================
    # CONTROLS
    # ==================================================================

    def _create_controls(self) -> None:
        self._input_text = ft.Text(
            "Input: -",
            size=13,
            color=ft.Colors.GREY_400,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        self._select_input_button = ft.ElevatedButton(
            text="Select INPUT folder",
            on_click=self._on_select_input_clicked,
            height=40,
            style=ft.ButtonStyle(
                color=ft.Colors.BLUE_200,
                bgcolor=ft.Colors.BLUE_900,
                shape=ft.RoundedRectangleBorder(radius=9),
            ),
        )

        self._quality_dropdown = self._dropdown(
            "Quality",
            _DEFAULT_QUALITY,
            [(label, label) for label in _QUALITY_OPTIONS],
            width=150,
        )

        self._downscale_switch = ft.Switch(
            value=False,
            active_color=ft.Colors.ORANGE_400,
            on_change=self._on_downscale_changed,
        )

        self._threshold_dropdown = self._dropdown(
            "Downscale files larger than",
            _DEFAULT_THRESHOLD_LABEL,
            _THRESHOLD_OPTIONS,
            width=230,
        )
        self._threshold_dropdown.disabled = True

        self._compress_button = ft.ElevatedButton(
            text="Compress",
            disabled=True,
            on_click=self._on_compress_clicked,
            height=44,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.INDIGO_500,
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
        )

        self._cancel_button = ft.ElevatedButton(
            text="Cancel",
            disabled=True,
            on_click=self._on_cancel_clicked,
            height=44,
            style=ft.ButtonStyle(
                color=ft.Colors.RED_200,
                bgcolor=ft.Colors.RED_900,
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
        )

        self._file_progress_bar = ft.ProgressBar(
            value=0,
            visible=False,
            color=ft.Colors.PURPLE_300,
            bgcolor=ft.Colors.GREY_800,
            border_radius=6,
        )

        self._overall_progress_bar = ft.ProgressBar(
            value=0,
            visible=False,
            color=ft.Colors.INDIGO_400,
            bgcolor=ft.Colors.GREY_800,
            border_radius=6,
        )

        self._log_field = ft.TextField(
            multiline=True,
            read_only=True,
            expand=True,
            text_size=12,
            color=ft.Colors.GREY_300,
            bgcolor=ft.Colors.TRANSPARENT,
            border=ft.InputBorder.NONE,
            content_padding=0,
            cursor_color=ft.Colors.BLUE_300,
        )

    def _dropdown(self, label, value, options, width) -> ft.Dropdown:
        return ft.Dropdown(
            label=label,
            value=value,
            width=width,
            text_size=13,
            color=ft.Colors.GREY_100,
            bgcolor=ft.Colors.GREY_900,
            border_color=ft.Colors.GREY_700,
            focused_border_color=ft.Colors.INDIGO_400,
            label_style=ft.TextStyle(color=ft.Colors.GREY_400),
            options=[
                ft.dropdown.Option(
                    key=key,
                    content=ft.Text(key, size=13, color=ft.Colors.GREY_100),
                )
                for key, _ in options
            ],
        )

    # ==================================================================
    # BUILD
    # ==================================================================

    def build(self) -> ft.Control:
        if not FFMPEG_AVAILABLE:
            self._add_log(
                "ffmpeg not found — video compression is unavailable."
            )

        return ft.Container(
            padding=ft.padding.only(left=28, right=28, top=24, bottom=24),
            expand=True,
            content=ft.Column(
                spacing=16,
                expand=True,
                controls=[
                    ft.Text(
                        "Compress videos",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREY_100,
                    ),

                    ft.Text(
                        "Re-encode videos to H.264 (.mp4) in place, keeping "
                        "resolution. Originals are moved to _Backup/. A file is "
                        "replaced only if the result is smaller.",
                        size=13,
                        color=ft.Colors.GREY_500,
                    ),

                    create_folder_card(
                        title="INPUT",
                        icon=ft.Icons.FOLDER_SPECIAL_OUTLINED,
                        icon_color=ft.Colors.BLUE_300,
                        icon_background=ft.Colors.BLUE_900,
                        text_control=self._input_text,
                        button=self._select_input_button,
                    ),

                    ft.Row(
                        spacing=16,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            self._quality_dropdown,
                            self._threshold_dropdown,
                        ],
                    ),

                    ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            self._downscale_switch,
                            ft.Column(
                                spacing=1,
                                controls=[
                                    ft.Text(
                                        "Downscale very large videos to 720p",
                                        size=13,
                                        color=ft.Colors.GREY_200,
                                    ),
                                    ft.Text(
                                        "Only files above the size threshold; "
                                        "aspect ratio is kept.",
                                        size=11,
                                        color=ft.Colors.GREY_500,
                                    ),
                                ],
                            ),
                        ],
                    ),

                    ft.Row(
                        spacing=10,
                        controls=[
                            self._compress_button,
                            self._cancel_button,
                        ],
                    ),

                    ft.Column(
                        spacing=6,
                        controls=[
                            ft.Text(
                                "Current file",
                                size=11,
                                color=ft.Colors.GREY_600,
                            ),
                            self._file_progress_bar,
                            ft.Text(
                                "Overall",
                                size=11,
                                color=ft.Colors.GREY_600,
                            ),
                            self._overall_progress_bar,
                        ],
                    ),

                    ft.Container(height=1, bgcolor=ft.Colors.GREY_800),

                    ft.Text(
                        "Log",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREY_200,
                    ),

                    ft.Container(
                        content=self._log_field,
                        bgcolor=ft.Colors.GREY_900,
                        border=ft.border.all(1, ft.Colors.GREY_800),
                        border_radius=12,
                        padding=14,
                        expand=True,
                    ),
                ],
            ),
        )

    # ==================================================================
    # FOLDER / SETTINGS
    # ==================================================================

    def _on_select_input_clicked(self, _: ft.ControlEvent) -> None:
        folder = select_folder()
        if folder is None:
            return
        self._input_folder = folder
        self._input_text.value = folder
        self._add_log(f"Input folder: {folder}")
        self._update_buttons()

    def _on_downscale_changed(self, _: ft.ControlEvent) -> None:
        self._update_buttons()

    def _selected_crf(self) -> int:
        return CRF_BY_QUALITY.get(self._quality_dropdown.value, 23)

    def _selected_threshold_mb(self) -> float:
        for label, megabytes in _THRESHOLD_OPTIONS:
            if label == self._threshold_dropdown.value:
                return megabytes
        return 500.0

    # ==================================================================
    # COMPRESS
    # ==================================================================

    def _on_compress_clicked(self, _: ft.ControlEvent) -> None:
        self._cancel_requested = False
        self._set_running(True)

        self._page.run_task(self._run_compress)

    async def _run_compress(self) -> None:
        try:
            service = VideoCompressorService(
                input_folder=self._input_folder,
                crf=self._selected_crf(),
                downscale_720=self._downscale_switch.value,
                threshold_mb=self._selected_threshold_mb(),
                log=self._add_log,
                cancel_check=lambda: self._cancel_requested,
                progress=self._on_overall_progress,
                file_progress=self._on_file_progress,
            )

            await service.run()

        except Exception as error:
            self._add_log(f"ERROR: {error}")

        finally:
            self._set_running(False)

    def _on_cancel_clicked(self, _: ft.ControlEvent) -> None:
        self._cancel_requested = True
        self._add_log("Cancellation requested...")

    def _on_overall_progress(self, done: int, total: int) -> None:
        self._overall_progress_bar.value = (done / total) if total else None
        self._page.update()

    def _on_file_progress(self, fraction: float) -> None:
        self._file_progress_bar.value = fraction
        self._page.update()

    # ==================================================================
    # LOGGING / STATE
    # ==================================================================

    def _add_log(self, message: str) -> None:
        print(message)
        self._log_field.value += message + "\n"
        self._log_field.cursor_position = len(self._log_field.value)
        self._page.update()

    def _set_running(self, running: bool) -> None:
        self._running = running

        self._file_progress_bar.visible = running
        self._overall_progress_bar.visible = running
        if running:
            self._file_progress_bar.value = 0
            self._overall_progress_bar.value = 0

        self._update_buttons()

    def _update_buttons(self) -> None:
        ready = bool(self._input_folder and FFMPEG_AVAILABLE)

        self._compress_button.disabled = self._running or not ready
        self._cancel_button.disabled = not self._running
        self._select_input_button.disabled = self._running
        self._quality_dropdown.disabled = self._running
        self._downscale_switch.disabled = self._running
        self._threshold_dropdown.disabled = (
            self._running or not self._downscale_switch.value
        )

        self._page.update()
