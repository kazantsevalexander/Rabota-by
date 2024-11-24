import os
import requests
from flask import Flask, render_template, request
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import numpy as np
from datetime import datetime

app = Flask(__name__)


def fetch_vacancies(specialty='графический дизайнер', page=0):
    url = 'https://api.hh.ru/vacancies'
    params = {
        'text': specialty,
        'area': '1002',  # Код региона для Минска
        'per_page': 100,
        'page': page,
        'employment': 'full',
        'schedule': 'fullDay',
        'order_by': 'publication_time'
    }
    headers = {
        'User-Agent': 'api-test-agent'
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None


from datetime import datetime

def process_vacancies(vacancies):
    processed = []
    for item in vacancies:
        salary = item.get('salary')
        if salary and salary.get('currency') == 'BYR':
            salary_from = salary.get('from')
            salary_to = salary.get('to')
            if salary_from and salary_to:
                average_salary = (salary_from + salary_to) / 2
                salary_display = f"{salary_from} - {salary_to} BYN"
            elif salary_from:
                average_salary = salary_from
                salary_display = f"от {salary_from} BYN"
            elif salary_to:
                average_salary = salary_to
                salary_display = f"до {salary_to} BYN"
            else:
                average_salary = None
                salary_display = "Не указана"
        else:
            average_salary = None
            salary_display = "Не указана"

        # Преобразование даты публикации
        published_at = item.get('published_at')
        if published_at:
            try:
                # Преобразование строки в объект datetime
                dt = datetime.strptime(published_at, '%Y-%m-%dT%H:%M:%S%z')
                # Форматирование в день-месяц-год
                formatted_date = dt.strftime('%d-%m-%Y')
            except ValueError:
                formatted_date = "Неизвестно"
        else:
            formatted_date = "Неизвестно"

        processed.append({
            'name': item['name'],
            'url': item['alternate_url'],
            'employer': item['employer']['name'] if item.get('employer') else 'N/A',
            'published_at': formatted_date,
            'salary': salary_display,
            'average_salary': average_salary
        })
    return processed

def save_salary_plot(salaries, total_vacancies):
    if not salaries:
        return None
    plt.figure(figsize=(10, 6))
    plt.hist(salaries, bins=10, color='skyblue', edgecolor='black')
    plt.title(f'Распределение зарплат в Минске\nОбщее количество вакансий: {total_vacancies}')
    plt.xlabel('Зарплата (BYN)')
    plt.ylabel('Количество вакансий')
    plt.grid(True)
    plot_path = os.path.join('static', 'salary_distribution.png')
    plt.savefig(plot_path)
    plt.close()
    return plot_path

@app.route('/')
def index():
    # Получение данных из параметров запроса
    specialty = request.args.get('specialty', 'графический дизайнер')
    sort_by = request.args.get('sort_by', 'published_at')  # По умолчанию сортировка по дате публикации
    min_salary = request.args.get('min_salary', type=float, default=0)

    # Сбор всех вакансий через API
    all_vacancies = []
    page = 0
    while True:
        data = fetch_vacancies(specialty, page)
        if data and 'items' in data:
            all_vacancies.extend(data['items'])
            if data['pages'] - page > 1:
                page += 1
            else:
                break
        else:
            break

    # Обработка и фильтрация вакансий
    processed_vacancies = process_vacancies(all_vacancies)
    filtered_vacancies = [v for v in processed_vacancies if (v['average_salary'] or 0) >= min_salary]

    # Сортировка данных
    if sort_by == 'name':
        filtered_vacancies.sort(key=lambda x: x['name'])
    elif sort_by == 'employer':
        filtered_vacancies.sort(key=lambda x: x['employer'])
    elif sort_by == 'published_at':
        filtered_vacancies.sort(
            key=lambda x: datetime.strptime(x['published_at'], '%d-%m-%Y') if x['published_at'] != "Неизвестно" else datetime.min,
            reverse=True
        )
    elif sort_by == 'average_salary':
        filtered_vacancies.sort(key=lambda x: (x['average_salary'] or 0), reverse=True)

    # Подготовка данных для графика зарплат
    salaries = [v['average_salary'] for v in filtered_vacancies if v['average_salary']]
    plot_path = save_salary_plot(salaries, len(all_vacancies))

    return render_template('index.html',
                           plot_path='/static/salary_distribution.png',
                           vacancies=filtered_vacancies,
                           total_vacancies=len(all_vacancies),
                           specialty=specialty)


if __name__ == '__main__':
    app.run(debug=True)
