import fdb

def connect_to_db():
    con = fdb.connect(
        dsn='C:/Program Files/RedDatabase/TAXOPARK',  # ToDo: вынести в конфиг
        user='SYSDBA',
        password='masterkey',
    )
    return con
