"""Tables and scientific figures for the phase-3 author-contribution audit."""
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from prepare_data import ROOT,DOCS,sha256
from audit_episode_constraint import WORK,OLD
from report_refinement import paired_intervals
from run_phase3 import write_json

def read(path):return json.loads(path.read_text(encoding='utf-8'))

def main():
    ablation=read(WORK/'new-check-results.json');lock=read(WORK/'pre-fit-lock.json')
    fit=read(WORK/'candidates.json');c4=read(WORK/'pair-envelope-v2/development-results.json')
    selected=read(WORK/'pair-envelope-v2/selection-before-development-replay.json')
    write_json(DOCS/'phase3-pair-envelope-policy.json',{
      'source_policy':'C4_training_pair_envelope_72','source_npz_sha256':selected['model_sha256'],
      'observed_run_thresholds_seconds':[300,900],'free_pauses_seconds':[30,45,selected['free_cap_seconds']],
      'occupied_pauses_seconds':[30,60,60],
      'derivation':'Inherited C3 startup rule; long free cap computed from Jan-Jun complete adjacent occupied/free training pairs',
      'history':'Observed sequence of equal sampled states, not known true physical duration',
      'scope':'phase3_development_candidate; recorded-path certificate only; final test not evaluated',
      'selection_record_sha256':sha256(WORK/'pair-envelope-v2/selection-before-development-replay.json')})
    old=read(OLD/'fresh-check-results.json');old_selection=read(OLD/'selection-before-fresh-check.json')['selected']
    controls=read(WORK/'pair-envelope-controls/results.json')
    previous=read(OLD/'pre-fit-lock.json');verification=read(DOCS/'phase3-novelty-verification.json')
    records=[];ci={};comparisons={}
    for cohort in ('check256','check512'):
        for label in ('primary_7_days','sensitivity_1_day'):
            item=c4['cohorts'][f'{cohort}_{label}'];c4_path=WORK/'pair-envelope-v2'/f'{cohort}_{label}.npz'
            if cohort=='check256':
                group=ablation['cohorts'][label]['results'];r0=group['fixed60'];r3=group['missed_episodes_at_least_60_seconds']
                ref_path=WORK/label/'fixed60.npz';c3_path=WORK/label/'missed_episodes_at_least_60_seconds.npz'
            else:
                group=old['cohorts'][label]['results'];r0=group['fixed_60'];r3=group[old_selection['without_time']]
                ref_path=OLD/label/'fixed_60.npz';c3_path=OLD/label/f"{old_selection['without_time']}.npz"
            reference=np.load(ref_path)['by_bay_phase'];a=np.load(c4_path)['by_bay_phase'];b=np.load(c3_path)['by_bay_phase']
            np.testing.assert_array_equal(a[:,:,0],reference[:,:,0]);np.testing.assert_array_equal(a[:,:,9],reference[:,:,9])
            ci[f'{cohort}_{label}']={'C4_vs_fixed60':paired_intervals(a,reference,seed=20261025),
                                    'C4_vs_C3':paired_intervals(a,b,seed=20261025)}
            methods={'fixed60':r0,'C3_75':r3,'C4_72':item,**controls['cohorts'][f'{cohort}_{label}']};comparisons[f'{cohort}_{label}']=methods
            for name in controls['cohorts'][f'{cohort}_{label}']:
                control=np.load(WORK/'pair-envelope-controls'/f'{cohort}_{label}_{name}.npz')['by_bay_phase']
                ci[f'{cohort}_{label}'][name+'_vs_fixed60']=paired_intervals(control,reference,seed=20261025)
            for name,row in methods.items():
                m=row['metrics'];records.append([cohort,label,name,m['samples_per_bay_day'],row['checks_reduction_percent'],
                    m['false_free_seconds_per_bay_day'],m['false_occupied_seconds_per_bay_day'],
                    *[m['vacancy_duration_profiles'][str(t)]['missed'] for t in (0,30,60,120,300)],
                    row.get('original_quality_passes',row.get('quality_passes',True))])
    write_json(WORK/'pair-envelope-v2/paired-bay-intervals.json',{'draws':2000,'seed':20261025,
      'unit':'BayId, retaining all phases/windows together','intervals':ci,
      'limits':'Spatial bootstrap on development data; not a confidence guarantee for unseen event risk or independent dates.'})
    with (DOCS/'phase3-novelty-results.csv').open('w',newline='',encoding='utf-8-sig') as file:
        writer=csv.writer(file);writer.writerow(['cohort','windows','policy','checks_per_bay_day','checks_reduction_percent',
            'F_seconds_per_bay_day','O_seconds_per_bay_day','missed0_episode_phases','missed30_episode_phases',
            'missed60_episode_phases','missed120_episode_phases','missed300_episode_phases','original_quality_passes']);writer.writerows(records)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    folder=DOCS/'figures';folder.mkdir(exist_ok=True);colors=['#64748b','#0891b2','#7c3aed']
    fig,axes=plt.subplots(2,3,figsize=(12.8,7.2))
    keys=[('samples_per_bay_day','Вимірювань на місце за добу'),('false_free_seconds_per_bay_day','Помилково «вільно», с/добу'),('false_occupied_seconds_per_bay_day','Помилково «зайнято», с/добу')]
    for row,label in enumerate(('primary_7_days','sensitivity_1_day')):
        for col,(key,title) in enumerate(keys):
            group=comparisons[f'check512_{label}'];values=[group[n]['metrics'][key] for n in ('fixed60','C3_75','C4_72')]
            ax=axes[row,col];ax.bar(range(3),values,color=colors,width=.62)
            for x,y in enumerate(values):ax.text(x,y+max(values)*.018,f'{y:.1f}',ha='center',fontsize=10)
            ax.set_ylim(0,max(values)*1.18);ax.set_xticks(range(3),['Кожні 60 с','C3 / 75 с','C4 / 72 с']);ax.set_title(title,fontsize=11)
            ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
            if col==0:ax.set_ylabel('Вікна від 7 діб' if row==0 else 'Вікна від 1 доби')
    fig.suptitle('Обґрунтована межа паузи: перевірка на 512 місцях',fontsize=16,y=.985)
    fig.text(.5,.935,'Розроблення, липень-вересень 2019. У всіх трьох правилах M60 = 0 за 10 зсувів.',ha='center',color='#475569')
    fig.text(.5,.018,'Джерело: City of Melbourne, дані за 2019 рік (CC BY 4.0); обчислення автора. Це не остаточний тест.',ha='center',fontsize=9,color='#475569')
    fig.tight_layout(rect=(0,.045,1,.91))
    for ext in ('png','svg'):fig.savefig(folder/f'phase3-pair-envelope-tradeoff.{ext}',dpi=180)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12.8,5.4),gridspec_kw={'width_ratios':[1.15,1]})
    labels=[];values=[]
    for cohort in ('check256','check512'):
        for label,caption in (('primary_7_days','від 7 діб'),('sensitivity_1_day','від 1 доби')):
            labels.append(f"{cohort[5:]} місць, {caption}")
            values.append(c4['cohorts'][f'{cohort}_{label}']['complete_risky_pairs_all_phases']['75'])
    y=np.arange(4);axes[0].barh(y,values,color=colors[1],height=.55)
    for i,v in enumerate(values):axes[0].text(v+.1,i,str(v),va='center')
    axes[0].set_yticks(y,labels);axes[0].invert_yaxis();axes[0].set_xlim(0,max(values)+1)
    axes[0].set_xlabel('Повні пари з D ≥ 60 с та B + D < 75 с')
    axes[0].set_title('75 с: додатна верхня межа ризикових епізодів',fontsize=11)
    axes[0].grid(axis='x',alpha=.15);axes[0].set_axisbelow(True)
    axes[1].axis('off');axes[1].text(.06,.86,'72 с: 0 таких пар',fontsize=19,fontweight='bold',color=colors[2])
    axes[1].text(.06,.66,'За паузи після «зайнято» не більше 60 с\nце виключає повний пропуск хвилинного\nзвільнення на цих записаних траєкторіях.',fontsize=12,linespacing=1.5)
    axes[1].text(.06,.34,'Умова стосується всіх зсувів розкладу,\nа не лише десяти перевірених.',fontsize=12,linespacing=1.5)
    axes[1].text(.06,.12,'Додатна межа для 75 с не означає, що C3\nобов’язково пропустить ці епізоди.\nГарантії для невідомого майбутнього немає.',fontsize=10.5,color='#475569',linespacing=1.4)
    fig.suptitle('Чим аналітична перевірка відрізняється від десяти повторів',fontsize=15,y=.97)
    fig.text(.5,.02,'Пари пораховано один раз на повному вікні. Вікна від 1 доби включають вікна від 7 діб.',ha='center',fontsize=9,color='#475569')
    fig.tight_layout(rect=(0,.05,1,.9))
    for ext in ('png','svg'):fig.savefig(folder/f'phase3-pair-envelope-certificate.{ext}',dpi=180)
    plt.close(fig)
    def table(cohort):
        rows=['| Вікна | Правило | Вимірів/добу | Менше вимірів | F, с/добу | O, с/добу | M60 | Умови якості |',
              '|---|---|---:|---:|---:|---:|---:|---|']
        for label,caption in (('primary_7_days','Від 7 діб'),('sensitivity_1_day','Від 1 доби')):
            for name,item in comparisons[f'{cohort}_{label}'].items():
                m=item['metrics'];passes=item.get('original_quality_passes',item.get('quality_passes',True))
                rows.append(f"| {caption} | {name} | {m['samples_per_bay_day']:.2f} | {item['checks_reduction_percent']:.2f}% | {m['false_free_seconds_per_bay_day']:.2f} | {m['false_occupied_seconds_per_bay_day']:.2f} | {m['vacancy_duration_profiles']['60']['missed']} | {'так' if passes else 'ні'} |")
        return '\n'.join(rows)
    def interval(value):return '['+', '.join(f'{x:.2f}' for x in value)+']'
    intervals='\n'.join(f"- {cohort[5:]} місць, {'від 7 діб' if label=='primary_7_days' else 'від 1 доби'}: скорочення вимірів {interval(ci[f'{cohort}_{label}']['C4_vs_fixed60']['checks_reduction_percent'])}%; різниця F {interval(ci[f'{cohort}_{label}']['C4_vs_fixed60']['F_difference_seconds_per_day'])}; різниця O {interval(ci[f'{cohort}_{label}']['C4_vs_fixed60']['O_difference_seconds_per_day'])} с/місце/добу."
      for cohort in ('check256','check512') for label in ('primary_7_days','sensitivity_1_day'))
    bound_rows='\n'.join(f"| {cohort[5:]} | {'Від 7 діб' if label=='primary_7_days' else 'Від 1 доби'} | {c4['cohorts'][f'{cohort}_{label}']['complete_risky_pairs_all_phases']['75']} | {c4['cohorts'][f'{cohort}_{label}']['complete_risky_pairs_all_phases']['72']} |"
      for cohort in ('check256','check512') for label in ('primary_7_days','sensitivity_1_day'))
    overlap={cohort:len(set(bays)&set(previous['training_bays'])) for cohort,bays in [('check256',lock['new_check_bays']),('check512',previous['fresh_check_bays'])]}
    report=f'''# Фаза 3: перевірка авторського внеску й правило C4

Дата: 25.10.2026. Ідентифікатор: `phase3-novelty-audit-20261025`. Основний Google-документ і презентації не змінювалися.

**Результат:** додаткове обмеження на пропуски саме по собі не пояснило перевагу C3. Натомість отримано окреме аналітичне обґрунтування максимальної паузи та реалізовано C4, де довга пауза визначається за навчальними парами тривалостей. Воно дає меншу економію вимірів, але для перевірених траєкторій - сильніше обґрунтування відсутності хвилинних пропусків. Світову новизну та перевагу над усіма аналогами не встановлено. **Фаза 4 поки закрита.**

## 1. Контрольна перевірка початкової претензії

До запуску зафіксовано [план](phase3-novelty-audit-plan.json): однакові 256 навчальних місць, початкове хвилинне правило, 12 ефективних груп стану/спостереженої тривалості, множина дій, дві ітерації пошуку, сітка ваг та правила вибору. Відрізнялося лише обмеження:

1. Тільки дві тривалості помилкового показу F/O.
2. Додатково загальна кількість повністю пропущених звільнень M0 не більша за хвилинне правило.
3. Додатково кількість повністю пропущених звільнень від хвилини M60 не більша за хвилинне правило, тобто нуль.

Для кожної групи отримано 27 конфігурацій, разом 81; кеш містить {fit['training_evaluations']} різних навчальних відтворень. Захищений варіант точно відтворив попередні таблиці C3 для всіх 27 конфігурацій. **Усі три групи обрали одну й ту саму таблицю.** Їхні результати на нових 256 місцях збігаються до сирих лічильників. Умову успіху «менше M60, ніж у двох контролів» не виконано.

Отже, значущість самого показника тривалості події не означає, що обмеження реально змінило обрану політику. Побудовано також синтетичний приклад: дві історії з однаковими спостереженнями, F/O, чотирма переходами та двома загальними пропусками, але з різним M60. Він доводить відмінність критеріїв, проте не доводить ефекту нашого обмеження на реальних даних.

## 2. Що саме додано в C4

Отримано необхідну умову: якщо після «зайнято» пауза не перевищує 60 с, для повного пропуску вільного епізоду від хвилини сума його тривалості D та безпосередньо попередньої зайнятості B повинна бути меншою за максимальну паузу G після «вільно»:

```text
Повний пропуск D >= 60 с  =>  B + D < G.
```

Кількість таких пар є верхньою межею кількості пропусків на конкретній траєкторії. Якщо пар немає, пропуск виключено для всіх розкладів, що дотримуються меж пауз. [Повні припущення, доведення, формули та причинне правило C4](phase3-pair-envelope-method.md).

У {selected['eligible_training_pairs']} навчальних пар мінімальна сума дорівнює {selected['minimum_training_pair_sum_seconds']} с. За зафіксованим до навчання правилом `G=min(120, min(B+D))` отримано **72 с**. У C3 замінено тільки довгу вільну паузу 75 на 72 с; початкові 30/45 с і зайняті 30/60 с залишилися однаковими. Підбору G за липнем-вереснем не було. Довга пауза застосовується після 900 с однакових спостережених показів «вільно»; це не відомий справжній вік вільного стану.

Це авторська модифікація з конкретним виведенням, а не нова назва колишньої таблиці. Але сама простота виведення чи відмінність реалізації ще не доводить наукової новизни. [Матриця найближчих джерел і точні межі прочитання](phase3-novelty-sources.md).

## 3. Межі перевірки

Після первинної контрольної перевірки **256 місць уже стали даними розроблення**. C4 перевіряється на раніше відомих групах 128/256/512; жодну з них не називаємо новим остаточним сліпим тестом. Нові 256 не перетинаються з попередніми 128/512 та 166 місцями старого префікса. 256 і 512 взаємно не перетинаються, разом це 768 перевірочних BayId. Із навчальними 256 BayId збігаються відповідно {overlap['check256']} та {overlap['check512']} місць, але навчання - січень-червень, перевірка - липень-вересень. Отже, ці результати не є повною перевіркою перенесення на невідомі місця.

Використано 10 однакових початкових зсувів для всіх правил. Вікна від 1 доби включають основні вікна від 7 діб, тому це перевірка чутливості, а не незалежний другий експеримент. М60 у таблицях - **кількість пар «епізод-зсув»**, а не кількість незалежних фізичних подій. Обидві помилки та кількість вимірів нормовані на спільний час відтворення.

F - час, коли показано «вільно», а записано «зайнято»; O - зворотна помилка. Джерело траєкторій: [City of Melbourne, 2019](https://data.melbourne.vic.gov.au/explore/dataset/on-street-car-parking-sensor-data-2019/information/), CC BY 4.0. Підготовка й прогалини описані у [фазі 2](phase2-data-report.md). Записані сенсорні стани не є незалежною фізичною розміткою.

## 4. Числові результати

### Група 256 місць

{table('check256')}

### Група 512 місць

{table('check512')}

![Порівняння кількості перевірок і часу двох помилок](figures/phase3-pair-envelope-tradeoff.png)

На всіх чотирьох поєднаннях групи й тривалості вікна C4 виконав початкові умови F/O/M60 і зменшив число перевірок порівняно з хвилинним правилом. **Скорочення становить 1.56-3.01%.** C3/75 економить більше вимірів. C4 не домінує над ним за всіма помилками: зокрема, O на 512 місцях трохи більша за O C3, хоча нижча за хвилинне правило.

Окремо за [заздалегідь записаним планом контролів](phase3-pair-envelope-controls-plan.json) перевірено простіші правила. `simple75` - раніше обране нарощування: після «вільно» 45 с до 900 с однакових показів, потім 75 с; після «зайнято» завжди 60 с. `simple72` змінює тільки 75 на ту саму навчальну межу 72 с. `state_only72` завжди чекає 72 с після «вільно» й 60 с після «зайнято».

Стале правило дає найбільшу економію, але помилка F приблизно на 19% більша за хвилинне правило. Просте нарощування з межею 72 с економить 5.91-6.44%, проте не виконує точну умову O на трьох із чотирьох перевірок. Перевищення мале: приблизно 0.17-0.82 с/місце/добу. Це **не встановлення статистично значущої шкоди**: парні інтервали збережено разом з усіма іншими й потребують відповідної інтерпретації. На нових 256 основних місцях початкове `simple75` теж трохи порушило F. Отже, складніший C4 залишаємо як варіант із більшим запасом щодо помилок, а прості правила - як обов'язкові конкуренти. Висновок «C4 кращий за всі прості правила» був би неправдивим.

Орієнтовні 95% парні інтервали для C4 проти хвилинного правила, 2000 повторних вибірок **місць**, зі збереженням усіх їхніх вікон і зсувів:

{intervals}

Це оцінка розкиду між місцями на даних розроблення. Вона не враховує всю залежність між сусідніми місцями та спільними датами й не дає гарантії нульового ризику майбутніх подій. Повні інтервали C4 проти C3 збережено окремо.

## 5. Що додала аналітична перевірка

Для цього лічильника кожне повне вікно розглядається один раз, без множення на десять зсувів:

| Місць | Вікна | Пар з D>=60 та B+D<75 | Пар з D>=60 та B+D<72 |
|---:|---|---:|---:|
{bound_rows}

![Відмінність аналітичного обмеження від кількох повторів розкладу](figures/phase3-pair-envelope-certificate.png)

Для 72 с отримано нуль на всіх повних вікнах цих двох груп. За доведеним твердженням це виключає хвилинні пропуски **на цих записах** для будь-якого початкового зсуву політики з відповідними межами. Для 75 с теорема залишає ненульову верхню межу. Це не доказ того, що конкретний C3 обов'язково реалізує хоча б один із цих пропусків.

Початкова груба межа за однією короткою зайнятістю була значно слабшою: наприклад, для 256 місць/7 діб давала 10346 пар «епізод-зсув» проти 10 у межі за сумою. Уточнення відсікає довгі вільні епізоди, які фізично не вміщаються в паузу. Межа може залишатися консервативною; вона не прогнозує фактичну кількість пропусків.

## 6. Що можна захищати, а що залишається відкритим

Маємо власний аналітичний результат, його реалізацію та кероване порівняння зміни тільки одного елемента розкладу. Для формулювання внеску пропонується [вузький опис у записці C4](phase3-pair-envelope-method.md), який не приписує автору винахід адаптивного опитування.

Поки не встановлено: світову новизну цієї конструкції; перевагу над найближчими методами за однаковою вимогою до гарантованої межі; стійкість калібрування до зміни періоду, часових похибок та рідкісних записів. Мінімум 72 с з навчання не є законом поведінки всіх машин. Збереження умови на даних липня-вересня - результат перевірки, а не доказ її збереження назавжди.

Тому [умову входу у фазу 4](phase3-novelty-gate.json) не відкрито. Наступне вузьке завдання фази 3 - завершити зіставлення саме доведеної умови й калібрування з найближчою літературою та оцінити стійкість навчального мінімуму. Перевірка простіших контролів уже виконана; її не переносимо мовчки на майбутнє. Остаточні 867 місць не оцінювалися. Значного переписування магістерської зараз не потрібно.

## 7. Відтворення і перевірки

Пройшли **{verification['tests_run']} перевірок**, включно з незалежним симулятором, граничними моментами, однаковими майбутньо-незалежними рішеннями, контрольним втручанням в обмеження, випадковими та вичерпними короткими траєкторіями для двох аналітичних меж. [Протокол перевірок](phase3-novelty-verification.json).

Основні команди з кореня репозиторію після встановлення наявних залежностей дослідження:

```powershell
python research/parking_sampling/audit_episode_constraint.py
python research/parking_sampling/assess_cycle_certificate.py
python research/parking_sampling/assess_pair_certificate.py
python research/parking_sampling/fit_pair_envelope.py
python research/parking_sampling/assess_pair_envelope_controls.py
python research/parking_sampling/verify_novelty_audit.py
python research/parking_sampling/build_novelty_report.py
```

Підсумкові [таблиці CSV](phase3-novelty-results.csv); графіки PNG/SVG розміщено в `figures`. Сирі масиви, навчальні таблиці, зафіксовані вибірки й рішення до повторного відтворення - у `.codex-work/parking-novelty-audit-20261025/`. Виправлення порожньої навчальної вибірки винесено в C4 v2; результат на фактичній непорожній вибірці не змінився, код v1 збережено окремо. Старі код, результати й протоколи фаз 1-3 не переписувалися; поточний README має історичний знімок.
'''
    (DOCS/'phase3-novelty-audit.md').write_text(report,encoding='utf-8')
    print(json.dumps({'report':str(DOCS/'phase3-novelty-audit.md'),'rows':len(records),'tests':verification['tests_run'],'overlap_with_training_bays':overlap}))

if __name__=='__main__':main()
