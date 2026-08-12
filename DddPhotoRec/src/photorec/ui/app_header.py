import flet as ft


def create_app_header() -> ft.Control:
    return ft.Container(
        padding=ft.padding.only(
            left=28,
            right=28,
            top=24,
            bottom=20,
        ),
        bgcolor=ft.Colors.GREY_900,
        content=ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=48,
                    height=48,
                    border_radius=14,
                    bgcolor=ft.Colors.INDIGO_900,
                    alignment=ft.alignment.center,
                    content=ft.Icon(
                        ft.Icons.PHOTO_LIBRARY_ROUNDED,
                        size=26,
                        color=ft.Colors.INDIGO_200,
                    ),
                ),

                ft.Container(width=16),

                ft.Column(
                    spacing=2,
                    expand=True,
                    controls=[
                        ft.Text(
                            "Photo Recovery Toolkit",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.GREY_100,
                        ),
                        ft.Text(
                            "Recover, organize and clean your photo library",
                            size=13,
                            color=ft.Colors.GREY_500,
                        ),
                    ],
                ),
            ],
        ),
    )