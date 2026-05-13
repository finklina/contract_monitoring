from database import get_db, init_db
import random
from datetime import datetime, timedelta

def load_test_data():
    """Заполнение базы данных тестовыми данными (50 договоров)"""
    conn = get_db()
    
    count = conn.execute('SELECT COUNT(*) as cnt FROM contract').fetchone()['cnt']
    if count > 0:
        print(f"В базе уже есть {count} договоров. Пропускаем загрузку.")
        conn.close()
        return
    
    services = ['Аудит', 'Оценка', 'Консалтинг', 'Юридические услуги', 'Налоговое консультирование']
    for s in services:
        conn.execute('INSERT INTO service (service_name) VALUES (?)', (s,))
    
    managers = [
        ('Медникова Екатерина', 'mednikova@rc-prm.ru'),
        ('Ольга Козырева', 'ok@rc-prm.ru'),
        ('Дмитрий Козырев', 'dk@rc-prm.ru'),
    ]
    for m in managers:
        conn.execute('INSERT INTO manager (manager_name, manager_email) VALUES (?, ?)', (m[0], m[1]))
    
    clients_data = [
        ('ООО "Альфа"', '7701010101', '+7(495)111-22-33'),
        ('ООО "Бета"', '7702020202', '+7(495)222-33-44'),
        ('АО "Гамма"', '7703030303', '+7(495)333-44-55'),
        ('ООО "Дельта"', '7704040404', '+7(495)444-55-66'),
        ('ЗАО "Эпсилон"', '7705050505', '+7(495)555-66-77'),
        ('ООО "Дзета"', '7706060606', '+7(495)666-77-88'),
        ('АО "Эта"', '7707070707', '+7(495)777-88-99'),
        ('ООО "Тета"', '7708080808', '+7(495)888-99-00'),
        ('ЗАО "Йота"', '7709090909', '+7(495)999-00-11'),
        ('ООО "Каппа"', '7710101010', '+7(495)000-11-22'),
        ('ООО "Лямбда"', '7711111111', '+7(495)111-22-33'),
        ('АО "Мю"', '7712121212', '+7(495)222-33-44'),
        ('ООО "Ню"', '7713131313', '+7(495)333-44-55'),
        ('ЗАО "Кси"', '7714141414', '+7(495)444-55-66'),
        ('ООО "Омикрон"', '7715151515', '+7(495)555-66-77'),
        ('АО "Пи"', '7716161616', '+7(495)666-77-88'),
        ('ООО "Ро"', '7717171717', '+7(495)777-88-99'),
        ('ЗАО "Сигма"', '7718181818', '+7(495)888-99-00'),
        ('ООО "Тау"', '7719191919', '+7(495)999-00-11'),
        ('АО "Ипсилон"', '7720202020', '+7(495)000-11-22'),
    ]
    
    for c in clients_data:
        conn.execute('INSERT INTO client (client_name, client_INN, client_phone_number) VALUES (?, ?, ?)', c)
    
    service_ids = [s['id_service'] for s in conn.execute('SELECT id_service FROM service').fetchall()]
    manager_ids = [m['id_manager'] for m in conn.execute('SELECT id_manager, manager_name FROM manager').fetchall()]
    client_ids = [c['id_client'] for c in conn.execute('SELECT id_client, client_name FROM client').fetchall()]
    
    
    contracts = []
    start_date = datetime(2023, 1, 1)
    
    for i in range(1, 51):
        contract_number = f"Д-{i:03d}"
        
        days_offset = random.randint(0, 1095)  # 3 года
        signing_date = start_date + timedelta(days=days_offset)
        date_str = signing_date.strftime('%Y-%m-%d')
        
        status = random.choice(['Выполнен', 'Выполнен', 'Выполнен', 'Выполнен', 'Выполнен', 'Выполнен', 'В работе', 'В работе', 'В работе', 'Просрочен'][:10])
        
        contract_type = random.choice(['н', 'с', 'н', 'с', 'н', 'с', 'н', 'с', 'н', 'с'])
        
        client_id = random.choice(client_ids)
        
        manager_id = random.choice(manager_ids)
        
        service_id = random.choice(service_ids)
        
        price = random.randint(50000, 5000000)

        finishing_date = signing_date + timedelta(days=random.randint(30, 365))
        finishing_date_str = finishing_date.strftime('%Y-%m-%d')
        
        contracts.append({
            'number': contract_number,
            'date': date_str,
            'status': status,
            'type': contract_type,
            'client_id': client_id,
            'manager_id': manager_id,
            'service_id': service_id,
            'price': price,
            'finishing_date': finishing_date_str
        })
    
    for contract in contracts:
        conn.execute('''
            INSERT INTO object (id_service, price, finishing_date)
            VALUES (?, ?, ?)
        ''', (contract['service_id'], contract['price'], contract['finishing_date']))
        
        object_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        
        conn.execute('''
            INSERT INTO contract (contract_number, signing_contract_date, status, type, id_client, id_manager, id_object)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (contract['number'], contract['date'], contract['status'], 
              contract['type'], contract['client_id'], contract['manager_id'], object_id))
    
    conn.commit()
    
    total = conn.execute('SELECT COUNT(*) as cnt FROM contract').fetchone()['cnt']
    conn.close()
    
    print(f"Загружено {total} договоров")
    print(f"  - Менеджеры: {len(managers)}")
    print(f"  - Клиенты: {len(clients_data)}")
    print(f"  - Услуги: {len(services)}")

if __name__ == '__main__':
    init_db()
    load_test_data()
    print("Готово!")