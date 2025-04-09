import time
import threading
from datetime import datetime
import pprint
import random

import flet as ft
from flet_audio import Audio

from learning_words import WORDS
from colors import COLORS
from paginated_datatable import PaginatedDataTable
from logger_config import logger
from utils import compress_bool_list_to_hex, decompress_bool_list_from_hex
from storage import StorageManager


class WordTrainer:
    def __init__(self, page):
        self.page = page
        self.storage = StorageManager(page)
        self.initialize_state()
        self.setup_ui()

    def initialize_state(self):
        """Инициализация состояния приложения."""
        self.page.scroll = ft.ScrollMode.AUTO
        self.page.title = "Изучение английских слов"
        self.page.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        self.words = WORDS
        self.colors = COLORS
        self.is_running = False
        self.session_duration_sec = 0
        self.session_duration_min = 0

        # Инициализация переменных состояния
        self.current_word_index = self.storage.get("current_word_index", default=0)
        self.delay = self.storage.get("delay", default=1)
        self.order_learning_words = self.storage.get("order_learning_words", default="1")
        self.is_transcription = self.storage.get("is_transcription", default=True)
        self.english_color = self.storage.get("english_color", default=ft.Colors.BLACK.value)
        self.transcription_color = self.storage.get("transcription_color", default=ft.Colors.BLACK.value)
        self.russian_color = self.storage.get("russian_color", default=ft.Colors.BLACK.value)

        # Инициализация списков слов
        if not self.storage.contains_key("word_lists"):
            self.storage.set("word_lists", {"default": compress_bool_list_to_hex([False] * len(self.words))})
        self.word_lists = self.storage.get("word_lists")
        self.current_list_name = list(self.word_lists.keys())[0] if self.word_lists else "default"
        self.selected_words_bool = decompress_bool_list_from_hex(self.word_lists[self.current_list_name], len(self.words))

        # Инициализация статистики
        self.monthly_statistics = {}
        raw_monthly_statistics = {}
        for key in self.storage.get_keys(datetime.now().strftime('statistics.%Y-%m')):
            raw_monthly_statistics[key] = self.storage.get(key)

        # Сортировка статистики по дням
        self.monthly_statistics = dict(sorted(raw_monthly_statistics.items(), key=lambda item: int(item[0].split('-')[-1])))

    def setup_ui(self):
        """Настройка пользовательского интерфейса."""
        self.duration_time = ft.Text(value="", size=20, text_align=ft.TextAlign.CENTER)
        self.index_display = ft.Text(value="", size=30, text_align=ft.TextAlign.START)
        self.first_row_word_display = ft.Text(value="", size=30, text_align=ft.TextAlign.START)
        self.first_row_transcription_word_display = ft.Text(value="", size=30, text_align=ft.TextAlign.END)
        self.second_row_word_display = ft.Text(value="", size=30, text_align=ft.TextAlign.START)
        self.second_row_transcription_word_display = ft.Text(value="", size=30, text_align=ft.TextAlign.END)

        self.start_button = ft.ElevatedButton(text="Старт", on_click=self.start_button_click)
        self.stop_button = ft.ElevatedButton(text="Пауза", on_click=self.stop_button_click, disabled=True)

        self.delay_control = ft.Slider(min=1, max=10, value=self.delay, divisions=9, label="Ускорение {value}", on_change=self.set_delay)
        self.theme_control = ft.Switch(label="Тема (Светлая/Тёмная)", on_change=self.theme_changed)
        self.current_word_index_control = ft.Slider(
            min=0,
            max=1000,
            value=self.current_word_index,
            divisions=100,
            label="{value}",
            on_change=self.set_current_word_index,
        )
        self.storage_current_word_index_button = ft.ElevatedButton(text="Сохранить текущую позицию", on_click=self.storage_current_word_index_click)
        self.learning_words_radiogroup = ft.RadioGroup(
            content=ft.Column(
                [
                    ft.Radio(value="1", label="Англ - транскрипция - задержка - рус"),
                    ft.Radio(value="2", label="Рус - задержка - транскрипция - англ"),
                ]
            ),
            on_change=self.learning_words_radiogroup_changed,
        )
        self.learning_words_radiogroup.value = self.order_learning_words
        self.transcription_control = ft.Checkbox(label='Отображать транскрипцию', value=self.is_transcription, on_change=self.transcription_changed)

        # Поле ввода названия списка
        self.list_name_input = ft.TextField(label="Название списка", width=200, value="")

        # Выпадающий список из сохраненных списков слов
        self.list_selector = ft.Dropdown(
            width=200,
            options=[ft.dropdown.Option(name) for name in self.word_lists.keys()],
            value=self.current_list_name,
            on_change=lambda e: self.load_selected_list(e.control.value),
        )

        # Выпадающие списки для года и месяца
        self.year_dropdown = self.create_year_dropdown()
        self.month_dropdown = self.create_month_dropdown()

        # Инициализация таблицы с пагинацией
        self.paginated_table = PaginatedDataTable(
            width=700,
            border=ft.border.all(2, "red"),
            border_radius=10,
            vertical_lines=ft.BorderSide(3, "blue"),
            horizontal_lines=ft.BorderSide(1, "green"),
            sort_column_index=0,
            sort_ascending=True,
            heading_row_color=ft.Colors.BLACK12,
            heading_row_height=100,
            data_row_color={ft.ControlState.HOVERED: "0x30FF0000"},
            show_checkbox_column=True,
            divider_thickness=0,
            column_spacing=20,
            columns=[
                ft.DataColumn(ft.Text("Номер"), numeric=True),
                ft.DataColumn(ft.Text("Слово")),
            ],
            rows_per_page=50,
            rows=self.create_table_rows(),
        )

        # Инициализация страниц
        self.setup_pages()

    def setup_pages(self):
        """Настройка страниц приложения."""
        self.home_page = self.create_home_page()
        self.training_page = self.create_training_page()
        self.dictionary_page = self.create_dictionary_page()
        self.statistic_page = self.create_statistic_page()
        self.settings_page = self.create_settings_page()
        self.dev_storage_page = self.create_dev_storage_page()

        self.page.on_route_change = self.route_change
        self.page.on_view_pop = self.view_pop
        self.page.go(self.page.route)
        self.page.update()

    def load_selected_list(self, list_name):
        """Загрузка выбранного списка слов."""
        self.current_list_name = list_name
        self.selected_words_bool = decompress_bool_list_from_hex(self.word_lists[list_name], len(self.words))
        self.paginated_table.set_rows(self.create_table_rows())
        self.list_name_input.value = '' if list_name == 'default' else list_name
        self.update_list_selector()
        self.page.update()

    def update_list_selector(self):
        """Обновление выпадающего списка списков слов."""
        self.list_selector.options = [ft.dropdown.Option(name) for name in self.word_lists.keys()]
        self.list_selector.value = self.current_list_name
        self.page.update()

    def save_datatable_button_click(self, e):
        """Сохранение изменений в таблице."""
        if not self.list_name_input.value.strip():
            self.page.open(ft.AlertDialog(title=ft.Text("Введите название списка!")))
            return

        list_name = self.list_name_input.value.strip()
        self.word_lists[list_name] = compress_bool_list_to_hex(self.selected_words_bool)
        self.current_list_name = list_name
        self.storage.set('word_lists', self.word_lists)
        self.update_list_selector()
        self.list_name_input.value = ""
        self.page.open(ft.AlertDialog(title=ft.Text("Список успешно сохранен!")))
        self.page.update()

    def delete_list_button_click(self, e):
        """Удаление текущего списка слов."""
        if len(self.word_lists) <= 1:
            self.page.open(ft.AlertDialog(title=ft.Text("Нельзя удалить последний список!")))
            return
        elif self.current_list_name == 'default':
            self.page.open(ft.AlertDialog(title=ft.Text("Нельзя удалить этот список!")))
            return

        deleted_list_name = self.current_list_name
        del self.word_lists[self.current_list_name]
        self.current_list_name = list(self.word_lists.keys())[0]
        self.storage.set('word_lists', self.word_lists)
        self.load_selected_list(self.current_list_name)
        self.page.open(ft.AlertDialog(title=ft.Text(f"Список {deleted_list_name} удален!")))

    def create_home_page(self):
        """Создание главной страницы."""
        return ft.View(
            route="/",
            appbar=ft.AppBar(bgcolor="teal", color="white", title=ft.Text("Главная")),
            navigation_bar=self.create_navbar(),
            drawer=self.create_drawer(),
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Image(src="homeimage_200x200.png", width=self.page.width, height=200, fit=ft.ImageFit.FILL),
                ft.Text('Выберите раздел:', size=30, font_family="Georgia", weight=ft.FontWeight.BOLD),
                self.create_button_group(),
            ]
        )

    def create_training_page(self):
        """Создание страницы тренировки."""
        return ft.View(
            route="training-page",
            appbar=ft.AppBar(
                title=ft.Text("Изучение слов"),
                color="white",
                bgcolor="#1da1f2",
                leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=self.view_pop),
            ),
            navigation_bar=self.create_navbar(),
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Row([self.duration_time], alignment=ft.MainAxisAlignment.END),
                ft.Row([self.list_selector], alignment=ft.MainAxisAlignment.START),
                ft.Row([self.index_display], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([self.first_row_word_display, self.first_row_transcription_word_display], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([self.second_row_word_display, self.second_row_transcription_word_display], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([self.start_button, self.stop_button], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row(),
                ft.Row([self.storage_current_word_index_button], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row(),
                ft.Row([ft.ElevatedButton(text="Повторить", on_click=self.repeat_current_word_index)], alignment=ft.MainAxisAlignment.CENTER),
            ]
        )

    def create_dictionary_page(self):
        """Создание страницы словаря."""
        return ft.View(
            route="dictionary-page",
            appbar=ft.AppBar(
                title=ft.Text("Словарь"),
                color="white",
                bgcolor="cyan",
                leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=self.view_pop),
            ),
            navigation_bar=self.create_navbar(),
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Text('Редактирование списка изучаемых слов', size=30, font_family="Georgia", weight=ft.FontWeight.BOLD),
                ft.Row([self.list_selector, self.list_name_input]),
                ft.Row([
                    ft.ElevatedButton(text="Сохранить изменения", on_click=self.save_datatable_button_click),
                    ft.ElevatedButton(text="Удалить текущий список", on_click=self.delete_list_button_click),
                ]),
                self.create_paginated_table(),
            ]
        )

    def create_statistic_page(self):
        """Создание страницы статистики."""
        return ft.View(
            route="statistic-page",
            appbar=ft.AppBar(
                title=ft.Text("Статистика"),
                color="white",
                bgcolor="cyan",
                leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=self.view_pop),
            ),
            navigation_bar=self.create_navbar(),
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Text('Раздел для отображения статистики', size=30, font_family="Georgia", weight=ft.FontWeight.BOLD),
                ft.Row([self.year_dropdown, self.month_dropdown], alignment=ft.MainAxisAlignment.CENTER),
                self.create_chart_container(),
            ]
        )

    def create_settings_page(self):
        """Создание страницы настроек."""
        return ft.View(
            route="settings-page",
            appbar=ft.AppBar(
                title=ft.Text("Настройки"),
                color="white",
                bgcolor="cyan",
                leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=self.view_pop),
            ),
            navigation_bar=self.create_navbar(),
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Text("Скорость:"),
                self.delay_control,
                ft.Text("Номер текущего слова:"),
                self.current_word_index_control,
                self.transcription_control,
                ft.Text("Установите цвет слов:"),
                self.create_color_dropdown("Английского", self.english_color, self.english_color_dropdown_changed),
                self.create_color_dropdown("Транскрипции", self.transcription_color, self.transcription_color_dropdown_changed),
                self.create_color_dropdown("Русского", self.russian_color, self.russian_color_dropdown_changed),
                ft.Text("Выберите вариант изучения английских слов:"),
                self.learning_words_radiogroup,
            ]
        )

    def create_dev_storage_page(self):
        """Создание страницы разработчика для работы с хранилищем."""
        return ft.View(
            route="dev-storage-page",
            appbar=ft.AppBar(
                title=ft.Text("DevTools: Storage"),
                color="white",
                bgcolor="cyan",
                leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=self.view_pop),
            ),
            navigation_bar=self.create_navbar(),
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Text(value='Редактирование client_storage:', size=20),
                self.create_dev_tools_storage_list(),
            ]
        )

    def selected_navbar(self, e):
        """Обработчик выбора пункта в навигационной панели."""
        if e.control.selected_index == 0:
            pass  # Главная страница
        elif e.control.selected_index == 1:
            pass  # Страница проекта
        elif e.control.selected_index == 2:
            self.page.open(self.confirm_dialog)  # Выход
        else:
            self.page.go("/")  # Возврат на главную

    def selected_drawer(self, e):
        """Обработчик выбора пункта в боковом меню."""
        if e.control.selected_index == 0:
            self.page.go('settings-page')  # Настройки
        elif e.control.selected_index == 3:
            self.page.go('dev-storage-page')  # Раздел разработчика
        elif e.control.selected_index == 4:
            self.generate_test_statistics()  # Генерация тестовой статистики
        elif e.control.selected_index == 5:
            self.remove_test_statistics()  # Удаление тестовой статистики

    def generate_test_statistics(self):
        """Генерация тестовой статистики."""
        for year in ['2024', '2025']:
            for month in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']:
                for day in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15',
                            '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31']:
                    self.storage.set(f'statistics.{year}-{month}-{day}', random.randint(5, 120))
        self.page.open(ft.AlertDialog(title=ft.Text("Тестовая статистика успешно создана!")))

    def remove_test_statistics(self):
        """Удаление тестовой статистики."""
        for key in self.storage.get_keys('statistics.'):
            self.storage.remove(key)
        self.page.open(ft.AlertDialog(title=ft.Text("Тестовая статистика успешно удалена!")))

    def create_navbar(self):
        """Создание навигационной панели."""
        return ft.NavigationBar(
            on_change=self.selected_navbar,
            destinations=[
                ft.NavigationDrawerDestination(label="Menu", icon=ft.Icon(ft.Icons.GRID_VIEW_ROUNDED)),
                ft.NavigationDrawerDestination(label="Project", icon=ft.Icon(ft.Icons.ROCKET_LAUNCH_OUTLINED)),
                ft.NavigationDrawerDestination(label="Exit", icon=ft.Icon(ft.Icons.CANCEL)),
            ]
        )

    def create_drawer(self):
        """Создание бокового меню."""
        return ft.NavigationDrawer(
            on_change=self.selected_drawer,
            controls=[
                ft.Container(height=20),
                self.theme_control,
                ft.Divider(thickness=2),
                ft.NavigationDrawerDestination(label="Настройки", icon=ft.Icons.SETTINGS, selected_icon=ft.Icon(ft.Icons.SETTINGS_OUTLINED)),
                ft.NavigationDrawerDestination(label="Telegram", icon=ft.Icons.TELEGRAM, selected_icon=ft.Icon(ft.Icons.TELEGRAM_OUTLINED)),
                ft.NavigationDrawerDestination(label="Email", icon=ft.Icons.EMAIL, selected_icon=ft.Icon(ft.Icons.EMAIL_OUTLINED)),
                ft.Divider(thickness=2),
                ft.Text("DevTools:", size=20, text_align=ft.TextAlign.CENTER),
                ft.NavigationDrawerDestination(label="Storage", icon=ft.Icons.STORAGE, selected_icon=ft.Icon(ft.Icons.STORAGE_OUTLINED)),
                ft.NavigationDrawerDestination(label="Создать Тестовую статистики", icon=ft.Icons.DEVELOPER_MODE, selected_icon=ft.Icon(ft.Icons.DEVELOPER_MODE_OUTLINED)),
                ft.NavigationDrawerDestination(label="Удалить Тестовую статистики", icon=ft.Icons.DEVELOPER_MODE, selected_icon=ft.Icon(ft.Icons.DEVELOPER_MODE_OUTLINED)),
            ],
        )

    def create_button_group(self):
        """Создание группы кнопок для главной страницы."""
        return ft.Row(
            width=self.page.width,
            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            controls=[
                self.create_button("Тренировка", "eng_80x40.png", lambda _: self.page.go("training-page")),
                self.create_button("Словарь", "dict_80x40.png", lambda _: self.page.go("dictionary-page")),
                self.create_button("Статистика", "stat_80x40.png", lambda _: self.page.go("statistic-page")),
            ]
        )

    def create_button(self, text, image_src, on_click):
        """Создание кнопки с изображением и текстом."""
        return ft.OutlinedButton(
            height=100,
            width=100,
            content=ft.Container(
                padding=5,
                content=ft.Column(
                    controls=[
                        ft.Image(src=image_src),
                        ft.Text(text, size=12),
                    ]
                ),
            ),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            on_click=on_click,
        )

    def create_paginated_table(self):
        """Создание таблицы с пагинацией."""
        return PaginatedDataTable(
            width=700,
            border=ft.border.all(2, "red"),
            border_radius=10,
            vertical_lines=ft.BorderSide(3, "blue"),
            horizontal_lines=ft.BorderSide(1, "green"),
            sort_column_index=0,
            sort_ascending=True,
            heading_row_color=ft.Colors.BLACK12,
            heading_row_height=100,
            data_row_color={ft.ControlState.HOVERED: "0x30FF0000"},
            show_checkbox_column=True,
            divider_thickness=0,
            column_spacing=20,
            columns=[
                ft.DataColumn(ft.Text("Номер"), numeric=True),
                ft.DataColumn(ft.Text("Слово")),
            ],
            rows_per_page=50,
            rows=self.create_table_rows(),
        ).container

    def create_table_rows(self):
        """Создание строк для таблицы."""
        return [
            ft.DataRow(
                [ft.DataCell(ft.Text(f"{i+1}")), ft.DataCell(ft.Text(' '.join(w)))],
                selected=self.selected_words_bool[i],
                on_select_changed=self.data_table_on_select_changed,
            )
            for i, w in enumerate(self.words)
        ]

    def create_year_dropdown(self):
        """Создание выпадающего списка для выбора года."""
        years = sorted(set(key.split('.')[1].split('-')[0] for key in self.storage.get_keys('statistics')))
        self.year_dropdown = ft.Dropdown(
            width=150,
            options=[ft.dropdown.Option(year) for year in years],
            value=years[-1] if years else datetime.now().strftime('%Y'),
            label="Год",
            on_change=self.update_chart,
        )
        return self.year_dropdown

    def create_month_dropdown(self):
        """Создание выпадающего списка для выбора месяца."""
        months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
        self.month_dropdown = ft.Dropdown(
            width=150,
            options=[ft.dropdown.Option(month) for month in months],
            value=datetime.now().strftime('%m'),
            label="Месяц",
            on_change=self.update_chart,
        )
        return self.month_dropdown

    def update_chart(self, e=None):
        """Обновление графика статистики."""
        selected_year = self.year_dropdown.value
        selected_month = self.month_dropdown.value
        monthly_statistics = self.get_monthly_statistics(selected_year, selected_month)
        self.chart_container.content = self.create_chart(monthly_statistics)
        self.page.update()

    def create_chart_container(self):
        """Создание контейнера для графика."""
        self.chart_container = ft.Container()
        self.update_chart()
        return self.chart_container

    def create_color_dropdown(self, label, current_color, on_change):
        """Создание выпадающего списка для выбора цвета."""
        return ft.Dropdown(
            label=label,
            options=self.get_color_options(),
            value=current_color,
            on_change=on_change,
        )

    def get_color_options(self):
        """Получение списка цветов для выпадающего списка."""
        return [
            ft.dropdown.Option(
                key=color.value,
                content=ft.Text(value=color.value, color=color),
            )
            for color in self.colors
        ]

    def create_dev_tools_storage_list(self):
        """Создание списка для отображения ключей хранилища."""
        lv = ft.ListView(expand=1, spacing=10, padding=20, auto_scroll=True)
        for i, key in enumerate(self.storage.get_keys('')):
            val = self.storage.get(key)
            lv.controls.append(
                ft.Row(
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.ElevatedButton(text="Delete", on_click=self.storage_delete_button_click, data=key),
                        ft.Text(f"{i+1}. {key}: {val}", max_lines=2),
                    ]
                )
            )
        return lv

    def storage_delete_button_click(self, e):
        """Обработчик удаления ключа из хранилища."""
        try:
            self.storage.remove(e.control.data)
            self.page.open(
                ft.AlertDialog(
                    title=ft.Text(f"{e.control.data} успешно удалён!"),
                )
            )
        except Exception as er:
            logger.error(f'Error deleting data from client_storage: {er}')
            self.page.open(
                ft.AlertDialog(
                    title=ft.Text("Во время удаления произошла ошибка!"),
                )
            )
        self.page.update()

    def get_monthly_statistics(self, selected_year, selected_month):
        """Получение статистики за выбранный месяц и год."""
        raw_monthly_statistics = {}
        pattern = f'statistics.{selected_year}-{selected_month}'
        for key in self.storage.get_keys(pattern):
            raw_monthly_statistics[key] = self.storage.get(key)

        # Сортировка по дням
        return dict(sorted(raw_monthly_statistics.items(), key=lambda item: int(item[0].split('-')[-1])))

    def create_chart(self, monthly_statistics):
        """Создание графика статистики."""
        chart = ft.BarChart(
            bar_groups=[],
            border=ft.border.all(1, ft.Colors.GREY_400),
            left_axis=ft.ChartAxis(
                labels_size=40, title=ft.Text("Тренировка, минут"), title_size=40
            ),
            bottom_axis=ft.ChartAxis(
                labels=[],
                labels_size=40,
            ),
            horizontal_grid_lines=ft.ChartGridLines(
                color=ft.Colors.GREY_300, width=1, dash_pattern=[3, 3]
            ),
            tooltip_bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.GREY_300),
            max_y=120,
            interactive=True,
            expand=True,
        )

        j = 0
        for key, val in monthly_statistics.items():
            chart.bar_groups.append(
                ft.BarChartGroup(
                    x=j,
                    bar_rods=[
                        ft.BarChartRod(
                            from_y=0,
                            to_y=val,
                            width=10,
                            color=ft.Colors.RED,
                            tooltip=f'{key}, {val}мин.',
                            border_radius=0,
                        ),
                    ],
                ),
            )

            split_key = key.split('.')
            split_date = split_key[1].split('-')
            chart.bottom_axis.labels.append(
                ft.ChartAxisLabel(value=j, label=ft.Container(ft.Text(split_date[-1]), padding=5)),
            )
            j += 1

        return chart

    def start_button_click(self, e):
        """Обработчик нажатия на кнопку 'Старт'."""
        self.start_button.disabled = True
        self.stop_button.disabled = False
        self.page.update()
        threading.Thread(target=self.start_learning, daemon=True).start()

    def stop_button_click(self, e):
        """Обработчик нажатия на кнопку 'Пауза'."""
        self.is_running = False
        self.start_button.disabled = False
        self.stop_button.disabled = True
        self.page.update()

    def set_delay(self, e):
        """Установка задержки между словами."""
        self.delay = int(self.delay_control.value)
        self.storage.set('delay', self.delay)
        self.page.update()

    def theme_changed(self, e):
        """Переключение темы (светлая/тёмная)."""
        self.page.theme_mode = ft.ThemeMode.DARK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        self.storage.set("theme_mode", "DARK" if self.page.theme_mode == ft.ThemeMode.DARK else "LIGHT")
        self.page.update()

    def set_current_word_index(self, e):
        """Установка текущего индекса слова."""
        self.current_word_index = int(self.current_word_index_control.value)
        self.storage.set("current_word_index", self.current_word_index)
        self.page.update()

    def storage_current_word_index_click(self, e):
        """Сохранение текущего индекса слова в хранилище."""
        self.storage.set("current_word_index", self.current_word_index)
        self.page.update()

    def learning_words_radiogroup_changed(self, e):
        """Изменение порядка изучения слов."""
        self.order_learning_words = e.control.value
        self.storage.set("order_learning_words", e.control.value)
        self.page.update()

    def transcription_changed(self, e):
        """Переключение отображения транскрипции."""
        self.is_transcription = self.transcription_control.value
        self.storage.set("is_transcription", self.transcription_control.value)
        self.page.update()

    def english_color_dropdown_changed(self, e):
        """Изменение цвета английских слов."""
        self.english_color = e.control.value
        self.storage.set("english_color", e.control.value)
        self.page.update()

    def transcription_color_dropdown_changed(self, e):
        """Изменение цвета транскрипции."""
        self.transcription_color = e.control.value
        self.storage.set("transcription_color", e.control.value)
        self.page.update()

    def russian_color_dropdown_changed(self, e):
        """Изменение цвета русских слов."""
        self.russian_color = e.control.value
        self.storage.set("russian_color", e.control.value)
        self.page.update()

    def repeat_current_word_index(self, e):
        """Повтор текущего слова."""
        self.current_word_index -= 2
        if self.current_word_index < 0:
            self.current_word_index = 0
        self.page.update()

    def data_table_on_select_changed(self, e):
        """Обработчик изменения выбора строки в таблице."""
        idx = int(e.control.cells[0].content.value) - 1
        self.selected_words_bool[idx] = not e.control.selected
        e.control.selected = self.selected_words_bool[idx]
        self.page.update()

    def route_change(self, route):
        """Обработчик изменения маршрута."""
        self.page.views.clear()
        self.page.views.append(self.home_page)
        if self.page.route == "training-page":
            self.page.views.append(self.training_page)
        elif self.page.route == "dictionary-page":
            self.page.views.append(self.dictionary_page)
        elif self.page.route == "statistic-page":
            self.page.views.append(self.statistic_page)
        elif self.page.route == "settings-page":
            self.page.views.append(self.settings_page)
        elif self.page.route == "dev-storage-page":
            self.page.views.append(self.dev_storage_page)
        else:
            self.page.views.append(self.home_page)
        self.page.update()

    def view_pop(self, view):
        """Обработчик возврата на предыдущую страницу."""
        if self.page.route == "training-page":
            self.is_running = False
        self.page.views.pop()
        top_view = self.page.views[-1]
        self.page.go(top_view.route)

    def play_audio(self, word):
        """Воспроизведение аудио для слова."""
        try:
            audio_file_name = word.replace("'", "_")
            audio = Audio(src=f"audio/{audio_file_name}.mp3", autoplay=True)
            self.page.overlay.append(audio)
            self.page.update()
            time.sleep(1)  # Даем время для воспроизведения аудио
            self.page.overlay.remove(audio)
            self.page.update()
        except Exception as er:
            logger.error(f'Play audio Error: {er}')

    def start_learning(self):
        """Основной процесс изучения слов."""
        self.is_running = True
        start_time = time.time() - self.session_duration_sec

        if datetime.now().strftime('statistics.%Y-%m-%d') not in self.monthly_statistics:
            self.monthly_statistics[datetime.now().strftime('statistics.%Y-%m-%d')] = 0
            self.storage.set(datetime.now().strftime('statistics.%Y-%m-%d'), 0)

        while self.is_running and self.current_word_index < len(self.words):
            logger.info(f'current_word_index: {self.current_word_index}')

            if self.current_list_name == 'default':
                self.selected_words_bool[self.current_word_index] = True

            if not self.selected_words_bool[self.current_word_index]:
                self.current_word_index += 1
                continue  # Пропускаем слово, не выбранное для изучения

            duration_sec = int(time.time() - start_time)
            self.session_duration_sec = duration_sec
            current_date_key = datetime.now().strftime('statistics.%Y-%m-%d')

            logger.debug(f'duration_sec: {duration_sec}')
            logger.debug(f'session_duration_min: {self.session_duration_min}')
            logger.debug(f'monthly_statistics[current_date_key]: {self.monthly_statistics[current_date_key]}')
            logger.info(f'monthly_statistics: {self.monthly_statistics}')

            if current_date_key not in self.monthly_statistics:
                logger.debug('if current_date_key not in monthly_statistics:')
                self.monthly_statistics[current_date_key] = duration_sec // 60
                self.storage.set(current_date_key, self.monthly_statistics[current_date_key])

            if (duration_sec // 60) > self.session_duration_min:
                logger.debug('if (duration_sec // 60) > session_duration_min:')
                self.monthly_statistics[current_date_key] += 1
                self.session_duration_min += 1
                self.storage.set(current_date_key, self.monthly_statistics[current_date_key])

            self.duration_time.spans = [
                ft.TextSpan(
                    f'{duration_sec} сек',
                ),
            ]

            self.index_display.spans = [
                ft.TextSpan(
                    f'{self.current_word_index + 1}',
                    ft.TextStyle(size=30),
                ),
            ]

            english_word, english_transcription, russian_translation = self.words[self.current_word_index]

            if self.order_learning_words == '1':
                self.first_row_word_display.spans = [
                    ft.TextSpan(
                        english_word,
                        ft.TextStyle(size=30, color=self.english_color),
                    ),
                ]
                self.first_row_transcription_word_display.spans = []
                if self.is_transcription:
                    self.first_row_transcription_word_display.spans = [
                        ft.TextSpan(
                            f' {english_transcription}',
                            ft.TextStyle(size=30, color=self.transcription_color),
                        ),
                    ]
                self.second_row_word_display.spans = []
                self.second_row_transcription_word_display.spans = []
                self.page.update()
                time.sleep(0.5 + len(english_word + english_transcription) * 0.2 / self.delay)
                self.play_audio(english_word)
                self.second_row_word_display.spans = [
                    ft.TextSpan(
                        f'{russian_translation}',
                        ft.TextStyle(italic=True, size=30, color=self.russian_color),
                    ),
                ]
                self.page.update()
                time.sleep(0.5 + len(russian_translation) * 0.2 / self.delay)

            elif self.order_learning_words == '2':
                self.first_row_word_display.spans = [
                    ft.TextSpan(
                        russian_translation,
                        ft.TextStyle(italic=True, size=30, color=self.russian_color),
                    ),
                ]
                self.first_row_transcription_word_display.spans = []
                self.second_row_word_display.spans = []
                self.second_row_transcription_word_display.spans = []
                self.page.update()
                time.sleep(1 + len(russian_translation) * 0.2 / self.delay)
                self.play_audio(english_word)
                self.second_row_word_display.spans = [
                    ft.TextSpan(
                        f'{english_word}',
                        ft.TextStyle(size=30, color=self.english_color),
                    ),
                ]
                if self.is_transcription:
                    self.second_row_transcription_word_display.spans = [
                        ft.TextSpan(
                            f' {english_transcription}',
                            ft.TextStyle(size=30, color=self.transcription_color),
                        ),
                    ]
                self.page.update()
                time.sleep(0.5 + len(english_word + english_transcription) * 0.2 / self.delay)

            self.current_word_index += 1

        self.is_running = False
        self.start_button.disabled = False
        self.stop_button.disabled = True
        self.page.update()


def main(page: ft.Page):
    """Основная функция для запуска приложения."""
    trainer = WordTrainer(page)


if __name__ == "__main__":
    ft.app(target=main)