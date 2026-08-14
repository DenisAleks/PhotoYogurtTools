from typing import Optional

import flet as ft

from photorec.shared.file_picker import select_folder
from photorec.shared.folder_card import (
    create_folder_card,
)
from photorec.features.recovery.service import (
    PhotoRecoveryService,
)


class PhotoRecoveryTab:
    def __init__(
            self,
            page: ft.Page,
    ) -> None:
        self._page = page

        self._cancel_requested = False

        self._original_folder: Optional[str] = None
        self._recovered_folder: Optional[str] = None
        self._output_folder: Optional[str] = None

        self._create_controls()

    # ==================================================================
    # CONTROLS
    # ==================================================================

    def _create_controls(self) -> None:
        self._original_text = ft.Text(
            "Original: -",
            size=13,
            color=ft.Colors.GREY_400,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        self._recovered_text = ft.Text(
            "Recovered: -",
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

        self._move_files_switch = ft.Switch(
            value=False,
            active_color=ft.Colors.INDIGO_400,
        )

        self._cancel_button = ft.ElevatedButton(
            text="Cancel",
            disabled=True,
            on_click=self._on_cancel_clicked,
            height=44,
            style=ft.ButtonStyle(
                color=ft.Colors.RED_200,
                bgcolor=ft.Colors.RED_900,
                shape=ft.RoundedRectangleBorder(
                    radius=10,
                ),
            ),
        )

        self._analyze_button = ft.ElevatedButton(
            text="Process files",
            disabled=True,
            on_click=self._on_analyze_clicked,
            height=44,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.INDIGO_500,
                shape=ft.RoundedRectangleBorder(
                    radius=10,
                ),
            ),
        )

        self._select_original_button = (
            self._create_select_button(
                "Select ORIGINAL folder",
                ft.Colors.BLUE_200,
                ft.Colors.BLUE_900,
                self._on_select_original_clicked,
            )
        )

        self._select_recovered_button = (
            self._create_select_button(
                "Select RECOVERED folder",
                ft.Colors.PURPLE_200,
                ft.Colors.PURPLE_900,
                self._on_select_recovered_clicked,
            )
        )

        self._select_output_button = (
            self._create_select_button(
                "Select OUTPUT folder",
                ft.Colors.GREEN_200,
                ft.Colors.GREEN_900,
                self._on_select_output_clicked,
            )
        )

    def _create_select_button(
            self,
            text: str,
            color: str,
            background: str,
            on_click,
    ) -> ft.Control:
        return ft.ElevatedButton(
            text=text,
            on_click=on_click,
            height=40,
            style=ft.ButtonStyle(
                color=color,
                bgcolor=background,
                shape=ft.RoundedRectangleBorder(
                    radius=9,
                ),
            ),
        )

    # ==================================================================
    # BUILD
    # ==================================================================

    def build(self) -> ft.Control:
        self._add_log(
            "Application started."
        )

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
                        "Select folders",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREY_100,
                    ),

                    ft.Text(
                        "Choose the folders used during the recovery process.",
                        size=13,
                        color=ft.Colors.GREY_500,
                    ),

                    ft.Row(
                        spacing=14,
                        controls=[
                            create_folder_card(
                                title="ORIGINAL",
                                icon=ft.Icons.FOLDER_SPECIAL_OUTLINED,
                                icon_color=ft.Colors.BLUE_300,
                                icon_background=ft.Colors.BLUE_900,
                                text_control=self._original_text,
                                button=self._select_original_button,
                            ),

                            create_folder_card(
                                title="RECOVERED",
                                icon=ft.Icons.FOLDER_COPY_OUTLINED,
                                icon_color=ft.Colors.PURPLE_300,
                                icon_background=ft.Colors.PURPLE_900,
                                text_control=self._recovered_text,
                                button=self._select_recovered_button,
                            ),
                        ],
                    ),

                    create_folder_card(
                        title="OUTPUT",
                        icon=ft.Icons.FOLDER_OUTLINED,
                        icon_color=ft.Colors.GREEN_300,
                        icon_background=ft.Colors.GREEN_900,
                        text_control=self._output_text,
                        button=self._select_output_button,
                    ),

                    ft.Row(
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            self._move_files_switch,
                            ft.Column(
                                spacing=1,
                                controls=[
                                    ft.Text(
                                        "Move files instead of copying",
                                        size=13,
                                        color=ft.Colors.GREY_200,
                                    ),
                                    ft.Text(
                                        "When on, matched files are removed from "
                                        "the recovered folder. Off = safe copy.",
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
                            self._analyze_button,
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
                            ft.Container(
                                expand=True,
                            ),
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
                        border=ft.border.all(
                            1,
                            ft.Colors.GREY_800,
                        ),
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

    def _on_select_original_clicked(
            self,
            _: ft.ControlEvent,
    ) -> None:
        folder = select_folder()

        if folder is None:
            return

        self._original_folder = folder
        self._original_text.value = folder

        self._add_log(
            f"Original folder: {folder}"
        )

        self._update_state()

    def _on_select_recovered_clicked(
            self,
            _: ft.ControlEvent,
    ) -> None:
        folder = select_folder()

        if folder is None:
            return

        self._recovered_folder = folder
        self._recovered_text.value = folder

        self._add_log(
            f"Recovered folder: {folder}"
        )

        self._update_state()

    def _on_select_output_clicked(
            self,
            _: ft.ControlEvent,
    ) -> None:
        folder = select_folder()

        if folder is None:
            return

        self._output_folder = folder
        self._output_text.value = folder

        self._add_log(
            f"Output folder: {folder}"
        )

        self._update_state()

    # ==================================================================
    # ANALYSIS
    # ==================================================================

    def _on_analyze_clicked(self, _: ft.ControlEvent, ) -> None:
        self._cancel_requested = False

        self._analyze_button.disabled = True
        self._cancel_button.disabled = False
        self._move_files_switch.disabled = True

        self._page.update()

        self._page.run_task(
            self._run_analysis
        )

    def _on_cancel_clicked(
            self,
            _: ft.ControlEvent,
    ) -> None:
        self._cancel_requested = True

        self._add_log(
            "Cancellation requested..."
        )

    async def _run_analysis(self) -> None:
        try:
            service = PhotoRecoveryService(
                original_folder=self._original_folder,
                recovered_folder=self._recovered_folder,
                output_folder=self._output_folder,
                move_files=self._move_files_switch.value,
                log=self._add_log,
                cancel_check=lambda: self._cancel_requested,
            )

            await service.run()

        except Exception as e:
            self._add_log(
                f"ERROR: {e}"
            )

        finally:
            self._analyze_button.disabled = False
            self._cancel_button.disabled = True
            self._move_files_switch.disabled = False

            self._page.update()

    # ==================================================================
    # LOGGING
    # ==================================================================

    def _add_log(
            self,
            message: str,
    ) -> None:
        print(message)

        self._log_field.value += (
                message + "\n"
        )

        self._log_field.cursor_position = (
            len(self._log_field.value)
        )

        self._page.update()

    # ==================================================================
    # STATE
    # ==================================================================

    def _update_state(self) -> None:
        self._analyze_button.disabled = not (
                self._original_folder
                and self._recovered_folder
                and self._output_folder
        )

        self._page.update()
