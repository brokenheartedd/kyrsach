import sys
import os
import configparser
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget,
    QVBoxLayout, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QPushButton, QHBoxLayout,
    QMessageBox, QFormLayout, QLineEdit, QComboBox,
    QDateEdit, QLabel
)
import fdb
from datetime import date

# Load database path from config.ini
config = configparser.ConfigParser()
if not os.path.exists('config.ini'):
    print("Ошибка: файл config.ini не найден.")
    sys.exit(1)

config.read('config.ini')
db_path = config.get('GENERAL', 'db_path', fallback='')
if not db_path or not os.path.exists(db_path):
    print(f"Ошибка: путь к базе данных {db_path} не указан или файл не существует.")
    sys.exit(1)

try:
    # Подключение к базе данных
    con = fdb.connect(
        dsn=db_path,
        user='SYSDBA',
        password='masterkey',
        charset='UTF8',
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
            self.setup_table(tab_widget, "Заказы", "ORDERTABLE")
            self.setup_table(tab_widget, "Машины", "CAR")
            self.setup_table(tab_widget, "Водители", "DRIVER")
            self.setup_table(tab_widget, "Платежи", "PAYMENT")
            self.setup_table(tab_widget, "Детали платежей", "PAYMENT_DETAILS")
            self.setup_table(tab_widget, "Тарифы", "TARIFF")
            self.setup_order_form(tab_widget)
        except Exception as e:
            print(f"Ошибка при инициализации окна: {e}")
            sys.exit(1)

    def setup_table(self, tab_widget, tab_name, table_name):
        try:
            tab = QWidget()
            layout = QVBoxLayout()
            
            # Создаем QTableWidget
            table_widget = QTableWidget()
            table_widget.setEditTriggers(QAbstractItemView.DoubleClicked)
            table_widget.setSelectionMode(QAbstractItemView.SingleSelection)
            table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)

            # Загружаем данные в table_widget напрямую
            self.load_data(table_name, table_widget)

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
            layout.addWidget(table_widget)
            tab.setLayout(layout)
            self.tables[table_name] = table_widget  # Сохраняем ссылку на QTableWidget

            tab_widget.addTab(tab, tab_name)
        except Exception as e:
            print(f"Ошибка при настройке таблицы {table_name}: {e}")
            sys.exit(1)

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
            cursor.execute("SELECT ID, NAME, PRICE_PER_KM FROM TARIFF")
            tariffs = cursor.fetchall()
            self.tariffs_data = {tariff[0]: (tariff[2], 1.0) for tariff in tariffs}  # PRICE_PER_KM, COEFFICIENT
            self.all_tariffs = tariffs
            if not tariffs:
                QMessageBox.warning(None, "Предупреждение", "В базе данных нет тарифов. Добавьте тарифы в таблицу TARIFF.")
            for tariff in tariffs:
                self.tariff_combo.addItem(tariff[1], tariff[0])  # Показываем NAME, сохраняем ID

            # Выпадающий список для выбора водителя
            self.driver_combo = QComboBox()
            cursor.execute("SELECT ID, FULL_NAME FROM DRIVER")
            drivers = cursor.fetchall()
            if not drivers:
                QMessageBox.warning(None, "Предупреждение", "В базе данных нет водителей. Добавьте водителей в таблицу DRIVER.")
            for driver in drivers:
                self.driver_combo.addItem(driver[1], driver[0])  # Показываем FULL_NAME, сохраняем ID

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

            # Поле для метода оплаты
            self.payment_method_input = QComboBox()
            self.payment_method_input.addItems(["Картой", "Наличными", "Онлайн"])

            # Поле для номера транзакции
            self.transaction_number_input = QLineEdit()
            self.transaction_number_input.setPlaceholderText("Номер транзакции (опционально)")

            form_layout.addRow("Имя клиента:", self.client_name_input)
            form_layout.addRow("Телефон:", self.phone_input)
            form_layout.addRow("Тариф:", self.tariff_combo)
            form_layout.addRow("Водитель:", self.driver_combo)
            form_layout.addRow("Машина:", self.car_combo)
            form_layout.addRow("Дата заказа:", self.date_input)
            form_layout.addRow("Расстояние (км):", self.distance_input)
            form_layout.addRow(self.cost_label)
            form_layout.addRow("Метод оплаты:", self.payment_method_input)
            form_layout.addRow("Номер транзакции:", self.transaction_number_input)

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
            # Подключение обновления списка машин при смене водителя или тарифа
            self.driver_combo.currentIndexChanged.connect(self.update_car_combo)
            self.tariff_combo.currentIndexChanged.connect(self.update_car_combo)
        except Exception as e:
            print(f"Ошибка при настройке формы заказа: {e}")
            sys.exit(1)

    def update_car_combo(self):
        try:
            # Очищаем текущий список машин
            self.car_combo.clear()

            # Получаем ID выбранного водителя и тарифа
            driver_id = self.driver_combo.currentData()
            tariff_id = self.tariff_combo.currentData()
            if not driver_id or not tariff_id:
                self.car_combo.addItem("Выберите водителя и тариф", None)
                return

            # Получаем текущую дату
            current_date = self.date_input.date().toString("yyyy-MM-dd")

            # Получаем список занятых водителей (с активными заказами на текущую дату)
            cursor = con.cursor()
            cursor.execute("""
                SELECT DISTINCT ORDERTABLE.DRIVER_ID
                FROM ORDERTABLE
                JOIN PAYMENT ON ORDERTABLE.ID = PAYMENT.ORDER_ID
                WHERE ORDERTABLE.ORDER_DATE = ? AND PAYMENT.PAYMENT_STATUS = 'Не оплачено'
            """, (current_date,))
            busy_driver_ids = [row[0] for row in cursor.fetchall()]

            # Проверяем, занят ли выбранный водитель
            if driver_id in busy_driver_ids:
                self.car_combo.addItem("Водитель занят на эту дату", None)
                return

            # Получаем машины, привязанные к выбранному водителю и подходящие по тарифу
            cursor.execute("""
                SELECT ID, MODEL
                FROM CAR
                WHERE DRIVER_ID = ? AND TARIFF_ID = ?
            """, (driver_id, tariff_id))
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
            self.car_combo.addItem("Ошибка при загрузке машин", None)
            QMessageBox.critical(None, "Ошибка", f"Ошибка при обновлении списка машин: {str(e)}")

    def update_cost(self):
        try:
            distance_text = self.distance_input.text().strip()
            if not distance_text:
                self.cost_label.setText("Стоимость: 0.0")
                return
            distance = float(distance_text)
            if distance <= 0:
                self.cost_label.setText("Стоимость: 0.0")
                return

            tariff_id = self.tariff_combo.currentData()
            if not tariff_id:
                self.cost_label.setText("Стоимость: 0.0")
                return

            price_per_km, coefficient = self.tariffs_data.get(tariff_id, (0, 1.0))
            cost = distance * price_per_km * coefficient
            self.cost_label.setText(f"Стоимость: {cost:.2f}")
        except ValueError:
            self.cost_label.setText("Стоимость: 0.0")
        except Exception as e:
            print(f"Ошибка при расчете стоимости: {e}")
            self.cost_label.setText("Стоимость: 0.0")
            QMessageBox.critical(None, "Ошибка", f"Ошибка при расчете стоимости: {str(e)}")

    def save_order(self):
        try:
            # Получаем данные из формы
            client_name = self.client_name_input.text().strip()
            phone = self.phone_input.text().strip()
            driver_id = self.driver_combo.currentData()
            tariff_id = self.tariff_combo.currentData()
            order_date = self.date_input.date().toString("yyyy-MM-dd")
            distance_text = self.distance_input.text().strip()
            payment_method = self.payment_method_input.currentText()
            transaction_number = self.transaction_number_input.text().strip()

            # Проверка заполнения всех полей
            if not client_name:
                QMessageBox.warning(None, "Ошибка", "Введите имя клиента")
                return
            if not phone:
                QMessageBox.warning(None, "Ошибка", "Введите телефон")
                return
            if not driver_id:
                QMessageBox.warning(None, "Ошибка", "Выберите водителя")
                return
            if not tariff_id:
                QMessageBox.warning(None, "Ошибка", "Выберите тариф")
                return
            if not distance_text:
                QMessageBox.warning(None, "Ошибка", "Введите расстояние")
                return

            # Проверка расстояния
            try:
                distance = float(distance_text)
                if distance <= 0:
                    QMessageBox.warning(None, "Ошибка", "Расстояние должно быть больше 0")
                    return
            except ValueError:
                QMessageBox.warning(None, "Ошибка", "Расстояние должно быть числом")
                return

            # Проверка стоимости
            cost_text = self.cost_label.text().replace("Стоимость: ", "").strip()
            try:
                cost = float(cost_text)
                if cost <= 0:
                    QMessageBox.warning(None, "Ошибка", "Стоимость должна быть больше 0")
                    return
            except ValueError:
                QMessageBox.warning(None, "Ошибка", "Ошибка расчета стоимости")
                return

            cursor = con.cursor()
            # Генерируем новый ID для заказа
            cursor.execute("SELECT MAX(ID) FROM ORDERTABLE")
            max_id = cursor.fetchone()[0]
            new_order_id = (max_id or 0) + 1

            # Сохраняем заказ
            sql_order = """
            INSERT INTO ORDERTABLE (ID, CLIENT_NAME, PHONE, DRIVER_ID, TARIFF_ID, ORDER_DATE, DISTANCE)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql_order, (new_order_id, client_name, phone, driver_id, int(tariff_id), order_date, distance))

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

            # Сохраняем детали платежа
            cursor.execute("SELECT MAX(ID) FROM PAYMENT_DETAILS")
            max_payment_details_id = cursor.fetchone()[0]
            new_payment_details_id = (max_payment_details_id or 0) + 1

            sql_payment_details = """
            INSERT INTO PAYMENT_DETAILS (ID, ORDER_ID, PAYMENT_METHOD, TRANSACTION_NUMBER, PAYMENT_DATE)
            VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(sql_payment_details, (new_payment_details_id, new_order_id, payment_method, transaction_number if transaction_number else None, payment_date))

            con.commit()

            # Обновляем таблицы заказов, платежей и деталей платежей
            self.load_data("ORDERTABLE", self.tables["ORDERTABLE"])
            self.load_data("PAYMENT", self.tables["PAYMENT"])
            self.load_data("PAYMENT_DETAILS", self.tables["PAYMENT_DETAILS"])

            # Очищаем форму
            self.client_name_input.clear()
            self.phone_input.clear()
            self.distance_input.clear()
            self.cost_label.setText("Стоимость: 0.0")
            self.driver_combo.setCurrentIndex(-1)
            self.car_combo.clear()
            self.tariff_combo.setCurrentIndex(-1)
            self.payment_method_input.setCurrentIndex(0)
            self.transaction_number_input.clear()

            QMessageBox.information(None, "Успех", "Заказ и оплата успешно сохранены (статус: Не оплачено)")
        except Exception as e:
            con.rollback()
            print(f"Ошибка при сохранении заказа: {e}")
            QMessageBox.critical(None, "Ошибка", f"Ошибка сохранения заказа: {str(e)}")

    def process_payment_from_table(self, table_name):
        if table_name != "ORDERTABLE":
            return

        try:
            table_widget = self.tables[table_name]
            selected = table_widget.selectedIndexes()
            if not selected:
                QMessageBox.warning(None, "Предупреждение", "Выберите заказ для оплаты")
                return

            row = selected[0].row()
            order_id = table_widget.item(row, 0).text().strip()
            cursor = con.cursor()
            # Получаем данные заказа для расчета стоимости
            cursor.execute("SELECT TARIFF_ID, DISTANCE FROM ORDERTABLE WHERE ID = ?", (order_id,))
            row = cursor.fetchone()
            if not row:
                QMessageBox.warning(None, "Ошибка", "Заказ не найден")
                return
            tariff_id, distance = row
            cursor.execute("SELECT PRICE_PER_KM FROM TARIFF WHERE ID = ?", (tariff_id,))
            price_per_km = cursor.fetchone()[0] or 0
            cost = float(distance) * float(price_per_km)

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

            # Обновляем детали платежа
            cursor.execute("SELECT ID FROM PAYMENT_DETAILS WHERE ORDER_ID = ?", (order_id,))
            payment_details = cursor.fetchone()
            if payment_details:
                payment_details_id = payment_details[0]
                sql_update_details = """
                UPDATE PAYMENT_DETAILS SET PAYMENT_METHOD = ?, PAYMENT_DATE = ? WHERE ID = ?
                """
                cursor.execute(sql_update_details, ("Картой", payment_date, payment_details_id))
            else:
                cursor.execute("SELECT MAX(ID) FROM PAYMENT_DETAILS")
                max_payment_details_id = cursor.fetchone()[0]
                new_payment_details_id = (max_payment_details_id or 0) + 1
                sql_payment_details = """
                INSERT INTO PAYMENT_DETAILS (ID, ORDER_ID, PAYMENT_METHOD, PAYMENT_DATE)
                VALUES (?, ?, ?, ?)
                """
                cursor.execute(sql_payment_details, (new_payment_details_id, order_id, "Картой", payment_date))

            con.commit()

            # Обновляем таблицы
            self.load_data("ORDERTABLE", self.tables["ORDERTABLE"])
            self.load_data("PAYMENT", self.tables["PAYMENT"])
            self.load_data("PAYMENT_DETAILS", self.tables["PAYMENT_DETAILS"])

            QMessageBox.information(None, "Успех", f"Заказ {order_id} успешно оплачен (статус: Оплачено)")
        except Exception as e:
            con.rollback()
            print(f"Ошибка при оплате: {e}")
            QMessageBox.critical(None, "Ошибка", f"Ошибка оплаты: {str(e)}")

    def pay_with_card(self):
        try:
            # Получаем данные из формы
            client_name = self.client_name_input.text().strip()
            phone = self.phone_input.text().strip()
            driver_id = self.driver_combo.currentData()
            tariff_id = self.tariff_combo.currentData()
            order_date = self.date_input.date().toString("yyyy-MM-dd")
            distance_text = self.distance_input.text().strip()
            payment_method = self.payment_method_input.currentText()
            transaction_number = self.transaction_number_input.text().strip()

            # Проверка заполнения всех полей
            if not client_name:
                QMessageBox.warning(None, "Ошибка", "Введите имя клиента")
                return
            if not phone:
                QMessageBox.warning(None, "Ошибка", "Введите телефон")
                return
            if not driver_id:
                QMessageBox.warning(None, "Ошибка", "Выберите водителя")
                return
            if not tariff_id:
                QMessageBox.warning(None, "Ошибка", "Выберите тариф")
                return
            if not distance_text:
                QMessageBox.warning(None, "Ошибка", "Введите расстояние")
                return

            # Проверка расстояния
            try:
                distance = float(distance_text)
                if distance <= 0:
                    QMessageBox.warning(None, "Ошибка", "Расстояние должно быть больше 0")
                    return
            except ValueError:
                QMessageBox.warning(None, "Ошибка", "Расстояние должно быть числом")
                return

            # Проверка стоимости
            cost_text = self.cost_label.text().replace("Стоимость: ", "").strip()
            try:
                cost = float(cost_text)
                if cost <= 0:
                    QMessageBox.warning(None, "Ошибка", "Стоимость должна быть больше 0")
                    return
            except ValueError:
                QMessageBox.warning(None, "Ошибка", "Ошибка расчета стоимости")
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
                cursor.execute(sql, (order_id, client_name, phone, driver_id, int(tariff_id), order_date, distance))

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

                # Сохраняем детали платежа
                cursor.execute("SELECT MAX(ID) FROM PAYMENT_DETAILS")
                max_payment_details_id = cursor.fetchone()[0]
                new_payment_details_id = (max_payment_details_id or 0) + 1

                sql_payment_details = """
                INSERT INTO PAYMENT_DETAILS (ID, ORDER_ID, PAYMENT_METHOD, TRANSACTION_NUMBER, PAYMENT_DATE)
                VALUES (?, ?, ?, ?, ?)
                """
                cursor.execute(sql_payment_details, (new_payment_details_id, order_id, payment_method, transaction_number if transaction_number else None, payment_date))

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

                # Обновляем детали платежа
                cursor.execute("SELECT ID FROM PAYMENT_DETAILS WHERE ORDER_ID = ?", (order_id,))
                payment_details_id = cursor.fetchone()
                if payment_details_id:
                    payment_details_id = payment_details_id[0]
                    sql_update_details = """
                    UPDATE PAYMENT_DETAILS SET PAYMENT_METHOD = ?, PAYMENT_DATE = ?, TRANSACTION_NUMBER = ? WHERE ID = ?
                    """
                    cursor.execute(sql_update_details, (payment_method, payment_date, transaction_number if transaction_number else None, payment_details_id))
                else:
                    cursor.execute("SELECT MAX(ID) FROM PAYMENT_DETAILS")
                    max_payment_details_id = cursor.fetchone()[0]
                    new_payment_details_id = (max_payment_details_id or 0) + 1
                    sql_payment_details = """
                    INSERT INTO PAYMENT_DETAILS (ID, ORDER_ID, PAYMENT_METHOD, TRANSACTION_NUMBER, PAYMENT_DATE)
                    VALUES (?, ?, ?, ?, ?)
                    """
                    cursor.execute(sql_payment_details, (new_payment_details_id, order_id, payment_method, transaction_number if transaction_number else None, payment_date))

            con.commit()

            # Обновляем таблицы
            self.load_data("ORDERTABLE", self.tables["ORDERTABLE"])
            self.load_data("PAYMENT", self.tables["PAYMENT"])
            self.load_data("PAYMENT_DETAILS", self.tables["PAYMENT_DETAILS"])

            # Очищаем форму
            self.client_name_input.clear()
            self.phone_input.clear()
            self.distance_input.clear()
            self.cost_label.setText("Стоимость: 0.0")
            self.driver_combo.setCurrentIndex(-1)
            self.car_combo.clear()
            self.tariff_combo.setCurrentIndex(-1)
            self.payment_method_input.setCurrentIndex(0)
            self.transaction_number_input.clear()

            QMessageBox.information(None, "Успех", "Оплата картой успешно обработана (статус: Оплачено)")
        except Exception as e:
            con.rollback()
            print(f"Ошибка при оплате картой: {e}")
            QMessageBox.critical(None, "Ошибка", f"Ошибка оплаты картой: {str(e)}")

    def load_data(self, table_name, table_widget):
        try:
            cursor = con.cursor()
            if table_name == "CAR":
                cursor.execute("""
                    SELECT CAR.ID, MODEL, LICENSE_PLATE, DRIVER.FULL_NAME, TARIFF.NAME 
                    FROM CAR
                    LEFT JOIN DRIVER ON CAR.DRIVER_ID = DRIVER.ID
                    LEFT JOIN TARIFF ON CAR.TARIFF_ID = TARIFF.ID
                """)
            elif table_name == "ORDERTABLE":
                cursor.execute("""
                    SELECT ORDERTABLE.ID, CLIENT_NAME, PHONE, DRIVER.FULL_NAME, TARIFF.NAME, ORDER_DATE, DISTANCE
                    FROM ORDERTABLE
                    LEFT JOIN DRIVER ON ORDERTABLE.DRIVER_ID = DRIVER.ID
                    LEFT JOIN TARIFF ON ORDERTABLE.TARIFF_ID = TARIFF.ID
                """)
            elif table_name == "PAYMENT":
                cursor.execute("""
                    SELECT PAYMENT.ID, ORDERTABLE.CLIENT_NAME, PAYMENT.AMOUNT, PAYMENT.PAID_DATE, PAYMENT.PAYMENT_STATUS, PAYMENT.ORDER_ID
                    FROM PAYMENT
                    LEFT JOIN ORDERTABLE ON PAYMENT.ORDER_ID = ORDERTABLE.ID
                """)
            elif table_name == "PAYMENT_DETAILS":
                cursor.execute("""
                    SELECT PAYMENT_DETAILS.ID, ORDERTABLE.CLIENT_NAME, PAYMENT_METHOD, TRANSACTION_NUMBER, PAYMENT_DATE, PAYMENT_DETAILS.ORDER_ID
                    FROM PAYMENT_DETAILS
                    LEFT JOIN ORDERTABLE ON PAYMENT_DETAILS.ORDER_ID = ORDERTABLE.ID
                """)
            else:
                cursor.execute(f"SELECT * FROM {table_name}")

            rows = cursor.fetchall()

            if rows:
                if table_name == "PAYMENT":
                    columns = ["ID", "CLIENT_NAME", "AMOUNT", "PAID_DATE", "PAYMENT_STATUS", "ORDER_ID"]
                    table_widget.setColumnCount(len(columns) - 1)  # Скрываем ORDER_ID
                    table_widget.setHorizontalHeaderLabels(["ID", "Клиент", "Сумма", "Дата оплаты", "Статус"])
                elif table_name == "PAYMENT_DETAILS":
                    columns = ["ID", "CLIENT_NAME", "PAYMENT_METHOD", "TRANSACTION_NUMBER", "PAYMENT_DATE", "ORDER_ID"]
                    table_widget.setColumnCount(len(columns) - 1)  # Скрываем ORDER_ID
                    table_widget.setHorizontalHeaderLabels(["ID", "Клиент", "Метод оплаты", "Номер транзакции", "Дата"])
                else:
                    columns = [desc[0] for desc in cursor.description]
                    table_widget.setColumnCount(len(columns))
                    table_widget.setHorizontalHeaderLabels(columns)

                table_widget.setRowCount(len(rows))

                # Загружаем данные для выпадающих списков
                driver_list = [""]  # Пустой выбор
                tariff_list = [""]  # Пустой выбор
                order_list = [""]  # Пустой выбор
                payment_status_list = ["Оплачено", "Не оплачено"]
                cursor.execute("SELECT FULL_NAME FROM DRIVER")
                driver_list.extend([row[0] for row in cursor.fetchall()])
                cursor.execute("SELECT NAME FROM TARIFF")
                tariff_list.extend([row[0] for row in cursor.fetchall()])
                cursor.execute("SELECT ID FROM ORDERTABLE")
                order_list.extend([str(row[0]) for row in cursor.fetchall()])

                for row_idx, row in enumerate(rows):
                    for col_idx, value in enumerate(row):
                        if table_name == "CAR" and col_idx == 3:  # DRIVER
                            combo = QComboBox()
                            combo.addItems(driver_list)
                            combo.setCurrentText(str(value) if value else "")
                            table_widget.setCellWidget(row_idx, col_idx, combo)
                        elif table_name == "CAR" and col_idx == 4:  # TARIFF
                            combo = QComboBox()
                            combo.addItems(tariff_list)
                            combo.setCurrentText(str(value) if value else "")
                            table_widget.setCellWidget(row_idx, col_idx, combo)
                        elif table_name == "ORDERTABLE" and col_idx == 3:  # DRIVER
                            combo = QComboBox()
                            combo.addItems(driver_list)
                            combo.setCurrentText(str(value) if value else "")
                            table_widget.setCellWidget(row_idx, col_idx, combo)
                        elif table_name == "ORDERTABLE" and col_idx == 4:  # TARIFF
                            combo = QComboBox()
                            combo.addItems(tariff_list)
                            combo.setCurrentText(str(value) if value else "")
                            table_widget.setCellWidget(row_idx, col_idx, combo)
                        elif table_name == "PAYMENT" and col_idx == 1:  # CLIENT_NAME
                            item = QTableWidgetItem(str(value) if value is not None else "")
                            item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Только для чтения
                            table_widget.setItem(row_idx, col_idx, item)
                        elif table_name == "PAYMENT" and col_idx == 4:  # PAYMENT_STATUS
                            combo = QComboBox()
                            combo.addItems(payment_status_list)
                            combo.setCurrentText(str(value) if value else "Не оплачено")
                            table_widget.setCellWidget(row_idx, col_idx, combo)
                        elif table_name == "PAYMENT" and col_idx == 5:  # ORDER_ID (скрытый столбец)
                            continue  # Пропускаем отображение
                        elif table_name == "PAYMENT_DETAILS" and col_idx == 1:  # CLIENT_NAME
                            item = QTableWidgetItem(str(value) if value is not None else "")
                            item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Только для чтения
                            table_widget.setItem(row_idx, col_idx, item)
                        elif table_name == "PAYMENT_DETAILS" and col_idx == 5:  # ORDER_ID (скрытый столбец)
                            continue  # Пропускаем отображение
                        else:
                            item = QTableWidgetItem(str(value) if value is not None else "")
                            item.setFlags(item.flags() | Qt.ItemIsEditable)
                            table_widget.setItem(row_idx, col_idx, item)

            else:
                table_widget.setRowCount(0)
                table_widget.setColumnCount(0)

            table_widget.resizeColumnsToContents()
        except Exception as e:
            print(f"Ошибка при загрузке данных из таблицы {table_name}: {e}")
            QMessageBox.critical(None, "Ошибка", f"Ошибка при загрузке данных: {str(e)}")

    def add_row(self, table_name):
        try:
            table_widget = self.tables[table_name]
            row_pos = table_widget.rowCount()
            table_widget.insertRow(row_pos)

            col_count = table_widget.columnCount()

            # Загружаем данные для выпадающих списков
            cursor = con.cursor()
            driver_list = [""]  # Пустой выбор
            tariff_list = [""]  # Пустой выбор
            order_list = [""]  # Пустой выбор
            payment_status_list = ["Оплачено", "Не оплачено"]
            cursor.execute("SELECT FULL_NAME FROM DRIVER")
            driver_list.extend([row[0] for row in cursor.fetchall()])
            cursor.execute("SELECT NAME FROM TARIFF")
            tariff_list.extend([row[0] for row in cursor.fetchall()])
            cursor.execute("SELECT ID FROM ORDERTABLE")
            order_list.extend([str(row[0]) for row in cursor.fetchall()])

            for col in range(col_count):
                if table_name == "CAR":
                    if col == 3:  # DRIVER
                        combo = QComboBox()
                        combo.addItems(driver_list)
                        table_widget.setCellWidget(row_pos, col, combo)
                    elif col == 4:  # TARIFF
                        combo = QComboBox()
                        combo.addItems(tariff_list)
                        table_widget.setCellWidget(row_pos, col, combo)
                    else:
                        item = QTableWidgetItem("")
                        table_widget.setItem(row_pos, col, item)
                elif table_name == "ORDERTABLE":
                    if col == 3:  # DRIVER
                        combo = QComboBox()
                        combo.addItems(driver_list)
                        table_widget.setCellWidget(row_pos, col, combo)
                    elif col == 4:  # TARIFF
                        combo = QComboBox()
                        combo.addItems(tariff_list)
                        table_widget.setCellWidget(row_pos, col, combo)
                    else:
                        item = QTableWidgetItem("")
                        table_widget.setItem(row_pos, col, item)
                elif table_name == "PAYMENT":
                    if col == 1:  # CLIENT_NAME (не редактируемое поле)
                        item = QTableWidgetItem("")
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Только для чтения
                        table_widget.setItem(row_pos, col, item)
                    elif col == 4:  # PAYMENT_STATUS
                        combo = QComboBox()
                        combo.addItems(payment_status_list)
                        combo.setCurrentText("Не оплачено")
                        table_widget.setCellWidget(row_pos, col, combo)
                    else:
                        item = QTableWidgetItem("")
                        table_widget.setItem(row_pos, col, item)
                elif table_name == "PAYMENT_DETAILS":
                    if col == 1:  # CLIENT_NAME (не редактируемое поле)
                        item = QTableWidgetItem("")
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Только для чтения
                        table_widget.setItem(row_pos, col, item)
                    else:
                        item = QTableWidgetItem("")
                        table_widget.setItem(row_pos, col, item)
                else:
                    item = QTableWidgetItem("")
                    table_widget.setItem(row_pos, col, item)

        except Exception as e:
            print(f"Ошибка при добавлении строки в таблицу {table_name}: {e}")
            QMessageBox.critical(None, "Ошибка", f"Ошибка при добавлении строки: {str(e)}")

    def save_changes(self, table_name):
        try:
            table_widget = self.tables[table_name]
            cursor = con.cursor()

            # Получаем все столбцы из базы данных
            cursor.execute(f"SELECT * FROM {table_name} WHERE 1=0")
            columns = [desc[0] for desc in cursor.description]

            if not columns:
                QMessageBox.warning(None, "Предупреждение", "Нет столбцов для сохранения")
                return

            for row in range(table_widget.rowCount()):
                row_data = []
                all_empty = True
                for col in range(table_widget.columnCount()):
                    if table_name == "CAR" and col in [3, 4]:  # DRIVER, TARIFF
                        combo = table_widget.cellWidget(row, col)
                        if combo and combo.currentText():
                            if col == 3:  # DRIVER
                                cursor.execute("SELECT ID FROM DRIVER WHERE FULL_NAME = ?", (combo.currentText(),))
                                result = cursor.fetchone()
                                value = result[0] if result else None
                            elif col == 4:  # TARIFF
                                cursor.execute("SELECT ID FROM TARIFF WHERE NAME = ?", (combo.currentText(),))
                                result = cursor.fetchone()
                                value = result[0] if result else None
                        else:
                            value = None
                    elif table_name == "ORDERTABLE" and col in [3, 4]:  # DRIVER, TARIFF
                        combo = table_widget.cellWidget(row, col)
                        if combo and combo.currentText():
                            if col == 3:  # DRIVER
                                cursor.execute("SELECT ID FROM DRIVER WHERE FULL_NAME = ?", (combo.currentText(),))
                                result = cursor.fetchone()
                                value = result[0] if result else None
                            elif col == 4:  # TARIFF
                                cursor.execute("SELECT ID FROM TARIFF WHERE NAME = ?", (combo.currentText(),))
                                result = cursor.fetchone()
                                value = result[0] if result else None
                        else:
                            value = None
                    elif table_name == "PAYMENT" and col == 1:  # CLIENT_NAME (игнорируем, используем ORDER_ID)
                        continue  # Пропускаем это поле
                    elif table_name == "PAYMENT" and col == 4:  # PAYMENT_STATUS
                        combo = table_widget.cellWidget(row, col)
                        value = combo.currentText() if combo else "Не оплачено"
                    elif table_name == "PAYMENT_DETAILS" and col == 1:  # CLIENT_NAME (игнорируем, используем ORDER_ID)
                        continue  # Пропускаем это поле
                    else:
                        item = table_widget.item(row, col)
                        value = item.text().strip() if item else ""
                        value = value if value != "" else None
                    row_data.append(value)
                    if value:
                        all_empty = False

                if all_empty:
                    continue

                if table_name in ["PAYMENT", "PAYMENT_DETAILS"]:
                    # Добавляем ORDER_ID в данные для сохранения
                    client_name = table_widget.item(row, 1).text().strip()  # Получаем CLIENT_NAME из столбца
                    if not client_name:
                        QMessageBox.warning(None, "Ошибка", f"Клиент не указан в строке {row + 1}. Сохранение отменено.")
                        continue
                    cursor.execute("SELECT ID FROM ORDERTABLE WHERE CLIENT_NAME = ?", (client_name,))
                    order_id = cursor.fetchone()
                    if not order_id:
                        QMessageBox.warning(None, "Ошибка", f"Заказ для клиента {client_name} не найден. Сохранение отменено.")
                        continue
                    row_data.insert(1, order_id[0])  # Вставляем ORDER_ID на позицию 1

                # Проверяем, существует ли строка с таким ID в базе
                id_value = row_data[0]  # ID в первом столбце
                exists = False
                if id_value:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE ID = ?", (id_value,))
                    exists = cursor.fetchone()[0] > 0

                if not exists:
                    # Новая строка - генерируем ID
                    cursor.execute(f"SELECT MAX(ID) FROM {table_name}")
                    max_id = cursor.fetchone()[0]
                    new_id = (max_id or 0) + 1

                    while True:
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE ID = ?", (new_id,))
                        if cursor.fetchone()[0] == 0:
                            break
                        new_id += 1

                    row_data[0] = new_id
                    placeholders = ", ".join(["?"] * len(columns))
                    sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                else:
                    # Существующая строка - используем UPDATE
                    set_clause = ", ".join([f"{col} = ?" for col in columns[1:]])
                    sql = f"UPDATE {table_name} SET {set_clause} WHERE ID = ?"
                    row_data = row_data[1:] + [row_data[0]]

                cursor.execute(sql, row_data)

            con.commit()

            self.load_data(table_name, table_widget)
            QMessageBox.information(None, "Успех", "Изменения успешно сохранены")
        except Exception as e:
            con.rollback()
            print(f"Ошибка при сохранении изменений: {e}")
            QMessageBox.critical(None, "Ошибка", f"Ошибка сохранения: {str(e)}")

    def delete_row(self, table_name):
        try:
            table_widget = self.tables[table_name]
            selected = table_widget.selectedIndexes()

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
                    id_item = table_widget.item(row, 0)  # ID в первом столбце
                    if id_item and id_item.text().strip():
                        id_value = id_item.text().strip()
                        cursor.execute(f"DELETE FROM {table_name} WHERE ID = ?", (id_value,))
                        table_widget.removeRow(row)

                con.commit()

                self.load_data(table_name, table_widget)
                QMessageBox.information(None, "Успех", "Строка успешно удалена")
        except Exception as e:
            con.rollback()
            print(f"Ошибка при удалении строки: {e}")
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