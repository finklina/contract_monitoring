import sqlite3
from datetime import datetime

DATABASE = 'contracts.db'

def get_db():
    """Установка соединения с базой данных"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Создание всех таблиц по вашей структуре"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Таблица service
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS service (
            id_service INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name VARCHAR(100) NOT NULL
        )
    ''')
    
    # Таблица client
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS client (
            id_client INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name VARCHAR(150) NOT NULL,
            client_INN VARCHAR(12),
            client_phone_number VARCHAR(20)
        )
    ''')
    
    # Таблица manager
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS manager (
            id_manager INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_name VARCHAR(150) NOT NULL,
            manager_email VARCHAR(100)
        )
    ''')
    
    # Таблица object
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS object (
            id_object INTEGER PRIMARY KEY AUTOINCREMENT,
            id_service INTEGER NOT NULL,
            price INTEGER,
            finishing_date DATE,
            FOREIGN KEY (id_service) REFERENCES service(id_service)
        )
    ''')
    
    # Таблица contract
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contract (
            contract_number VARCHAR(50) NOT NULL UNIQUE,
            signing_contract_date DATE NOT NULL,
            status VARCHAR(20) DEFAULT 'В работе',
            type VARCHAR(1) DEFAULT 'с',
            id_client INTEGER NOT NULL,
            id_manager INTEGER,
            id_object INTEGER,
            FOREIGN KEY (id_client) REFERENCES client(id_client),
            FOREIGN KEY (id_manager) REFERENCES manager(id_manager),
            FOREIGN KEY (id_object) REFERENCES object(id_object)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("База данных инициализирована")