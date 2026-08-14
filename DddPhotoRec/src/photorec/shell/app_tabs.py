import flet as ft

from photorec.shared.future_tab import create_future_tab
from photorec.features.recovery.recovery_tab import (
    PhotoRecoveryTab,
)
from photorec.features.renamer.renamer_tab import (
    RenamerTab,
)


def create_app_tabs(page: ft.Page) -> ft.Control:
    recovery_tab = PhotoRecoveryTab(page)
    renamer_tab = RenamerTab(page)

    return ft.Tabs(
        selected_index=0,
        animation_duration=200,
        expand=True,
        divider_color=ft.Colors.GREY_800,
        indicator_color=ft.Colors.INDIGO_400,
        label_color=ft.Colors.INDIGO_200,
        unselected_label_color=ft.Colors.GREY_500,
        tabs=[
            ft.Tab(
                text="Photo Recovery",
                icon=ft.Icons.PHOTO_LIBRARY_OUTLINED,
                content=recovery_tab.build(),
            ),

            ft.Tab(
                text="Photo & Video Renamer",
                icon=ft.Icons.DRIVE_FILE_RENAME_OUTLINE,
                content=renamer_tab.build(),
            ),

            ft.Tab(
                text="Duplicates Finder",
                icon=ft.Icons.CONTENT_COPY_OUTLINED,
                content=create_future_tab(
                    "Duplicates Finder",
                    "This tool will find duplicate files inside your photo folders.",
                ),
            ),
        ],
    )