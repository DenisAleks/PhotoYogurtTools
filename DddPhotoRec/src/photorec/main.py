import flet as ft
from photorec.ui.main_window import MainWindow


def main(page: ft.Page) -> None:
    window = MainWindow(page)
    window.build()


# Flet start the application, and when the window is created, call main().
ft.app(target=main, view=ft.AppView.FLET_APP)





