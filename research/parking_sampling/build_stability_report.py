"""Reproducible scientific figures and conclusions for the C4 stability audit."""
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from prepare_data import DOCS
from stability_audit import WORK
from run_phase3 import write_json

def read(p):return json.loads(p.read_text(encoding='utf-8'))

def main():
    data=read(WORK/'results.json');history=read(WORK/'history-bound/results.json')
    checks=read(DOCS/'phase3-stability-verification.json')
    training=data['training'];primary=training['primary_7_days']['minimum_diagnostics'];sensitivity=training['sensitivity_1_day']['minimum_diagnostics']
    with (WORK/'smallest-pairs-primary_7_days.csv').open(encoding='utf-8-sig') as f:minimum=next(csv.DictReader(f))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    fig,axes=plt.subplots(1,2,figsize=(12.8,5.7),gridspec_kw={'width_ratios':[1,1.15]})
    caps=range(72,77);x=np.arange(5);width=.36
    for shift,key,color,label in ((-width/2,'primary_7_days','#7c3aed','Навчальні вікна від 7 діб'),
                                 (width/2,'sensitivity_1_day','#0891b2','Навчальні вікна від 1 доби')):
        freq=training[key]['minimum_diagnostics']['bootstrap']['cap_frequency']
        values=[100*freq.get(str(g),0)/2000 for g in caps]
        axes[0].bar(x+shift,values,width,color=color,label=label)
        for xx,yy in zip(x+shift,values):
            if yy>=1:axes[0].text(xx,yy+1.2,f'{yy:.1f}',ha='center',fontsize=9)
    axes[0].set_xticks(x,[str(g) for g in caps]);axes[0].set_xlabel('Межа паузи, с');axes[0].set_ylabel('Частка повторних вибірок, %')
    axes[0].set_ylim(0,108);axes[0].set_title('2000 повторних вибірок цілих місць',fontsize=11)
    axes[0].legend(frameon=False,fontsize=9,loc='upper right');axes[0].grid(axis='y',alpha=.15);axes[0].set_axisbelow(True)
    temporal=training['primary_7_days']['temporal'];x=np.arange(5)
    axes[1].plot(x,[r['cap_seconds'] for r in temporal],marker='o',lw=2,color='#7c3aed',label='Межа з попередніх місяців')
    axes[1].plot(x,[r['following_min_sum_seconds'] for r in temporal],marker='s',lw=2,color='#0891b2',label='Мінімальна пара наступного місяця')
    axes[1].set_xticks(x,['Лютий','Березень','Квітень','Травень','Червень']);axes[1].set_ylabel('Сума B+D або межа паузи, с')
    axes[1].set_yticks(range(72,79));axes[1].set_ylim(71.5,79)
    for i,r in enumerate(temporal):
        if r['following_risky_pairs']:axes[1].annotate(f"{r['following_risky_pairs']} ризикові пари" if r['following_risky_pairs']>1 else '1 ризикова пара',
            (i,r['following_min_sum_seconds']),xytext=(i-.65,78.2),arrowprops={'arrowstyle':'->','color':'#b45309'},fontsize=9,color='#92400e')
    axes[1].set_title('Перенесення калібрування на наступний місяць',fontsize=11);axes[1].legend(frameon=False,fontsize=9,loc='lower left')
    axes[1].grid(alpha=.15)
    fig.suptitle('72 секунди: підтримка в історії та межі перенесення',fontsize=15,y=.97)
    fig.text(.5,.075,'Повторні вибірки - діагностика стійкості, не довірчий інтервал фізичного мінімуму.',ha='center',fontsize=9,color='#475569')
    fig.text(.5,.025,'City of Melbourne, 2019 (CC BY 4.0); обчислення автора. Ризикова пара не означає фактичний пропуск.',ha='center',fontsize=9,color='#475569')
    fig.tight_layout(rect=(0,.12,1,.9))
    for ext in ('png','svg'):fig.savefig(DOCS/'figures'/f'phase3-c4-stability.{ext}',dpi=180)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12.8,5.4),sharey=True)
    for ax,label,caption in zip(axes,('primary_7_days','sensitivity_1_day'),('Вікна від 7 діб','Вікна від 1 доби')):
        names=('training256','check256','check512');x=np.arange(3)
        for shift,key,color,legend in ((-.18,'generic_pair_bound','#64748b','Загальна межа за парою'),(.18,'history_conditioned_bound','#0891b2','Межа з урахуванням історії')):
            values=[history['cohorts'][f'{name}_{label}'][key] for name in names]
            ax.bar(x+shift,values,.36,color=color,label=legend)
            for xx,yy in zip(x+shift,values):ax.text(xx,yy+.16,str(yy),ha='center',fontsize=11)
        ax.set_xticks(x,['Навчання\n256 місць','Перевірка\n256 місць','Перевірка\n512 місць']);ax.set_title(caption)
        ax.set_ylim(0,12.8);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    axes[0].set_ylabel('Верхня межа кількості епізодів без вимірювання')
    handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=2,frameon=False,bbox_to_anchor=(.5,.08))
    fig.suptitle('Точніший аналіз незміненого C3 з межею 75 секунд',fontsize=15,y=.97)
    fig.text(.5,.025,'Це посилення аналітичної межі, а не зменшення фактичних помилок карти. Дані: City of Melbourne; обчислення автора.',ha='center',fontsize=8.8,color='#475569')
    fig.tight_layout(rect=(0,.17,1,.9))
    for ext in ('png','svg'):fig.savefig(DOCS/'figures'/f'phase3-history-bound-comparison.{ext}',dpi=180)
    plt.close(fig)
    bootstrap_rows=[]
    for key,caption in (('primary_7_days','Від 7 діб'),('sensitivity_1_day','Від 1 доби')):
        d=training[key]['minimum_diagnostics'];bootstrap_rows.append(f"| {caption} | {training[key]['eligible_pairs']} | {d['minimum_pair_count']} | {len(d['minimum_support_bays'])} | {d['leave_one_pair_out_largest_cap_seconds']} с |")
    temporal_rows='\n'.join(f"| До кінця {r['prefix_through_month']}-го місяця | {r['cap_seconds']} | {r['following_month']} | {r['following_min_sum_seconds']} | {r['following_risky_pairs']} |" for r in training['primary_7_days']['temporal'])
    timing_rows=[]
    for label,group in [('Навчання, 7 діб',training['primary_7_days']),('Навчання, 1 доба',training['sensitivity_1_day']),
                        ('Перевірка 256, 1 доба',data['development']['check256']),('Перевірка 512, 1 доба',data['development']['check512'])]:
        timing_rows.append('| '+label+' | '+' | '.join(str(x['candidate_risky_pairs']) for x in group['timing'])+' |')
    history_rows='\n'.join(f"| {key} | {v['generic_pair_bound']} | {v['history_conditioned_bound']} |" for key,v in history['cohorts'].items())
    all_phase_windows=[r for v in data['development'].values() for r in v['phase_windows']]
    phase_rows='\n'.join(f"| {r['bay']} | {'так' if r['primary'] else 'ні'} | {r['risky_pairs']} | {r['C3_bad_offsets_count']} | {r['C4_bad_offsets_count']} |" for r in all_phase_windows)
    report=f'''# Фаза 3: стійкість C4 та уточнення авторського внеску

Дата: 25.10.2026. Ідентифікатор: `parking-stability-audit-20261025`. Цей звіт уточнює [попередню оцінку C4](phase3-novelty-audit.md), не змінюючи її сирі результати. Основний Google-документ, презентації, прошивка та остаточні 867 місць не змінювалися й не оцінювалися.

**Висновок:** C4/72 не підтверджено як краще дослідницьке ядро порівняно з C3/75. Число 72 визначається рідкісними записами, а суцільний перебір зсувів не виявив переваги C4 за кількістю неспостережених хвилинних епізодів. Отримано корисне окреме посилення аналітичної межі з урахуванням історії. Його не видаємо за новий алгоритм із доведеною перевагою над літературою. **Фаза 4 залишається закритою.**

## 1. Що перевіряли

До запуску зафіксовано [план стійкості](phase3-stability-plan.json). Попередні результати навчання та перевірок уже були відомі. Використано ті самі 256 навчальних BayId за січень-червень і дві розробницькі групи 256/512 BayId за липень-вересень. Остаточну вибірку не відкривали; жодне нове число не називаємо остаточним сліпим тестом.

Окремий [план уточнення межі](phase3-history-bound-plan.json) записано після отримання результату суцільного перебору. Це чесно позначене аналітичне продовження, а не гіпотеза, нібито зафіксована до всіх цих результатів. Політики C3/C4, їхні пороги і ваги не переналаштовували.

Джерело станів: [City of Melbourne, On-street Car Parking Sensor Data - 2019](https://data.melbourne.vic.gov.au/explore/dataset/on-street-car-parking-sensor-data-2019/information/), CC BY 4.0. Обчислення авторські; записані інтервали не є незалежною фізичною розміткою. Час - локальні цивільні позначки, не підтверджений UTC.

## 2. Від чого залежить число 72

| Навчальні вікна | Повних пар з D>=60 | Пар із мінімумом 72 | Місць, які підтримують мінімум | Найбільша межа після вилучення однієї пари |
|---|---:|---:|---:|---:|
{chr(10).join(bootstrap_rows)}

У головній навчальній вибірці це один запис на місці **{minimum['bay']}**, {minimum['occupied_start']}: записана зайнятість тривала **{minimum['B_seconds']} с**, наступний вільний епізод - **{minimum['D_seconds']} с**. Сума - 72 с. Вилучення цієї пари, її місця або її вікна змінює навчальну межу на 73 с. Це не підстава видаляти запис як «поганий»: причини короткої сенсорної зайнятості незалежно не перевірено.

У ширшій навчальній історії від 1 доби значення 72 підтримують три місця: {', '.join(map(str,sensitivity['minimum_support_bays']))}. Таким чином, у ширшому наборі підтримка краща, проте число все одно не стає фізичною нижньою межею майбутніх подій.

У 2000 повторних вибірках цілих місць із поверненням головний навчальний мінімум зберігся в **{primary['bootstrap']['cap_frequency']['72']}/2000 = {100*primary['bootstrap']['cap_frequency']['72']/2000:.2f}%** випадків. Інші результати - від 73 до 76 с. Для ширшої історії 72 с зберігається в **{sensitivity['bootstrap']['cap_frequency']['72']}/2000 = {100*sensitivity['bootstrap']['cap_frequency']['72']/2000:.2f}%** випадків. Це діагностика впливу вибору місць; її не називаємо довірчим інтервалом справжнього мінімуму. Епізоди всередині місця не вважаємо незалежними.

![Стійкість навчальної межі та перенесення на наступний місяць](figures/phase3-c4-stability.png)

## 3. Чи переноситься мінімум на наступний місяць

Для кожного префікса використано тільки повні пари, що завершилися строго до межі наступного місяця. Наступний місяць не впливав на значення межі. Усічені на календарній межі пари виключено. Використано початково відібрані вікна від 7 діб, а не новий відбір за результатом місяця.

| Навчальна історія | Межа, с | Місяць наступної перевірки | Найменша наступна пара, с | Пар нижче попередньої межі |
|---|---:|---:|---:|---:|
{temporal_rows}

Після січня-березня межа була 75 с; у квітні з'явилися дві коротші пари. Після квітня межа стала 73 с; у травні з'явилася пара 72 с. Це безпосередній приклад того, що мінімум минулої історії може не залишитися мінімумом наступної. Додатний лічильник означає втрату нульової аналітичної межі, а не встановлений фактичний пропуск політики.

Це перевірка **калібрування межі**, а не послідовний прогнозний тест усього C3: його початкові 30/45-секундні кроки раніше навчалися на всьому січні-червні. Такий тест не підміняємо неправдивим «навчалися тільки до кожного місяця».

## 4. Гіпотетична неточність часових меж

Якщо кожна межа записаного стану могла б мати похибку до `delta` с зі збереженням порядку станів, то реальна сума двох послідовних тривалостей не менша за `S_recorded-2*delta`. Для реального епізоду від хвилини записана вільна тривалість може бути від `60-2*delta`. Порахуємо кандидати, які після такого розширення можуть порушити умову для незмінних 72 с.

| Історія | delta=0 | delta=1 с | delta=2 с | delta=5 с |
|---|---:|---:|---:|---:|
{chr(10).join(timing_rows)}

Це умовний аналіз чутливості, а не виміряна похибка Melbourne або нашого пристрою. Позитивний лічильник не означає, що всі ці зміщення справді можливі одночасно чи що пропуски обов'язково стануться. Результат показує, що гарантію для точних записаних секунд не можна автоматично переносити на неточні фізичні часові межі.

## 5. Суцільна перевірка початкових зсувів

Загальна межа `B+D<75` залишала лише **8 повних вікон**, на яких C3 теоретично міг мати хвилинний епізод без вимірювання. На решті вікон відсутність таких епізодів уже випливає з нульової загальної межі. На кожному з цих восьми вікон відтворено незмінні C3/75 і C4/72 за **всіх 3600 цілих початкових зсувів від 0 до 3599 с**.

| BayId | Вікно від 7 діб | Загальних ризикових пар | Зсувів із M60>0, C3 | Зсувів із M60>0, C4 |
|---:|---|---:|---:|---:|
{phase_rows}

Разом **{len(all_phase_windows)*3600*2} відтворень вікна-політики**, і в обох правилах M60=0. Для C3 не знайдено реального записаного прикладу пропуску в цій області стартів. Отже, стверджувати «C4 прибрав пропуски, які робив C3» не можна. C4 витрачає більше вимірів; зниження окремих F/O з попереднього звіту не скасовує цього компромісу.

Область перебору - перша година від початку кожного вікна. Для цілих часових меж, цілих пауз і правила без часу доби будь-який дробовий зсув усередині однієї секунди дає ту саму послідовність прочитаних станів: дробова частина не змінюється, а різниці між моментами вимірювань цілі. Це пояснює повноту секундної сітки в цій моделі; не поширюємо її на довільний старт у будь-який день вікна, інші політики або неточні часові позначки.

## 6. Що вдалося посилити аналітично

Довга пауза C3 можлива лише після 900 с однакових показів. Зайнятий інтервал тривалістю від 75 с мусить потрапити хоча б в одне вимірювання; після виявлення зайнятості 60-секундне обмеження змушує отримати зайнятий показ не раніше ніж за 60 с до його кінця. Це обмежує можливий вік наступної спостереженої вільної послідовності.

Отримано додаткову необхідну умову `p-r>A`, яку можна застосувати разом з `B+D<G`. [Припущення й повне доведення](phase3-history-bound-method.md). Це аналіз повноти спостереження, а не новий спосіб читати прихований стан без виміру.

| Історія | Загальна верхня межа | Верхня межа з історією |
|---|---:|---:|
{history_rows}

![Посилення верхньої межі без зміни C3](figures/phase3-history-bound-comparison.png)

На основних перевірочних вікнах обох груп отримано нуль і для C3/75. Отже, тут аналітичне обґрунтування вже не потребує 72 с. На коротших вікнах залишаються 2 та 1 потенційні епізоди; нуль у переборі першої години не перетворює цю додатну межу на нуль для довільного старту.

Це підтверджене посилення **нашої попередньої аналітичної оцінки**. Не називаємо його автоматично вдосконаленням літературного алгоритму або фактичної точності системи.

## 7. Уточнення змісту M60

M60 рахує вільні епізоди від хвилини без вимірювання всередині. За обмеження пауз після «зайнято» до 60 с такий неспостережений епізод не може весь час показуватися зайнятим: попередній утримуваний показ мусить бути «вільно». Це вже випливає з доведення C4.

Тому M60 - показник **покриття епізодів актуальними вимірами**, а не безпосередньо кількість вільних місць, які водієві помилково не показали. Для точності карти безпосередні метрики - F та O. Їх не підміняємо новою назвою M60. Вимогу мати свіже підтвердження кожного хвилинного звільнення можна задати окремо; її практичну необхідність і саме число 60 с ще не доведено зовнішнім джерелом.

Це не зміна старих лічильників задля кращого результату: старе визначення збережено. Уточнюється тільки те, які твердження цей лічильник справді підтримує.

## 8. Внесок і рішення щодо подальшої роботи

Повні результати та межі читання джерел наведено в [оновленому зіставленні](phase3-stability-sources.md). S12 і S13 тепер опрацьовано до кінця основного тексту; S11 залишається доступним лише в анотації. Причинне планування, історія, пропущені події, мінімальні тривалості й оптимізація з обмеженнями вже відомі. Саме їх поєднання або відсутність знайденого однакового коду не доводять новизни.

**C4/72 не закріплюємо як головну авторську новизну.** Його позитивні числа реальні, але обґрунтування через рідкісний мінімум і відсутня перевага за M60 роблять сильну заяву необґрунтованою. Напрям адаптивного планування вимірювань залишається; основний текст магістерської зараз не переписуємо.

Точний наявний самостійний результат можна сформулювати так:

> Уточнено аналітичну верхню межу кількості вільних епізодів без вимірювання для розкладів із короткими початковими паузами. Крім тривалостей послідовних станів, ураховано обмеження віку спостереженої послідовності, що випливає з обов'язкового спостереження достатньо тривалої зайнятості. Показано, на яких записаних історіях це посилює обґрунтування повноти вимірювань без зменшення максимальної паузи.

Це кандидат на вузький аналітичний внесок, а не встановлена світова новизна нового алгоритму. За вимоги саме покращеного алгоритму планування ця частина ще не завершена. Потрібно оцінити достатність такого внеску для вимог магістерської та, якщо необхідне алгоритмічне поліпшення, спочатку зафіксувати конкретний недолік найсильнішого аналога й перевіряти зміну саме цього недоліку. Запуск остаточного тесту не замінює цієї роботи. [Умова переходу](phase3-novelty-gate.json) залишається закритою.

## 9. Перевірки й відтворення

Пройшли **{checks['tests_run']} перевірок**: старі 59 та нові перевірки впливу мінімуму, часового поділу, похибок меж, повного перебору, уточненого доведення й різниці між покриттям та показом стану. [Протокол](phase3-stability-verification.json). Старі протоколи не переписано.

```powershell
python research/parking_sampling/stability_audit.py
python research/parking_sampling/assess_history_certificate.py
python research/parking_sampling/verify_stability.py
python research/parking_sampling/build_stability_report.py
python research/parking_sampling/verify_stability_artifacts.py
```

Сирі дані діагностики, вплив кожного місця, часові префікси й усі масиви 3600 зсувів збережено в `.codex-work/parking-stability-audit-20261025/`. Графіки доступні у PNG/SVG; попередні докази й результати збережено з історією версій.
'''
    (DOCS/'phase3-stability-report.md').write_text(report,encoding='utf-8')
    write_json(WORK/'conclusion.json',{'C4_promoted_as_author_improvement':False,'C3_C4_phase_miss_difference':0,
      'new_history_bound_confirmed_on_synthetic_and_recorded_paths':True,'scientific_novelty_established':False,
      'phase4_may_start':False,'final_test_evaluated':False})
    print(json.dumps({'report':str(DOCS/'phase3-stability-report.md'),'tests':checks['tests_run'],'phase_replays':len(all_phase_windows)*3600*2}))

if __name__=='__main__':main()
