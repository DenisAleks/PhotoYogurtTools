import flet as ft

from photorec.shell.app_header import create_app_header
from photorec.shell.app_tabs import create_app_tabs


class MainWindow:
    def __init__(self, page: ft.Page) -> None:
        self._page = page

    def build(self) -> None:
        self._configure_page()

        self._page.add(
            ft.Column(
                spacing=0,
                expand=True,
                controls=[
                    create_app_header(),
                    create_app_tabs(self._page),
                ],
            )
        )

    def _configure_page(self) -> None:
        self._page.title = "Photo Recovery Toolkit"

        self._page.window.width = 1240
        self._page.window.height = 960
        self._page.window.min_width = 950
        self._page.window.min_height = 720

        self._page.padding = 0

        self._page.bgcolor = ft.Colors.GREY_900

        self._page.theme = ft.Theme(
            font_family="Inter",
            color_scheme=ft.ColorScheme(
                primary=ft.Colors.INDIGO_400,
                secondary=ft.Colors.PURPLE_400,
            ),
        )