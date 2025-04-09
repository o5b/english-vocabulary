import flet as ft


class PaginatedDataTable(ft.DataTable):
    def __init__(
        self,
        rows=None,
        rows_per_page=20,
        border=None,
        border_radius=None,
        width=None,
        height=None,
        **kwargs
    ):
        # Инициализируем родительский класс DataTable
        super().__init__(
            rows=rows if rows else [],
            border=border,
            border_radius=border_radius,
            width=width,
            height=height,
            **kwargs
        )

        # Параметры пагинации
        self.all_rows = rows if rows else []
        self.rows_per_page = rows_per_page
        self.current_page = 1

        # Выпадающий список для выбора количества строк на странице
        self.rows_per_page_dropdown = ft.Dropdown(
            width=100,
            options=[
                # ft.dropdown.Option("5", "5"),
                ft.dropdown.Option("10", "10"),
                ft.dropdown.Option("20", "20"),
                ft.dropdown.Option("50", "50"),
                ft.dropdown.Option("100", "100"),
            ],
            value=str(rows_per_page),
            on_change=self.on_rows_per_page_change
        )

        # Поле ввода для номера страницы
        self.page_input = ft.TextField(
            width=50,
            height=40,
            text_align=ft.TextAlign.CENTER,
            value=str(self.current_page),
            on_submit=self.on_page_input_submit,
            keyboard_type=ft.KeyboardType.NUMBER
        )

        # Контейнер для кнопок пагинации
        self.pagination_controls = ft.Row(
            controls=[],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10
        )

        # Основной контейнер
        self.container = ft.Column(
            controls=[
                self,
                self.pagination_controls
            ]
        )

        # Обновляем пагинацию при инициализации
        self.update_pagination()

    def update_pagination(self):
        """Обновляет отображаемые строки и элементы управления пагинацией"""
        # Вычисляем общее количество страниц
        total_pages = max(1, (len(self.all_rows) + self.rows_per_page - 1) // self.rows_per_page)

        # Корректируем текущую страницу
        if self.current_page > total_pages:
            self.current_page = total_pages
        if self.current_page < 1:
            self.current_page = 1

        # Обновляем значение поля ввода
        self.page_input.value = str(self.current_page)

        # Вычисляем индексы для текущей страницы
        start_idx = (self.current_page - 1) * self.rows_per_page
        end_idx = start_idx + self.rows_per_page

        # Обновляем строки таблицы
        self.rows = self.all_rows[start_idx:end_idx]

        # Очищаем и обновляем элементы пагинации
        self.pagination_controls.controls.clear()

        # Добавляем элементы управления
        self.pagination_controls.controls.extend([
            ft.Row([
                # ft.Text("Строк:"),
                self.rows_per_page_dropdown
            ]),
            ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                disabled=self.current_page == 1,
                on_click=lambda e: self.change_page(self.current_page - 1)
            ),
            ft.Row([
                # ft.Text("Страница"),
                self.page_input,
                ft.Text(f"из {total_pages}")
            ]),
            ft.IconButton(
                icon=ft.Icons.ARROW_FORWARD,
                disabled=self.current_page == total_pages,
                on_click=lambda e: self.change_page(self.current_page + 1)
            )
        ])

        # Обновляем страницу
        if self.page:
            self.page.update()

    def change_page(self, new_page):
        """Переключает на указанную страницу"""
        self.current_page = new_page
        self.update_pagination()

    def on_rows_per_page_change(self, e):
        """Обработчик изменения количества строк на странице"""
        self.rows_per_page = int(self.rows_per_page_dropdown.value)
        self.current_page = 1  # Сбрасываем на первую страницу
        self.update_pagination()

    def on_page_input_submit(self, e):
        """Обработчик ввода номера страницы"""
        try:
            new_page = int(self.page_input.value)
            total_pages = max(1, (len(self.all_rows) + self.rows_per_page - 1) // self.rows_per_page)
            if 1 <= new_page <= total_pages:
                self.current_page = new_page
            else:
                self.page_input.value = str(self.current_page)  # Возвращаем старое значение
        except ValueError:
            self.page_input.value = str(self.current_page)  # Возвращаем старое значение
        self.update_pagination()

    def set_rows(self, rows):
        """Устанавливает новые строки и обновляет пагинацию"""
        self.all_rows = rows
        self.update_pagination()

    def did_mount(self):
        """Вызывается после монтирования компонента"""
        self.update_pagination()
