# Відтворення результатів

У репозиторії доступні код застосунку й прошивки, демонстрація, протокол,
зафіксовані параметри та підсумки оцінювання на 867 паркомісцях.

## Перевірка опублікованих результатів

Команди виконуються з кореня репозиторію. Дослідження перевірено з Python 3.12.

```powershell
python -m pip install numpy==2.3.5
python tools/verify_research_delivery.py
```

Скрипт звіряє контрольні суми й підсумовує збережені лічильники для 17
розкладів у двох наборах вікон. Ця перевірка працює одразу після клонування.

## Повторне оцінювання з відкритого набору даних

Джерело сенсорних записів – [On-street Car Parking Sensor Data - 2019](https://data.melbourne.vic.gov.au/explore/dataset/on-street-car-parking-sensor-data-2019/information/),
опубліковане містом Мельбурн за ліцензією CC BY 4.0.
[Вихідний архів CSV](https://opendatasoft-s3.s3.amazonaws.com/downloads/archive/7pgd-bdf2.zip)
завантажується з порталу. Зафіксовані контрольні суми джерела наведено
в [реєстрі підготовки даних](../research/adaptive-sampling/phase2-data-lock.json).

```powershell
python -m pip install -r research/parking_sampling/requirements.txt
python research/parking_sampling/download_source.py --workdir .research-data/melbourne-2019
python research/parking_sampling/prepare_data.py --workdir .research-data/melbourne-2019
python research/parking_sampling/replay_final.py --workdir .research-data/melbourne-2019
```

Підготовка розпаковує приблизно 7,5 ГБ записів і створює проміжні файли в
локальній робочій папці. Повторне оцінювання використовує зафіксовані
параметри та звіряє результат кожного розкладу окремо для кожного паркомісця.

- [Запуск браузерної демонстрації](../../frontend/README.md)
- [Протокол експерименту і склад вибірки](../research/adaptive-sampling/phase4-display-protocol.md)
- [Графік і підсумкова таблиця](../research/adaptive-sampling/phase4-display-report.md)
- [Повні результати CSV](../research/adaptive-sampling/phase4-display-results.csv)
