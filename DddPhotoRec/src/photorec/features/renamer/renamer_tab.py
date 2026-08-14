from datetime import datetime
from typing import List, Optional

import flet as ft

from photorec.features.renamer.models import RenameOperation
from photorec.features.renamer.name_builder import NameBuilder
from photorec.features.renamer.service import (
    RenamerService,
    undo_operations,
)
from photorec.shared.file_picker import select_folder
from photorec.shared.folder_card import create_folder_card


#
# (label shown in dropdown, pattern written into the field).
# A "/" in a pattern creates a subfolder. Tokens: YYYY YY MM MMM MMMM DD
# HH hh mm ss, plus {name} (original name) and {loc} (place from GPS).
#
_PRESETS = [
    (
        "2024/10/2024-10-05_14-30-22",
        "YYYY/MM/YYYY-MM-DD_HH-mm-ss",
    ),
    (
        "2024/10/20241005_143022",
        "YYYY/MM/YYYYMMDD_HHmmss",
    ),
    (
        "2024/10/IMG_2024-10-05_14-30-22",
        "YYYY/MM/IMG_YYYY-MM-DD_HH-mm-ss",
    ),
    (
        "2024/10/2024-10-05_14-30-22_Lisbon  (adds place)",
        "YYYY/MM/YYYY-MM-DD_HH-mm-ss_{loc}",
    ),
    (
        "2024/October/2024-10-05_14-30-22",
        "YYYY/MMMM/YYYY-MM-DD_HH-mm-ss",
    ),
    (
        "2024/10/05/2024-10-05_14-30-22  (day subfolders)",
        "YYYY/MM/DD/YYYY-MM-DD_HH-mm-ss",
    ),
    (
        "2024/10/2024-10-05_14-30-22_IMG_1234  (keeps name)",
        "YYYY/MM/YYYY-MM-DD_HH-mm-ss_{name}",
    ),
    (
        "2024-10-05_14-30-22  (no subfolders)",
        "YYYY-MM-DD_HH-mm-ss",
    ),
    (
        "2024/10/2024-10-05_Lisbon  (date + place)",
        "YYYY/MM/YYYY-MM-DD_{loc}",
    ),
]

_CUSTOM_LABEL = "Custom…"

_DEFAULT_PATTERN = _PRESETS[0][1]

# Fixed sample used only to render the live "Example:" preview.
_SAMPLE_DATE = datetime(2024, 10, 5, 14, 30, 22)
_SAMPLE_STEM = "IMG_1234"
_SAMPLE_EXT = ".jpg"
_SAMPLE_PLACE = "Lisbon"


class RenamerTab:
    def __init__(self, page: ft.Page) -> None:
        self._page = page

        self._cancel_requested = False
        self._running = False

        self._input_folder: Optional[str] = None
        self._last_operations: List[RenameOperation] = []

        self._builder = NameBuilder()

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

        self._preset_dropdown = ft.Dropdown(
            label="Preset",
            value=_PRESETS[0][0],
            on_change=self._on_preset_changed,
            text_size=13,
            color=ft.Colors.GREY_100,
            bgcolor=ft.Colors.GREY_900,
            border_color=ft.Colors.GREY_700,
            focused_border_color=ft.Colors.INDIGO_400,
            label_style=ft.TextStyle(color=ft.Colors.GREY_400),
            options=[
                self._preset_option(label)
                for label, _ in _PRESETS
            ] + [self._preset_option(_CUSTOM_LABEL)],
        )

        self._pattern_field = ft.TextField(
            label="Rename pattern",
            value=_DEFAULT_PATTERN,
            on_change=self._on_pattern_changed,
            text_size=13,
            color=ft.Colors.GREY_100,
            bgcolor=ft.Colors.GREY_900,
            border_color=ft.Colors.GREY_700,
            focused_border_color=ft.Colors.INDIGO_400,
            cursor_color=ft.Colors.BLUE_300,
            label_style=ft.TextStyle(color=ft.Colors.GREY_400),
            hint_style=ft.TextStyle(color=ft.Colors.GREY_600),
            helper_style=ft.TextStyle(color=ft.Colors.GREY_500),
            hint_text="YYYY/MM/YYYY-MM-DD_HH-mm-ss",
            helper_text=(
                "Tokens: YYYY YY MM MMM MMMM DD HH hh mm ss  •  "
                "{name} = original name, {loc} = place  •  / = subfolder"
            ),
        )

        self._preview_text = ft.Text(
            "",
            size=13,
            color=ft.Colors.INDIGO_200,
            selectable=True,
        )

        self._rename_button = ft.ElevatedButton(
            text="Rename all",
            disabled=True,
            on_click=self._on_rename_clicked,
            height=44,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.INDIGO_500,
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
        )

        self._undo_button = ft.ElevatedButton(
            text="Undo last rename",
            disabled=True,
            on_click=self._on_undo_clicked,
            height=44,
            style=ft.ButtonStyle(
                color=ft.Colors.AMBER_200,
                bgcolor=ft.Colors.AMBER_900,
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

    def _preset_option(self, label: str) -> ft.dropdown.Option:
        return ft.dropdown.Option(
            key=label,
            content=ft.Text(
                label,
                size=13,
                color=ft.Colors.GREY_100,
            ),
            style=ft.ButtonStyle(color=ft.Colors.GREY_100),
        )

    # ==================================================================
    # BUILD
    # ==================================================================

    def build(self) -> ft.Control:
        self._update_preview()

        return ft.Container(
            padding=ft.padding.only(
                left=28,
                right=28,
                top=24,
                bottom=24,
            ),
            expand=True,
            content=ft.Column(
                spacing=18,
                expand=True,
                controls=[
                    ft.Text(
                        "Rename & sort by date",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREY_100,
                    ),

                    ft.Text(
                        "Rename photos & videos by their capture date and "
                        "move them into dated folders (e.g. 2024/10).",
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

                    self._preset_dropdown,
                    self._pattern_field,

                    ft.Container(
                        padding=ft.padding.symmetric(
                            horizontal=14,
                            vertical=10,
                        ),
                        bgcolor=ft.Colors.GREY_900,
                        border=ft.border.all(1, ft.Colors.GREY_800),
                        border_radius=10,
                        content=self._preview_text,
                    ),

                    ft.Row(
                        spacing=10,
                        controls=[
                            self._rename_button,
                            self._undo_button,
                            self._cancel_button,
                        ],
                    ),

                    ft.Container(
                        height=1,
                        bgcolor=ft.Colors.GREY_800,
                    ),

                    ft.Row(
                        controls=[
                            ft.Text(
                                "Logs",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.GREY_200,
                            ),
                            ft.Container(expand=True),
                            ft.Text(
                                "Diagnostics",
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

    # ==================================================================
    # PATTERN
    # ==================================================================

    def _on_preset_changed(self, _: ft.ControlEvent) -> None:
        label = self._preset_dropdown.value

        for preset_label, pattern in _PRESETS:
            if preset_label == label:
                self._pattern_field.value = pattern
                break

        self._update_preview()
        self._update_buttons()

    def _on_pattern_changed(self, _: ft.ControlEvent) -> None:
        self._sync_preset_dropdown()
        self._update_preview()
        self._update_buttons()

    def _sync_preset_dropdown(self) -> None:
        pattern = self._pattern_field.value or ""

        matched = next(
            (
                label
                for label, preset_pattern in _PRESETS
                if preset_pattern == pattern
            ),
            _CUSTOM_LABEL,
        )

        if self._preset_dropdown.value != matched:
            self._preset_dropdown.value = matched

    def _update_preview(self) -> None:
        pattern = (self._pattern_field.value or "").strip()

        if not pattern:
            self._preview_text.value = "Example:  —"
        else:
            try:
                relative = self._builder.build(
                    pattern=pattern,
                    date=_SAMPLE_DATE,
                    original_stem=_SAMPLE_STEM,
                    extension=_SAMPLE_EXT,
                    place=_SAMPLE_PLACE,
                )
                self._preview_text.value = f"Example:  {relative}"
            except Exception as error:
                self._preview_text.value = f"Invalid pattern: {error}"

        self._page.update()

    # ==================================================================
    # RENAME
    # ==================================================================

    def _on_rename_clicked(self, _: ft.ControlEvent) -> None:
        self._cancel_requested = False
        self._set_running(True)

        self._page.run_task(self._run_rename)

    async def _run_rename(self) -> None:
        try:
            service = RenamerService(
                input_folder=self._input_folder,
                pattern=self._pattern_field.value,
                log=self._add_log,
                cancel_check=lambda: self._cancel_requested,
            )

            operations = await service.run()

            if operations:
                self._last_operations = operations

        except Exception as error:
            self._add_log(f"ERROR: {error}")

        finally:
            self._set_running(False)

    # ==================================================================
    # UNDO
    # ==================================================================

    def _on_undo_clicked(self, _: ft.ControlEvent) -> None:
        self._cancel_requested = False
        self._set_running(True)

        self._page.run_task(self._run_undo)

    async def _run_undo(self) -> None:
        try:
            await undo_operations(
                self._last_operations,
                log=self._add_log,
                cancel_check=lambda: self._cancel_requested,
            )

            self._last_operations = []

        except Exception as error:
            self._add_log(f"ERROR: {error}")

        finally:
            self._set_running(False)

    def _on_cancel_clicked(self, _: ft.ControlEvent) -> None:
        self._cancel_requested = True

        self._add_log("Cancellation requested...")

    # ==================================================================
    # LOGGING
    # ==================================================================

    def _add_log(self, message: str) -> None:
        print(message)

        self._log_field.value += message + "\n"

        self._log_field.cursor_position = len(self._log_field.value)

        self._page.update()

    # ==================================================================
    # STATE
    # ==================================================================

    def _set_running(self, running: bool) -> None:
        self._running = running
        self._update_buttons()

    def _update_buttons(self) -> None:
        ready = bool(
            self._input_folder
            and (self._pattern_field.value or "").strip()
        )

        self._rename_button.disabled = self._running or not ready
        self._undo_button.disabled = (
            self._running or not self._last_operations
        )
        self._cancel_button.disabled = not self._running
        self._select_input_button.disabled = self._running

        self._page.update()
