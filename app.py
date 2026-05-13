from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from database import get_db
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from io import BytesIO
from flask import Response
from datetime import datetime
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

try:
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
    FONT_NAME = 'DejaVuSans'
except:
    try:
        pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
        FONT_NAME = 'Arial'
    except:
        FONT_NAME = 'Helvetica'
        print("ВНИМАНИЕ: Русский шрифт не загружен, используем Helvetica")

app = Flask(__name__)

app.secret_key = 'secret-key-for-contract-monitoring'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_available_years():
    """Получение списка лет, за которые есть договоры"""
    conn = get_db()
    years = conn.execute('''
        SELECT DISTINCT strftime('%Y', signing_contract_date) as year 
        FROM contract 
        ORDER BY year DESC
    ''').fetchall()
    conn.close()
    return [str(y['year']) for y in years]

def get_kpi():
    """Расчёт ключевых показателей для карточек за всё время"""
    conn = get_db()
    
    total = conn.execute('SELECT COUNT(*) as cnt FROM contract').fetchone()['cnt']
    completed = conn.execute('SELECT COUNT(*) as cnt FROM contract WHERE status = "Выполнен"').fetchone()['cnt']
    in_progress = conn.execute('SELECT COUNT(*) as cnt FROM contract WHERE status = "В работе"').fetchone()['cnt']
    overdue = conn.execute('SELECT COUNT(*) as cnt FROM contract WHERE status = "Просрочен"').fetchone()['cnt']
    
    total_amount = conn.execute('SELECT SUM(price) as total FROM object').fetchone()['total'] or 0
    
    conn.close()
    
    return {
        'total': total,
        'completed': completed,
        'in_progress': in_progress,
        'overdue': overdue,
        'total_amount': total_amount
    }

def get_stats_for_period(year, month_from=None, month_to=None):
    """Возвращает статистику по договорам за указанный период"""
    conn = get_db()
    
    where_clause = "strftime('%Y', c.signing_contract_date) = ?"
    params = [str(year)]
    
    if month_from and month_to:
        where_clause += " AND CAST(strftime('%m', c.signing_contract_date) AS INTEGER) BETWEEN ? AND ?"
        params.extend([month_from, month_to])
    elif month_from:
        where_clause += " AND strftime('%m', c.signing_contract_date) = ?"
        params.append(str(month_from).zfill(2))
    
    count_query = f'''
        SELECT 
            SUM(CASE WHEN c.type = 'н' THEN 1 ELSE 0 END) as new_count,
            SUM(CASE WHEN c.type = 'с' THEN 1 ELSE 0 END) as old_count,
            SUM(CASE WHEN c.status = 'Выполнен' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN c.status = 'В работе' THEN 1 ELSE 0 END) as in_progress,
            COUNT(*) as total
        FROM contract c
        WHERE {where_clause}
    '''
 
    amount_query = f'''
        SELECT 
            SUM(CASE WHEN c.type = 'н' THEN o.price ELSE 0 END) as new_amount,
            SUM(CASE WHEN c.type = 'с' THEN o.price ELSE 0 END) as old_amount,
            SUM(CASE WHEN c.status = 'Выполнен' THEN o.price ELSE 0 END) as completed_amount,
            SUM(CASE WHEN c.status = 'В работе' THEN o.price ELSE 0 END) as in_progress_amount,
            SUM(o.price) as total_amount
        FROM contract c
        JOIN object o ON c.id_object = o.id_object
        WHERE {where_clause}
    '''
    
    count_result = conn.execute(count_query, params).fetchone()
    amount_result = conn.execute(amount_query, params).fetchone()
    
    if month_from and month_to:
        months_range = range(month_from, month_to + 1)
    elif month_from:
        months_range = range(month_from, month_from + 1)
    else:
        months_range = range(1, 13)
    
    labels = [str(m) for m in months_range]
    totals = []
    amounts = []
    
    for month in months_range:
        month_str = str(month).zfill(2)
        query = '''
            SELECT COUNT(*) as total, SUM(o.price) as total_amount
            FROM contract c
            JOIN object o ON c.id_object = o.id_object
            WHERE strftime("%Y", c.signing_contract_date) = ? 
            AND strftime("%m", c.signing_contract_date) = ?
        '''
        res = conn.execute(query, (str(year), month_str)).fetchone()
        totals.append(res['total'] or 0)
        amounts.append(res['total_amount'] or 0)
    
    conn.close()
    
    return {
        'year': year,
        'month_from': month_from,
        'month_to': month_to,
        'new_count': count_result['new_count'] or 0,
        'old_count': count_result['old_count'] or 0,
        'completed': count_result['completed'] or 0,
        'in_progress': count_result['in_progress'] or 0,
        'total': count_result['total'] or 0,
        'new_amount': amount_result['new_amount'] or 0,
        'old_amount': amount_result['old_amount'] or 0,
        'completed_amount': amount_result['completed_amount'] or 0,
        'in_progress_amount': amount_result['in_progress_amount'] or 0,
        'total_amount': amount_result['total_amount'] or 0,
        'monthly_totals': totals,
        'monthly_amounts': amounts,
        'months_labels': labels
    }
    

def get_monthly_stats_for_year(year, month_from=None, month_to=None):
    """Получение помесячной статистики для графиков"""
    conn = get_db()
    
    if month_from and month_to:
        months_range = range(month_from, month_to + 1)
    elif month_from:
        months_range = range(month_from, month_from + 1)
    else:
        months_range = range(1, 13)
    
    labels = [str(m) for m in months_range]
    totals = [0] * len(months_range)
    amounts = [0] * len(months_range)
    
    for idx, month in enumerate(months_range):
        month_str = str(month).zfill(2)
        query = '''
            SELECT COUNT(*) as total, SUM(ci.price) as total_amount
            FROM contract c
            JOIN contract_item ci ON c.id_contract = ci.id_contract
            WHERE strftime('%Y', sighing_contract_date) = ? AND strftime('%m',  sighing_contract_date) = ?
        '''
        result = conn.execute(query, (str(year), month_str)).fetchone()
        totals[idx] = result['total'] or 0
        amounts[idx] = result['total_amount'] or 0
    
    conn.close()
    return {'labels': labels, 'totals': totals, 'amounts': amounts}

# Начальная страница, маршрут для вывода списка договоров
@app.route('/')
def contracts():
    conn = get_db()
    all_contracts = conn.execute('''
        SELECT 
            c.contract_number,
            c.signing_contract_date,
            c.status,
            c.type,
            cl.client_name,
            cl.client_INN,
            cl.client_phone_number,
            m.manager_name,
            m.manager_email,
            s.service_name,
            o.price,
            o.finishing_date
        FROM contract c
        JOIN client cl ON c.id_client = cl.id_client
        LEFT JOIN manager m ON c.id_manager = m.id_manager
        LEFT JOIN object o ON c.id_object = o.id_object
        LEFT JOIN service s ON o.id_service = s.id_service
        ORDER BY c.signing_contract_date DESC
    ''').fetchall()
    conn.close()
    return render_template('contracts.html', contracts=all_contracts)

# Маршрут для формирования дашборда
@app.route('/dashboard')
def dashboard():
    conn = get_db()
    
    total = conn.execute('SELECT COUNT(*) as cnt FROM contract').fetchone()['cnt']
    completed = conn.execute('SELECT COUNT(*) as cnt FROM contract WHERE status = "Выполнен"').fetchone()['cnt']
    in_progress = conn.execute('SELECT COUNT(*) as cnt FROM contract WHERE status = "В работе"').fetchone()['cnt']
    overdue = conn.execute('SELECT COUNT(*) as cnt FROM contract WHERE status = "Просрочен"').fetchone()['cnt']
    total_amount = conn.execute('SELECT SUM(price) as total FROM object').fetchone()['total'] or 0
    
    kpi = {
        'total': total, 
        'completed': completed, 
        'in_progress': in_progress, 
        'overdue': overdue, 
        'total_amount': total_amount
    }
    
    years = conn.execute('''
        SELECT DISTINCT strftime("%Y", signing_contract_date) as year 
        FROM contract 
        ORDER BY year DESC
    ''').fetchall()
    years = [str(y['year']) for y in years]
    
    conn.close()
    
    period1 = get_stats_for_period(years[0] if len(years) > 0 else 2024)
    period2 = get_stats_for_period(years[1] if len(years) > 1 else years[0]) if len(years) > 1 else None
    
    return render_template('dashboard.html', 
                           years=years,
                           kpi=kpi,
                           period1=period1,
                           period2=period2)

# Маршрут для добавления нового договора
@app.route('/contracts/new', methods=['GET', 'POST'])
def contract_new():
    conn = get_db()
    services = conn.execute('SELECT id_service, service_name FROM service').fetchall()
    managers = conn.execute('SELECT id_manager, manager_name FROM manager').fetchall()
    
    if request.method == 'POST':
        try:
            contract_number = request.form.get('contract_number')
            signing_date = request.form.get('signing_contract_date')
            status = request.form.get('status', 'В работе')
            contract_type = request.form.get('type', 'с')
            
            existing = conn.execute('SELECT contract_number FROM contract WHERE contract_number = ?', 
                                     (contract_number,)).fetchone()
            if existing:
                flash('Договор с таким номером уже существует!', 'danger')
                return redirect(url_for('contract_new'))
            
            client_name = request.form.get('client_name')
            client_inn = request.form.get('client_INN', '')
            client_phone = request.form.get('client_phone_number', '')
            
            client = conn.execute('SELECT id_client FROM client WHERE client_name = ?', (client_name,)).fetchone()
            if client:
                client_id = client['id_client']
                conn.execute('''
                    UPDATE client SET client_INN=?, client_phone_number=?
                    WHERE id_client=?
                ''', (client_inn, client_phone, client_id))
            else:
                conn.execute('''
                    INSERT INTO client (client_name, client_INN, client_phone_number)
                    VALUES (?, ?, ?)
                ''', (client_name, client_inn, client_phone))
                client_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            
            manager_name = request.form.get('manager_name')
            manager_id = None
            if manager_name:
                manager_email = request.form.get('manager_email', '')
                manager = conn.execute('''
                    SELECT id_manager FROM manager WHERE manager_name = ? AND manager_email = ?
                ''', (manager_name, manager_email)).fetchone()
                if manager:
                    manager_id = manager['id_manager']
                else:
                    conn.execute('''
                        INSERT INTO manager (manager_name, manager_email)
                        VALUES (?, ?)
                    ''', (manager_name, manager_email))
                    manager_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            
            service_id = request.form.get('service_id')
            object_id = None
            if service_id:
                price = float(request.form.get('price', 0))
                finishing_date = request.form.get('finishing_date') or None
                
                conn.execute('''
                    INSERT INTO object (id_service, price, finishing_date)
                    VALUES (?, ?, ?)
                ''', (service_id, price, finishing_date))
                object_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            
            conn.execute('''
                INSERT INTO contract (contract_number, signing_contract_date, status, type, id_client, id_manager, id_object)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (contract_number, signing_date, status, contract_type, client_id, manager_id, object_id))
            
            conn.commit()
            conn.close()
            
            flash('Договор успешно добавлен!', 'success')
            return redirect(url_for('contracts'))
            
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'danger')
            return redirect(url_for('contract_new'))
    
    conn.close()
    return render_template('contract_form.html', services=services, managers=managers)

# Маршрут для удаления договора
@app.route('/contracts/<contract_number>/delete', methods=['POST'])
def contract_delete(contract_number):
    conn = get_db()
    
    obj = conn.execute('SELECT id_object FROM contract WHERE contract_number = ?', (contract_number,)).fetchone()
    if obj and obj['id_object']:
        conn.execute('DELETE FROM object WHERE id_object = ?', (obj['id_object'],))
    
    conn.execute('DELETE FROM contract WHERE contract_number = ?', (contract_number,))
    conn.commit()
    conn.close()
    
    flash('Договор удалён', 'warning')
    return redirect(url_for('contracts'))
    
# Маршрут для загрузки списка договоров файлом Excel
@app.route('/upload', methods=['GET', 'POST'])
def upload_excel():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('выбран', 'danger')
            return redirect(url_for('upload_excel'))
        
        file = request.files['file']
        if file.filename == '':
            flash('Файл не выбран', 'danger')
            return redirect(url_for('upload_excel'))
        
        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('Поддерживаются только файлы Excel (.xlsx, .xls)', 'danger')
            return redirect(url_for('upload_excel'))
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        try:
            wb = load_workbook(filepath, data_only=True)
            ws = wb.active
            
            headers = []
            for cell in ws[1]:
                val = str(cell.value).lower() if cell.value else ''
                headers.append(val)
            
            col_map = {}
            for idx, col in enumerate(headers):
                if 'номер' in col or 'number' in col:
                    col_map['contract_number'] = idx
                elif 'дата' in col or 'date' in col:
                    col_map['signing_date'] = idx
                elif 'клиент' in col or 'client' in col:
                    col_map['client_name'] = idx
                elif 'сумма' in col or 'amount' in col or 'price' in col or 'стоимость' in col:
                    col_map['price'] = idx
                elif 'тип' in col or 'type' in col:
                    col_map['type'] = idx
                elif 'статус' in col or 'status' in col:
                    col_map['status'] = idx
                elif 'инн' in col or 'inn' in col:
                    col_map['inn'] = idx
                elif 'телефон' in col or 'phone' in col:
                    col_map['phone'] = idx
                elif 'менеджер' in col or 'manager' in col:
                    col_map['manager_name'] = idx
                elif 'email' in col:
                    col_map['manager_email'] = idx
                elif 'услуга' in col or 'service' in col:
                    col_map['service_name'] = idx
                elif 'срок' in col or 'finishing_date' in col or 'deadline' in col:
                    col_map['finishing_date'] = idx
            
            required = ['contract_number', 'signing_date', 'client_name', 'price']
            missing = [r for r in required if r not in col_map]
            if missing:
                flash(f'Отсутствуют обязательные колонки: {missing}', 'danger')
                return redirect(url_for('upload_excel'))
            
            conn = get_db()
            success_count = 0
            errors = []
            
            existing_services = {s['service_name']: s['id_service'] for s in conn.execute('SELECT id_service, service_name FROM service').fetchall()}
            existing_managers = {m['manager_name']: m['id_manager'] for m in conn.execute('SELECT id_manager, manager_name FROM manager').fetchall()}
            existing_clients = {c['client_name']: c['id_client'] for c in conn.execute('SELECT id_client, client_name FROM client').fetchall()}
            
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    if not row or not any(row):
                        continue
                    
                    contract_number = str(row[col_map['contract_number']]).strip() if row[col_map['contract_number']] else None
                    date_val = row[col_map['signing_date']]
                    client_name = str(row[col_map['client_name']]).strip() if row[col_map['client_name']] else None
                    price = float(row[col_map['price']]) if row[col_map['price']] else 0
                    
                    contract_type = 'с'
                    if 'type' in col_map and row[col_map['type']]:
                        type_val = str(row[col_map['type']]).strip().lower()
                        if type_val in ['н', 'новый', 'new']:
                            contract_type = 'н'
                    
                    status = 'В работе'
                    if 'status' in col_map and row[col_map['status']]:
                        status_val = str(row[col_map['status']]).strip()
                        if status_val in ['Выполнен', 'выполнен']:
                            status = 'Выполнен'
                    
                    client_inn = str(row[col_map['inn']]).strip() if 'inn' in col_map and row[col_map['inn']] else ''
                    client_phone = str(row[col_map['phone']]).strip() if 'phone' in col_map and row[col_map['phone']] else ''
                    
                    manager_name = str(row[col_map['manager_name']]).strip() if 'manager_name' in col_map and row[col_map['manager_name']] else None
                    manager_email = str(row[col_map['manager_email']]).strip() if 'manager_email' in col_map and row[col_map['manager_email']] else ''
                    
                    service_name = str(row[col_map['service_name']]).strip() if 'service_name' in col_map and row[col_map['service_name']] else None
                    finishing_date = None
                    if 'finishing_date' in col_map and row[col_map['finishing_date']]:
                        if isinstance(row[col_map['finishing_date']], datetime):
                            finishing_date = row[col_map['finishing_date']].strftime('%Y-%m-%d')
                        else:
                            finishing_date = str(row[col_map['finishing_date']]).strip()
                    
                    if isinstance(date_val, datetime):
                        date_str = date_val.strftime('%Y-%m-%d')
                    else:
                        date_str = str(date_val).strip()
                    
                    if not contract_number or not date_str or not client_name:
                        errors.append(f"Строка {row_idx}: отсутствуют обязательные поля")
                        continue
                    
                    existing = conn.execute('SELECT contract_number FROM contract WHERE contract_number = ?', (contract_number,)).fetchone()
                    if existing:
                        errors.append(f"Строка {row_idx}: договор {contract_number} уже существует")
                        continue
                    
                    if client_name in existing_clients:
                        client_id = existing_clients[client_name]
                        conn.execute('''
                            UPDATE client SET client_INN=?, client_phone_number=?
                            WHERE id_client=?
                        ''', (client_inn, client_phone, client_id))
                    else:
                        conn.execute('''
                            INSERT INTO client (client_name, client_INN, client_phone_number)
                            VALUES (?, ?, ?)
                        ''', (client_name, client_inn, client_phone))
                        client_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
                        existing_clients[client_name] = client_id
                    
                    manager_id = None
                    if manager_name:
                        if manager_name in existing_managers:
                            manager_id = existing_managers[manager_name]
                            conn.execute('UPDATE manager SET manager_email=? WHERE id_manager=?', (manager_email, manager_id))
                        else:
                            conn.execute('''
                                INSERT INTO manager (manager_name, manager_email)
                                VALUES (?, ?)
                            ''', (manager_name, manager_email))
                            manager_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
                            existing_managers[manager_name] = manager_id
                    
                    service_id = None
                    if service_name:
                        if service_name in existing_services:
                            service_id = existing_services[service_name]
                        else:
                            conn.execute('INSERT INTO service (service_name) VALUES (?)', (service_name,))
                            service_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
                            existing_services[service_name] = service_id
                    
                    object_id = None
                    if service_id:
                        conn.execute('''
                            INSERT INTO object (id_service, price, finishing_date)
                            VALUES (?, ?, ?)
                        ''', (service_id, price, finishing_date))
                        object_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
                    
                    conn.execute('''
                        INSERT INTO contract (contract_number, signing_contract_date, status, type, id_client, id_manager, id_object)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (contract_number, date_str, status, contract_type, client_id, manager_id, object_id))
                    
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Строка {row_idx}: {str(e)}")
            
            conn.commit()
            conn.close()
            
            flash(f'Загружено {success_count} договоров. Ошибки: {len(errors)}', 
                  'success' if success_count > 0 else 'warning')
            for err in errors[:10]:
                flash(err, 'danger')
                
        except Exception as e:
            flash(f'Ошибка при обработке файла: {str(e)}', 'danger')
        
        return redirect(url_for('contracts'))
    
    return render_template('upload_excel.html')

# Маршрут для редактирования договора
@app.route('/contracts/<contract_number>/edit', methods=['GET', 'POST'])
def contract_edit(contract_number):
    conn = get_db()
    
    if request.method == 'POST':
        try:
            conn.execute('''
                UPDATE contract 
                SET signing_contract_date = ?, 
                    status = ?, 
                    type = ?
                WHERE contract_number = ?
            ''', (
                request.form['signing_contract_date'],
                request.form['status'],
                request.form['type'],
                contract_number
            ))
            
            client_id = conn.execute('SELECT id_client FROM contract WHERE contract_number = ?', (contract_number,)).fetchone()['id_client']
            conn.execute('''
                UPDATE client 
                SET client_name = ?, 
                    client_INN = ?, 
                    client_phone_number = ?
                WHERE id_client = ?
            ''', (
                request.form['client_name'],
                request.form.get('client_INN', ''),
                request.form.get('client_phone_number', ''),
                client_id
            ))
            
            manager_id = conn.execute('SELECT id_manager FROM contract WHERE contract_number = ?', (contract_number,)).fetchone()['id_manager']
            if manager_id:
                conn.execute('''
                    UPDATE manager 
                    SET manager_name = ?, 
                        manager_email = ?
                    WHERE id_manager = ?
                ''', (
                    request.form['manager_name'],
                    request.form.get('manager_email', ''),
                    manager_id
                ))
            elif request.form.get('manager_name'):
                conn.execute('''
                    INSERT INTO manager (manager_name, manager_email)
                    VALUES (?, ?)
                ''', (
                    request.form['manager_name'],
                    request.form.get('manager_email', '')
                ))
                new_manager_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
                conn.execute('UPDATE contract SET id_manager = ? WHERE contract_number = ?', (new_manager_id, contract_number))
            
            object_id = conn.execute('SELECT id_object FROM contract WHERE contract_number = ?', (contract_number,)).fetchone()['id_object']
            service_id = request.form.get('service_id')
            price = float(request.form.get('price', 0))
            finishing_date = request.form.get('finishing_date') or None
            
            if object_id:
                conn.execute('''
                    UPDATE object 
                    SET id_service = ?, 
                        price = ?, 
                        finishing_date = ?
                    WHERE id_object = ?
                ''', (service_id, price, finishing_date, object_id))
            elif service_id:
                conn.execute('''
                    INSERT INTO object (id_service, price, finishing_date)
                    VALUES (?, ?, ?)
                ''', (service_id, price, finishing_date))
                new_object_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
                conn.execute('UPDATE contract SET id_object = ? WHERE contract_number = ?', (new_object_id, contract_number))
            
            conn.commit()
            conn.close()
            
            flash('Договор успешно обновлён!', 'success')
            return redirect(url_for('contracts'))
            
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'danger')
            return redirect(url_for('contract_edit', contract_number=contract_number))
    
    contract = conn.execute('''
        SELECT 
            c.contract_number,
            c.signing_contract_date,
            c.status,
            c.type,
            cl.id_client,
            cl.client_name,
            cl.client_INN,
            cl.client_phone_number,
            m.id_manager,
            m.manager_name,
            m.manager_email,
            s.id_service,
            s.service_name,
            o.price,
            o.finishing_date
        FROM contract c
        JOIN client cl ON c.id_client = cl.id_client
        LEFT JOIN manager m ON c.id_manager = m.id_manager
        LEFT JOIN object o ON c.id_object = o.id_object
        LEFT JOIN service s ON o.id_service = s.id_service
        WHERE c.contract_number = ?
    ''', (contract_number,)).fetchone()
    
    services = conn.execute('SELECT id_service, service_name FROM service').fetchall()
    managers = conn.execute('SELECT id_manager, manager_name FROM manager').fetchall()
    conn.close()
    
    if not contract:
        flash('Договор не найден', 'danger')
        return redirect(url_for('contracts'))
    
    return render_template('contract_edit.html', 
                          contract=contract, 
                          services=services, 
                          managers=managers)

# Маршрут для вывода карточек KPI
@app.route('/api/stats')
def api_stats():
    period1_year = request.args.get('period1_year', type=int)
    period1_month_from = request.args.get('period1_month_from', type=int)
    period1_month_to = request.args.get('period1_month_to', type=int)
    
    period2_year = request.args.get('period2_year', type=int)
    period2_month_from = request.args.get('period2_month_from', type=int)
    period2_month_to = request.args.get('period2_month_to', type=int)
    
    stats1 = get_stats_for_period(period1_year, period1_month_from, period1_month_to) if period1_year else None
    stats2 = get_stats_for_period(period2_year, period2_month_from, period2_month_to) if period2_year else None
    
    return jsonify({'period1': stats1, 'period2': stats2})

# Маршрут для экспорта дашборда
@app.route('/dashboard/export/pdf')
def export_pdf():
    conn = get_db()
    
    period1_year = request.args.get('period1_year', 2024, type=int)
    period1_month_from = request.args.get('period1_month_from', type=int)
    period1_month_to = request.args.get('period1_month_to', type=int)
    period2_year = request.args.get('period2_year', 2025, type=int)
    period2_month_from = request.args.get('period2_month_from', type=int)
    period2_month_to = request.args.get('period2_month_to', type=int)
    
    stats1 = get_stats_for_period(period1_year, period1_month_from, period1_month_to)
    stats2 = get_stats_for_period(period2_year, period2_month_from, period2_month_to)
    kpi = get_kpi()
    conn.close()
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Normal'], alignment=1, fontSize=16, spaceAfter=20, fontName=FONT_NAME)
    heading_style = ParagraphStyle('HeadingStyle', parent=styles['Normal'], fontSize=12, spaceAfter=10, fontName=FONT_NAME)
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName=FONT_NAME, fontSize=10)
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontName=FONT_NAME, fontSize=9, alignment=1)
    
    elements = []
    
    elements.append(Paragraph("Дашборд аналитики договоров", title_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_style))
    elements.append(Spacer(1, 20))
    
    elements.append(Paragraph("Ключевые показатели (KPI)", heading_style))
    kpi_data = [
        [Paragraph("Показатель", cell_style), Paragraph("Значение", cell_style)],
        [Paragraph("Всего договоров", cell_style), Paragraph(str(kpi['total']), cell_style)],
        [Paragraph("Выполнено", cell_style), Paragraph(str(kpi['completed']), cell_style)],
        [Paragraph("В работе", cell_style), Paragraph(str(kpi['in_progress']), cell_style)],
        [Paragraph("Просрочено", cell_style), Paragraph(str(kpi['overdue']), cell_style)],
        [Paragraph("Общая сумма", cell_style), Paragraph(f"{kpi['total_amount']:,.0f} руб.", cell_style)]
    ]
    
    kpi_table = Table(kpi_data, colWidths=[100*mm, 80*mm])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (1, -1), 'CENTER'),
        ('GRID', (0, 0), (1, -1), 1, colors.black)
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 20))
    
    period1_title = f"Период 1: {stats1['year']}"
    if stats1['month_from'] and stats1['month_to']:
        period1_title += f" (месяцы {stats1['month_from']}-{stats1['month_to']})"
    elements.append(Paragraph(period1_title, heading_style))
    
    period1_data = [
        [Paragraph("Показатель", cell_style), Paragraph("Новые (н)", cell_style), Paragraph("Старые (с)", cell_style), Paragraph("Выполнено", cell_style), Paragraph("В работе", cell_style), Paragraph("ИТОГО", cell_style)],
        [Paragraph("Количество", cell_style), Paragraph(str(stats1['new_count']), cell_style), Paragraph(str(stats1['old_count']), cell_style), Paragraph(str(stats1['completed']), cell_style), Paragraph(str(stats1['in_progress']), cell_style), Paragraph(str(stats1['total']), cell_style)],
        [Paragraph("Сумма (руб.)", cell_style), Paragraph(f"{stats1['new_amount']:,.0f}", cell_style), Paragraph(f"{stats1['old_amount']:,.0f}", cell_style), Paragraph(f"{stats1['completed_amount']:,.0f}", cell_style), Paragraph(f"{stats1['in_progress_amount']:,.0f}", cell_style), Paragraph(f"{stats1['total_amount']:,.0f}", cell_style)]
    ]
    
    p1_table = Table(period1_data, colWidths=[55*mm, 30*mm, 30*mm, 30*mm, 30*mm, 30*mm])
    p1_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (5, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (5, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (5, -1), 'CENTER'),
        ('GRID', (0, 0), (5, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (5, 2), colors.lightgrey)
    ]))
    elements.append(p1_table)
    elements.append(Spacer(1, 20))
    
    period2_title = f"Период 2: {stats2['year']}"
    if stats2['month_from'] and stats2['month_to']:
        period2_title += f" (месяцы {stats2['month_from']}-{stats2['month_to']})"
    elements.append(Paragraph(period2_title, heading_style))
    
    period2_data = [
        [Paragraph("Показатель", cell_style), Paragraph("Новые (н)", cell_style), Paragraph("Старые (с)", cell_style), Paragraph("Выполнено", cell_style), Paragraph("В работе", cell_style), Paragraph("ИТОГО", cell_style)],
        [Paragraph("Количество", cell_style), Paragraph(str(stats2['new_count']), cell_style), Paragraph(str(stats2['old_count']), cell_style), Paragraph(str(stats2['completed']), cell_style), Paragraph(str(stats2['in_progress']), cell_style), Paragraph(str(stats2['total']), cell_style)],
        [Paragraph("Сумма (руб.)", cell_style), Paragraph(f"{stats2['new_amount']:,.0f}", cell_style), Paragraph(f"{stats2['old_amount']:,.0f}", cell_style), Paragraph(f"{stats2['completed_amount']:,.0f}", cell_style), Paragraph(f"{stats2['in_progress_amount']:,.0f}", cell_style), Paragraph(f"{stats2['total_amount']:,.0f}", cell_style)]
    ]
    
    p2_table = Table(period2_data, colWidths=[55*mm, 30*mm, 30*mm, 30*mm, 30*mm, 30*mm])
    p2_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (5, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (5, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (5, -1), 'CENTER'),
        ('GRID', (0, 0), (5, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (5, 2), colors.lightgrey)
    ]))
    elements.append(p2_table)
    
    doc.build(elements)
    buffer.seek(0)
    
    return Response(
        buffer,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename=dashboard_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'}
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)
