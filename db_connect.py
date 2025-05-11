import fdb

def connect_to_db():
    con = fdb.connect(
        dsn='C:/Users/user/Documents/TAXI',  # ToDo: вынести в конфиг
        user='SYSDBA',
        password='masterkey',
    )
    return con
