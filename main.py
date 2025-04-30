import sys
import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QTableView, QAbstractItemView, QPushButton, QHBoxLayout
from PyQt5.QtGui import QStandardItemModel, QStandardItem
import fdb


con = fdb.connect(
    dsn='localhost:D:/Dmitry/Projects/leonid-kyrsach/kyrsach-db/TAXOPARK.DB', # ToDo: вынести в конфиг
    user='SYSDBA',
    password='masterkey',
    charset='UTF8')


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Настройка окна
        self.setWindowTitle("Таксопарк 666")
        self.setGeometry(100, 100, 800, 600)

        # Создание QTabWidget
        tab_widget = QTabWidget()
        self.setCentralWidget(tab_widget)

        # Создание вкладок
        self.cars_tab = QWidget()
        self.drivers_tab = QWidget()
        self.ordertable_tab = QWidget()
        self.payments_tab = QWidget()
        self.tariffs_tab = QWidget()

        # Добавление вкладок
        tab_widget.addTab(self.cars_tab, "Машины")
        tab_widget.addTab(self.drivers_tab, "Водители")
        tab_widget.addTab(self.ordertable_tab, "Заказы")
        tab_widget.addTab(self.payments_tab, "Платежи")
        tab_widget.addTab(self.tariffs_tab, "Тарифы")

        # Настроим таблицы для каждой вкладки
        self.setup_table(self.cars_tab, "CAR")
        self.setup_table(self.drivers_tab, "DRIVER")
        self.setup_table(self.ordertable_tab, "ORDERTABLE")
        self.setup_table(self.payments_tab, "PAYMENT")
        self.setup_table(self.tariffs_tab, "TARIFF")

    def setup_table(self, tab, table_name):
        layout = QVBoxLayout()
        table_view = QTableView()
        table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Подключение к базе данных и выполнение запроса
        cursor = con.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        # Создание модели данных
        model = QStandardItemModel(len(rows), len(columns))
        model.setHorizontalHeaderLabels(columns)

        for row_idx, row in enumerate(rows):
            for col_idx, value in enumerate(row):
                item = QStandardItem(str(value))
                model.setItem(row_idx, col_idx, item)

        table_view.setModel(model)
        table_view.resizeColumnsToContents()

        # Добавление кнопок
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

    def add_row(self, table_name):
        print(f"Add row to {table_name}")  # Placeholder for adding a row

    def save_changes(self, table_name):
        print(f"Save changes to {table_name}")  # Placeholder for saving changes

    def delete_row(self, table_name):
        print(f"Delete row from {table_name}")  # Placeholder for deleting a row


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
