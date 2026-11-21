"""Publish the data-preparation record from completed, verified artifacts."""
from datetime import datetime,timezone
import json
from pathlib import Path
import platform

import duckdb

from prepare_data import ROOT,DOCS,sha256

WORK=ROOT/'.codex-work/parking-research-phase2-20261018'

def integer(value):
    return f'{int(value):,}'.replace(',',' ')

def days(value):
    return f'{value/86400:,.2f}'.replace(',',' ')

def main():
    prepared=WORK/'prepared'
    data=json.loads((prepared/'data-manifest.json').read_text(encoding='utf-8'))
    source=json.loads((WORK/'source/source-manifest.json').read_text(encoding='utf-8'))
    verified=json.loads((prepared/'verification.json').read_text(encoding='utf-8'))
    figures=json.loads((DOCS/'figures/phase2-figure-manifest.json').read_text(encoding='utf-8'))
    if not verified['all_passed'] or data['final_policy_metrics_evaluated']:
        raise ValueError('Only verified data with unopened policy outcomes may be published')
    con=duckdb.connect(str(WORK/'preparation.duckdb'),read_only=True)
    clean_rows=con.execute('SELECT count(*) FROM clean_intervals').fetchone()[0]
    raw_segments=con.execute('SELECT count(*) FROM segments').fetchone()[0]
    con.close()
    quality={v['quality']:v['seconds'] for v in data['quality_year_grid']}
    primary=[v for v in data['window_summary'] if v['is_primary']]
    total_primary=sum(v['seconds'] for v in primary)
    total_year=sum(quality.values())
    known=quality['known']
    roles={
      'train_development':'Навчання, місця для розроблення',
      'validation_development':'Налаштування, місця для розроблення',
      'exploratory_late_development':'Пошуковий жовтень-грудень',
      'quarantine_train_reserved':'Січень-червень зарезервованих місць',
      'quarantine_validation_unused':'Липень-вересень зарезервованих місць, не для налаштування',
      'quarantine_final_test':'Остаточний тест, жовтень-грудень',
    }
    table='\n'.join(f"| {roles[v['split_role']]} | {integer(v['bays'])} | {integer(v['windows'])} | {days(v['seconds'])} |" for v in primary)
    labels={'known':'Однозначний записаний стан','internal_gap':'Прогалини всередині спостереженої історії','conflict':'Одночасні суперечливі стани','dst_mask':'Два виключені дні переходу часу','outside_observed_span':'Час поза першим/останнім наявним записом місця'}
    qtable='\n'.join(f"| {labels.get(v['quality'],v['quality'])} | {days(v['seconds'])} | {100*v['seconds']/total_year:.3f}% |" for v in data['quality_year_grid'])
    count=data['raw_parse']['source_rows']
    text=f'''# Фаза 2. Підготовка повного набору даних

Дата: 18.10.2026. **Фаза 2 завершена.** Методи планування на остаточній вибірці не запускалися.

## 1. Результат

Кількість опрацьованих записів - **{integer(count)}**, паркомісць - **{integer(data['valid_after_clipping']['bays'])}**. Підготовлено неперервні вікна для навчання, налаштування та остаточного порівняння. Основний остаточний тест містить **{integer(data['final_primary_test_bays'])} раніше не використаних у пілоті місць**; заданий у протоколі практичний мінімум 20 місць виконано. Це результат підготовки даних, а не підтвердження переваги алгоритму.

## 2. Походження та умови використання

Джерело S5: City of Melbourne, *On-street Car Parking Sensor Data - 2019*. [Офіційна сторінка](https://data.melbourne.vic.gov.au/explore/dataset/on-street-car-parking-sensor-data-2019/information/), [офіційні метадані](https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets/on-street-car-parking-sensor-data-2019), [архів](https://opendatasoft-s3.s3.amazonaws.com/downloads/archive/7pgd-bdf2.zip). Власні кількості у цьому звіті отримано повним читанням архіву, а не округленим описом на порталі.

Метадані власника вказують **CC BY** та посилання на [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode). Збережено відповідь API із цими полями. Запис DataVic також отримано через API; його загальна позначка `other-open` менш конкретна, ніж ліцензія власника. У підписах рисунків зазначаємо власника даних та авторство обчислень. Основний портал та його API зараз не містять рядків цієї таблиці, тому використано окремий офіційний архів.

Архів: {integer(source['archive_bytes'])} байтів. Основний CSV: {integer(source['csv_bytes'])} байтів. Перевірено CRC всіх ZIP-записів, збережено SHA-256 архіву й CSV. Службовий метафайл macOS не вважається таблицею спостережень.

```text
ZIP SHA-256: {source['archive_sha256']}
CSV SHA-256: {source['csv_sha256']}
```

Знімки метаданих і сирі дані знаходяться в `.codex-work/parking-research-phase2-20261018/source/`. Ключі наукових джерел і бібліографія: [реєстр](sources.md), [BibTeX](references.bib).

## 3. Перевірка та очищення

- Усі рядки прочитані строгим CSV-парсером із явними подвійними лапками. Поле тривалості може містити кому всередині лапок; рядки з такими значеннями не відкидались.
- Помилок розпізнавання BayId, часових позначок і двійкового стану не виявлено.
- **{integer(data['raw_parse']['nonpositive_interval_rows'])}** інтервалів із нульовою або від'ємною тривалістю виключено. Після цього кількість вхідних інтервалів становить {integer(data['valid_after_clipping']['valid_interval_rows'])}.
- Суміжні й сумісні перекривні записи одного стану об'єднано. Сформовано {integer(clean_rows)} однозначних інтервалів стану та {integer(raw_segments)} неперервних ділянок до календарного поділу й фільтру довжини.
- Прогалини та суперечливі перекриття залишено невідомими. Історія через них не продовжується вигаданим станом.
- Дати 07.04.2019 і 06.10.2019 виключено за наперед заданим правилом через відсутність UTC-зсуву. Використовується локальний календар, а не підтверджений UTC.

Кількість сирих додатних рядків тривалістю до хвилини - {integer(data['raw_parse']['positive_raw_intervals_under_60s'])}. **Це не число коротких звільнень**: рядки можуть бути частинами одного стану і спочатку об'єднуються.

### Покриття календарної сітки

Знаменник таблиці - 365 діб для кожного включеного місця, тобто вся календарна сітка {integer(data['valid_after_clipping']['bays'])} місць. Час поза першою/останньою подією не називаємо встановленою несправністю датчика.

| Категорія | Місце-діб | Частка календарної сітки |
|---|---:|---:|
{qtable}

Місце-доба означає сумарний час, поділений на 86400 секунд. Однозначні сумісні перекриття не є конфліктами; їхня сумарна тривалість {days(data['known_same_state_overlap_seconds'] or 0)} місце-діб є підмножиною однозначного часу. Не всі такі перекриття автоматично є точними дублікатами рядків.

## 4. Поділ даних

Відбір виконано за [протоколом фази 1](phase1-protocol.md). Усі 166 місць із початкового префікса виключені з остаточного тесту. Додатково перевірено, що всі 250 000 раніше прочитаних рядків збігаються за полями з початком поточного повного CSV.

Нові зарезервовані місця визначено хешем BayId, без перегляду якості роботи алгоритму. Для навчання відведено січень-червень, налаштування - липень-вересень незарезервованих місць, остаточного тесту - жовтень-грудень зарезервованих місць.

Основні вікна від 7 діб:

| Підвибірка | Паркомісць | Вікон | Місце-діб |
|---|---:|---:|---:|
{table}

Кількості місць між рядками не додаються: одне місце може мати історію в різні періоди. Разом основні вікна зберігають {days(total_primary)} місце-діб, або {100*total_primary/known:.2f}% однозначного часу. Додатково збережено коротші вікна від 1 доби для передбаченої перевірки чутливості. У файлах основну вибірку потрібно явно відбирати через `is_primary=true`.

Історія зарезервованих місць за січень-червень відкладена до фіксації навчального конвеєра; липень-вересень цих місць не використовується для налаштування. Остаточні файли відокремлені процедурно; це не шифрування або технічна заборона доступу. Підготовка й перевірка структури інтервалів не є оцінюванням методу на тесті.

## 5. Перші графіки

Графіки побудовано **тільки на основній навчальній підвибірці для розроблення**: {integer(figures['bays'])} місць, {integer(figures['windows'])} вікон. Остаточні інтервали для цих рисунків не читалися. Це власні обчислення з даних S5.

### Зайнятість і наявність даних

![Зайнятість і покриття навчальних даних](figures/phase2-training-occupancy.png)

Верхня частина показує зайнятість серед відомого часу, нижня - частку доступного часу включених місць. Невідомі ділянки не підмінені вільним станом. [Векторний SVG](figures/phase2-training-occupancy.svg).

### Тривалості станів

![Розподіл тривалостей станів у навчальних даних](figures/phase2-training-durations.png)

Крайні обрізані епізоди кожного вікна виключено. По горизонталі тривалість, по вертикалі частка епізодів, не довших за неї. Крива описує записані сенсорні стани; вона не встановлює, які звільнення були придатними для водія. [Векторний SVG](figures/phase2-training-durations.svg).

## 6. Перевірка та відтворення

Пройшли вісім контрольних тестів, зокрема порівняння точного проходу з незалежним посекундним підрахунком на випадкових перекриттях. Повний конвеєр додатково перевірено на синтетичному CSV із комою в лапках. Перевірка готових файлів підтвердила контрольні суми, суцільність покриття кожного вікна, відсутність перекриттів, злиття повторів, календарний поділ та правильність резервування місць.

Код і команди: [research/parking_sampling](../../../research/parking_sampling/README.md). Зафіксовані результати підготовки й перевірки: [phase2-data-lock.json](phase2-data-lock.json). Хеші графіків: [реєстр рисунків](figures/phase2-figure-manifest.json). Налаштування застосунку, його сервер і прошивку ця фаза не змінює.

Великі дані залишаються в робочій теці й не додаються до Git. Звіт фіксує походження, кількості й контрольні суми, щоб обчислення можна було повторити.

## 7. Межі висновку та наступна фаза

Даних достатньо для запланованого порівняння за кількістю місць і часовим покриттям. Це ще не оцінка статистичної потужності та не доказ користі кандидата. Обмеження відбору вікон, сенсорного походження станів, одного міста й одного року зберігаються.

Наступна фаза 3: спільний симулятор, регулярні й прості адаптивні правила, відтворення сильного аналога S2, реалізація C0/C1/C2 та зіставлення конкретного правила з близькими роботами. Налаштування відбуватиметься на відведених для цього даних. Порівняльні графіки економії й помилок з'являться після реалізації та перевірки методів.
'''
    (DOCS/'phase2-data-report.md').write_text(text,encoding='utf-8')
    lock={
      'locked_at_utc':datetime.now(timezone.utc).isoformat(),'phase':2,'phase_complete':True,
      'data_preparation':data,'verification':verified,
      'source_snapshot':source,
      'source_license':{'label':'CC BY','version':'4.0','url':'https://creativecommons.org/licenses/by/4.0/legalcode','evidence':'source official_api.json metas.default.license and license_url'},
      'clean_interval_rows':clean_rows,'raw_continuous_segments':raw_segments,
      'figures_manifest_sha256':sha256(DOCS/'figures/phase2-figure-manifest.json'),
      'phase2_report_sha256':sha256(DOCS/'phase2-data-report.md'),
      'code_sha256':{p.name:sha256(p) for p in (ROOT/'research/parking_sampling').glob('*.py')},
      'python_version':platform.python_version(),
      'historical_phase1_readme_snapshot':{'path':'docs/research/adaptive-sampling/phase1-roadmap-snapshot.md','sha256':sha256(DOCS/'phase1-roadmap-snapshot.md')},
      'current_roadmap_sha256':sha256(DOCS/'README.md'),
      'final_policy_results_opened':False,
    }
    (DOCS/'phase2-data-lock.json').write_text(json.dumps(lock,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'phase_2_complete':True,'rows':count,'bays':data['valid_after_clipping']['bays'],'final_test_bays':data['final_primary_test_bays'],'report':str(DOCS/'phase2-data-report.md')},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
