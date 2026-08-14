import flet as ft


def create_future_tab(
    title: str,
    description: str,
) -> ft.Control:
    return ft.Container(
        alignment=ft.alignment.center,
        expand=True,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12,
            controls=[
                ft.Container(
                    width=64,
                    height=64,
                    border_radius=18,
                    bgcolor=ft.Colors.GREY_900,
                    alignment=ft.alignment.center,
                    content=ft.Icon(
                        ft.Icons.CONSTRUCTION_OUTLINED,
                        size=30,
                        color=ft.Colors.GREY_600,
                    ),
                ),

                ft.Text(
                    title,
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.GREY_300,
                ),

                ft.Container(
                    width=500,
                    content=ft.Text(
                        description,
                        size=13,
                        text_align=ft.TextAlign.CENTER,
                        color=ft.Colors.GREY_600,
                    ),
                ),
            ],
        ),
    )