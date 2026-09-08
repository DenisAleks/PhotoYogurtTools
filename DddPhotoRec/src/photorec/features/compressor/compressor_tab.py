from typing import Optional

import flet as ft

from photorec.features.compressor.service import CompressorService
from photorec.shared.file_picker import select_folder
from photorec.shared.folder_card import create_folder_card


# (label shown, target in MB)
_TARGET_OPTIONS = [
    ("1 MB", 1.0),
    ("2 MB", 2.0),
    ("3 MB", 3.0),
    ("5 MB", 5.0),
]
_DEFAULT_TARGET_LABEL = "2 MB"


class CompressorTab:
    def __init__(self, page: ft.Page) -> None:
        self._page = page

        self._cancel_requested = False
        self._running = False

        self._input_folder: Optional[str] = None
        self._output_folder: Optional[str] = None

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

        self._output_text = ft.Text(
            "Output: -",
            size=13,
            color=ft.Colors.GREY_400,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        self._select_input_button = self._select_button(
            "Select INPUT folder",
            ft.Colors.BLUE_200,
            ft.Colors.BLUE_900,
            self._on_select_input_clicked,
        )

        self._select_output_button = self._select_button(
            "Select OUTPUT folder",
            ft.Colors.GREEN_200,
            ft.Colors.GREEN_900,
            self._on_select_output_clicked,
        )

        self._convert_switch = ft.Switch(
            value=True,
            active_color=ft.Colors.INDIGO_400,
        )

        self._in_place_switch = ft.Switch(
            value=False,
            active_color=ft.Colors.ORANGE_400,
            on_change=self._on_mode_changed,
        )

        self._progress_bar = ft.ProgressBar(
            value=0,
            visible=False,
            color=ft.Colors.INDIGO_400,
            bgcolor=ft.Colors.GREY_800,
            border_radius=6,
        )

        self._target_dropdown = ft.Dropdown(
            label="Target max size",
            value=_DEFAULT_TARGET_LABEL,
            width=160,
            text_size=13,
            color=ft.Colors.GREY_100,
            bgcolor=ft.Colors.GREY_900,
            border_color=ft.Colors.GREY_700,
            focused_border_color=ft.Colors.INDIGO_400,
            label_style=ft.TextStyle(color=ft.Colors.GREY_400),
            options=[
                ft.dropdown.Option(
                    key=label,
                    content=ft.Text(label, size=13, color=ft.Colors.GREY_100),
                )
                for label, _ in _TARGET_OPTIONS
            ],
        )

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

    def _select_button(self, text, color, background, on_click) -> ft.Control:
        return ft.ElevatedButton(
            text=text,
            on_click=on_click,
            height=40,
            style=ft.ButtonStyle(
                color=color,
                bgcolor=background,
                shape=ft.RoundedRectangleBorder(radius=9),
            ),
        )

    # ==================================================================
    # BUILD
    # ==================================================================

    def build(self) -> ft.Control:
        return ft.Container(
            padding=ft.padding.only(left=28, right=28, top=24, bottom=24),
            expand=True,
            content=ft.Column(
                spacing=16,
                expand=True,
                controls=[
                    ft.Text(
                        "Compress photos",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREY_100,
                    ),

                    ft.Text(
                        "Shrink large photos to a target size at the same "
                        "resolution. By default compressed copies go to OUTPUT "
                        "and originals are untouched. In-place mode backs "
                        "originals up to _Backup/ and moves videos to _Video/.",
                        size=13,
                        color=ft.Colors.GREY_500,
                    ),

                    ft.Row(
                        spacing=14,
                        controls=[
                            create_folder_card(
                                title="INPUT",
                                icon=ft.Icons.FOLDER_SPECIAL_OUTLINED,
                                icon_color=ft.Colors.BLUE_300,
                                icon_background=ft.Colors.BLUE_900,
                                text_control=self._input_text,
                                button=self._select_input_button,
                            ),
                            create_folder_card(
                                title="OUTPUT",
                                icon=ft.Icons.FOLDER_OUTLINED,
                                icon_color=ft.Colors.GREEN_300,
                                icon_background=ft.Colors.GREEN_900,
                                text_control=self._output_text,
                                button=self._select_output_button,
                            ),
                        ],
                    ),

                    ft.Row(
                        spacing=16,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            self._target_dropdown,
                            ft.Row(
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    self._convert_switch,
                                    ft.Column(
                                        spacing=1,
                                        controls=[
                                            ft.Text(
                                                "Convert HEIC / HEIF / PNG to JPEG",
                                                size=13,
                                                color=ft.Colors.GREY_200,
                                            ),
                                            ft.Text(
                                                "For Windows-friendly files. Off "
                                                "= keep original formats.",
                                                size=11,
                                                color=ft.Colors.GREY_500,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),

                    ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            self._in_place_switch,
                            ft.Column(
                                spacing=1,
                                controls=[
                                    ft.Text(
                                        "Compress in place (keep originals in "
                                        "_Backup)",
                                        size=13,
                                        color=ft.Colors.GREY_200,
                                    ),
                                    ft.Text(
                                        "Replaces files in the INPUT folder; "
                                        "moves videos to _Video/. OUTPUT is "
                                        "ignored.",
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

                    self._progress_bar,

                    ft.Container(height=1, bgcolor=ft.Colors.GREY_800),

                    ft.Row(
                        controls=[
                            ft.Text(
                                "Compression log",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.GREY_200,
                            ),
                            ft.Container(expand=True),
                            ft.Text(
                                "Originals untouched · videos skipped",
                                size=11,
                                color=ft.Colors.GREY_600,
                            ),
                        ],
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
    # FOLDER SELECTION
    # ==================================================================

    def _on_select_input_clicked(self, _: ft.ControlEvent) -> None:
        folder = select_folder()
        if folder is None:
            return
        self._input_folder = folder
        self._input_text.value = folder
        self._add_log(f"Input folder: {folder}")
        self._update_buttons()

    def _on_select_output_clicked(self, _: ft.ControlEvent) -> None:
        folder = select_folder()
        if folder is None:
            return
        self._output_folder = folder
        self._output_text.value = folder
        self._add_log(f"Output folder: {folder}")
        self._update_buttons()

    # ==================================================================
    # COMPRESS
    # ==================================================================

    def _on_compress_clicked(self, _: ft.ControlEvent) -> None:
        self._cancel_requested = False
        self._set_running(True)

        self._page.run_task(self._run_compress)

    async def _run_compress(self) -> None:
        try:
            service = CompressorService(
                input_folder=self._input_folder,
                output_folder=self._output_folder,
                convert_to_jpeg=self._convert_switch.value,
                in_place=self._in_place_switch.value,
                target_mb=self._selected_target_mb(),
                log=self._add_log,
                cancel_check=lambda: self._cancel_requested,
                progress=self._on_progress,
            )

            await service.run()

        except Exception as error:
            self._add_log(f"ERROR: {error}")

        finally:
            self._set_running(False)

    def _on_mode_changed(self, _: ft.ControlEvent) -> None:
        self._update_buttons()

    def _on_progress(self, done: int, total: int) -> None:
        self._progress_bar.value = (done / total) if total else None
        self._page.update()

    def _on_cancel_clicked(self, _: ft.ControlEvent) -> None:
        self._cancel_requested = True
        self._add_log("Cancellation requested...")

    def _selected_target_mb(self) -> float:
        for label, megabytes in _TARGET_OPTIONS:
            if label == self._target_dropdown.value:
                return megabytes
        return 2.0

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

        self._progress_bar.visible = running
        if running:
            self._progress_bar.value = 0

        self._update_buttons()

    def _update_buttons(self) -> None:
        in_place = self._in_place_switch.value

        # In-place mode works entirely inside INPUT; OUTPUT isn't needed.
        ready = bool(
            self._input_folder and (in_place or self._output_folder)
        )

        self._compress_button.disabled = self._running or not ready
        self._cancel_button.disabled = not self._running
        self._select_input_button.disabled = self._running
        self._select_output_button.disabled = self._running or in_place
        self._convert_switch.disabled = self._running
        self._in_place_switch.disabled = self._running
        self._target_dropdown.disabled = self._running

        self._page.update()
