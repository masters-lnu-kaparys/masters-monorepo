"""Refinement audit, paired bay bootstrap and scientific PNG/SVG output."""
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from prepare_data import ROOT,DOCS,sha256
from refine_policy import WORK
from run_phase3 import write_json

def paired_intervals(candidate,reference,seed=20261020,draws=2000):
    # Keep all phases/windows of each BayId together. Never resample phases as bays.
    a=candidate.sum(axis=1).astype(float);b=reference.sum(axis=1).astype(float)
    rng=np.random.default_rng(seed);weights=rng.multinomial(len(a),np.full(len(a),1/len(a)),size=draws)
    aa=weights@a;bb=weights@b;days=aa[:,0]/86400
    values={'checks_reduction_percent':100*(1-aa[:,1]/bb[:,1]),
      'F_difference_seconds_per_day':(aa[:,2]-bb[:,2])/days,
      'O_difference_seconds_per_day':(aa[:,3]-bb[:,3])/days,
      'M60_difference_percentage_points':100*(aa[:,14]/np.maximum(1,aa[:,9])-bb[:,14]/np.maximum(1,bb[:,9]))}
    return {key:np.quantile(value,[.025,.975]).tolist() for key,value in values.items()}

def main():
    fresh=json.loads((WORK/'fresh-check-results.json').read_text(encoding='utf-8'))
    controls=json.loads((WORK/'controls/fresh-check-results.json').read_text(encoding='utf-8'))
    selection=json.loads((WORK/'selection-before-fresh-check.json').read_text(encoding='utf-8'))
    control_selection=json.loads((WORK/'controls/selection-before-check.json').read_text(encoding='utf-8'))
    tuning=json.loads((WORK/'tuning-results.json').read_text(encoding='utf-8'))
    diagnosis=json.loads((WORK/'old-C2-diagnostic.json').read_text(encoding='utf-8'))
    fit=json.loads((WORK/'models/candidates.json').read_text(encoding='utf-8'))
    check=json.loads((DOCS/'phase3-refinement-verification.json').read_text(encoding='utf-8'))
    selection_names=selection['selected'];main_name=selection_names['full'];ci={};rows=[];all_results={}
    for cohort,group in fresh['cohorts'].items():
        results=dict(group['results']);files={name:WORK/cohort/f'{name}.npz' for name in results}
        for family,item in controls['cohorts'][cohort].items():
            key=family;results[key]=item;files[key]=WORK/'controls'/f'{cohort}_{family}.npz'
        reference=np.load(files['fixed_60'])['by_bay_phase'];ci[cohort]={}
        for name,item in results.items():
            values=np.load(files[name]);np.testing.assert_array_equal(values['bays'],np.load(files['fixed_60'])['bays'])
            if not np.array_equal(values['by_bay_phase'][:,:,0],reference[:,:,0]):raise ValueError('Unequal exposure')
            ci[cohort][name]=paired_intervals(values['by_bay_phase'],reference)
            m=item['metrics']
            rows.append([cohort,name,m['samples_per_bay_day'],m['false_free_seconds_per_bay_day'],m['false_occupied_seconds_per_bay_day'],
              *[m['vacancy_duration_profiles'][str(t)]['missed_fraction'] for t in (0,30,60,120,300)],item['checks_reduction_percent'],item['quality_passes']])
        all_results[cohort]=results
    write_json(WORK/'paired-bay-intervals.json',{'draws':2000,'unit':'BayId, with all windows and common phases retained together','seed':20261020,'intervals':ci,
      'zero_event_note':'A degenerate zero bootstrap interval is not a guarantee of zero unseen-event risk.'})
    with (DOCS/'phase3-refinement-results.csv').open('w',newline='',encoding='utf-8-sig') as file:
        writer=csv.writer(file);writer.writerow(['cohort','policy','checks_per_bay_day','F_seconds_per_bay_day','O_seconds_per_bay_day','M0','M30','M60','M120','M300','checks_reduction_percent','all_quality_constraints_pass']);writer.writerows(rows)
    results=all_results['primary_7_days'];reference=results['fixed_60']['metrics']
    no_time_name=selection_names['without_time']
    labels={'fixed_60':'Регулярно, 60 с','old_C2_resource1440':'Початковий C2',main_name:'Повний C3',no_time_name:'C3 без часу доби',
      'guarded_C2':'C2 з обмеженням пауз','backoff':'Просте нарощування пауз','S2_1440':'S2, бюджет 1440','S2_2880':'S2, бюджет 2880'}
    if main_name=='fixed_60':labels['fixed_60']='Регулярно, 60 с (також запасний C3)'
    extra=[no_time_name] if no_time_name not in ('fixed_60',main_name) else []
    names=['fixed_60','old_C2_resource1440']+([main_name] if main_name!='fixed_60' else [])+extra+['guarded_C2','backoff','S2_1440','S2_2880']
    colors=['#64748b','#dc2626']+(['#0284c7'] if main_name!='fixed_60' else [])+(['#0891b2'] if extra else [])+['#059669','#7c3aed','#ea580c','#ca8a04']
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    fig,axes=plt.subplots(1,3,figsize=(14,6.7))
    specs=[('samples_per_bay_day','Вимірювань на місце за добу'),('false_free_seconds_per_bay_day','Помилково «вільно», с/місце/добу'),('false_occupied_seconds_per_bay_day','Помилково «зайнято», с/місце/добу')]
    short=['60 с','C2']+(['C3'] if main_name!='fixed_60' else [])+(['C3/без часу'] if extra else [])+['C2+','Простий','S2/1440','S2/2880']
    for ax,(key,label) in zip(axes,specs):
        values=[results[n]['metrics'][key] for n in names];ax.bar(range(len(names)),values,color=colors,width=.68)
        ax.axhline(reference[key],color='#334155',linestyle=':',lw=1);ax.set_ylabel(label)
        ax.set_xticks(range(len(names)),short,rotation=35,ha='right');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('Перевірка доопрацьованого розкладу на інших 512 місцях',fontsize=15,y=.97)
    fig.text(.5,.91,'Липень-вересень 2019. Налаштування за цією перевіркою не змінювали. Це ще не остаточний тест.',ha='center',color='#475569')
    handles=[plt.Rectangle((0,0),1,1,color=c) for c in colors]
    fig.legend(handles,[labels[n] for n in names],loc='lower center',ncol=3,bbox_to_anchor=(.5,.055),frameon=False)
    fig.text(.5,.015,'Усі частки повністю пропущених звільнень і умови якості наведено в таблиці; менше вимірів саме по собі не означає кращий метод.',ha='center',fontsize=9,color='#475569')
    fig.subplots_adjust(left=.07,right=.98,top=.83,bottom=.36,wspace=.35)
    figures=[]
    for ext in ('png','svg'):
        path=DOCS/'figures'/f'phase3-refinement-fresh-check.{ext}';fig.savefig(path,dpi=180,facecolor='white');figures.append(path)
    plt.close(fig)
    def tablerow(name,item):
        m=item['metrics'];return f"| {labels.get(name,name)} | {m['samples_per_bay_day']:.2f} | {item['checks_reduction_percent']:.2f}% | {m['false_free_seconds_per_bay_day']:.2f} | {m['false_occupied_seconds_per_bay_day']:.2f} | {100*m['vacancy_duration_profiles']['60']['missed_fraction']:.5f}% | {'так' if item['quality_passes'] else 'ні'} |"
    primary_table='\n'.join(tablerow(n,results[n]) for n in names)
    sensitive=all_results['sensitivity_1_day'];sensitivity_table='\n'.join(tablerow(n,sensitive[n]) for n in names)
    selected_rows=[x for x in tuning['results'] if x['name']==main_name]
    own_primary=results[main_name];own_sensitivity=sensitive[main_name]
    passed=main_name!='fixed_60' and own_primary['quality_passes'] and own_sensitivity['quality_passes'] and own_primary['checks_reduction_percent']>0 and own_sensitivity['checks_reduction_percent']>0
    successful=[]
    for name in [*set(selection_names.values()),'guarded_C2','backoff']:
        if name=='fixed_60':continue
        if all(all_results[c][name]['quality_passes'] and all_results[c][name]['checks_reduction_percent']>0 for c in all_results):successful.append(name)
    successful=sorted(successful)
    verdict=('Повний C3 із часом доби виконав усі початкові умови якості на обох додаткових перевірках і зменшив кількість вимірів.' if passed else 'Повний C3 із часом доби не пройшов обидві додаткові перевірки через пропуски звільнень від хвилини. Його не залишаємо основним кандидатом.')
    training_verdict='У C3 на початковій вибірці не знайдено конфігурації, що проходить навчальні й перевірочні умови одночасно; застосовано запасні 60 секунд.'
    if selected_rows:
        chosen=selected_rows[0];m=chosen['tuning_metrics'];ref=tuning['tuning_reference']
        training_verdict=f"Обрано `{main_name}`: на початкових 128 місцях зменшення перевірок {100*(1-chosen['tuning_raw'][1]/ref[1]):.2f}%, F={m['false_free_seconds_per_bay_day']:.2f}, O={m['false_occupied_seconds_per_bay_day']:.2f} с/місце/добу, M60={chosen['tuning_raw'][14]}. Конфігурацію зафіксовано до читання результатів інших 512 місць."
    intervals=ci['primary_7_days'][main_name]
    def interval(key):return '['+', '.join(f'{x:.2f}' for x in intervals[key])+']'
    positive_rows='\n'.join(f"- **{labels.get(n,n)}:** скорочення на {results[n]['checks_reduction_percent']:.2f}% у вікнах від 7 діб і на {sensitive[n]['checks_reduction_percent']:.2f}% у вікнах від 1 доби; обидві помилки не вищі за хвилинне правило, M60=0 на обох перевірках." for n in successful)
    positive_ci='\n'.join(f"- {labels.get(n,n)}: скорочення перевірок {np.round(ci['primary_7_days'][n]['checks_reduction_percent'],2).tolist()}%, різниця F {np.round(ci['primary_7_days'][n]['F_difference_seconds_per_day'],2).tolist()}, різниця O {np.round(ci['primary_7_days'][n]['O_difference_seconds_per_day'],2).tolist()} с/місце/добу." for n in successful)
    compact=DOCS/'phase3-refined-policy.json'
    learned=np.load(WORK/'models'/f'{no_time_name}.npz')['lookup']
    expected_free=np.array([30,30,45,75,75,75]);expected_occupied=np.array([30,30,60,60,60,60])
    if not np.array_equal(learned[:24],np.tile(expected_free,4)) or not np.array_equal(learned[24:],np.tile(expected_occupied,4)):
        raise ValueError('Compact representation must match frozen learned policy exactly')
    write_json(compact,{'source_policy':no_time_name,'source_npz_sha256':sha256(WORK/'models'/f'{no_time_name}.npz'),
      'observed_run_thresholds_seconds':[300,900],'free_pauses_seconds':[30,45,75],'occupied_pauses_seconds':[30,60,60],
      'history':'Time since first observation in the latest sequence of equal sampled states, not known true physical duration',
      'derivation':'Exact compression of repeated rows; no retraining or adjustment after fresh development check',
      'scope':'candidate_for_final_test_not_validated_physical_deployment'})
    entry=DOCS/'phase4-entry-lock.json'
    write_json(entry,{'decision_stage':'after_development_512_before_final_867','primary_candidate':no_time_name,
      'selection_after_fresh_development_check':True,'initial_full_C3_failure_preserved':True,'model_parameters_retuned_after_check':False,
      'reason':'No-time C3 passes both pointwise quality checks and reduces both errors with negative paired interval bounds; backoff is a mandatory stronger efficiency comparator.',
      'primary_compact_policy':compact.relative_to(ROOT).as_posix(),'primary_compact_policy_sha256':sha256(compact),
      'mandatory_comparators':['fixed60','backoff_45_900_75_60','S2_1440','S2_2880'],
      'development_selected_models':selection_names,'quality_conditions':['F<=F60','O<=O60','M60<=M60_60'],
      'code_sha256':{name:sha256(ROOT/'research/parking_sampling'/name) for name in ('refine_policy.py','kernels.py','simulation.py','trained_schedule.py')},
      'original_final_test_source':'phase2-data-lock.json','final_test_evaluated':False,
      'interpretation':'New primary hypothesis selected during development; no claim it was the sole primary candidate before the 512-bay check.'})
    report=f'''# Доопрацювання фази 3: діагностика, C3 та перевірка перенесення

Дата: 18.10.2026. Версія `phase3-refinement-C3-v1`. Попередній негативний результат [фази 3](phase3-method-report.md) збережено. **Остаточний тест на 867 місцях не запускався.**

**{verdict}**

Водночас перевірку пройшли такі зафіксовані до її запуску варіанти:

{positive_rows if positive_rows else 'Жоден із перевірених варіантів не дав скорочення за всіх початкових умов.'}

Це додаткові результати розроблення. Варіант без часу доби та просте правило не оголошуються заднім числом єдиним початково обраним основним методом. Жодну таблицю після перевірки не переналаштовували.

## Чому змінюємо правило

Діагностика попередньої точки C2 на 128 місцях показала: із {sum(diagnosis['M60_by_last_sample_state'].values()):,} пропущених звільнень-повторів від хвилини {diagnosis['M60_by_last_sample_state']['occupied']:,} виникли після останнього виміру «зайнято», {diagnosis['M60_by_last_sample_state']['free']} - після «вільно». Усі сталися за пауз 120 або 300 секунд. Повтор тут означає той самий епізод за іншого початку розкладу, а не нову фізичну подію. Діагностичні лічильники окремо перевірені зіставленням із незалежним симулятором.

Отже, змінено конкретні складові. Після виміру «зайнято» C3 може призначати лише 15, 30, 45 або 60 секунд. Після «вільно» доступні також 75, 90 і 120 секунд. Межа для одного останнього стану сама по собі не гарантує нуль пропусків: за довгої паузи після «вільно» також можливі кілька невидимих переходів. Тому всі пропуски далі рахуються повністю, як передбачено протоколом.

Друга зміна - спосіб навчання. C2 оцінював локальний ризик окремої паузи, а потім збирав із таких рішень розклад. C3 оцінює **весь розклад** повторним відтворенням навчальної історії. Після кожної пробної зміни таблиці заново враховуються всі викликані нею моменти перевірок і спостережувана історія. Справжній момент переходу не стає вхідною ознакою.

Причинне планування вже вивчається у [S2](https://doi.org/10.1109/TCOMM.2022.3160563); пошук політики з обмеженнями також не є новою загальною ідеєю, див. [S10](https://proceedings.mlr.press/v70/achiam17a.html). Наш скінченний пошук не відтворює CPO і не має його гарантій. Кандидат на прикладний внесок - конкретне правило для цієї паркувальної постановки та результати його перевірки. [Джерела й межі використання](phase3-refinement-sources.md).

## Навчання та вибір

До навчання збережено [план](phase3-refinement-plan.json), код і точні списки місць. Власні таблиці навчаються на січні-червні 256 місць із `train_development`, вибраних за хешем ідентифікатора; по три спільні початки розкладу, вікна від семи діб. Нову навчальну історію зарезервованих місць не відкривали.

Контекст містить ті самі 48 комбінацій останнього стану, часу доби та спостережуваної тривалості. Початкова таблиця - всюди 60 секунд. Покоординатний перебір робить не більше двох проходів та мінімізує C/C60 + λF·F/F60 + λO·O/O60, відкидаючи будь-яку таблицю з додатковим навчальним M60. Для λF і λO взято 0.25, 1, 4; після навчання перевірено межі паузи «вільно» 75, 90, 120 секунд. Є варіанти без часу доби й без спостережуваної тривалості. Разом {len(fit['candidates'])} конфігурацій; {fit['evaluations']} навчальних відтворень. Це пошук кандидата, а не доказ оптимальності.

Остаточний вибір усередині кожного варіанта зроблено на тих самих 128 місцях липня-вересня, які вже використовувалися для розроблення. Збережено початкові вимоги F≤F60, O≤O60, M60≤M60_60 і відбір за мінімумом перевірок; додатково конфігурація має проходити їх на навчанні. **Умови не послаблювали.** {training_verdict}

Щоб перевірити, чи потрібен складніший спосіб навчання, до нової перевірки також зафіксовано [два додаткові контролі](phase3-refinement-comparators.json): C2 із межами пауз та просте нарощування паузи після послідовних однакових вимірів. Їхні параметри теж вибрано тільки на початкових 128 місцях. Зміни C2-C3 включають навчання, межі пауз та сітку дій; це не чиста перевірка однієї складової. Контролі потрібні саме для обмеження надто широких висновків.

## Додаткова перевірка: інші 512 місць

Після фіксації вибору виконано один запланований запуск на 512 інших місцях липня-вересня, виключивши початкові 128 і всі місця з раніше прочитаного префікса. Їх не добирали за успішністю алгоритму. Таблиці після результатів цієї перевірки не змінювалися. Це додаткова перевірка розроблення, а не остаточний жовтень-грудень.

Джерело всіх даних - [City of Melbourne, On-street Car Parking Sensor Data - 2019, S5](https://data.melbourne.vic.gov.au/explore/dataset/on-street-car-parking-sensor-data-2019/information/). Числа нижче - власні обчислення. Вікна від 7 діб: {fresh['cohorts']['primary_7_days']['windows']}; вікна від 1 доби: {fresh['cohorts']['sensitivity_1_day']['windows']}. Другий набір містить перший та додаткові коротші вікна, тому ці перевірки не є незалежними одна від одної.

F/O - секунди неправильного показу на місце за добу. M60 - частка повністю пропущених звільнень від 60 секунд. «Умови» означає всі три вимоги якості одночасно; додатне скорочення перевірок саме по собі недостатнє.

| Метод, вікна від 7 діб | Перевірок/добу | Скорочення | F | O | M60 | Умови |
|---|---:|---:|---:|---:|---:|---|
{primary_table}

| Метод, вікна від 1 доби | Перевірок/добу | Скорочення | F | O | M60 | Умови |
|---|---:|---:|---:|---:|---:|---|
{sensitivity_table}

![Доопрацьовані методи на інших місцях](figures/phase3-refinement-fresh-check.png)

[CSV з усіма порогами тривалості](phase3-refinement-results.csv), [векторний рисунок](figures/phase3-refinement-fresh-check.svg). Джерело даних - S5; обчислення й рисунок авторські. Адаптація S2 використовує незмінні навчальні переходи з фази 3; її фактична частота може відрізнятися від номінальної.

## Розкид і перевірки

Для C3 відносно регулярних 60 секунд на вікнах від 7 діб обчислено парні 95% процентильні інтервали за 2000 повторними вибірками паркомісць: скорочення перевірок {interval('checks_reduction_percent')}%, різниця F {interval('F_difference_seconds_per_day')}, різниця O {interval('O_difference_seconds_per_day')} с/місце/добу. Усі вікна та десять початків одного місця залишаються разом. Ці інтервали не перетворюють перевірку розроблення на незалежний остаточний тест і не доводять еквівалентність якості.

Для варіантів, що пройшли обидві перевірки, ті самі інтервали:

{positive_ci}

Якщо в даних немає жодного пропуску, нульовий інтервал повторного вибирання не доводить неможливість пропусків у майбутньому. Порівняння спирається на записані стани сенсорів; їхню фізичну точність на нашому обладнанні не перевірено. Вимірювання енергії та батарейних відсотків у цих результатах немає.

**Пройшли {check['tests_run']} перевірок**, включно з новими паузами 45/75/90 секунд, правильністю діагностики, виключенням ознак і навчального обмеження M60. [Протокол](phase3-refinement-verification.json). Код попередньої фази та її негативні результати збережено; нові файли мають окрему версію. [Поточний реєстр](phase3-refinement-lock.json) містить контрольні суми моделей, вибору до перевірки, даних, коду й результатів.

## Рішення

{verdict} Додаткові контролі показують, чи пояснює результат уже саме обмеження довгих пауз або простіше правило. Числа цих контролів не приховуються навіть тоді, коли вони кращі за C3. Перевага складнішого навчання й світова новизна не випливають із факту його реалізації.

У фазу 4 доцільно передати **всі вже зафіксовані варіанти, що пройшли перевірки**, та прості й літературні бази. Не вибирати за остаточним тестом нові параметри. C3 без часу доби має інший компроміс помилок і частоти, ніж просте нарощування пауз, тому саме остаточне порівняння потрібне для висновку про практичну користь навчання. До нього некоректно обіцяти перевагу складнішого варіанта.

**За підсумками розроблення основним кандидатом для фази 4 обрано C3 без часу доби**, а просте нарощування пауз залишено обов'язковим контролем. Це вибір після додаткової перевірки, до остаточного тесту; він явно зафіксований у [phase4-entry-lock.json](phase4-entry-lock.json). Навчені паузи після перевірки не змінювалися. На додаткових даних у C3 без часу доби нижчі обидві помилки, тоді як у простого правила менше вимірів; це різні точки компромісу. Для простого правила інтервал різниці F містить невелике погіршення, тому рівність якості не доведена.

Його точна навчена таблиця стискається до трьох рядків без зміни жодного рішення:

| Час від початку послідовності однакових вимірів | Після «вільно» | Після «зайнято» |
|---|---:|---:|
| До 5 хвилин | 30 с | 30 с |
| Від 5 до 15 хвилин | 45 с | 60 с |
| Від 15 хвилин | 75 с | 60 с |

Це спостережувана послідовність, а не відомий безперервний фізичний стан. Збережено [точну конфігурацію](phase3-refined-policy.json) та окрему функцію вибору паузи у коді; її еквівалентність навченій таблиці перевірено. Тут немає припущення про пропуски ультразвукового відбиття.

Основний Google-документ, Canva, прошивка й API не змінювалися. Подальша зміна після цієї перевірки потребує нової позначеної версії. Остаточні 867 місць залишено для фази 4.
'''
    (DOCS/'phase3-refinement-report.md').write_text(report,encoding='utf-8')
    paths=[PLAN for PLAN in [DOCS/'phase3-refinement-plan.json',DOCS/'phase3-refinement-comparators.json',DOCS/'phase3-refinement-sources.md',DOCS/'phase3-refinement-references.bib',DOCS/'phase3-refinement-report.md',DOCS/'phase3-refinement-results.csv',DOCS/'phase3-refinement-verification.json']]
    paths+=figures+[compact,entry,DOCS/'README.md',DOCS/'phase3-roadmap-snapshot.md',DOCS/'phase3-refinement-history.json']+list(WORK.rglob('*.json'))+list(WORK.rglob('*.npz'))
    paths+=[ROOT/'research/parking_sampling'/name for name in ('refine_policy.py','refinement_controls.py','diagnose_schedule.py','report_refinement.py','test_refinement.py','verify_refinement.py','trained_schedule.py','README-C3.md')]
    write_json(DOCS/'phase3-refinement-lock.json',{'version':'C3-v1-after-fresh-development-check','files':{p.relative_to(ROOT).as_posix():sha256(p) for p in paths},
      'C3_full':main_name,'C3_passes_both_checks':bool(passed),'successful_frozen_variants':successful,'final_test_evaluated':False,
      'old_code_preserved':True,'original_quality_conditions_changed':False,'fresh_outcomes_used_for_retuning':False})
    print(json.dumps({'report':str(DOCS/'phase3-refinement-report.md'),'C3':main_name,'C3_passes_both_checks':bool(passed),'successful_variants':successful},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
