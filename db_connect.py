import fdb

def connect_to_db():
    con = fdb.connect(
        dsn='localhost:C:/Program Files/RedDatabase/taxopark',
        user='SYSDBA',
        password='masterkey',
    )
    return con
