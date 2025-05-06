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

# Подключение к базе данных
con = fdb.connect(
    dsn='C:/Program Files/RedDatabase/TAXOPARK',
    user='SYSDBA',
    password='masterkey',
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Таксопарк 666")
        self.setGeometry(100, 100, 800, 600)

        tab_widget = QTabWidget()
        self.setCentralWidget(tab_widget)

        self.tables = {}

        # Настройка вкладок
        self.setup_table(tab_widget, "Машины", "CAR")
        self.setup_table(tab_widget, "Водители", "DRIVER")
        self.setup_table(tab_widget, "Заказы", "ORDERTABLE")
        self.setup_table(tab_widget, "Платежи", "PAYMENT")
        self.setup_table(tab_widget, "Тарифы", "TARIFF")
        self.setup_order_form(tab_widget)

    def setup_table(self, tab_widget, tab_name, table_name):
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

        # Сохраняем ссылки на модель и представление
        self.tables[table_name] = (model, table_view)

        # Настройка кнопок
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add")
        save_button = QPushButton("Save")
        delete_button = QPushButton("Delete")

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

    def setup_order_form(self, tab_widget):
        tab = QWidget()
        layout = QVBoxLayout()

        # Форма для заполнения заказа
        form_layout = QFormLayout()

        self.client_name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+79991234567")

        # Выпадающий список для выбора водителя
        self.driver_combo = QComboBox()
        cursor = con.cursor()
        cursor.execute("SELECT ID, NAME FROM DRIVER")
        drivers = cursor.fetchall()
        for driver in drivers:
            self.driver_combo.addItem(f"{driver[1]} (ID: {driver[0]})", driver[0])

        # Выпадающий список для выбора тарифа
        self.tariff_combo = QComboBox()
        cursor.execute("SELECT ID, NAME, PRICE_PER_KM FROM TARIFF")
        tariffs = cursor.fetchall()
        self.tariffs_data = {tariff[0]: tariff[2] for tariff in tariffs}  # Сохраняем тарифы для расчета
        for tariff in tariffs:
            self.tariff_combo.addItem(f"{tariff[1]} (ID: {tariff[0]})", tariff[0])

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
        form_layout.addRow("Водитель:", self.driver_combo)
        form_layout.addRow("Тариф:", self.tariff_combo)
        form_layout.addRow("Дата заказа:", self.date_input)
        form_layout.addRow("Расстояние (км):", self.distance_input)
        form_layout.addRow(self.cost_label)

        # Кнопки для расчета, сохранения, оплаты и оплаты картой
        button_layout = QHBoxLayout()
        calc_button = QPushButton("Рассчитать стоимость")
        save_button = QPushButton("Сохранить заказ")
        pay_button = QPushButton("Оплатить")
        card_pay_button = QPushButton("Оплатить картой")

        calc_button.clicked.connect(self.calculate_cost)
        save_button.clicked.connect(self.save_order)
        pay_button.clicked.connect(self.process_payment)
        card_pay_button.clicked.connect(self.pay_with_card)

        button_layout.addWidget(calc_button)
        button_layout.addWidget(save_button)
        button_layout.addWidget(pay_button)
        button_layout.addWidget(card_pay_button)

        layout.addLayout(form_layout)
        layout.addLayout(button_layout)
        tab.setLayout(layout)
        tab_widget.addTab(tab, "Новый заказ")

    def calculate_cost(self):
        try:
            distance = float(self.distance_input.text().strip())
            tariff_id = self.tariff_combo.currentData()
            price_per_km = self.tariffs_data.get(tariff_id, 0)
            cost = distance * price_per_km
            self.cost_label.setText(f"Стоимость: {cost:.2f}")
            return cost
        except ValueError:
            QMessageBox.warning(None, "Ошибка", "Введите корректное расстояние (число)")
            return None

    def save_order(self):
        client_name = self.client_name_input.text().strip()
        phone = self.phone_input.text().strip()
        driver_id = self.driver_combo.currentData()
        tariff_id = self.tariff_combo.currentData()
        order_date = self.date_input.date().toString("yyyy-MM-dd")
        distance = self.distance_input.text().strip()

        if not all([client_name, phone, driver_id, tariff_id, distance]):
            QMessageBox.warning(None, "Ошибка", "Заполните все поля")
            return

        cost = self.calculate_cost()
        if cost is None:
            return

        cursor = con.cursor()
        try:
            # Генерируем новый ID для заказа
            cursor.execute("SELECT MAX(ID) FROM ORDERTABLE")
            max_id = cursor.fetchone()[0]
            new_order_id = (max_id or 0) + 1

            # Отладочный вывод параметров
            print(f"Parameters for ORDERTABLE: ID={new_order_id}, CLIENT_NAME={client_name}, PHONE={phone}, DRIVER_ID={driver_id}, TARIFF_ID={tariff_id}, ORDER_DATE={order_date}, DISTANCE={float(distance)}")
            print(f"TARIFF_ID type: {type(tariff_id)}, value: {tariff_id}, length: {len(str(tariff_id))}")

            # Сохраняем заказ
            sql_order = """
            INSERT INTO ORDERTABLE (ID, CLIENT_NAME, PHONE, DRIVER_ID, TARIFF_ID, ORDER_DATE, DISTANCE)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql_order, (new_order_id, client_name, phone, driver_id, int(tariff_id), order_date, float(distance)))

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

    def process_payment(self):
        client_name = self.client_name_input.text().strip()
        phone = self.phone_input.text().strip()
        driver_id = self.driver_combo.currentData()
        tariff_id = self.tariff_combo.currentData()
        order_date = self.date_input.date().toString("yyyy-MM-dd")
        distance = self.distance_input.text().strip()

        if not all([client_name, phone, driver_id, tariff_id, distance]):
            QMessageBox.warning(None, "Ошибка", "Заполните все поля перед оплатой")
            return

        cost = self.calculate_cost()
        if cost is None:
            return

        cursor = con.cursor()
        try:
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
                cursor.execute(sql, (order_id, client_name, phone, driver_id, int(tariff_id), order_date, float(distance)))

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

            # Обновляем статус оплаты на "Оплачено"
            cursor.execute("SELECT ID FROM PAYMENT WHERE ORDER_ID = ? AND PAYMENT_STATUS = 'Не оплачено'", (order_id,))
            payment_id = cursor.fetchone()
            if payment_id:
                payment_id = payment_id[0]
                payment_date = date.today().strftime("%Y-%m-%d")
                sql_update = """
                UPDATE PAYMENT SET AMOUNT = ?, PAID_DATE = ?, PAYMENT_STATUS = ? WHERE ID = ?
                """
                cursor.execute(sql_update, (cost, payment_date, "Оплачено", payment_id))
            else:
                # Если записи "Не оплачено" нет, создаем новую с "Оплачено"
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

            QMessageBox.information(None, "Успех", "Оплата успешно обработана (статус: Оплачено)")
        except Exception as e:
            con.rollback()
            QMessageBox.critical(None, "Ошибка", f"Ошибка обработки оплаты: {str(e)}")

    def pay_with_card(self):
        client_name = self.client_name_input.text().strip()
        phone = self.phone_input.text().strip()
        driver_id = self.driver_combo.currentData()
        tariff_id = self.tariff_combo.currentData()
        order_date = self.date_input.date().toString("yyyy-MM-dd")
        distance = self.distance_input.text().strip()

        if not all([client_name, phone, driver_id, tariff_id, distance]):
            QMessageBox.warning(None, "Ошибка", "Заполните все поля перед оплатой")
            return

        cost = self.calculate_cost()
        if cost is None:
            return

        cursor = con.cursor()
        try:
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
                cursor.execute(sql, (order_id, client_name, phone, driver_id, int(tariff_id), order_date, float(distance)))

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
        cursor = con.cursor()
        try:
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            if rows:
                columns = [desc[0] for desc in cursor.description]
                model.setHorizontalHeaderLabels(columns)
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
            QMessageBox.critical(None, "Ошибка загрузки", f"Ошибка при загрузке данных: {str(e)}")

    def add_row(self, table_name):
        model, _ = self.tables[table_name]
        num_columns = model.columnCount()
        if num_columns == 0:
            return
        row = [QStandardItem("") for _ in range(num_columns)]
        for item in row:
            item.setEditable(True)
        model.appendRow(row)

    def save_changes(self, list_name):
        model, _ = self.tables[list_name]
        cursor = con.cursor()

        try:
            columns = [model.headerData(col, Qt.Horizontal) for col in range(model.columnCount())]
            if not columns:
                QMessageBox.warning(None, "Предупреждение", "Нет столбцов для сохранения")
                return

            for row in range(model.rowCount()):
                row_data = []
                all_empty = True
                for col in range(model.columnCount()):
                    item = model.item(row, col)
                    value = item.text().strip() if item else ""
                    row_data.append(value if value != "" else None)
                    if value != "":
                        all_empty = False

                if all_empty:
                    continue

                # Проверяем, существует ли строка с таким ID в базе
                id_value = row_data[0]
                cursor.execute(f"SELECT COUNT(*) FROM {list_name} WHERE ID = ?", (id_value,))
                exists = cursor.fetchone()[0] > 0

                if not exists:
                    # Новая строка - используем INSERT
                    cursor.execute(f"SELECT MAX(ID) FROM {list_name}")
                    max_id = cursor.fetchone()[0]
                    new_id = (max_id or 0) + 1

                    while True:
                        cursor.execute(f"SELECT COUNT(*) FROM {list_name} WHERE ID = ?", (new_id,))
                        if cursor.fetchone()[0] == 0:
                            break
                        new_id += 1

                    row_data[0] = str(new_id)
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
            QMessageBox.information(None, "Успех", "Изменения успешно сохранены")
        except Exception as e:
            con.rollback()
            QMessageBox.critical(None, "Ошибка", f"Ошибка сохранения: {str(e)}")

    def delete_row(self, table_name):
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
            try:
                for index in selected:
                    row = index.row()
                    id_item = model.item(row, 0)
                    if id_item and id_item.text().strip():
                        cursor.execute(f"DELETE FROM {table_name} WHERE ID = ?", (id_item.text().strip(),))
                        model.removeRow(row)

                con.commit()
                self.load_data(table_name, model)
                QMessageBox.information(None, "Успех", "Строка успешно удалена")
            except Exception as e:
                con.rollback()
                QMessageBox.critical(None, "Ошибка", f"Ошибка удаления: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())