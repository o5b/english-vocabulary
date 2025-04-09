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
from utils import compress_bool_list_to_hex, decompress_bool_list_from_hex
from logger_config import logger


def main(page: ft.Page):
    page.scroll = ft.ScrollMode.AUTO
    page.title = "Изучение английских слов"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    words = WORDS
    colors = COLORS
    is_running = False
    session_duration_sec = 0
    session_duration_min = 0

    print('page.client_storage.get_keys:')
    pprint.pp(page.client_storage.get_keys(""))
    for key in page.client_storage.get_keys(""):
        print(f'key: {key}, val: {page.client_storage.get(key)}')
    # page.client_storage.clear()

    if not page.client_storage.contains_key("current_word_index"):
        page.client_storage.set("current_word_index", 0)
    current_word_index = page.client_storage.get("current_word_index")

    if not page.client_storage.contains_key("theme_mode"):
        page.client_storage.set("theme_mode", "LIGHT")
    if page.client_storage.get("theme_mode") == 'LIGHT':
        page.theme_mode = ft.ThemeMode.LIGHT
    elif page.client_storage.get("theme_mode") == 'DARK':
        page.theme_mode = ft.ThemeMode.DARK

    if page.client_storage.contains_key('delay'):
        delay = page.client_storage.get('delay')
        if delay < 1:
            delay = 1
            page.client_storage.set('delay', 1)
    else:
        delay = 1
        page.client_storage.set('delay', 1)

    if not page.client_storage.contains_key('order_learning_words'):
        page.client_storage.set('order_learning_words', '1')
    order_learning_words = page.client_storage.get('order_learning_words')

    if not page.client_storage.contains_key(datetime.now().strftime('statistics.%Y-%m-%d')):
        page.client_storage.set(datetime.now().strftime('statistics.%Y-%m-%d'), 0)
    raw_monthly_statistics = {}
    for key in page.client_storage.get_keys(datetime.now().strftime('statistics.%Y-%m')):
        raw_monthly_statistics[key] = page.client_storage.get(key)
    # print(f'raw_monthly_statistics: {raw_monthly_statistics}')

    # Функция для извлечения последнего числа из ключа
    def get_day(key):
        return int(key.split('-')[-1])

    # Сортировка словаря по последнему числу в ключе
    monthly_statistics = dict(sorted(raw_monthly_statistics.items(), key=lambda item: get_day(item[0])))
    # print(f'monthly_statistics: {monthly_statistics}')

    # Получение доступных годов и месяцев
    years = sorted(set(key.split('.')[1].split('-')[0] for key in page.client_storage.get_keys('statistics')))
    months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']

    if not page.client_storage.contains_key('is_transcription'):
        page.client_storage.set('is_transcription', True)
    is_transcription = page.client_storage.get('is_transcription')

    if not page.client_storage.contains_key('english_color'):
        page.client_storage.set('english_color', ft.Colors.BLACK.value)
    english_color = page.client_storage.get('english_color')

    if not page.client_storage.contains_key('transcription_color'):
        page.client_storage.set('transcription_color', ft.Colors.BLACK.value)
    transcription_color = page.client_storage.get('transcription_color')

    if not page.client_storage.contains_key('russian_color'):
        page.client_storage.set('russian_color', ft.Colors.BLACK.value)
    russian_color = page.client_storage.get('russian_color')

    # Инициализация начального списка, если хранилище пустое
    if not page.client_storage.contains_key('word_lists'):
        page.client_storage.set('word_lists', {'default': compress_bool_list_to_hex([False] * len(words))})

    # Получаем все списки из хранилища
    word_lists = page.client_storage.get('word_lists') or {}
    current_list_name = ft.Ref[str]()
    current_list_name.current = list(word_lists.keys())[0] if word_lists else 'default'
    selected_words_bool = decompress_bool_list_from_hex(word_lists[current_list_name.current], len(words))

    for key in word_lists.keys():
        if not page.client_storage.contains_key(f"current_word_index.{key}"):
            page.client_storage.set(f"current_word_index.{key}", 0)
    current_word_index_list = page.client_storage.get_keys("current_word_index.")

    def play_audio(word):
        print(f'def play_audio(word): word: {word}')
        try:
            audio_file_name = word.replace("'", "_")
            print(f'def play_audio(word): audio_file_name: {audio_file_name}')
            audio = Audio(src=f"audio/{audio_file_name}.mp3", autoplay=True)
            page.overlay.append(audio)
            page.update()
            time.sleep(1)  # Даем время для воспроизведения аудио
            page.overlay.remove(audio)
            page.update()
        except Exception as er:
            logger.error(f'Play audio Error: {er}')

    def start_learning():
        nonlocal is_running, delay, current_word_index, order_learning_words, session_duration_sec, session_duration_min,is_transcription, english_color, transcription_color, russian_color, monthly_statistics, selected_words_bool, current_word_index_list
        # selected_rows_data_table
        is_running = True
        start_time = time.time() - session_duration_sec

        if datetime.now().strftime('statistics.%Y-%m-%d') not in monthly_statistics:
            monthly_statistics[datetime.now().strftime('statistics.%Y-%m-%d')] = 0
            page.client_storage.set(datetime.now().strftime('statistics.%Y-%m-%d'), 0)

        while is_running and current_word_index < len(words):
            logger.info(f'current_word_index: {current_word_index}')

            if current_list_name.current == 'default':
                selected_words_bool[current_word_index] = True

            if not selected_words_bool[current_word_index]:
                current_word_index += 1
                continue    # пропускаем слово не выбранное для изучения

            duration_sec = int(time.time() - start_time)
            session_duration_sec = duration_sec
            current_date_key = datetime.now().strftime('statistics.%Y-%m-%d')

            logger.debug(f'duration_sec: {duration_sec}')
            logger.debug(f'session_duration_min: {session_duration_min}')
            logger.debug(f'monthly_statistics[current_date_key]: {monthly_statistics[current_date_key]}')
            logger.info(f'monthly_statistics: {monthly_statistics}')

            if current_date_key not in monthly_statistics:
                logger.debug('if current_date_key not in monthly_statistics:')
                monthly_statistics[current_date_key] = duration_sec // 60
                page.client_storage.set(current_date_key, monthly_statistics[current_date_key])

            if (duration_sec // 60) > session_duration_min:
                logger.debug('if (duration_sec // 60) > session_duration_min:')
                monthly_statistics[current_date_key] += 1
                session_duration_min += 1
                page.client_storage.set(current_date_key, monthly_statistics[current_date_key])

            duration_time.spans = [
                ft.TextSpan(
                    f'{duration_sec} сек',
                ),
            ]

            index_display.spans = [
                ft.TextSpan(
                    f'{current_word_index + 1}',
                    ft.TextStyle(size=30),
                ),
            ]

            english_word, english_transcription, russian_translation = words[current_word_index]

            if order_learning_words == '1':
                first_row_word_display.spans = [
                    ft.TextSpan(
                        english_word,
                        ft.TextStyle(size=30, color=english_color),
                    ),
                ]
                first_row_transcription_word_display.spans = []
                if is_transcription:
                    first_row_transcription_word_display.spans = [
                        ft.TextSpan(
                            f' {english_transcription}',
                            ft.TextStyle(size=30, color=transcription_color),
                        ),
                    ]
                second_row_word_display.spans = []
                second_row_transcription_word_display.spans = []
                page.update()
                time.sleep(0.5 + len(english_word + english_transcription) * 0.2 / delay)
                play_audio(english_word)
                second_row_word_display.spans = [
                    ft.TextSpan(
                        f'{russian_translation}',
                        ft.TextStyle(italic=True, size=30, color=russian_color),
                    ),
                ]
                page.update()
                time.sleep(0.5 + len(russian_translation) * 0.2 / delay)

            elif order_learning_words == '2':
                first_row_word_display.spans = [
                    ft.TextSpan(
                        russian_translation,
                        ft.TextStyle(italic=True, size=30, color=russian_color),
                    ),
                ]
                first_row_transcription_word_display.spans = []
                second_row_word_display.spans = []
                second_row_transcription_word_display.spans = []
                page.update()
                time.sleep(1 + len(russian_translation) * 0.2 / delay)
                play_audio(english_word)
                second_row_word_display.spans = [
                    ft.TextSpan(
                        f'{english_word}',
                        ft.TextStyle(size=30, color=english_color),
                    ),
                ]
                if is_transcription:
                    second_row_transcription_word_display.spans = [
                        ft.TextSpan(
                            f' {english_transcription}',
                            ft.TextStyle(size=30, color=transcription_color),
                        ),
                    ]
                page.update()
                time.sleep(0.5 + len(english_word + english_transcription) * 0.2 / delay)

            current_word_index += 1

        is_running = False
        start_button.disabled = False
        stop_button.disabled = True
        page.update()

    def start_button_click(e):
        start_button.disabled = True
        stop_button.disabled = False
        page.update()
        threading.Thread(target=start_learning, daemon=True).start()

    def stop_button_click(e):
        nonlocal is_running
        is_running = False
        start_button.disabled = False
        stop_button.disabled = True
        page.update()

    def set_delay(e):
        nonlocal delay
        delay = int(delay_control.value)
        page.client_storage.set('delay', delay)
        page.update()

    def theme_changed(e):
        page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        if page.theme_mode == ft.ThemeMode.LIGHT:
            page.client_storage.set("theme_mode", "LIGHT")
        else:
            page.client_storage.set("theme_mode", "DARK")
        page.update()

    def set_current_word_index(e):
        nonlocal current_word_index
        current_word_index = int(current_word_index_control.value)
        page.client_storage.set("current_word_index", current_word_index)
        page.update()

    def storage_current_word_index_click(e):
        nonlocal current_word_index
        page.client_storage.set("current_word_index", current_word_index)
        page.update()

    def learning_words_radiogroup_changed(e):
        nonlocal order_learning_words
        order_learning_words = e.control.value
        page.client_storage.set("order_learning_words", e.control.value)
        page.update()

    def save_datatable_button_click(e):
        nonlocal selected_words_bool
        print(f'def save_datatable_button_click(e) -> selected_words_bool before set: {selected_words_bool}')
        try:
            page.client_storage.set('selected_words_bool', compress_bool_list_to_hex(selected_words_bool))
            compressed_from_storage = page.client_storage.get('selected_words_bool')
            selected_words_bool = decompress_bool_list_from_hex(compressed_from_storage, len(words))
            page.open(
                ft.AlertDialog(
                    title=ft.Text("Изменения успешно сохранены!"),
                )
            )
        except Exception as er:
            print(f'Error save data-table to user-storage: {er}')
            page.open(
                ft.AlertDialog(
                    title=ft.Text("Во время сохранения изменений произошла ошибка!"),
                )
            )
        page.update()

    def get_paginated_table():
        nonlocal selected_words_bool
        word_rows = []

        for i, w in enumerate(words, start=0):
            s = ' '.join(w)
            word_rows.append(
                ft.DataRow(
                    [ft.DataCell(ft.Text(f"{i+1}")), ft.DataCell(ft.Text(f"{s}"))],
                    selected=selected_words_bool[i],
                    on_select_changed=data_table_on_select_changed,
                ),
            )

        paginated_table = PaginatedDataTable(
            width=700,
            # bgcolor="yellow",
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
                ft.DataColumn(
                    ft.Text("Номер"),
                    numeric=True,
                ),
                ft.DataColumn(
                    ft.Text("Слово"),
                ),
            ],
            rows_per_page=20,
            rows=word_rows,
        )

        return paginated_table.container

    def transcription_changed(e):
        nonlocal is_transcription
        is_transcription = transcription_control.value
        page.client_storage.set("is_transcription", transcription_control.value)
        page.update()

    def get_color_options():
        nonlocal colors
        options = []
        for color in colors:
            options.append(
                ft.dropdown.Option(
                    key=color.value,
                    content=ft.Text(value=color.value, color=color),
                )
            )
        return options

    def english_color_dropdown_changed(e):
        nonlocal english_color
        english_color = e.control.value
        page.client_storage.set("english_color", e.control.value)
        e.control.color = e.control.value
        page.update()

    def transcription_color_dropdown_changed(e):
        nonlocal transcription_color
        transcription_color = e.control.value
        page.client_storage.set("transcription_color", e.control.value)
        e.control.color = e.control.value
        page.update()

    def russian_color_dropdown_changed(e):
        nonlocal russian_color
        russian_color = e.control.value
        page.client_storage.set("russian_color", e.control.value)
        e.control.color = e.control.value
        page.update()

    def dev_tools_storage_list():
        lv = ft.ListView(expand=1, spacing=10, padding=20, auto_scroll=True)
        for i, key in enumerate(page.client_storage.get_keys('')):
            val = page.client_storage.get(key)
            lv.controls.append(
                ft.Row(
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.ElevatedButton(text="Delete", on_click=storage_delete_button_click, data=key),
                        ft.Text(f"{i+1}. {key}: {val}", max_lines=2),
                    ]
                )
            )
        return lv

    def storage_delete_button_click(e):
        try:
            page.client_storage.remove(e.control.data)
            page.open(
                ft.AlertDialog(
                    title=ft.Text(f"{e.control.data} успешно удалён!"),
                )
            )
        except Exception as er:
            print(f'Error deleted data from client_storage: {er}')
            page.open(
                ft.AlertDialog(
                    title=ft.Text("Во время удаления произошла ошибка!"),
                )
            )
        page.update()

    def repeat_current_word_index(e):
        nonlocal current_word_index
        current_word_index -= 2
        if current_word_index < 0:
            current_word_index = 0
        page.update()

    def generate_test_statistics():
        for year in ['2024', '2025']:
            for month in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']:
                for day in ['01', '03', '02', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15',
                        '16', '17', '18', '19', '21', '20', '22', '23', '24', '25', '27', '26', '28', '29', '30', '31']:
                    page.client_storage.set(f'statistics.{year}-{month}-{day}', random.randint(5, 120))

    def remove_test_statistics():
        for key in page.client_storage.get_keys('statistics.'):
            page.client_storage.remove(key)

    def terminate_app(e):
        page.close(confirm_dialog)

    def handle_close(e):
        page.close(confirm_dialog)

    confirm_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Please confirm"),
        content=ft.Text("Do you really want to exit this app?"),
        actions=[
            ft.ElevatedButton("Yes", on_click=terminate_app),
            ft.OutlinedButton("No", on_click=handle_close),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    duration_time = ft.Text(value="", size=20, text_align=ft.TextAlign.CENTER)
    index_display = ft.Text(value="", size=30, text_align=ft.TextAlign.START)
    first_row_word_display = ft.Text(value="", size=30, text_align=ft.TextAlign.START)
    first_row_transcription_word_display = ft.Text(value="", size=30, text_align=ft.TextAlign.END)
    second_row_word_display = ft.Text(value="", size=30, text_align=ft.TextAlign.START)
    second_row_transcription_word_display = ft.Text(value="", size=30, text_align=ft.TextAlign.END)
    start_button = ft.ElevatedButton(text="Старт", on_click=start_button_click)
    stop_button = ft.ElevatedButton(text="Пауза", on_click=stop_button_click, disabled=True)
    delay_control = ft.Slider(min=1, max=10, value=delay, divisions=9, label="Ускорение {value}", on_change=set_delay)
    theme_control = ft.Switch(label="Тема (Светлая/Тёмная)", on_change=theme_changed)
    current_word_index_control = ft.Slider(
        min=0,
        max=1000,
        value=current_word_index,
        divisions=100,
        label="{value}",
        on_change=set_current_word_index,
    )
    storage_current_word_index_button = ft.ElevatedButton(text="Сохранить текущую позицию", on_click=storage_current_word_index_click)
    learning_words_radiogroup = ft.RadioGroup(
        content=ft.Column(
            [
                ft.Radio(value="1", label="Англ - транскрипция - задержка - рус"),
                ft.Radio(value="2", label="Рус - задержка - транскрипция - англ"),
            ]
        ),
        on_change=learning_words_radiogroup_changed,
    )
    learning_words_radiogroup.value = order_learning_words
    transcription_control = ft.Checkbox(label='Отображать транскрипцию', value=is_transcription, on_change=transcription_changed)

    # Поле ввода названия списка
    list_name_input = ft.TextField(
        label="Название списка",
        width=200,
        value=""
    )

    # Выпадающий список из сохраненных списков слов
    list_selector = ft.Dropdown(
        width=200,
        options=[ft.dropdown.Option(name) for name in word_lists.keys()],
        value=current_list_name.current,
        on_change=lambda e: load_selected_list(e.control.value)
    )

    def update_list_selector():
        list_selector.options = [ft.dropdown.Option(name) for name in word_lists.keys()]
        list_selector.value = current_list_name.current
        page.update()

    def load_selected_list(list_name):
        nonlocal selected_words_bool
        current_list_name.current = list_name
        selected_words_bool = decompress_bool_list_from_hex(word_lists[list_name], len(words))
        paginated_table.set_rows(create_table_rows())
        list_name_input.value = '' if list_name == 'default' else list_name
        update_list_selector()

    def save_datatable_button_click(e):
        nonlocal selected_words_bool, word_lists
        if not list_name_input.value.strip():
            page.open(ft.AlertDialog(title=ft.Text("Введите название списка!")))
            return None

        list_name = list_name_input.value.strip()
        word_lists[list_name] = compress_bool_list_to_hex(selected_words_bool)
        current_list_name.current = list_name
        page.client_storage.set('word_lists', word_lists)
        update_list_selector()
        list_name_input.value = ""
        page.open(ft.AlertDialog(title=ft.Text("Список успешно сохранен!")))
        page.update()

    def delete_list_button_click(e):
        nonlocal word_lists
        if len(word_lists) <= 1:
            page.open(ft.AlertDialog(title=ft.Text("Нельзя удалить последний список!")))
            return None
        elif current_list_name.current == 'default':
            page.open(ft.AlertDialog(title=ft.Text("Нельзя удалить этот список!")))
            return None

        deleted_list_name = current_list_name.current
        del word_lists[current_list_name.current]
        current_list_name.current = list(word_lists.keys())[0]
        page.client_storage.set('word_lists', word_lists)
        load_selected_list(current_list_name.current)
        page.open(ft.AlertDialog(title=ft.Text(f"Список {deleted_list_name} удален!")))

    def data_table_on_select_changed(e):
        nonlocal selected_words_bool
        idx = int(e.control.cells[0].content.value) - 1
        selected_words_bool[idx] = not e.control.selected
        e.control.selected = selected_words_bool[idx]
        page.update()

    def create_table_rows():
        return [
            ft.DataRow(
                [ft.DataCell(ft.Text(f"{i+1}")), ft.DataCell(ft.Text(' '.join(w)))],
                selected=selected_words_bool[i],
                on_select_changed=data_table_on_select_changed,
            )
            for i, w in enumerate(words)
        ]

    paginated_table = PaginatedDataTable(
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
        rows=create_table_rows(),
    )

    # Создаем выпадающие списки
    year_dropdown = ft.Dropdown(
        width=150,
        options=[ft.dropdown.Option(year) for year in years],
        value=years[-1],  # Последний доступный год по умолчанию
        label="Год"
    )

    month_dropdown = ft.Dropdown(
        width=150,
        options=[ft.dropdown.Option(month) for month in months],
        value=datetime.now().strftime('%m'),  # Текущий месяц по умолчанию
        label="Месяц"
    )

    # Контейнер для графика
    chart_container = ft.Container()

    def get_monthly_statistics(selected_year, selected_month):
        raw_monthly_statistics = {}
        pattern = f'statistics.{selected_year}-{selected_month}'
        for key in page.client_storage.get_keys(pattern):
            raw_monthly_statistics[key] = page.client_storage.get(key)

        # Сортировка по дням
        return dict(sorted(raw_monthly_statistics.items(), key=lambda item: int(item[0].split('-')[-1])))

    def create_chart(monthly_statistics):
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

    def update_chart(e):
        selected_year = year_dropdown.value
        selected_month = month_dropdown.value
        monthly_statistics = get_monthly_statistics(selected_year, selected_month)
        chart_container.content = create_chart(monthly_statistics)
        page.update()

    # Инициализация начального графика
    initial_stats = get_monthly_statistics(year_dropdown.value, month_dropdown.value)
    chart_container.content = create_chart(initial_stats)

    # Привязка обработчиков изменения к выпадающим спискам
    year_dropdown.on_change = update_chart
    month_dropdown.on_change = update_chart

    def selected_drawer(e):
        if e.control.selected_index == 0:
            page.go('settings-page')
        elif e.control.selected_index == 3:
            page.go('dev-storage-page')
        elif e.control.selected_index == 4:
            generate_test_statistics()
        elif e.control.selected_index == 5:
            remove_test_statistics()

    drawer = ft.NavigationDrawer(
        on_change=selected_drawer,
        controls=[
            ft.Container(
                height=20,
            ),
            theme_control,
            ft.Divider(thickness=2),
            ft.NavigationDrawerDestination(
                label="Настройки",
                icon=ft.Icons.SETTINGS,
                selected_icon=ft.Icon(ft.Icons.SETTINGS_OUTLINED),
            ),
            ft.NavigationDrawerDestination(
                label="Telegram",
                icon=ft.Icons.TELEGRAM,
                selected_icon=ft.Icon(ft.Icons.TELEGRAM_OUTLINED),
            ),
            ft.NavigationDrawerDestination(
                label="Email",
                icon=ft.Icons.EMAIL,
                selected_icon=ft.Icon(ft.Icons.EMAIL_OUTLINED),
            ),
            ft.Divider(thickness=2),
            ft.Text("DevTools:", size=20, text_align=ft.TextAlign.CENTER),
            ft.NavigationDrawerDestination(
                label="Storage",
                icon=ft.Icons.STORAGE,
                selected_icon=ft.Icon(ft.Icons.STORAGE_OUTLINED),
            ),
            ft.NavigationDrawerDestination(
                label="Создать Тестовую статистики",
                icon=ft.Icons.DEVELOPER_MODE,
                selected_icon=ft.Icon(ft.Icons.DEVELOPER_MODE_OUTLINED),
            ),
            ft.NavigationDrawerDestination(
                label="Удалить Тестовую статистики",
                icon=ft.Icons.DEVELOPER_MODE,
                selected_icon=ft.Icon(ft.Icons.DEVELOPER_MODE_OUTLINED),
            ),
        ],
    )

    def selected_navbar(e):
        print(f'e.control.selected_index: {e.control.selected_index}')
        if e.control.selected_index == 0:
            pass
        elif e.control.selected_index == 1:
            pass
        elif e.control.selected_index == 2:
            page.open(confirm_dialog)
        else:
            page.go("/")

    navbar = ft.NavigationBar(
        on_change = selected_navbar,
        destinations=[
            ft.NavigationDrawerDestination(
                label="Menu",
                icon=ft.Icon(ft.Icons.GRID_VIEW_ROUNDED),
            ),
            ft.NavigationDrawerDestination(
                label="Project",
                icon=ft.Icon(ft.Icons.ROCKET_LAUNCH_OUTLINED),
            ),
            ft.NavigationDrawerDestination(
                label="Exit",
                icon=ft.Icon(ft.Icons.CANCEL),
            ),
        ]
    )

    def route_change(route):
        page.views.clear()
        page.views.append(home_page)
        if page.route == "training-page":
            page.views.append(training_page)
        elif page.route == "dictionary-page":
            page.views.append(dictionary_page)
        elif page.route == "statistic-page":
            page.views.append(statistic_page)
        elif page.route == "settings-page":
            page.views.append(settings_page)
        elif page.route == "dev-storage-page":
            page.views.append(dev_storage_page)
        else:
            page.views.append(home_page)
        page.update()

    def view_pop(view):
        if page.route == "training-page":
            nonlocal is_running
            is_running = False
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    training_button = ft.OutlinedButton(
        height=100,
        width=100,
        content=ft.Container(
            padding=5,
            content=ft.Column(
                controls=[
                    ft.Image(src="eng_80x40.png"),
                    ft.Text('Тренировка', size=12),
                ]
            ),
        ),
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        on_click=lambda _:page.go("training-page"),
    )

    dictionary_button = ft.OutlinedButton(
        height=100,
        width=100,
        content=ft.Container(
            padding=5,
            content=ft.Column(
                controls=[
                    ft.Image(src="dict_80x40.png"),
                    ft.Text('Словарь', size=12),
                ]
            ),
        ),
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        on_click=lambda _:page.go("dictionary-page"),
    )

    statistic_button = ft.OutlinedButton(
        height=100,
        width=100,
        content=ft.Container(
            padding=5,
            content=ft.Column(
                controls=[
                    ft.Image(src="stat_80x40.png"),
                    ft.Text('Статистика', size=12),
                ]
            ),
        ),
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        on_click=lambda _:page.go("statistic-page"),
    )

    button_group = ft.Row(
        width=page.width,
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        controls=[
            training_button,
            dictionary_button,
            statistic_button,
        ]
    )

    home_page = ft.View(
        route="/",
        appbar=ft.AppBar(
            bgcolor="teal",
            color="white",
            title=ft.Text("Главная"),
        ),
        navigation_bar=navbar,
        drawer=drawer,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Image(src="homeimage_200x200.png", width=page.width, height=200, fit=ft.ImageFit.FILL),
            ft.Text('Выберите раздел:', size=30, font_family="Georgia", weight=ft.FontWeight.BOLD),
            button_group,
        ]
    )

    training_page = ft.View(
        route="training-page",
        appbar=ft.AppBar(
            title=ft.Text("Изучение слов"),
            color="white",
            bgcolor="#1da1f2",
            leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=view_pop),
        ),
        navigation_bar=navbar,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Row([duration_time], alignment=ft.MainAxisAlignment.END),
            ft.Row([list_selector], alignment=ft.MainAxisAlignment.START),
            ft.Row([index_display], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([first_row_word_display, first_row_transcription_word_display], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([second_row_word_display, second_row_transcription_word_display], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([start_button, stop_button], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row(),
            ft.Row([storage_current_word_index_button], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row(),
            ft.Row([ft.ElevatedButton(text="Повторить", on_click=repeat_current_word_index)], alignment=ft.MainAxisAlignment.CENTER),
        ]
    )

    dictionary_page = ft.View(
        route="dictionary-page",
        appbar=ft.AppBar(
            title=ft.Text("Словарь"),
            color="white",
            bgcolor="cyan",
            leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=view_pop),
        ),
        navigation_bar=navbar,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text('Редактирование списка изучаемых слов', size=30, font_family="Georgia", weight=ft.FontWeight.BOLD),
            ft.Row([list_selector, list_name_input]),
            ft.Row([
                ft.ElevatedButton(text="Сохранить изменения", on_click=save_datatable_button_click),
                ft.ElevatedButton(text="Удалить текущий список", on_click=delete_list_button_click),
            ]),
            paginated_table.container,
        ]
    )

    statistic_page = ft.View(
        route="statistic-page",
        appbar=ft.AppBar(
            title=ft.Text("Статистика"),
            color="white",
            bgcolor="cyan",
            leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=view_pop),
        ),
        navigation_bar=navbar,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text('Раздел для отображения статистики', size=30, font_family="Georgia", weight=ft.FontWeight.BOLD),
            ft.Row([year_dropdown, month_dropdown], alignment=ft.MainAxisAlignment.CENTER),
            chart_container,
        ]
    )

    settings_page = ft.View(
        route="settings-page",
        appbar=ft.AppBar(
            title=ft.Text("Настройки"),
            color="white",
            bgcolor="cyan",
            leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=view_pop),
        ),
        navigation_bar=navbar,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text("Скорость:"),
            delay_control,
            ft.Text("Номер текущего слова:"),
            current_word_index_control,
            transcription_control,
            ft.Text("Установите цвет слов:"),
            ft.Dropdown(
                # editable=True,
                label="Английского",
                options=get_color_options(),
                on_change=english_color_dropdown_changed,
            ),
            ft.Dropdown(
                # editable=True,
                label="Транскрипции",
                options=get_color_options(),
                on_change=transcription_color_dropdown_changed,
            ),
            ft.Dropdown(
                # editable=True,
                label="Русского",
                options=get_color_options(),
                on_change=russian_color_dropdown_changed,
            ),
            ft.Text("Выберите вариант изучения английских слов:"),
            learning_words_radiogroup,
        ]
    )

    dev_storage_page = ft.View(
        route="dev-storage-page",
        appbar=ft.AppBar(
            title=ft.Text("DevTools: Storage"),
            color="white",
            bgcolor="cyan",
            leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=view_pop),
        ),
        navigation_bar=navbar,#page.views.clear
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text(value='Редактирование client_storage:', size=20),
            dev_tools_storage_list(),
        ]
    )

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route)
    page.update()


ft.app(target=main)
