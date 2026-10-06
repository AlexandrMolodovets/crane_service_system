# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import traceback
import io
import os
from supabase import create_client, Client
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ============================================
# ⚠️ ВСТАВЬТЕ ВАШИ ДАННЫЕ ИЗ SUPABASE:
# ============================================
SUPABASE_URL = "https://mkrhnmnleisforgghhfi.supabase.co"
SUPABASE_KEY = "sb_publishable_e8yY4CZsXpSVpYe1RgmlwQ_HAJXARth"
# ============================================

# Подключение к Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Подключение к Supabase установлено")
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")
    exit(1)

app = FastAPI(title="Crane Service System")

def get_month_name(date_str: str) -> str:
    """Преобразует дату в название месяца"""
    if not date_str:
        return ""
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    try:
        month_num = int(date_str.split('-')[1]) if '-' in date_str else 1
        return months[month_num - 1] if 1 <= month_num <= 12 else ""
    except:
        return ""

# ========== HTML ФОРМА (как раньше, с полным чек-листом) ==========
FORM_HTML = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Обслуживание портальных кранов</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #e9ecef; margin: 0; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 5px 20px rgba(0,0,0,0.1); }
        h1 { color: #1a3a5c; border-bottom: 3px solid #2c5f8a; padding-bottom: 10px; }
        h2 { color: #2c5f8a; margin-top: 30px; font-size: 1.3em; border-left: 4px solid #2c5f8a; padding-left: 15px; }
        .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .form-group { display: flex; flex-direction: column; }
        .form-group label { font-weight: 600; margin-bottom: 5px; color: #495057; }
        .form-group input, .form-group select, .form-group textarea { padding: 10px; border: 1px solid #ced4da; border-radius: 6px; font-size: 14px; }
        .form-group textarea { resize: vertical; min-height: 60px; }
        .checklist-section { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #dee2e6; }
        .checklist-item { display: grid; grid-template-columns: 1fr auto 1fr; gap: 15px; align-items: center; margin-bottom: 15px; padding: 10px; background: white; border-radius: 6px; }
        .checklist-item label { font-weight: 500; }
        .checklist-item select, .checklist-item input { padding: 8px; border-radius: 4px; border: 1px solid #ced4da; }
        button { background: #2c5f8a; color: white; border: none; padding: 12px 30px; border-radius: 6px; font-size: 16px; cursor: pointer; margin: 10px 5px; }
        button:hover { background: #1a3a5c; }
        .btn-success { background: #28a745; }
        .btn-secondary { background: #6c757d; }
        .nav { margin-bottom: 20px; }
        .nav a { margin-right: 15px; color: #007bff; text-decoration: none; }
        @media (max-width: 768px) { .checklist-item { grid-template-columns: 1fr; gap: 8px; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏗️ Акт технического обслуживания портального крана</h1>
        <div class="nav">
            <a href="/">➕ Создать отчёт</a>
            <a href="/reports">📋 Список отчётов</a>
        </div>
        <hr>
        
        <form id="serviceForm">
            <h2>📋 Общая информация</h2>
            <div class="form-grid">
                <div class="form-group"><label>Дата осмотра *</label><input type="date" id="inspection_date" required></div>
                <div class="form-group"><label>Тип крана *</label>
                    <select id="crane_type" required>
                        <option value="">Выберите...</option>
                        <option value="Альбатрос">Альбатрос</option>
                        <option value="Ганц">Ганц</option>
                        
                    </select>
                </div>
                <div class="form-group"><label>Номер крана *</label><input type="text" id="crane_number" placeholder="Например: ПК-123" required></div>
                <div class="form-group"><label>Место нахождения *</label><input type="text" id="location" placeholder="Грузовой район" required></div>
                <div class="form-group"><label>ФИО специалиста *</label><input type="text" id="technician_name" placeholder="Иванов И.И." required></div>
            </div>
            
            <h2>📝 Ремонтные работы по замечаниям из сменного журнала</h2>
            <div class="form-grid">
                <div class="form-group"><label>Замечания из сменного журнала</label><textarea id="journal_remarks" rows="3" placeholder="Перечислите замечания..."></textarea></div>
                <div class="form-group"><label>Скрытые неисправности, выявленные при осмотре</label><textarea id="repair_work_done" rows="3" placeholder="Что было выявлено..."></textarea></div>
            </div>
            
            <h2>✅ Карта технического обслуживания</h2>
            <div id="dynamicChecklist"></div>
            
            <h2>🔍 Работы по устранению замечаний и неисправностей</h2>
            <div class="form-group"><textarea id="hidden_defects" rows="4" placeholder="Что было сделано..."></textarea></div>
            
            <h2>📊 Заключение о работоспособности</h2>
            <div class="form-group">
                <select id="conclusion" required>
                    <option value="">Выберите заключение...</option>
                    <option value="operational">✅ Кран исправен, может эксплуатироваться</option>
                    <option value="limited">⚠️ Имеются мелкие неисправности, но кран работоспособен</option>
                    <option value="inoperational">❌ Кран неисправен, эксплуатация запрещена</option>
                </select>
            </div>
            
            <div style="margin-top: 30px; text-align: center;">
                <button type="submit" class="btn-success">💾 Сохранить отчёт</button>
                <button type="button" onclick="window.location.href='/reports'" class="btn-secondary">📋 Список отчётов</button>
            </div>
        </form>
    </div>
    
    <script>
        const checklistItems = [
            "Проверка и обслуживание кольцевого токоприемника КБ",
            "Проверка и обслуживание ЦТ",
            "Визуальный осмотр ЧРП подъема и замыкания",
            "Визуальный осмотр ЧРП механизма вылета стрелы",
            "Визуальный осмотр ЧРП поворота стрелы",
            "Визуальный осмотр ЧРП передвижения крана",
            "Проверка электрооборудования силовых шкафов и шкафов управления",
            "Проверка блока бесперебойного питания на 24В",
            "Проверка роторных конечных и путевых выключателей",
            "Проверка ультразвуковых датчиков противостолкновения",
            "Проверка электрической части двигателей",
            "Проверка работы энкодеров",
            "Проверка работы анемометра",
            "Проверка датчиков прибора безопасности (ОГП)",
            "Проверка работы джойстиков",
            "Проверка светосигнальной арматуры и электрооборудования кресло-пульта",
            "Проверка и анализ буфера ошибок PLC",
            "Диагностика коммуникационной сети (Ethernet, Profibus, CAN, DeviceNET)",
            "Проверка настроек частотных преобразователей Siemens",
            "Проверка настроек частотных преобразователей Gefran",
            "Проверка настроек частотных преобразователей Schneider Electric",
            "Проверка и анализ буфера ошибок частотных преобразователей Siemens",
            "Проверка и анализ буфера ошибок частотных преобразователей Gefran",
            "Проверка и анализ буфера ошибок частотных преобразователей Schneider Electric",
            "Устранение ошибок (в случае обнаружения)",
            "Проверка механического крепления частотных преобразователей",
            "Протяжка силовых клеммных соединений",
            "Чистка частотных преобразователей от пыли и грязи",
            "Проверка параметров, уставок защиты и блокировок",
            "Создание/сверка резервных копий настроек частотных преобразователей",
            "Замена фильтрующих элементов в силовых шкафах и шкафах управления"
        ];
        
        function generateChecklist() {
            const container = document.getElementById('dynamicChecklist');
            let html = `<div class="checklist-section">`;
            
            checklistItems.forEach((item, index) => {
                const itemId = `item_${index}`;
                html += `
                    <div class="checklist-item">
                        <label><strong>${item}</strong></label>
                        <select id="status_${itemId}">
                            <option value="done">✅ Выполнено</option>
                            <option value="pending">⏳ Не выполнено</option>
                            <option value="needs_repair">⚠️ В ремонте</option>
                            <option value="n_a">➖ Выполнить невозможно</option>
                        </select>
                        <input type="text" id="notes_${itemId}" placeholder="Примечания">
                    </div>
                `;
            });
            html += `</div>`;
            container.innerHTML = html;
        }
        
        async function submitReport(event) {
            event.preventDefault();
            
            const serviceData = {};
            checklistItems.forEach((item, index) => {
                const itemId = `item_${index}`;
                serviceData[itemId] = {
                    name: item,
                    status: document.getElementById(`status_${itemId}`).value,
                    notes: document.getElementById(`notes_${itemId}`).value || ""
                };
            });
            
            const reportData = {
                inspection_date: document.getElementById('inspection_date').value,
                crane_type: document.getElementById('crane_type').value,
                crane_number: document.getElementById('crane_number').value,
                location: document.getElementById('location').value,
                journal_remarks: document.getElementById('journal_remarks').value,
                repair_work_done: document.getElementById('repair_work_done').value,
                service_data: serviceData,
                hidden_defects: document.getElementById('hidden_defects').value,
                conclusion: document.getElementById('conclusion').value,
                technician_name: document.getElementById('technician_name').value
            };
            
            if (!reportData.inspection_date || !reportData.crane_type || !reportData.crane_number || !reportData.location || !reportData.technician_name || !reportData.conclusion) {
                alert('❌ Заполните все обязательные поля!');
                return;
            }
            
            try {
                const response = await fetch('/api/reports', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(reportData)
                });
                const result = await response.json();
                
                if (result.success) {
                    alert(`✅ Отчёт успешно сохранён! ID: ${result.report_id}`);
                    if (confirm('Скачать отчёт в формате PDF?')) {
                        window.open(`/api/reports/${result.report_id}/pdf`, '_blank');
                    }
                    window.location.href = '/reports';
                } else {
                    alert('❌ Ошибка: ' + (result.error || 'Неизвестная ошибка'));
                }
            } catch (error) {
                alert('❌ Ошибка при сохранении: ' + error.message);
            }
        }
        
        document.getElementById('inspection_date').value = new Date().toISOString().split('T')[0];
        generateChecklist();
        document.getElementById('serviceForm').addEventListener('submit', submitReport);
    </script>
</body>
</html>
'''

# HTML список отчётов
LIST_HTML = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Список отчётов</title>
    <style>
        body { font-family: 'Segoe UI', Arial; background: #f0f2f5; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: auto; background: white; padding: 20px; border-radius: 10px; }
        h1 { color: #1a3a5c; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background: #1a3a5c; color: white; }
        tr:hover { background: #f5f5f5; }
        .btn { padding: 5px 12px; margin: 0 3px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn-pdf { background: #dc3545; color: white; }
        .btn-del { background: #6c757d; color: white; }
        .nav { margin-bottom: 20px; }
        .nav a { margin-right: 15px; color: #007bff; text-decoration: none; }
        .filter-bar { margin: 20px 0; display: flex; gap: 10px; flex-wrap: wrap; }
        .filter-bar input, .filter-bar button { padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 Журнал отчётов по обслуживанию кранов</h1>
        <div class="nav">
            <a href="/">➕ Создать новый отчёт</a>
        </div>
        
        <div class="filter-bar">
            <input type="text" id="filterCrane" placeholder="Номер крана">
            <input type="date" id="filterDateFrom">
            <input type="date" id="filterDateTo">
            <button onclick="loadReports()">🔍 Поиск</button>
        </div>
        
        <div id="reportsContent"></div>
    </div>
    
    <script>
        async function loadReports() {
            const crane = document.getElementById('filterCrane').value;
            const dateFrom = document.getElementById('filterDateFrom').value;
            const dateTo = document.getElementById('filterDateTo').value;
            
            let url = '/api/reports?';
            if (crane) url += `crane_number=${crane}&`;
            if (dateFrom) url += `date_from=${dateFrom}&`;
            if (dateTo) url += `date_to=${dateTo}&`;
            
            try {
                const response = await fetch(url);
                const data = await response.json();
                const container = document.getElementById('reportsContent');
                
                if (!data.reports || data.reports.length === 0) {
                    container.innerHTML = '<p>Нет отчётов</p>';
                    return;
                }
                
                let html = '<table><thead><tr><th>ID</th><th>Дата</th><th>Тип</th><th>Номер</th><th>Место</th><th>Техник</th><th>Заключение</th><th>Действия</th></tr></thead><tbody>';
                
                data.reports.forEach(r => {
                    let status = '';
                    if (r.conclusion === 'operational') status = '✅ Исправен';
                    else if (r.conclusion === 'limited') status = '⚠️ Работоспособен';
                    else status = '❌ Неисправен';
                    
                    html += `<tr>
                        <td>${r.id}</td>
                        <td>${r.inspection_date}</td>
                        <td>${r.crane_type}</td>
                        <td>${r.crane_number}</td>
                        <td>${r.location}</td>
                        <td>${r.technician_name}</td>
                        <td>${status}</td>
                        <td>
                            <a href="/api/reports/${r.id}/pdf" target="_blank" class="btn btn-pdf">📄 PDF</a>
                            <button onclick="deleteReport(${r.id})" class="btn btn-del">🗑️</button>
                         </d>
                    </tr>`;
                });
                html += '</tbody></table>';
                container.innerHTML = html;
            } catch (error) {
                console.error('Error:', error);
                container.innerHTML = '<p>Ошибка загрузки отчётов</p>';
            }
        }
        
        async function deleteReport(id) {
            if (confirm('Удалить отчёт?')) {
                const response = await fetch(`/api/reports/${id}`, { method: 'DELETE' });
                if (response.ok) {
                    loadReports();
                } else {
                    alert('Ошибка при удалении');
                }
            }
        }
        
        loadReports();
    </script>
</body>
</html>
'''

class CraneReport(BaseModel):
    inspection_date: str
    crane_type: str
    crane_number: str
    location: str
    journal_remarks: Optional[str] = ""
    repair_work_done: Optional[str] = ""
    service_data: Dict[str, Any]
    hidden_defects: Optional[str] = ""
    conclusion: str
    technician_name: str

# ========== ГЕНЕРАЦИЯ PDF ==========
def generate_pdf_report(report: dict) -> io.BytesIO:
    """Генерация PDF-отчёта"""
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(A4),
        rightMargin=10*mm,
        leftMargin=10*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )
    
    # Шрифт
    font_path = os.path.join(os.path.dirname(__file__), "DejaVuSans.ttf")
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont('RussianFont', font_path))
            font_name = 'RussianFont'
        except:
            font_name = 'Helvetica'
    else:
        font_name = 'Helvetica'
    
    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontName=font_name, fontSize=9, spaceAfter=3)
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontName=font_name, fontSize=14, alignment=TA_CENTER, spaceAfter=10)
    bold_style = ParagraphStyle('Bold', parent=normal_style, fontName=font_name, fontSize=9)
    
    story = []
    
    inspection_date = report.get('inspection_date', '')
    date_day = inspection_date[-2:] if len(inspection_date) >= 2 else ''
    date_year = inspection_date[:4] if len(inspection_date) >= 4 else ''
    month_name = get_month_name(inspection_date)
    
    # Шапка

    story.append(Paragraph(f"Участок: {report.get('location', '')}", normal_style))
    story.append(Spacer(1, 5))
    story.append(Paragraph(f"Кран: \"{report.get('crane_number', '')}\"", normal_style))
    story.append(Spacer(1, 5))
    story.append(Paragraph(f"Дата: «{date_day}» {month_name} {date_year} г.", normal_style))
    story.append(Spacer(1, 5))
    story.append(Paragraph(f"Время: с 09:00 до 17:00 ", normal_style))
    story.append(Spacer(1, 5))
    story.append(Paragraph("Кран в ПТО передал: _________________ _________________", normal_style))
    story.append(Spacer(1, 10))
    
    # Заголовок
    story.append(Paragraph("Карта", title_style))
    story.append(Paragraph("планового технического обслуживания (ПТО)", title_style))
    story.append(Paragraph("электрического оборудования крана портального перегрузочного", title_style))
    story.append(Spacer(1, 10))
    
    # Таблица чек-листа
    service_data = report.get('service_data', {})
    status_symbols = {"done": "✅", "pending": "⏳", "needs_repair": "⚠️", "n_a": "➖"}
    
    work_items = [
        "Проверка и обслуживание кольцевого токоприемника КБ",
        "Проверка и обслуживание ЦТ",
        "Визуальный осмотр ЧРП подъема и замыкания",
        "Визуальный осмотр ЧРП механизма вылета стрелы",
        "Визуальный осмотр ЧРП поворота стрелы",
        "Визуальный осмотр ЧРП передвижения крана",
        "Проверка электрооборудования силовых шкафов",
        "Проверка блока бесперебойного питания 24В",
        "Проверка роторных конечных выключателей",
        "Проверка ультразвуковых датчиков",
        "Проверка электрической части двигателей",
        "Проверка работы энкодеров",
        "Проверка работы анемометра",
        "Проверка датчиков ОГП",
        "Проверка работы джойстиков",
        "Проверка светосигнальной арматуры",
        "Проверка буфера ошибок PLC",
        "Диагностика коммуникационной сети",
        "Проверка настроек ЧРП",
        "Проверка буфера ошибок ЧРП",
        "Устранение ошибок",
        "Проверка крепления ЧРП",
        "Протяжка клемм ЧРП",
        "Чистка ЧРП",
        "Проверка параметров защиты",
        "Резервные копии ЧРП",
        "Замена фильтрующих элементов"
    ]
    
    table_data = [["№", "Перечень выполняемых работ", "Отметка", "Примечание"]]
    row_num = 1
    for item in work_items:
        status = "pending"
        notes = ""
        for key, val in service_data.items():
            if val.get('name', '') == item:
                status = val.get('status', 'pending')
                notes = val.get('notes', '')
                break
        mark = status_symbols.get(status, "⏳")
        table_data.append([str(row_num), item, mark, notes[:40]])
        row_num += 1
    
    table = Table(table_data, colWidths=[12*mm, 95*mm, 20*mm, 40*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), font_name), ('FONTSIZE', (0,0), (-1,-1), 7),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2c5f8a')), ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (0,-1), 'CENTER'), ('ALIGN', (2,0), (2,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'), ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(table)
    story.append(Spacer(1, 10))
    
    # Ремонтные работы
    story.append(Paragraph("Ремонтные работы по замечаниям из сменного журнала", bold_style))
    repair = report.get('repair_work_done', 'Не требуется') or 'Не требуется'
    story.append(Paragraph(repair, normal_style))
    story.append(Spacer(1, 5))
    
    # Скрытые дефекты и заключение
    defects = report.get('hidden_defects', 'Не выявлено') or 'Не выявлено'
    conclusion = report.get('conclusion', '')
    if conclusion == 'operational':
        conclusion_text = "Кран ИСПРАВЕН и может эксплуатироваться"
    elif conclusion == 'limited':
        conclusion_text = "Кран требует ОГРАНИЧЕНИЙ в эксплуатации"
    else:
        conclusion_text = "Кран НЕИСПРАВЕН, эксплуатация ЗАПРЕЩЕНА"
    
    footer_data = [["Скрытые дефекты:", defects, f"Заключение:\n{conclusion_text}"]]
    footer_table = Table(footer_data, colWidths=[40*mm, 80*mm, 65*mm])
    footer_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), font_name), ('FONTSIZE', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'TOP'), ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(footer_table)
    story.append(Spacer(1, 15))
    
    # Подписи
    story.append(Paragraph("Кран после работ сдал:", normal_style))
    story.append(Paragraph("_________________ _________________ _________________", normal_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Кран после работ принял: {conclusion_text}", normal_style))
    story.append(Paragraph("_________________ _________________ _________________", normal_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Замечания: {report.get('journal_remarks', 'Нет')}", normal_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Замечания устранил:", normal_style))
    story.append(Paragraph("_________________ _________________ _________________", normal_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


# ========== API ЭНДПОИНТЫ ==========
@app.get("/")
async def home():
    return HTMLResponse(content=FORM_HTML)

@app.get("/reports")
async def reports_page():
    return HTMLResponse(content=LIST_HTML)

@app.post("/api/reports")
async def create_report(report: CraneReport):
    try:
        data = report.model_dump()
        data["created_at"] = datetime.now().isoformat()
        data["service_data"] = json.dumps(data["service_data"], ensure_ascii=False)
        
        print(f"📝 Сохраняем: кран {data['crane_number']}, дата {data['inspection_date']}")
        result = supabase.table("crane_reports").insert(data).execute()
        
        if result.data and len(result.data) > 0:
            print(f"✅ Сохранён ID: {result.data[0]['id']}")
            return {"success": True, "report_id": result.data[0]["id"]}
        else:
            return {"success": False, "error": "Не удалось создать отчёт"}
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/reports")
async def get_reports(crane_number: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None):
    try:
        query = supabase.table("crane_reports").select("*")
        if crane_number:
            query = query.ilike("crane_number", f"%{crane_number}%")
        if date_from:
            query = query.gte("inspection_date", date_from)
        if date_to:
            query = query.lte("inspection_date", date_to)
        query = query.order("inspection_date", desc=True)
        result = query.execute()
        return {"success": True, "reports": result.data}
    except Exception as e:
        return {"success": False, "reports": []}

@app.get("/api/reports/{report_id}/pdf")
async def download_pdf(report_id: int):
    result = supabase.table("crane_reports").select("*").eq("id", report_id).execute()
    if not result.data:
        raise HTTPException(404, "Report not found")
    
    report = result.data[0]
    if report.get("service_data") and isinstance(report["service_data"], str):
        report["service_data"] = json.loads(report["service_data"])
    
    pdf_buffer = generate_pdf_report(report)
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Karta_PTO_{report_id}.pdf"}
    )

@app.delete("/api/reports/{report_id}")
async def delete_report(report_id: int):
    supabase.table("crane_reports").delete().eq("id", report_id).execute()
    return {"success": True}

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("🚀 СИСТЕМА КАРТ ПТО ПОРТАЛЬНЫХ КРАНОВ")
    print("="*60)
    print(f"✅ Подключено к: {SUPABASE_URL}")
    print("📍 Откройте: http://localhost:8000")
    print("="*60 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")