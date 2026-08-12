import flet as ft


def create_folder_card(
    title: str,
    icon: str,
    icon_color: str,
    icon_background: str,
    text_control: ft.Control,
    button: ft.Control,
) -> ft.Control:
    return ft.Container(
        padding=16,
        border_radius=14,
        bgcolor=ft.Colors.GREY_900,
        border=ft.border.all(
            1,
            ft.Colors.GREY_800,
        ),
        expand=True,
        content=ft.Row(
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=42,
                    height=42,
                    border_radius=11,
                    bgcolor=icon_background,
                    alignment=ft.alignment.center,
                    content=ft.Icon(
                        icon,
                        size=22,
                        color=icon_color,
                    ),
                ),

                ft.Column(
                    spacing=5,
                    expand=True,
                    controls=[
                        ft.Text(
                            title,
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.GREY_500,
                        ),
                        text_control,
                    ],
                ),

                button,
            ],
        ),
    )