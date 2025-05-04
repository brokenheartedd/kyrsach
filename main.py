import sys
import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget,
    QVBoxLayout, QTableView, QAbstractItemView,
    QPushButton, QHBoxLayout, QMessageBox
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
import fdb

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

    def load_data(self, table_name, model):
        cursor = con.cursor()
        try:
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            print(f"Loaded {len(rows)} rows from {table_name}: {rows}")
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

                print(f"Executing SQL: {sql} with data: {row_data}")
                cursor.execute(sql, row_data)

            con.commit()
            print("Changes committed successfully")

            # Проверяем, что данные действительно сохранены
            cursor.execute(f"SELECT * FROM {list_name}")
            saved_data = cursor.fetchall()
            print(f"Data in {list_name} after commit: {saved_data}")

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