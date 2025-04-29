from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
from db_connect import connect_to_db

class OrderTableWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Список заказов")
        self.setGeometry(100, 100, 800, 400)

        self.layout = QVBoxLayout()
        self.table = QTableWidget()
        self.layout.addWidget(self.table)
        self.setLayout(self.layout)

        self.load_data()

    def load_data(self):
        connection = connect_to_db()
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM ORDERTABLE")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        self.table.setColumnCount(len(columns))
        self.table.setRowCount(len(rows))
        self.table.setHorizontalHeaderLabels(columns)

        for row_idx, row_data in enumerate(rows):
            for col_idx, cell in enumerate(row_data):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(cell)))

        connection.close()


if __name__ == '__main__':
    app = QApplication([])
    window = OrderTableWindow()
    window.show()
    app.exec_()
