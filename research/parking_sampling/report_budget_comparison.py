"""Scientific figures and honest interpretation of frozen and hindsight controls."""
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from prepare_data import DOCS
from budget_comparison import definitions
from run_budget_comparison import WORK,read,FAMILIES
from run_phase3 import write_json

TITLES={'fixed':'Періодичні','state':'Лише стан','two_stage':'Дві ступені','S2':'Адаптація S2','pooled':'Усі контролі'}
CELLS=('check256_primary_7_days','check256_sensitivity_1_day','check512_primary_7_days','check512_sensitivity_1_day')


def short_cell(cell):
    return ('256 місць' if cell.startswith('check256') else '512 місць')+(', від 7 діб' if 'primary' in cell else ', від 1 доби')


def coverage_annex_section():
    from budget_coverage_annex import ANNEX
    annex=read(ANNEX/'results.json')
    lines=['## Додаткова перевірка з однаковою вимогою покриття', '',
      'Цей додаток оголошено **після** основного зіставлення, коли виявлено вищий M60 простих контролів. Його пошуковий характер явно зафіксовано в [плані додатка](phase3-budget-coverage-annex-plan.json). Контролям також надали ту саму раніше навчену паузу72с: додано27 постійних за станом і30 двоступеневих правил, загалом326 визначень разом із C3/C4. Кандидати не переналаштовували.', '',
      'Під час нового добору ваг до тих самих обмежень ресурсу додали `M60контр<=M60канд` у кожній навчальній/налагоджувальній комірці. Ваги збережено перед запуском додаткових контролів на256/512. Окремо знову обчислено оптимістичну межу за рівності очікуваного бюджету та з тим самим обмеженням M60 на перевірочній комірці.', '',
      'Для розглянутої скінченної родини періодичних правил та адаптацій S2 не знайдено допустимої суміші з таким ресурсом і покриттям. Це результат конкретного банку політик та записів, а не теорема про неможливість будь-якого періодичного або марковського методу. У [технічній версії2](phase3-budget-coverage-annex-v2-plan.json) виправлено лише облік цього допустимого результату «немає розв’язку»; перший незавершений запуск, його код і чотири точні банки лічильників збережено.', '',
      '| Група / вікна | Кандидат | t, лише стан | t, дві ступені | t, усі допустимі контролі |',
      '|---|---|---:|---:|---:|']
    for cell in CELLS:
        for target in ('C3','C4'):
            vals=[]
            for family in ('state','two_stage','pooled'):
                e=annex['cohorts'][cell][target+'_'+family]['hindsight_envelope']
                vals.append(f"{e['max_error_ratio']:.4f}" if e['feasible'] else 'немає')
            lines.append('| '+short_cell(cell)+' | '+target+' | '+' | '.join(vals)+' |')
    lines += ['', 'Значення t має те саме значення, що в основній таблиці, але тепер обмежено також M60, а прості контролі мають доступ до72с. Для C3 оптимістичний двоступеневий контроль має найгірше з двох відношень помилок вище1 на1,69-2,25%. Для C4 перевага непослідовна й мала: значення лежать від0,9971 до1,0087. Ці числа не означають відповідної зміни загальної точності карти у процентних пунктах.', '',
      'Результат **зафіксованого** двоступеневого контролю наведено нижче. Відхилення - контроль відносно кандидата; M60 є очікуваним числом із десятьма фазами. «Допустимий» перевіряє одночасно ресурс і M60.', '',
      '| Група / вікна | Кандидат | Ресурс, % | F, % | O, % | M60 контролю | Допустимий |',
      '|---|---|---:|---:|---:|---:|---|']
    for cell in CELLS:
        for target in ('C3','C4'):
            x=annex['cohorts'][cell][target+'_two_stage']
            vals=[f'{100*(x[k]-1):+.3f}' for k in ('frozen_control_to_target_resource_ratio','frozen_control_to_target_F_ratio','frozen_control_to_target_O_ratio')]
            admitted=x['frozen_control_M60_admissible'] and x['frozen_control_resource_admissible']
            lines.append('| '+short_cell(cell)+' | '+target+' | '+' | '.join(vals)+f" | {x['frozen_control_metrics']['M60_expected_count']:.3f} | {'так' if admitted else 'ні'} |")
    lines += ['', 'У трьох комірках, де зафіксований простий контроль C3 дотримується ресурсу та M60, C3 має обидві помилки приблизно на2% нижчі. У вікнах від доби групи512 контроль порушує M60. Зафіксований контроль C4 також порушує M60 на512/від доби, а на256/від доби перевищує бюджет. Такі контролі не називаємо загальними переможцями.', '',
      '95% точкові парні інтервали різниць кандидата мінус контроль для цього додатка:', '',
      '| Група / вікна | Кандидат | Різниця F, с/місце-добу | Різниця O, с/місце-добу |', '|---|---|---|---|']
    for cell in CELLS:
        for target in ('C3','C4'):
            ci=annex['cohorts'][cell][target+'_two_stage']['paired_bay_intervals_target_minus_control']
            def fmt(k):return '['+', '.join(f'{v:+.3f}' for v in ci[k])+']'
            lines.append(f"| {short_cell(cell)} | {target} | {fmt('F_difference_seconds_per_day')} | {fmt('O_difference_seconds_per_day')} |")
    lines += ['', 'Отримано невеликий умовний виграш додаткової ступені C3 за вимоги покриття. Це конкретні власні дані, але їх не можна перетворювати на загальну алгоритмічну новизну. Відому раніше одиницю M60 C3 на128 місцях налаштування/від доби збережено; новий додаток її не скасовує та не повертає C3 як автоматичного переможця початкового протоколу.', '',
      'Усі значення додатка збережено [в окремому CSV](phase3-budget-coverage-annex-results.csv) та `coverage-annex-v2/results.json`. Оптимістичні межі, зафіксовані контролі й недопустимі задачі розділені. Остаточний тест залишається закритим.', '']
    fields=('cohort','target','family','frozen_fit_feasible','hindsight_feasible','hindsight_t','resource_ratio','F_ratio','O_ratio','M60_expected','resource_admissible','M60_admissible')
    with (DOCS/'phase3-budget-coverage-annex-results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for cell,rows in annex['cohorts'].items():
            for key,x in rows.items():
                target,family=key.split('_',1);e=x['hindsight_envelope']
                row={'cohort':cell,'target':target,'family':family,'frozen_fit_feasible':x['frozen_control_feasible_in_fitting'],
                     'hindsight_feasible':e['feasible'],'hindsight_t':e.get('max_error_ratio')}
                if x['frozen_control_feasible_in_fitting']:
                    row.update({'resource_ratio':x['frozen_control_to_target_resource_ratio'],'F_ratio':x['frozen_control_to_target_F_ratio'],
                       'O_ratio':x['frozen_control_to_target_O_ratio'],'M60_expected':x['frozen_control_metrics']['M60_expected_count'],
                       'resource_admissible':x['frozen_control_resource_admissible'],'M60_admissible':x['frozen_control_M60_admissible']})
                writer.writerow(row)
    return lines


def make_figures(results):
    bank=definitions();names=[d.policy.name for d in bank]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'svg.fonttype':'none'})
    fig,axes=plt.subplots(2,2,figsize=(14,9),layout='constrained')
    for ax,cell in zip(axes.flat,CELLS):
        group=results['cohorts'][cell]['equal_expected_budget_hindsight_envelopes']
        for target,shift,color in (('C3',-.23,'#087fbd'),('C4',.23,'#00a496')):
            y=[100*(group[target+'_'+family]['max_error_ratio']-1) for family in FAMILIES]
            bars=ax.bar(np.arange(5)+shift,y,width=.4,color=color,label=target)
            for bar,value in zip(bars,y):
                ax.annotate(f'{value:+.2f}%',(bar.get_x()+bar.get_width()/2,value),
                  xytext=(0,(4 if target=='C3' else 15) if value>=0 else (-12 if target=='C3' else -23)),
                  textcoords='offset points',ha='center',fontsize=8)
        ax.axhline(0,color='#34435b',lw=1)
        ax.set_xticks(np.arange(5),[TITLES[f] for f in FAMILIES],rotation=14,ha='right')
        ax.set_title(short_cell(cell),fontweight='bold');ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
        ax.set_ylim(-6,37);ax.legend(frameon=False)
        ax.set_ylabel('Найгірша з двох відносних помилок, %')
    fig.suptitle('Оптимістичний контроль за точно однакового очікуваного бюджету',fontsize=16,fontweight='bold')
    fig.supxlabel('Показано 100(t-1), де t = min max(Fконтр/Fканд, Oконтр/Oканд). Нижче нуля: контроль зменшує обидві помилки.\n'
      'Ваги підібрано за результатами кожної групи; покриття M60 не обмежено. Це порівняльна межа, а не перевірений алгоритм.\n'
      'Липень-вересень 2019; дані City of Melbourne, CC BY 4.0. Власні обчислення на даних розроблення.',fontsize=10)
    for ext in ('png','svg'):fig.savefig(DOCS/'figures'/f'phase3-budget-envelopes.{ext}',dpi=180)
    plt.close(fig)
    cell='check512_sensitivity_1_day'
    data=np.load(WORK/'banks'/(cell+'.npz'));raw=data['by_bay'].sum(axis=1).astype(float)
    days=raw[:,0]/86400;x=raw[:,1]/days
    fig,axes=plt.subplots(1,2,figsize=(14,7.5))
    for ax,index,title in zip(axes,(2,3),('Помилково «вільно»','Помилково «зайнято»')):
        for family,color,marker,size in (('state','#94a3b8','o',19),('two_stage','#087fbd','o',27),('S2','#be7a22','^',48)):
            keep=np.array([family in d.groups for d in bank])&(x>=1000)&(x<=2000)
            ax.scatter(x[keep],raw[keep,index]/days[keep],s=size,marker=marker,color=color,alpha=.7,label=TITLES[family])
        for target,color,marker in (('C3','#d82d62','*'),('C4','#00886e','D')):
            j=names.index(target);y=raw[j,index]/days[j]
            ax.scatter([x[j]],[y],s=190 if target=='C3' else 85,marker=marker,color=color,zorder=6,label=target)
            ax.annotate(target,(x[j],y),xytext=(10,-13 if target=='C3' else 9),textcoords='offset points',color=color,fontweight='bold')
        ax.set_xlabel('Вимірювань на місце-добу');ax.set_ylabel('Секунд на місце-добу')
        ax.set_title(title,fontweight='bold');ax.grid(alpha=.16);ax.set_xlim(1000,2000)
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.145),ncol=5,frameon=False)
    fig.suptitle('Витрати та помилки: C3/C4 поряд із сильними простими правилами',fontsize=16,fontweight='bold',y=.97)
    fig.text(.5,.035,'512 місць, усі відомі вікна від доби, 10 початкових фаз. Крапки - окремі фактично відтворені розклади.\n'
      'Це дані розроблення; кольорові хмари не є довірчими інтервалами.\n'
      'Джерело даних: City of Melbourne 2019, CC BY 4.0. Власне відтворення.',fontsize=10,ha='center')
    fig.subplots_adjust(left=.065,right=.985,top=.86,bottom=.29,wspace=.25)
    for ext in ('png','svg'):fig.savefig(DOCS/'figures'/f'phase3-budget-error-scatter.{ext}',dpi=180)
    plt.close(fig)


def main():
    r=read(WORK/'development-results.json');selection=read(WORK/'selection-before-check-replay.json')
    make_figures(r)
    path=DOCS/'phase3-budget-comparison-results.csv'
    fields=('cohort','target','family','comparison','samples_per_bay_day','F_seconds_per_bay_day',
            'O_seconds_per_bay_day','M60_expected_count','eligible60_episode_phases','control_to_target_resource_ratio',
            'control_to_target_F_ratio','control_to_target_O_ratio','max_error_ratio')
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for cell,group in r['cohorts'].items():
            for key,item in group['frozen_controls'].items():
                target,family=key.split('_',1)
                writer.writerow({'cohort':cell,'target':target,'family':family,'comparison':'frozen_mixture',
                  **item['control_metrics'],**{k:item[k] for k in ('control_to_target_resource_ratio','control_to_target_F_ratio','control_to_target_O_ratio')},
                  'max_error_ratio':max(item['control_to_target_F_ratio'],item['control_to_target_O_ratio'])})
            for key,item in group['equal_expected_budget_hindsight_envelopes'].items():
                target,family=key.split('_',1);target_raw=np.array(group['frozen_controls'][key]['target_raw']);raw=np.array(item['expected_raw'])
                writer.writerow({'cohort':cell,'target':target,'family':family,'comparison':'hindsight_exact_expected_budget',
                  **item['metrics'],'control_to_target_resource_ratio':raw[1]/target_raw[1],
                  'control_to_target_F_ratio':raw[2]/target_raw[2],'control_to_target_O_ratio':raw[3]/target_raw[3],
                  'max_error_ratio':item['max_error_ratio']})
    simple=[];frozen_dominance=[]
    for cell,group in r['cohorts'].items():
        for target in ('C3','C4'):
            item=group['equal_expected_budget_hindsight_envelopes'][target+'_two_stage']
            simple.append({'cohort':cell,'target':target,'max_error_ratio':item['max_error_ratio']})
            fr=group['frozen_controls'][target+'_two_stage']
            frozen_dominance.append({'cohort':cell,'target':target,
                'control_point_dominates_on_resource_F_O_only':fr['frozen_control_point_dominates_target'],
                'target_M60':fr['target_metrics']['M60_expected_count'],'control_M60_expected':fr['control_metrics']['M60_expected_count'],
                'resource_ratio':fr['control_to_target_resource_ratio'],'F_ratio':fr['control_to_target_F_ratio'],'O_ratio':fr['control_to_target_O_ratio']})
    max_deviation=max(abs(x['max_error_ratio']-1) for x in simple)
    conclusion={'created_on':'2026-10-25','simple_two_stage_hindsight_envelopes':simple,
      'simple_two_stage_frozen_comparisons':frozen_dominance,
      'max_absolute_two_stage_minimax_ratio_deviation_percent':100*max_deviation,
      'scientific_novelty_established':False,'new_superior_algorithm_promoted':False,
      'phase4_may_start':False,'final_test_evaluated':False,'new_check_cohort_opened':False}
    write_json(WORK/'conclusion.json',conclusion)
    lines=['# C3/C4 і сильні прості контролі за однакового бюджету',
      '', 'Дата: 25.10.2026. Фаза3, повторне використання даних розроблення. Це власні експериментальні результати, не остаточний тест.',
      '', '## Навіщо виконано це порівняння',
      '', 'Попередні порівняння з хвилинним правилом не ізолювали користь історії за однакових витрат. Тут окремо перевірено, чи потрібні додаткові ступені C3/C4 порівняно з простим правилом, яке також враховує час від останньої спостереженої зміни.',
      '', 'У [S1 Lean Sensing](https://kclpure.kcl.ac.uk/ws/portalfiles/portal/51708026/Binder1.pdf) вже розглядають адаптацію паркувальних вимірювань за контекстом і компроміс між витратами та якістю. [S2 Champati та ін.,2022](https://doi.org/10.1109/TCOMM.2022.3160563) оптимізує частоту й штраф за вік для марковського джерела. Загальний принцип адаптації та оптимізація за бюджетом відомі; тут вони є джерельними підставами і контролями, а не заявою про власну новизну.',
      '', '[План](phase3-budget-comparison-plan.json),269 розкладів і код зафіксовано до запуску. Параметри контролів вибрано на256 навчальних місцях січня-червня та128 місцях налаштування липня-вересня. Після збереження ваг виконано новий порівняльний запуск на вже досліджених групах256/512. Оскільки їхні попередні результати відомі, це не новий незалежний тест. Групи256 і512 не перетинаються; вікна від доби містять вікна від7діб.',
      '', '## Що порівнювали і як вирівняли ресурс',
      '', '| Родина | Визначення | Число розкладів |', '|---|---|---:|',
      '| Періодичні | Одна пауза після будь-якого показу, від5 до300с | 13, входять до наступних169 |',
      '| Лише останній стан | Окрема постійна пауза після «вільно» та «зайнято» | 169 |',
      '| Просте правило з історією | Дві ступені для кожного стану: коротка пауза спочатку, довша після порога; пороги вільного300/900с, зайнятого300с | 90 |',
      '| Адаптація S2 | Незмінена марковська реалізація з вісьмома номінальними бюджетами | 8 |',
      '| C3/C4 | Незмінені три ступені після «вільно», дві після «зайнято»; довга вільна пауза75/72с | 2 |',
      '', 'Контролям дозволено випадково вибирати один повний розклад на початку відомого вікна, не знаючи його майбутнього. Ваги цього вибору однакові для всіх місць і підібрані на навчанні/налаштуванні. Середні лічильники такої суміші дорівнюють зваженим лічильникам повних розкладів. Це **очікуваний середній ресурс**, а не точна кількість вимірів кожного конкретного пристрою. Дробові M60 у таблицях також є математичним сподіванням суміші.',
      '', 'Ваги добирали мінімізацією найгіршого відношення F/O контролю до кандидата. На кожній із чотирьох комірок навчання/налаштування вимагали не перевищувати кількість вимірів кандидата. Однакова експозиція, початкові фази та перший вимір враховані без поправок за номінальною частотою. Загальне лінійне програмування або така суміш не оголошуються новим алгоритмом.',
      '', 'Дві оцінки чітко розділено:',
      '', '1. **Зафіксований контроль.** Ваги визначено до поточного запуску перевірочних груп. Перевіряємо перенесення якості й бюджету. Якщо ресурс на перевірці перевищено, це явно показуємо.',
      '2. **Оптимістична межа за точно рівного очікуваного бюджету.** Для кожної перевірочної комірки окремо обрано найкращу суміш за її власними результатами з рівністю кількості вимірів. Вона навмисно має перевагу знання результатів. Це порівняльна межа можливостей заданої родини, а не незалежно перевірений алгоритм, який уже можна встановити на датчик.',
      '', 'S2 використовує раніше зафіксовану січнево-червневу модель4218 місць, тоді як C3 та новий добір простих контролів -256 навчальних місць плюс128 місць налаштування. Відмінність обсягу навчання явно збережена. Початкова ціль S2 - штраф за вік на акт вимірювання, вона не тотожна часу неправильного показу. Навіть гірший результат адаптації S2 тут не спростовує оптимальність статті у її постановці.',
      '', '## Оптимістичне порівняння за точно однакового очікуваного бюджету',
      '', 'Нижче наведено `t=min max(Fконтр/Fканд,Oконтр/Oканд)`. Значення нижче1 означає: у цій родині існує суміш, яка за точно рівного ресурсу має обидві помилки нижчими. Значення вище1 означає, що одночасно знизити обидві помилки в цій скінченній родині не вдалося; воно не доводить перевагу кандидата за кожною помилкою окремо.',
      '', '| Група / вікна | Кандидат | Періодичні | Лише стан | Дві ступені | S2 | Усі контролі |', '|---|---|---:|---:|---:|---:|---:|']
    for cell in CELLS:
        env=r['cohorts'][cell]['equal_expected_budget_hindsight_envelopes']
        for target in ('C3','C4'):
            lines.append('| '+short_cell(cell)+' | '+target+' | '+' | '.join(f"{env[target+'_'+family]['max_error_ratio']:.4f}" for family in FAMILIES)+' |')
    lines += ['', '![Порівняння родин](figures/phase3-budget-envelopes.png)',
      '', f"Для двоступеневих контролів найбільше абсолютне відхилення t від1 у цих восьми порівняннях становить {100*max_deviation:.2f}%. Це опис співвідношення спільних помилок, не перевірка статистичної еквівалентності й не допуск, погоджений із користувачами.",
      '', '## Перенесення зафіксованого простого контролю',
      '', 'Додатне відхилення ресурсу нижче означає, що контроль робить більше вимірів за кандидата; таку пару не можна називати порівнянням із дотриманим однаковим лімітом. F/O подані відносно кандидата, від’ємне значення краще для контролю.',
      '', '| Група / вікна | Кандидат | Ресурс контролю, % відхилення | F контролю, % відхилення | O контролю, % відхилення |', '|---|---|---:|---:|---:|']
    for cell in CELLS:
        for target in ('C3','C4'):
            item=r['cohorts'][cell]['frozen_controls'][target+'_two_stage']
            lines.append('| '+short_cell(cell)+' | '+target+' | '+' | '.join(f'{100*(item[k]-1):+.3f}' for k in ('control_to_target_resource_ratio','control_to_target_F_ratio','control_to_target_O_ratio'))+' |')
    lines += ['', 'Для цих зафіксованих сумішей виконано2000 парних повторних відборів цілих BayId. Усі фази та вікна одного місця залишаються разом. 95% інтервали є точковими, пошуковими, умовними щодо вже навчених моделей; вони не враховують перенавчання й не мають поправки на всі зіставлення та попередній вибір. Інтервали для оптимістичної межі не видаємо за підтверджувальну статистику.',
      '', '| Група / вікна | Кандидат | 95% інтервал різниці F, с/місце-добу | 95% інтервал різниці O |', '|---|---|---|---|']
    for cell in CELLS:
        for target in ('C3','C4'):
            ci=r['cohorts'][cell]['frozen_controls'][target+'_two_stage']['paired_bay_intervals_target_minus_control']
            def interval(key):return '['+', '.join(f'{x:+.3f}' for x in ci[key])+']'
            lines.append(f"| {short_cell(cell)} | {target} | {interval('F_difference_seconds_per_day')} | {interval('O_difference_seconds_per_day')} |")
    lines += ['', 'Знак останньої таблиці: кандидат мінус контроль. Додатна різниця означає більше помилок у C3/C4. Для перевірки відповідності бюджету потрібно одночасно читати попередню таблицю ресурсу; сам інтервал якості не вирівнює витрати.',
      '', '## Ціна близьких помилок відображення: покриття епізодів',
      '', 'Контролі вище оптимізували F/O без обмеження M60, як зафіксовано у плані. Тому близька або краща якість карти не означає виконання всіх початкових критеріїв дослідження. Нижче M60 зафіксованого двоступеневого контролю і відповідного кандидата. Дробові числа - сподівання вибору розкладу; десять початкових фаз включені в лічильник.',
      '', '| Група / вікна | Кандидат | M60 кандидата | Очікуваний M60 простого контролю |', '|---|---|---:|---:|']
    for cell in CELLS:
        for target in ('C3','C4'):
            item=r['cohorts'][cell]['frozen_controls'][target+'_two_stage']
            lines.append(f"| {short_cell(cell)} | {target} | {item['target_metrics']['M60_expected_count']:.0f} | {item['control_metrics']['M60_expected_count']:.3f} |")
    lines += ['', 'Ця різниця не дає права оголосити простий контроль загальним переможцем. Вона також не доводить значущу перевагу карти C3/C4: M60 означає відсутність виміру всередині епізоду, а не його цілковито неправильне відображення. Вимогу свіжого підтвердження кожного звільнення і поріг60с потрібно обґрунтовувати як окрему мету моніторингу, а не приписувати користувачеві або галузевому стандарту.',
      '', '![Витрати і якість](figures/phase3-budget-error-scatter.png)',
      '', '## Обґрунтований висновок для внеску',
      '', 'Порівняння із періодичними та залежними лише від останнього стану правилами показує користь аналізу спостереженої історії в цій задачі. Саму цю ідею вже містить література, тому вона не є достатньою заявою про новизну.',
      '', 'За F/O без обмеження покриття сильний простий контроль із двома ступенями є близьким конкурентом C3/C4, проте його M60 гірший. Додаткова перевірка за однакового M60 виявила невеликий умовний виграш C3. Для C4 істотної послідовної переваги над сильним простим контролем не встановлено. Близькість чисел не доводить еквівалентності; оптимістичний добір за перевірочною групою не є готовим переможним алгоритмом.',
      '', 'Власними результатами залишаються відтворюваний аналіз на відкритій історії, кількісне відокремлення користі історії від складності розкладу та умовна аналітична межа покриття. Це дослідницький матеріал для магістерської, але попередня вимога щодо обґрунтованої новизни ефективнішого алгоритму ще не виконана. Фаза3 залишається відкритою. На підставі цього зіставлення не додаємо ще одну ступінь або нову модель без окремої обґрунтованої гіпотези.',
      '', 'M60 залишено у всіх сирих лічильниках і [повній таблиці](phase3-budget-comparison-results.csv). Попередніх вимог до нього не скасовано. Цей експеримент окремо перевіряє помилки відображення; наукові гарантії не виводяться з одного записаного випадку покриття.',
      '', '## Відтворення, джерела та обмеження',
      '', 'Джерело даних: [City of Melbourne2019](https://data.melbourne.vic.gov.au/explore/dataset/on-street-car-parking-sensor-data-2019/information/), CC BY4.0, [конвеєр підготовки](phase2-data-report.md). Це сенсорні записи, а не незалежна фізична розмітка автомобілів. Січень-червень і липень-вересень розділені за часом; частина BayId може бути в обох періодах. Жовтень-грудень867 зарезервованих місць та зарезервований липень-вересень не відкривали.',
      '', 'У кожній комірці відтворено всі269 розкладів з однаковими початковими фазами; збережено підсумки кожного BayId, що включають усі його фази й вікна. Для S2 це десять фіксованих випадкових траєкторій на перевірці, а не точне математичне сподівання щодо його внутрішньої випадковості. Сподівання суміші стосується вибору повного розкладу на цих відтвореннях.',
      '', 'Код і дані запуску: `.codex-work/parking-budget-comparison-20261025/`. Ваги добору збережено в `selection-before-check-replay.json`, умови запуску - `pre-fit-lock.json` і `pre-check-lock.json`. У `development-results.json` окремо лежать зафіксовані контролі та оптимістичні межі. Є [план](phase3-budget-comparison-plan.json), [таблиця](phase3-budget-comparison-results.csv), [перевірки](phase3-budget-comparison-verification.json) і [маніфест](phase3-budget-comparison-artifacts.json). Старі результати не перезаписано.',
      '', 'Власні F/O та бюджетний аналіз не є вимірюванням споживання ESP32, точності ультразвуку чи строку роботи батареї. Основний Google-документ, Canva, прошивка та API в цьому досліді не змінювалися.', '']
    insertion=lines.index('## Обґрунтований висновок для внеску')
    lines[insertion:insertion]=coverage_annex_section()
    (DOCS/'phase3-budget-comparison-report.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'max_two_stage_minimax_deviation_percent':100*max_deviation,'novelty_established':False,'figures':2}))


if __name__=='__main__':main()
