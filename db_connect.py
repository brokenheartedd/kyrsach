import fdb


def get_connection():
    return fdb.connect(
        dsn=r'C:\Program Files\RedDatabase\TAXOPARK',
        user='SYSDBA',
        password='masterkey',
        charset='UTF8'
    )

def get_orders():
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT ORDER_ID, ORDER_DATE, CLIENT_PHONE, DRIVER_ID, TARIFF_ID, DISTANCE_KM FROM ORDERTABLE")
    rows = cur.fetchall()
    con.close()
    return rows
