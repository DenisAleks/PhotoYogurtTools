from typing import List, Optional

import flet as ft

from photorec.features.duplicates.models import DuplicateGroup
from photorec.features.duplicates.service import DuplicatesService
from photorec.shared.file_picker import select_folder
from photorec.shared.folder_card import create_folder_card
from photorec.shared.rename_ops import RenameOperation, undo_operations


class DuplicatesTab:
    def __init__(self, page: ft.Page) -> None:
        self._page = page

        self._cancel_requested = False
        self._running = False

        self._input_folder: Optional[str] = None

        self._groups: List[DuplicateGroup] = []
        self._applied = False
        self._last_operations: List[RenameOperation] = []

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

        self._scan_button = ft.ElevatedButton(
            text="Scan for duplicates",
            disabled=True,
            on_click=self._on_scan_clicked,
            height=44,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.INDIGO_500,
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
        )

        self._rename_button = ft.ElevatedButton(
            text="Rename duplicates",
            disabled=True,
            on_click=self._on_rename_clicked,
            height=44,
            style=ft.ButtonStyle(
                color=ft.Colors.ORANGE_200,
                bgcolor=ft.Colors.ORANGE_900,
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
        )

        self._undo_button = ft.ElevatedButton(
            text="Undo",
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

    # ==================================================================
    # BUILD
    # ==================================================================

    def build(self) -> ft.Control:
        return ft.Container(
            padding=ft.padding.only(
                left=28,
                right=28,
                top=24,
                bottom=24,
            ),
            expand=True,
            content=ft.Column(
                spacing=16,
                expand=True,
                controls=[
                    ft.Text(
                        "Find duplicates",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREY_100,
                    ),

                    ft.Text(
                        "Find byte-identical files in a folder and its "
                        "subfolders. Scan is read-only; Rename flags copies in "
                        "place with a _dup_ suffix — nothing is ever deleted.",
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
                        spacing=10,
                        controls=[
                            self._scan_button,
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
                                "Duplicates log",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.GREY_200,
                            ),
                            ft.Container(expand=True),
                            ft.Text(
                                "A full .md report is saved in the input folder",
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

        # A new folder invalidates any previous scan results.
        self._groups = []
        self._applied = False
        self._last_operations = []

        self._add_log(f"Input folder: {folder}")

        self._update_buttons()

    # ==================================================================
    # SCAN
    # ==================================================================

    def _on_scan_clicked(self, _: ft.ControlEvent) -> None:
        self._cancel_requested = False
        self._set_running(True)

        self._page.run_task(self._run_scan)

    async def _run_scan(self) -> None:
        try:
            service = DuplicatesService(
                input_folder=self._input_folder,
                log=self._add_log,
                cancel_check=lambda: self._cancel_requested,
            )

            groups, _report = await service.scan()

            self._groups = groups
            self._applied = False
            self._last_operations = []

        except Exception as error:
            self._add_log(f"ERROR: {error}")

        finally:
            self._set_running(False)

    # ==================================================================
    # RENAME
    # ==================================================================

    def _on_rename_clicked(self, _: ft.ControlEvent) -> None:
        self._cancel_requested = False
        self._set_running(True)

        self._page.run_task(self._run_rename)

    async def _run_rename(self) -> None:
        try:
            service = DuplicatesService(
                input_folder=self._input_folder,
                log=self._add_log,
                cancel_check=lambda: self._cancel_requested,
            )

            operations = await service.rename(self._groups)

            if operations:
                self._last_operations = operations
                self._applied = True

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

            # Files are back to their original names - renaming is available again.
            self._last_operations = []
            self._applied = False

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
        ready = bool(self._input_folder)

        self._scan_button.disabled = self._running or not ready
        self._rename_button.disabled = (
            self._running or self._applied or not self._groups
        )
        self._undo_button.disabled = (
            self._running or not self._last_operations
        )
        self._cancel_button.disabled = not self._running
        self._select_input_button.disabled = self._running

        self._page.update()
