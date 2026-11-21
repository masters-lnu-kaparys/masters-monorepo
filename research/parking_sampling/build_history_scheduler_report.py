"""Report the predeclared C5 experiment, including its negative result."""
import csv
from datetime import datetime, timedelta
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from prepare_data import ROOT, DOCS, sha256
from fit_history_scheduler import WORK, read
from run_phase3 import write_json

FIGURES = DOCS/'figures'
DAY = ('primary_7_days','sensitivity_1_day')


def figures(result,witness):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    by = {r['name']:r for r in result['candidates']}
    names=['fixed60','C3_shape_G75_A900','C3_shape_G72_A900',result['selected']['unrestricted_pooled'],result['selected']['history_guard_pooled']]
    labels=['Щохвилини','C3: пауза до 75 с','C4: пауза до 72 с','C5 без обмеження','C5 з обмеженням']
    colors=['#7a879b','#087fbd','#00a496','#b98635','#873faa']
    fig,axes=plt.subplots(2,3,figsize=(16,8.6),sharex='col',layout='constrained')
    for i,label in enumerate(DAY):
        for j,(metric,title) in enumerate(((1,'Кількість вимірювань'),(2,'Час помилкового «вільно»'),(3,'Час помилкового «зайнято»'))):
            ax=axes[i,j]
            ref=by['fixed60']['cells']['tuning_'+label]['raw'][metric]
            values=[100*(by[n]['cells']['tuning_'+label]['raw'][metric]/ref-1) for n in names]
            ax.barh(np.arange(len(names)),values,color=colors,height=.62)
            ax.axvline(0,color='#34435b',lw=1)
            ax.set_yticks(np.arange(len(names)),labels if j==0 else ['']*len(names))
            ax.invert_yaxis();ax.grid(axis='x',alpha=.18);ax.set_axisbelow(True)
            ax.set_xlim(min(-1,min(values)-8),max(3,max(values)+8))
            for k,v in enumerate(values):
                ax.text(v+(.5 if v>=0 else -.5),k,f'{v:+.1f}%',va='center',ha='left' if v>=0 else 'right',fontsize=10)
            if i==0:ax.set_title(title,fontweight='bold',pad=13)
            if i==1:ax.set_xlabel('Зміна відносно перевірок щохвилини, %')
        axes[i,0].set_ylabel('Відомі вікна від 7 діб' if i==0 else 'Відомі вікна від 1 доби',labelpad=12)
    fig.suptitle('C5: обмеження аналітичної межі збільшує кількість вимірювань',fontsize=17,fontweight='bold')
    fig.supxlabel('Початкові 128 місць налаштування, липень-вересень 2019; 10 спільних початкових зсувів.\n'
                  'Від’ємне значення краще. C3 має один M60 у вікнах від 1 доби; решта показаних правил — нуль.\n'
                  'Дані: City of Melbourne, CC BY 4.0. Власне відтворення; результати розроблення.',fontsize=10)
    for ext in ('png','svg'):fig.savefig(FIGURES/f'phase3-history-scheduler-comparison.{ext}',dpi=180)
    plt.close(fig)
    case=witness['cases'][0]
    arrays=np.load(ROOT/case['arrays_path'])
    epoch=datetime(1970,1,1)
    def date(v):return epoch+timedelta(seconds=int(v))
    ep=case['policies']['C3_shape_G75_A900']['missed_target_episodes'][0]
    index=ep['index'];ends=arrays['ends'];states=arrays['states']
    a,b=int(ends[index-1]),int(ends[index]);left=a-122;right=b+88
    fig,axes=plt.subplots(3,1,figsize=(13,7.5),sharex=True,layout='constrained')
    traces=[('Записаний стан',None),('C3: пауза до 75 с','C3_shape_G75_A900'),('C4: пауза до 72 с','C3_shape_G72_A900')]
    for ax,(title,name) in zip(axes,traces):
        ax.axvspan(date(a),date(b),color='#00a496',alpha=.14)
        if name is None:
            starts=np.r_[left,ends[(ends>left)&(ends<right)]]
            x=np.r_[starts,right]
            y=np.array([states[np.searchsorted(ends,t,side='right')] for t in starts])
            ax.step([date(t) for t in x],np.r_[y,y[-1]],where='post',lw=2,color='#34435b')
        else:
            decisions=arrays[name+'_decisions'];times=decisions[:,0]
            keep=decisions[(times>=left-120)&(times<=right+120)]
            ax.step([date(t) for t in keep[:,0]],keep[:,1],where='post',lw=1.6,color='#087fbd' if '75' in name else '#009b89')
            shown=keep[(keep[:,0]>=left)&(keep[:,0]<=right)]
            ax.scatter([date(t) for t in shown[:,0]],shown[:,1],s=38,color='#087fbd' if '75' in name else '#009b89',zorder=4)
            for t,s,run,pause,fb in shown:
                ax.annotate(date(t).strftime('%H:%M:%S'),(mdates.date2num(date(t)),s),xytext=(0,9 if s==0 else -20),
                            textcoords='offset points',ha='center',fontsize=9)
        ax.set_yticks([0,1],['Вільно','Зайнято']);ax.set_ylim(-.35,1.35)
        ax.set_ylabel(title,labelpad=13);ax.grid(axis='x',alpha=.2)
        ax.set_xlim(date(left),date(right))
    axes[0].text(date((a+b)//2),.48,'Вільний епізод: 60 с',ha='center',color='#007d6f',fontweight='bold')
    axes[1].text(date((a+b)//2),.48,'Немає виміру всередині; показ «вільно» зберігався',ha='center',fontsize=10)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    axes[-1].set_xlabel('20.08.2019, локальний час у вихідному записі')
    fig.suptitle('Один підтверджений випадок: місце 1247, початкова фаза № 6',fontsize=16,fontweight='bold')
    fig.supxlabel('Крапки — фактичні моменти змодельованих вимірювань; лінії — збережений показ.\n'
                  'Джерело: City of Melbourne 2019, CC BY 4.0. Незалежний симулятор підтвердив випадок.\n'
                  'Це покриття епізоду вимірюванням, а не повністю помилковий показ «зайнято».',fontsize=10)
    for ext in ('png','svg'):fig.savefig(FIGURES/f'phase3-history-scheduler-witness.{ext}',dpi=180)
    plt.close(fig)


def main():
    result=read(WORK/'results.json');calibration=read(WORK/'calibration.json')['calibration']
    witness=read(WORK/'verified-witnesses.json');by={r['name']:r for r in result['candidates']}
    fields=['policy','shape','G','A','cell','samples_per_bay_day','samples_reduction_percent','F_seconds_per_bay_day',
            'O_seconds_per_bay_day','M60','eligible60_episode_phases','passes_quality','failed_metrics','training_history_bound']
    with (DOCS/'phase3-history-scheduler-results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        out=csv.DictWriter(f,fieldnames=fields);out.writeheader()
        for row in result['candidates']:
            for cell,v in row['cells'].items():
                m=v['metrics'];out.writerow(dict(zip(fields,[row['name'],row['shape'],row['long_pause'],row['age_threshold'],cell,
                    m['samples_per_bay_day'],v['samples_reduction_percent'],m['false_free_seconds_per_bay_day'],
                    m['false_occupied_seconds_per_bay_day'],v['raw'][14],v['raw'][9],v['quality_passes'],
                    ','.join(v['failed_quality_metrics']),row['training_history_bound']])))
    figures(result,witness)
    lines=['# Конструювання розкладу за межею з урахуванням історії: C5',
      '', 'Дата: 25.10.2026. Фаза 3; усі наведені числа є власними результатами розроблення. Остаточні 867 місць не відкривали.',
      '', '**Рішення: C5 не приймаємо як поліпшення планування.** Виведена умова дає спосіб побудувати правило з нульовою аналітичною межею на навчальних записах, але в перевіреній родині це потребує більше вимірювань, ніж перевірки щохвилини. Заздалегідь визначений критерій корисності не виконано. Наукову новизну поліпшеного алгоритму не встановлено.',
      '', '## Що перевіряли',
      '', 'Планування частоти вимірювань та компроміс між витратами й актуальністю вже розглянуто в [S1](https://kclpure.kcl.ac.uk/ws/portalfiles/portal/51708026/Binder1.pdf). Причинне спостереження станів досліджено в [S2](https://doi.org/10.1109/TCOMM.2022.3160563). Неспостережені події між перевірками враховують [S8](https://users.ece.utexas.edu/~gustavo/papers/SBD21.pdf) та [S12](https://link.springer.com/article/10.1186/1687-1499-2013-9). Тому загальну ідею адаптивних пауз або обмеження пропусків авторською новизною не називаємо.',
      '', 'Власна перевірена тут модифікація - перетворення [умови H.1-H.3](phase3-history-bound-method.md) на правило вибору тривалості коротких початкових пауз. [План](phase3-history-scheduler-plan.json) і код зафіксовано до обчислення параметрів. Зіставлення з літературою не доводить відсутності тотожного результату в усіх попередніх працях.',
      '', 'Для довгої паузи G навчальна процедура знаходить усі ризикові пари «коротка зайнятість + вільний епізод від хвилини». За попередніми довгими зайнятостями визначає опору r, яка обмежує можливий початок спостереженої вільної послідовності. Беремо A=max(300,max(p-r)). Якщо довга пауза дозволена лише за спостереженого віку від A, умова p-r>A не виконується для жодної навчальної пари. Це достатня умова на конкретних записах, а не необхідний мінімальний поріг і не гарантія для нових даних.',
      '', 'Під час роботи правило використовує лише отримані покази та час від початку їхньої останньої незмінної послідовності. Справжні неспостережені переходи й навчальна опора r до пристрою не передаються. Калібрування - 256 місць у січні-червні, всі відомі вікна від доби. Перевірка якості - навчальна група і початкові 128 місць налаштування в липні-вересні; окремо вікна від 7 діб і від доби, відповідно 3 та 10 спільних початкових фаз.',
      '', 'Порівняно дві однакові родини: із фільтром аналітичної межі та без нього. Додано простіше правило і незмінені C3/C4/щохвилинний контроль. Усього 44 різні розклади, кожен у чотирьох комірках даних. Після результату жоден параметр не змінювали. Попередні групи перевірки 256/512 і нові місця тут не відкривали.',
      '', '## Параметри з навчальних даних', '', '| Довга пауза G, с | Пороговий вік A, с | Години | Ризикових пар | Місце, що задає максимум |', '|---:|---:|---:|---:|---|']
    for g,c in calibration.items():lines.append(f"| {g} | {c['required_age_seconds']} | {c['required_age_seconds']/3600:.2f} | {c['risky_pairs']} | {', '.join(map(str,c['maximum_support_bays']))} |")
    lines += ['', 'Великі A виникли через вимогу обнулити достатню верхню межу на всіх навчальних вікнах, включно з рідкісними послідовностями коротких станів. Це консервативність оцінки; вона не означає, що C3 фактично пропустив усі перелічені пари.',
      '', '## Витрати та якість на початкових 128 місцях налаштування',
      '', 'F - час показу «вільно» за записаної зайнятості; O - час показу «зайнято» за записаної вільності. Їхні одиниці - секунди на місце-добу. M60 - кількість епізодів від хвилини без жодного виміру всередині; повтори за початковими фазами рахуються окремо.',
      '', '| Вікна | Правило | Вимірів / місце-добу | Скорочення від щохвилинного, % | F | O | M60 |', '|---|---|---:|---:|---:|---:|---:|']
    named=[('Щохвилини','fixed60'),('C3/75','C3_shape_G75_A900'),('C4/72','C3_shape_G72_A900'),
           ('C5 без фільтра',result['selected']['unrestricted_pooled']),('C5 із фільтром',result['selected']['history_guard_pooled'])]
    for label in DAY:
        for title,name in named:
            c=by[name]['cells']['tuning_'+label];m=c['metrics']
            lines.append(f"| {'від 7 діб' if label==DAY[0] else 'від доби'} | {title} | {m['samples_per_bay_day']:.2f} | {c['samples_reduction_percent']:.2f} | {m['false_free_seconds_per_bay_day']:.2f} | {m['false_occupied_seconds_per_bay_day']:.2f} | {c['raw'][14]} |")
    lines += ['', '![Порівняння витрат і помилок](figures/phase3-history-scheduler-comparison.png)',
      '', 'Без фільтра вибрано G75/A14400; із фільтром - G75/A41621. Серед відповідних пошукових кандидатів вони мають найменші витрати за однакових обмежень F/O/M60 в усіх чотирьох комірках. **Це діагностичні переможці родини, а не рекомендовані системі правила:** щохвилинний контроль дешевший за обидва. Його не включали до пошукової родини, але явно перевіряли як контроль. C4 також дешевший і проходить усі ці емпіричні обмеження. У простій родині жоден кандидат не пройшов усі чотири комірки; застосовано передбачений щохвилинний контроль.',
      '', 'Порівняно з незміненим C3 аналітичний фільтр додає приблизно 22 процентні пункти витрат у цих комірках. При цьому C3 не проходить нову перевірку M60 на вікнах налаштування від доби. Тому це не порівняння двох однаково допустимих методів і не доказ домінування C3. Вибірка та суворіший фільтр тут відрізняються від первинного добору C3, який використовував основні вікна.',
      '', 'Зменшення F у C5 реальне в межах відтворення, але купується додатковими вимірами. Поставленого поліпшення ресурсу за прийнятної якості воно не дає. Жодна комбінація не пройшла попередньо зафіксовану умову: покращити скорочення вимірів C3 щонайменше на один процентний пункт у всіх чотирьох комірках. Нову перевірочну групу тому не відкривали.',
      '', '## Новий підтверджений випадок C3 та межі його значення',
      '', 'У початковій групі налаштування знайдено один M60: BayId1247, 20.08.2019, повтор №6, початковий зсув1376с. Запис: зайнято07:42:50-07:43:02 (12с), вільно07:43:02-07:44:02 (60с), сума72с. C3 отримує «вільно» о07:42:48, наступний вимір робить о07:44:03 і не спостерігає хвилинний епізод. У C4 вимір усередині нього є. Незалежний покроковий симулятор підтвердив усі17 підсумкових показників та гістограми для C3, C4 і двох кандидатів C5 на цьому вікні.',
      '', 'Вікно триває603835с - трохи менше7діб (604800с), тому його не було в основному відборі. Це конкретний приклад чутливості до порога відбору вікон. Усі інші правила та параметри залишено зафіксованими; випадок не використовували для їх зміни.',
      '', '![Підтверджений випадок](figures/phase3-history-scheduler-witness.png)',
      '', 'Це **вимірювання всередині епізоду**, а не відновлення цілого вільного епізоду з неправильного показу. C3 весь цей хвилинний інтервал показує «вільно». Неправильний показ «вільно» виникає під час короткої зайнятості перед ним. Один випадок не доводить загальне поліпшення C4 і не скасовує нестійкість калібрування72с.',
      '', 'Попередній перебір57600 відтворень не спростовано: він стосувався інших, неперетинних груп256/512. У них пропусків C3/C4 не знайдено. Тут відкрито ще не відтворену комбінацію старої групи128 і коротших вікон. Не слід узагальнювати жоден результат на всі місця чи всі можливі початки.',
      '', '## Що це змінює в дослідженні',
      '', '1. Аналітичну межу можна конструктивно використати для вибору порога; реалізацію перевірено. Вузький аналітичний результат залишається кандидатом внеску з невстановленою світовою оригінальністю.',
      '2. C5 як спосіб зменшення кількості вимірювань відхилено в зафіксованій родині. Не переносимо його в систему і не оголошуємо новим ефективним методом.',
      '3. Для C4 тепер є один конкретний записаний приклад поліпшення покриття відносно C3. Це обмежений емпіричний результат, а не підтвердження вимоги автора щодо сильного нового алгоритму.',
      '4. Детерміноване обнулення достатньої межі не використовуємо як автоматичний напрям подальшого налаштування. Основна задача залишається співвідношенням витрат і помилок відображення. Зміну вимог до M60 потрібно обґрунтувати окремо; цей звіт їх не змінює.',
      '5. Фаза3 відкрита. До фази4 не переходимо, фінальний тест не витрачаємо. Розділи магістерської, Google Docs і Canva цим експериментом не змінювали.',
      '', '## Відтворюваність і джерела',
      '', 'Дані: [City of Melbourne, On-street car parking sensor data2019](https://data.melbourne.vic.gov.au/explore/dataset/on-street-car-parking-sensor-data-2019/information/), CC BY4.0; [підготовка та маски](phase2-data-report.md). Це записані сенсорні стани, не незалежно перевірена фізична істина. Жодних висновків про точність ультразвуку або строк роботи батареї не робимо.',
      '', 'Файли експерименту: `.codex-work/parking-history-scheduler-20261025/` - pre-fit-lock.json, calibration.json, candidate-lock-before-replay.json, results.json,176файлів метрик, verified-witnesses.json і незалежно перевірений запис. [Повні числові результати](phase3-history-scheduler-results.csv) містять44×4 рядки. [План](phase3-history-scheduler-plan.json), [тести](phase3-history-scheduler-verification.json) та [маніфест](phase3-history-scheduler-artifacts.json) відокремлені від попередніх заморожених матеріалів.',
      '', 'S1/S2/S8/S12 - попередні методи й постановки; формула порога A та наведені числові результати - власна конструкція й обчислення. Прочитаний обсяг джерел і обмеження доступу зафіксовано в [аудиті літератури](phase3-stability-sources.md). Поточний точковий пошук не дав підстав оголошувати світову новизну цього способу побудови.', '']
    (DOCS/'phase3-history-scheduler-report.md').write_text('\n'.join(lines),encoding='utf-8')
    write_json(WORK/'decision.json',{'created_on':'2026-10-25','C5_promoted':False,'novel_improved_algorithm_established':False,
      'predeclared_usefulness_gate_passed':False,'verified_new_C3_M60':witness['verified_C3_M60'],
      'C4_general_superiority_claimed':False,'new_check_bays_opened':False,'phase4_may_start':False,
      'final_test_evaluated':False})
    print(json.dumps({'candidates':len(result['candidates']),'rows':len(result['candidates'])*4,'figures':2,'C5_promoted':False}))


if __name__=='__main__':main()
