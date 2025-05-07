import sys
import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget,
    QVBoxLayout, QTableView, QAbstractItemView,
    QPushButton, QHBoxLayout, QMessageBox, QFormLayout,
    QLineEdit, QComboBox, QDateEdit, QLabel
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
import fdb
from datetime import date

try:
    # Подключение к базе данных
    con = fdb.connect(
        dsn='C:/Program Files/RedDatabase/TAXOPARK',
        user='SYSDBA',
        password='masterkey',
    )
except Exception as e:
    print(f"Ошибка подключения к базе данных: {e}")
    sys.exit(1)

class MainWindow(QMainWindow):
    def __init__(self):
        try:
            super().__init__()
            self.setWindowTitle("Таксопарк 666")
            self.setGeometry(100, 100, 800, 600)

            tab_widget = QTabWidget()
            self.setCentralWidget(tab_widget)

            self.tables = {}
            self.tariff_levels = {  # Соответствие тарифов уровням
                1: 1,  # Стандарт → Уровень 1
                2: 2,  # Комфорт → Уровень 2
                3: 3   # Бизнес → Уровень 3
            }

            # Настройка вкладок
            self.setup_table(tab_widget, "Машины", "CAR")
            self.setup_table(tab_widget, "Водители", "DRIVER")
            self.setup_table(tab_widget, "Заказы", "ORDERTABLE")
            self.setup_table(tab_widget, "Платежи", "PAYMENT")
            self.setup_table(tab_widget, "Тарифы", "TARIFF")
            self.setup_order_form(tab_widget)
        except Exception as e:
            print(f"Ошибка при инициализации окна: {e}")
            sys.exit(1)

    def setup_table(self, tab_widget, tab_name, table_name):
        try:
            tab = QWidget()
            layout = QVBoxLayout()
            table_view = QTableView()
            table_view.setEditTriggers(QAbstractItemView.DoubleClicked)
            table_view.setSelectionMode(QAbstractItemView.SingleSelection)
            table_view.setSelectionBehavior(QAbstractItemView.SelectRows)

            # Инициализация модели
            model = QStandardItemModel()
            
            # Загрузка данных из базы
            self.load_data(table_name, model)

            table_view.setModel(model)
            table_view.resizeColumnsToContents()

            # Скрываем столбец ID (первый столбец)
            table_view.setColumnHidden(0, True)

            # Сохраняем ссылки на модель и представление
            self.tables[table_name] = (model, table_view)

            # Добавляем выпадающий список для статуса оплаты в таблице платежей
            if table_name == "PAYMENT":
                self.setup_payment_status_combo(table_name)

            # Настройка кнопок
            button_layout = QHBoxLayout()
            add_button = QPushButton("Add")
            save_button = QPushButton("Save")
            delete_button = QPushButton("Delete")
            if table_name == "ORDERTABLE":
                pay_button = QPushButton("Оплатить")
                pay_button.clicked.connect(lambda: self.process_payment_from_table(table_name))
                button_layout.addWidget(pay_button)

            add_button.clicked.connect(lambda: self.add_row(table_name))
            save_button.clicked.connect(lambda: self.save_changes(table_name))
            delete_button.clicked.connect(lambda: self.delete_row(table_name))

            button_layout.addWidget(add_button)
            button_layout.addWidget(save_button)
            button_layout.addWidget(delete_button)

            layout.addLayout(button_layout)
            layout.addWidget(table_view)
            tab.setLayout(layout)
            tab_widget.addTab(tab, tab_name)
        except Exception as e:
            print(f"Ошибка при настройке таблицы {table_name}: {e}")
            sys.exit(1)

    def setup_payment_status_combo(self, table_name):
        try:
            if table_name not in self.tables:
                raise KeyError(f"Таблица {table_name} не найдена в self.tables")
            
            model, table_view = self.tables[table_name]
            payment_status_index = 4  # Индекс столбца PAYMENT_STATUS (нумерация с 0, после скрытия ID)
            for row in range(model.rowCount()):
                combo = QComboBox()
                combo.addItems(["Не оплачено", "Оплачено"])
                current_status = model.item(row, payment_status_index).text()
                combo.setCurrentText(current_status if current_status in ["Не оплачено", "Оплачено"] else "Не оплачено")
                table_view.setIndexWidget(model.index(row, payment_status_index), combo)
                combo.currentTextChanged.connect(lambda text, r=row, c=payment_status_index: self.update_status(model, r, c, text))
        except Exception as e:
            print(f"Ошибка при установке выпадающих списков для {table_name}: {e}")
            raise

    def update_status(self, model, row, column, text):
        # Обновляем модель при изменении статуса
        item = QStandardItem(text)
        item.setEditable(False)
        model.setItem(row, column, item)

    def setup_order_form(self, tab_widget):
        try:
            tab = QWidget()
            layout = QVBoxLayout()

            # Форма для заполнения заказа
            form_layout = QFormLayout()

            self.client_name_input = QLineEdit()
            self.phone_input = QLineEdit()
            self.phone_input.setPlaceholderText("+79991234567")

            # Выпадающий список для выбора тарифа
            self.tariff_combo = QComboBox()
            cursor = con.cursor()
            cursor.execute("SELECT ID, NAME, PRICE_PER_KM, COEFFICIENT FROM TARIFF")
            tariffs = cursor.fetchall()
            self.tariffs_data = {tariff[0]: (tariff[2], tariff[3] if tariff[3] is not None else 1.0) for tariff in tariffs}  # PRICE_PER_KM, COEFFICIENT
            self.all_tariffs = tariffs
            for tariff in tariffs:
                self.tariff_combo.addItem(tariff[1], tariff[0])  # Показываем NAME, сохраняем ID

            # Выпадающий список для выбора машины
            self.car_combo = QComboBox()

            # Поле для даты
            self.date_input = QDateEdit()
            self.date_input.setCalendarPopup(True)
            self.date_input.setDate(date.today())

            # Поле для расстояния
            self.distance_input = QLineEdit()
            self.distance_input.setPlaceholderText("Введите расстояние в км")

            # Поле для отображения стоимости
            self.cost_label = QLabel("Стоимость: 0.0")

            form_layout.addRow("Имя клиента:", self.client_name_input)
            form_layout.addRow("Телефон:", self.phone_input)
            form_layout.addRow("Тариф:", self.tariff_combo)
            form_layout.addRow("Машина:", self.car_combo)
            form_layout.addRow("Дата заказа:", self.date_input)
            form_layout.addRow("Расстояние (км):", self.distance_input)
            form_layout.addRow(self.cost_label)

            # Кнопки для сохранения и оплаты картой
            button_layout = QHBoxLayout()
            save_button = QPushButton("Сохранить заказ")
            card_pay_button = QPushButton("Оплатить картой")

            save_button.clicked.connect(self.save_order)
            card_pay_button.clicked.connect(self.pay_with_card)

            button_layout.addWidget(save_button)
            button_layout.addWidget(card_pay_button)

            layout.addLayout(form_layout)
            layout.addLayout(button_layout)
            tab.setLayout(layout)
            tab_widget.addTab(tab, "Новый заказ")

            # Подключение автоматического расчета стоимости
            self.distance_input.textChanged.connect(self.update_cost)
            self.tariff_combo.currentTextChanged.connect(self.update_cost)
            # Подключение обновления списка машин при смене тарифа
            self.tariff_combo.currentIndexChanged.connect(self.update_car_combo)
        except Exception as e:
            print(f"Ошибка при настройке формы заказа: {e}")
            sys.exit(1)

    def update_car_combo(self):
        try:
            # Очищаем текущий список машин
            self.car_combo.clear()

            # Получаем ID выбранного тарифа
            tariff_id = self.tariff_combo.currentData()
            if not tariff_id:
                return  # Не заполняем список, если тариф не выбран

            # Получаем уровень выбранного тарифа
            tariff_level = self.tariff_levels.get(tariff_id, 1)

            # Получаем текущую дату
            current_date = self.date_input.date().toString("yyyy-MM-dd")

            # Получаем список занятых машин (связанных с активными заказами на текущую дату)
            cursor = con.cursor()
            cursor.execute("""
                SELECT DISTINCT ORDERTABLE.DRIVER_ID
                FROM ORDERTABLE
                JOIN PAYMENT ON ORDERTABLE.ID = PAYMENT.ORDER_ID
                WHERE ORDERTABLE.ORDER_DATE = ? AND PAYMENT.PAYMENT_STATUS = 'Не оплачено'
            """, (current_date,))
            busy_car_ids = [row[0] for row in cursor.fetchall()]

            # Формируем запрос для свободных машин с точным соответствием уровня тарифа
            if busy_car_ids:
                placeholders = ", ".join(["?" for _ in busy_car_ids])
                sql = f"""
                    SELECT ID, MODEL
                    FROM CAR
                    WHERE TARIFF_CLASS = ?
                    AND ID NOT IN ({placeholders})
                """
                params = [tariff_level] + busy_car_ids
            else:
                sql = """
                    SELECT ID, MODEL
                    FROM CAR
                    WHERE TARIFF_CLASS = ?
                """
                params = [tariff_level]

            cursor.execute(sql, params)
            available_cars = cursor.fetchall()

            # Заполняем список доступных машин
            if available_cars:
                for car_id, model in available_cars:
                    self.car_combo.addItem(model, car_id)  # Показываем MODEL, сохраняем ID
            else:
                self.car_combo.addItem("Нет доступных машин", None)

            # Обновляем стоимость после изменения списка машин
            self.update_cost()
        except Exception as e:
            print(f"Ошибка при обновлении списка машин: {e}")

    def update_cost(self):
        try:
            distance = float(self.distance_input.text().strip()) if self.distance_input.text().strip() else 0.0
            tariff_id = self.tariff_combo.currentData() or 0
            price_per_km, coefficient = self.tariffs_data.get(tariff_id, (0, 1.0))
            cost = distance * price_per_km * coefficient
            self.cost_label.setText(f"Стоимость: {cost:.2f}")
        except ValueError:
            self.cost_label.setText("Стоимость: 0.0")
        except Exception as e:
            print(f"Ошибка при расчете стоимости: {e}")

    def save_order(self):
        try:
            client_name = self.client_name_input.text().strip()
            phone = self.phone_input.text().strip()
            car_id = self.car_combo.currentData()  # Используем ID машины вместо водителя
            tariff_id = self.tariff_combo.currentData()
            order_date = self.date_input.date().toString("yyyy-MM-dd")
            distance = self.distance_input.text().strip()

            if not all([client_name, phone, car_id, tariff_id, distance]):
                QMessageBox.warning(None, "Ошибка", "Заполните все поля")
                return

            cost = float(self.cost_label.text().replace("Стоимость: ", "").strip())
            if cost <= 0:
                QMessageBox.warning(None, "Ошибка", "Стоимость должна быть больше 0")
                return

            cursor = con.cursor()
            # Генерируем новый ID для заказа
            cursor.execute("SELECT MAX(ID) FROM ORDERTABLE")
            max_id = cursor.fetchone()[0]
            new_order_id = (max_id or 0) + 1

            # Сохраняем заказ, используя CAR.ID как DRIVER_ID
            sql_order = """
            INSERT INTO ORDERTABLE (ID, CLIENT_NAME, PHONE, DRIVER_ID, TARIFF_ID, ORDER_DATE, DISTANCE)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql_order, (new_order_id, client_name, phone, car_id, int(tariff_id), order_date, float(distance)))

            # Создаем запись оплаты с статусом "Не оплачено"
            cursor.execute("SELECT MAX(ID) FROM PAYMENT")
            max_payment_id = cursor.fetchone()[0]
            new_payment_id = (max_payment_id or 0) + 1

            payment_date = date.today().strftime("%Y-%m-%d")
            sql_payment = """
            INSERT INTO PAYMENT (ID, ORDER_ID, AMOUNT, PAID_DATE, PAYMENT_STATUS)
            VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(sql_payment, (new_payment_id, new_order_id, cost, payment_date, "Не оплачено"))

            con.commit()

            # Обновляем таблицы заказов и платежей
            order_model, _ = self.tables["ORDERTABLE"]
            payment_model, _ = self.tables["PAYMENT"]
            self.load_data("ORDERTABLE", order_model)
            self.load_data("PAYMENT", payment_model)

            # Очищаем форму
            self.client_name_input.clear()
            self.phone_input.clear()
            self.distance_input.clear()
            self.cost_label.setText("Стоимость: 0.0")

            QMessageBox.information(None, "Успех", "Заказ и оплата успешно сохранены (статус: Не оплачено)")
        except Exception as e:
            con.rollback()
            QMessageBox.critical(None, "Ошибка", f"Ошибка сохранения: {str(e)}")

    def process_payment_from_table(self, table_name):
        if table_name != "ORDERTABLE":
            return

        try:
            model, table_view = self.tables[table_name]
            selected = table_view.selectionModel().selectedRows()
            if not selected:
                QMessageBox.warning(None, "Предупреждение", "Выберите заказ для оплаты")
                return

            # ID находится в скрытом столбце (индекс 0)
            order_id = model.item(selected[0].row(), 0).text().strip()
            cursor = con.cursor()
            # Получаем данные заказа для расчета стоимости
            cursor.execute("SELECT TARIFF_ID, DISTANCE FROM ORDERTABLE WHERE ID = ?", (order_id,))
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(None, "Ошибка", "Заказ не найден")
                return
            tariff_id, distance = row
            cursor.execute("SELECT PRICE_PER_KM, COEFFICIENT FROM TARIFF WHERE ID = ?", (tariff_id,))
            price_per_km, coefficient = cursor.fetchone() or (0, 1.0)
            cost = float(distance) * float(price_per_km) * float(coefficient)

            # Проверяем, есть ли запись оплаты
            cursor.execute("SELECT ID, AMOUNT FROM PAYMENT WHERE ORDER_ID = ? AND PAYMENT_STATUS = 'Не оплачено'", (order_id,))
            payment = cursor.fetchone()
            if payment:
                payment_id = payment[0]
                payment_date = date.today().strftime("%Y-%m-%d")
                sql_update = """
                UPDATE PAYMENT SET AMOUNT = ?, PAID_DATE = ?, PAYMENT_STATUS = ? WHERE ID = ?
                """
                cursor.execute(sql_update, (cost, payment_date, "Оплачено", payment_id))
            else:
                cursor.execute("SELECT MAX(ID) FROM PAYMENT")
                max_payment_id = cursor.fetchone()[0]
                new_payment_id = (max_payment_id or 0) + 1
                payment_date = date.today().strftime("%Y-%m-%d")
                sql_payment = """
                INSERT INTO PAYMENT (ID, ORDER_ID, AMOUNT, PAID_DATE, PAYMENT_STATUS)
                VALUES (?, ?, ?, ?, ?)
                """
                cursor.execute(sql_payment, (new_payment_id, order_id, cost, payment_date, "Оплачено"))

            con.commit()

            # Обновляем таблицы
            self.load_data("ORDERTABLE", model)
            payment_model, _ = self.tables["PAYMENT"]
            self.load_data("PAYMENT", payment_model)

            QMessageBox.information(None, "Успех", f"Заказ {order_id} успешно оплачен (статус: Оплачено)")
        except Exception as e:
            con.rollback()
            QMessageBox.critical(None, "Ошибка", f"Ошибка оплаты: {str(e)}")

    def pay_with_card(self):
        try:
            client_name = self.client_name_input.text().strip()
            phone = self.phone_input.text().strip()
            car_id = self.car_combo.currentData()  # Используем ID машины вместо водителя
            tariff_id = self.tariff_combo.currentData()
            order_date = self.date_input.date().toString("yyyy-MM-dd")
            distance = self.distance_input.text().strip()

            if not all([client_name, phone, car_id, tariff_id, distance]):
                QMessageBox.warning(None, "Ошибка", "Заполните все поля перед оплатой")
                return

            cost = float(self.cost_label.text().replace("Стоимость: ", "").strip())
            if cost <= 0:
                QMessageBox.warning(None, "Ошибка", "Стоимость должна быть больше 0")
                return

            cursor = con.cursor()
            # Проверяем, сохранен ли заказ
            cursor.execute("SELECT MAX(ID) FROM ORDERTABLE")
            max_order_id = cursor.fetchone()[0]
            if max_order_id is None:
                max_order_id = 0
            order_id = max_order_id + 1

            # Если заказ не сохранен, сохраняем его
            cursor.execute("SELECT COUNT(*) FROM ORDERTABLE WHERE ID = ?", (order_id,))
            if cursor.fetchone()[0] == 0:
                sql = """
                INSERT INTO ORDERTABLE (ID, CLIENT_NAME, PHONE, DRIVER_ID, TARIFF_ID, ORDER_DATE, DISTANCE)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(sql, (order_id, client_name, phone, car_id, int(tariff_id), order_date, float(distance)))

                # Создаем запись оплаты с статусом "Не оплачено"
                cursor.execute("SELECT MAX(ID) FROM PAYMENT")
                max_payment_id = cursor.fetchone()[0]
                new_payment_id = (max_payment_id or 0) + 1

                payment_date = date.today().strftime("%Y-%m-%d")
                sql_payment = """
                INSERT INTO PAYMENT (ID, ORDER_ID, AMOUNT, PAID_DATE, PAYMENT_STATUS)
                VALUES (?, ?, ?, ?, ?)
                """
                cursor.execute(sql_payment, (new_payment_id, order_id, cost, payment_date, "Не оплачено"))

            # Обновляем статус оплаты на "Оплачено" при оплате картой
            cursor.execute("SELECT ID FROM PAYMENT WHERE ORDER_ID = ?", (order_id,))
            payment_id = cursor.fetchone()
            if payment_id:
                payment_id = payment_id[0]
                payment_date = date.today().strftime("%Y-%m-%d")
                sql_update = """
                UPDATE PAYMENT SET AMOUNT = ?, PAID_DATE = ?, PAYMENT_STATUS = ? WHERE ID = ?
                """
                cursor.execute(sql_update, (cost, payment_date, "Оплачено", payment_id))
            else:
                # Если записи нет, создаем новую с "Оплачено"
                cursor.execute("SELECT MAX(ID) FROM PAYMENT")
                max_payment_id = cursor.fetchone()[0]
                new_payment_id = (max_payment_id or 0) + 1
                payment_date = date.today().strftime("%Y-%m-%d")
                sql_payment = """
                INSERT INTO PAYMENT (ID, ORDER_ID, AMOUNT, PAID_DATE, PAYMENT_STATUS)
                VALUES (?, ?, ?, ?, ?)
                """
                cursor.execute(sql_payment, (new_payment_id, order_id, cost, payment_date, "Оплачено"))

            con.commit()

            # Обновляем таблицы
            order_model, _ = self.tables["ORDERTABLE"]
            payment_model, _ = self.tables["PAYMENT"]
            self.load_data("ORDERTABLE", order_model)
            self.load_data("PAYMENT", payment_model)

            # Очищаем форму
            self.client_name_input.clear()
            self.phone_input.clear()
            self.distance_input.clear()
            self.cost_label.setText("Стоимость: 0.0")

            QMessageBox.information(None, "Успех", "Оплата картой успешно обработана (статус: Оплачено)")
        except Exception as e:
            con.rollback()
            QMessageBox.critical(None, "Ошибка", f"Ошибка оплаты картой: {str(e)}")

    def load_data(self, table_name, model):
        try:
            cursor = con.cursor()
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            if rows:
                columns = [desc[0] for desc in cursor.description]
                model.setHorizontalHeaderLabels(columns)  # Загружаем все заголовки, включая ID
                model.setRowCount(0)  # Очищаем модель перед загрузкой
                for row_idx, row in enumerate(rows):
                    items = []
                    for value in row:
                        item = QStandardItem(str(value) if value is not None else "")
                        item.setEditable(True)
                        items.append(item)
                    model.appendRow(items)
            else:
                cursor.execute(f"SELECT * FROM {table_name} WHERE 1=0")  # Получаем структуру таблицы
                columns = [desc[0] for desc in cursor.description]
                model.setHorizontalHeaderLabels(columns)
                model.setRowCount(0)
        except Exception as e:
            print(f"Ошибка при загрузке данных из таблицы {table_name}: {e}")
            sys.exit(1)

    def add_row(self, table_name):
        try:
            model, table_view = self.tables[table_name]
            # Количество столбцов в базе данных (включая скрытый ID)
            cursor = con.cursor()
            cursor.execute(f"SELECT * FROM {table_name} WHERE 1=0")
            num_columns = len([desc[0] for desc in cursor.description])
            
            row = []
            # Добавляем пустой элемент для скрытого столбца ID
            item_id = QStandardItem("")
            item_id.setEditable(False)  # ID не редактируется
            row.append(item_id)
            
            # Добавляем элементы для остальных столбцов
            for col in range(num_columns - 1):  # -1, так как ID уже добавлен
                item = QStandardItem("")
                item.setEditable(True)
                row.append(item)

            # Для таблицы CAR заменяем последний столбец (TARIFF_CLASS) на выпадающий список
            if table_name == "CAR":
                class_combo = QComboBox()
                class_combo.addItems(["Стандарт (1)", "Комфорт (2)", "Бизнес (3)"])
                class_combo.setCurrentIndex(-1)
                row[num_columns - 1] = QStandardItem("(выберите класс тарифа)")
                row[num_columns - 1].setData(class_combo, Qt.UserRole)
            # Для таблицы PAYMENT добавляем выпадающий список для PAYMENT_STATUS
            elif table_name == "PAYMENT":
                status_combo = QComboBox()
                status_combo.addItems(["Не оплачено", "Оплачено"])
                status_combo.setCurrentIndex(0)  # По умолчанию "Не оплачено"
                row[4] = QStandardItem("Не оплачено")  # Индекс 4 для PAYMENT_STATUS (с учетом скрытого ID)
                row[4].setData(status_combo, Qt.UserRole)

            model.appendRow(row)

            # Устанавливаем выпадающий список в ячейку
            if table_name == "CAR":
                table_view.setIndexWidget(
                    model.index(model.rowCount() - 1, num_columns - 1),
                    row[num_columns - 1].data(Qt.UserRole)
                )
            elif table_name == "PAYMENT":
                table_view.setIndexWidget(
                    model.index(model.rowCount() - 1, 4),
                    row[4].data(Qt.UserRole)
                )
                row[4].data(Qt.UserRole).currentTextChanged.connect(
                    lambda text, r=model.rowCount() - 1, c=4: self.update_status(model, r, c, text)
                )
        except Exception as e:
            print(f"Ошибка при добавлении строки в таблицу {table_name}: {e}")

    def save_changes(self, list_name):
        try:
            model, _ = self.tables[list_name]
            cursor = con.cursor()

            # Получаем все столбцы из базы данных (включая ID)
            cursor.execute(f"SELECT * FROM {list_name} WHERE 1=0")
            columns = [desc[0] for desc in cursor.description]

            if not columns:
                QMessageBox.warning(None, "Предупреждение", "Нет столбцов для сохранения")
                return

            for row in range(model.rowCount()):
                row_data = []
                all_empty = True
                for col in range(model.columnCount()):
                    item = model.item(row, col)
                    value = item.text().strip() if item else ""
                    if col == model.columnCount() - 1 and list_name == "CAR":
                        # Для последнего столбца CAR (TARIFF_CLASS) получаем значение из выпадающего списка
                        combo = item.data(Qt.UserRole) if item else None
                        if combo:
                            class_text = combo.currentText()
                            if class_text != "" and class_text != "(выберите класс тарифа)":
                                value = int(class_text.split("(")[1].replace(")", "").strip())
                            else:
                                value = None
                    row_data.append(value if value != "" else None)
                    if col > 0 and value != "" and value != "(выберите класс тарифа)":
                        all_empty = False

                if all_empty:
                    continue

                # Проверяем, существует ли строка с таким ID в базе
                id_value = row_data[0]  # ID находится в скрытом столбце
                exists = False
                if id_value:
                    cursor.execute(f"SELECT COUNT(*) FROM {list_name} WHERE ID = ?", (id_value,))
                    exists = cursor.fetchone()[0] > 0

                if not exists:
                    # Новая строка - генерируем ID
                    cursor.execute(f"SELECT MAX(ID) FROM {list_name}")
                    max_id = cursor.fetchone()[0]
                    new_id = (max_id or 0) + 1

                    while True:
                        cursor.execute(f"SELECT COUNT(*) FROM {list_name} WHERE ID = ?", (new_id,))
                        if cursor.fetchone()[0] == 0:
                            break
                        new_id += 1

                    row_data[0] = new_id
                    placeholders = ", ".join(["?"] * len(columns))
                    sql = f"INSERT INTO {list_name} ({', '.join(columns)}) VALUES ({placeholders})"
                else:
                    # Существующая строка - используем UPDATE
                    set_clause = ", ".join([f"{col} = ?" for col in columns[1:]])
                    sql = f"UPDATE {list_name} SET {set_clause} WHERE ID = ?"
                    row_data = row_data[1:] + [row_data[0]]

                cursor.execute(sql, row_data)

            con.commit()

            self.load_data(list_name, model)
            
            # Восстанавливаем выпадающие списки для PAYMENT после перезагрузки данных
            if list_name == "PAYMENT":
                self.setup_payment_status_combo(list_name)
                
            QMessageBox.information(None, "Успех", "Изменения успешно сохранены")
        except Exception as e:
            con.rollback()
            QMessageBox.critical(None, "Ошибка", f"Ошибка сохранения: {str(e)}")

    def delete_row(self, table_name):
        try:
            model, table_view = self.tables[table_name]
            selected = table_view.selectionModel().selectedRows()

            if not selected:
                QMessageBox.warning(None, "Предупреждение", "Выберите строку для удаления")
                return

            reply = QMessageBox.question(
                None, "Подтверждение",
                "Вы уверены, что хотите удалить выбранную строку?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                cursor = con.cursor()
                for index in selected:
                    row = index.row()
                    id_item = model.item(row, 0)  # ID в скрытом столбце
                    if id_item and id_item.text().strip():
                        id_value = id_item.text().strip()
                        cursor.execute(f"DELETE FROM {table_name} WHERE ID = ?", (id_value,))
                        model.removeRow(row)

                con.commit()

                self.load_data(table_name, model)
                
                # Восстанавливаем выпадающие списки для PAYMENT после удаления
                if table_name == "PAYMENT":
                    self.setup_payment_status_combo(table_name)
                    
                QMessageBox.information(None, "Успех", "Строка успешно удалена")
        except Exception as e:
            con.rollback()
            QMessageBox.critical(None, "Ошибка", f"Ошибка удаления: {str(e)}")

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Ошибка при запуске приложения: {e}")
        sys.exit(1)