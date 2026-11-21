"""Scientific figures and a candid practical-result report, all prior failures retained."""
import csv
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from prepare_data import ROOT,DOCS,sha256
from run_phase3 import write_json
from assess_analytic_contribution import read
from run_local_risk import WORK as BASE,old_bank
from local_risk_calibration_v3 import WORK as CAL
from budget_comparison import definitions


def clean(text):return re.sub(r'(?<=[а-яіїєґА-ЯІЇЄҐ])(?=\d)|(?<=\d)(?=[а-яіїєґА-ЯІЇЄҐ])',' ',text)


def main():
    result=read(CAL/'results.json');selection=read(CAL/'selection-before-check.json');head=result['headline']
    audit=read(CAL/'independent-audit/runtime-and-aggregation.json');full=read(BASE/'full-model-control/results.json')
    wide=read(BASE/'wide-control/results.json');union=read(BASE/'union-control/results.json');first=read(BASE/'check-results.json')
    cells=list(result['cohorts']);rows=[result['cohorts'][c][head] for c in cells]
    labels=['256 / ≥7 діб','256 / ≥1 доби','512 / ≥7 діб','512 / ≥1 доби']
    figs=DOCS/'figures';color='#0099ac';navy='#25375d'
    fig,axes=plt.subplots(1,3,figsize=(14,5.2),layout='constrained',sharey=True)
    for ax,metric,title in zip(axes,('calls','F','O'),('Менше вимірювань, %','Менший час помилки «вільно», с','Менший час помилки «зайнято», с')):
        x=[];lo=[];hi=[]
        for row in rows:
            ci=row['paired_primary_minus_fixed60']
            if metric=='calls':value=row['primary_calls_reduction_percent'];interval=ci['resource_difference_percent']
            else:
                key='F_seconds_per_bay_day' if metric=='F' else 'O_seconds_per_bay_day'
                value=row['reference_metrics'][key]-row['primary_metrics'][key]
                interval=ci[metric+'_difference_seconds_per_day']
            x.append(value);lo.append(-interval[1]);hi.append(-interval[0])
        ax.errorbar(x,np.arange(4),xerr=[np.array(x)-lo,np.array(hi)-x],fmt='o',capsize=5,color=color,lw=2)
        ax.axvline(0,color='#a2afbf',ls='--');ax.set_title(title,fontsize=11,loc='left',weight='bold',color=navy)
        ax.set(yticks=range(4),yticklabels=labels,xlim=(0,max(hi)*1.2),ylim=(3.5,-.4))
        for i,v in enumerate(x):ax.annotate(f'{v:.1f}',(v,i),xytext=(0,-14),textcoords='offset points',ha='center',fontsize=10)
        ax.spines[['top','right']].set_visible(False)
        ax.set_xlabel('Відносно перевірок щохвилини' if metric=='calls' else 'Секунд на місце-добу')
    fig.suptitle('Зафіксований локальний метод: менші витрати й обидві помилки карти',weight='bold',fontsize=14)
    fig.supxlabel('Реалізований вибір таблиць, зерно 20261025. Точкові 95% інтервали: парний відбір цілих місць; розроблення, не остаточний тест.\nНабори від доби включають набори від 7 діб. Менше вимірювань не є виміряною економією батареї.',fontsize=9)
    for ext in ('png','svg'):fig.savefig(figs/('phase3-local-risk-results.'+ext),dpi=200)
    plt.close(fig)
    # Exact-resource reference sets; this is explicitly hindsight, not frozen CI.
    matrix=np.array([[(full['cohorts'][c][f]['t']-1)*100 for f in ('pooled','bay_state','unshrunk')]+
      [(wide['cohorts'][c]['hindsight_equal_expected_budget']['t']-1)*100,
       (union['cohorts'][c]['hindsight_equal_expected_budget']['t']-1)*100] for c in cells])
    fig,ax=plt.subplots(figsize=(12,5.6),layout='constrained');im=ax.imshow(matrix,cmap='Blues',vmin=0,vmax=max(30,float(matrix.max())),aspect='auto')
    ax.set(xticks=range(5),xticklabels=['Спільна\nоцінка','Лише місце\nта стан','Локальна без\nзгладжування','Широкі прості\nправила','Прості та всі\nпопередні'],yticks=range(4),yticklabels=labels)
    for i in range(4):
        for j in range(5):ax.text(j,i,f'+{matrix[i,j]:.1f}%',ha='center',va='center',weight='bold',color='white' if matrix[i,j]>20 else navy,fontsize=12)
    fig.suptitle('Однаковий очікуваний бюджет: оптимістична межа контрольних родин',weight='bold',fontsize=13)
    fig.colorbar(im,ax=ax,shrink=.85,label='Перевищення принаймні однієї помилки, %')
    fig.supxlabel('Ретроспективний добір ваг за кожним перевірочним набором. Це не готові зафіксовані конкуренти.\nЗначення (t−1)×100%; не означає перевищення ОБОХ помилок або переваги над усіма алгоритмами.',fontsize=9)
    for ext in ('png','svg'):fig.savefig(figs/('phase3-local-risk-controls.'+ext),dpi=200)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,5.5),layout='constrained');y=np.arange(4)
    losses=[100*audit['aggregation'][c]['primary_M60_fraction'] for c in cells]
    axes[0].barh(y,losses,color='#d89554')
    for i,v in enumerate(losses):axes[0].text(v+.005,i,f'{v:.3f}%',va='center')
    axes[0].set(yticks=y,yticklabels=labels,xlim=(0,.31),xlabel='Вільні епізоди ≥60 с без нового виміру, %')
    axes[0].set_title('Ціна скорочення вимірювань',loc='left',weight='bold',fontsize=12)
    for offset,key,col,label in ((-.15,'bays_worse_F',navy,'Більший час помилки «вільно»'),(.15,'bays_worse_O',color,'Більший час помилки «зайнято»')):
        values=[100*audit['aggregation'][c][key]/audit['aggregation'][c]['bays'] for c in cells]
        axes[1].barh(y+offset,values,.28,color=col,label=label)
    axes[1].set(yticks=y,yticklabels=labels,xlim=(0,55),xlabel='Частка місць із гіршим особистим показником, %')
    axes[1].set_title('Середній виграш не гарантує\nвиграшу кожного місця',loc='left',weight='bold',fontsize=11)
    axes[1].legend(fontsize=8,loc='lower right',frameon=False)
    for ax in axes:ax.set_ylim(4.1,-.55);ax.spines[['top','right']].set_visible(False)
    fig.supxlabel('Порівняння зі щохвилинним контролем; у нього M60=0. Спостережений вільний епізод і правильний показ карти - різні метрики.\nПоказано основне зафіксоване зерно; поріг допустимого M60 у цій роботі не вигадується з результатів.',fontsize=9)
    for ext in ('png','svg'):fig.savefig(figs/('phase3-local-risk-tradeoffs.'+ext),dpi=200)
    plt.close(fig)
    with (DOCS/'phase3-local-risk-results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['cell','allocation','calls_per_bay_day','F_seconds_per_bay_day','O_seconds_per_bay_day','M60','eligible60','calls_reduction_percent'])
        for c,row in zip(cells,rows):
            for kind,key,red in (('primary','primary_metrics',row['primary_calls_reduction_percent']),('expected','expected_metrics',row['expected_calls_reduction_percent']),('fixed60','reference_metrics',0)):
                m=row[key];writer.writerow([c,kind,*[m[k] for k in ('samples_per_bay_day','F_seconds_per_bay_day','O_seconds_per_bay_day','M60_expected_count','eligible60_episode_phases')],red])
    with (DOCS/'phase3-local-risk-controls.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['cell','family','hindsight_exact_budget_t','not_deployable_frozen_comparison'])
        for c in cells:
            for family,item in full['cohorts'][c].items():writer.writerow([c,'same_model_'+family,item['t'],True])
            writer.writerow([c,'wide900',wide['cohorts'][c]['hindsight_equal_expected_budget']['t'],True])
            writer.writerow([c,'all_previous_and_wide1226',union['cohorts'][c]['hindsight_equal_expected_budget']['t'],True])
    table=[];decreases={'calls':[],'F':[],'O':[]}
    for label,row,c in zip(labels,rows,cells):
        m=row['primary_metrics'];r=row['reference_metrics'];f=100*(1-m['F_seconds_per_bay_day']/r['F_seconds_per_bay_day']);o=100*(1-m['O_seconds_per_bay_day']/r['O_seconds_per_bay_day'])
        decreases['calls'].append(row['primary_calls_reduction_percent']);decreases['F'].append(f);decreases['O'].append(o)
        table.append(f"| {label} | {m['samples_per_bay_day']:.1f} | {row['primary_calls_reduction_percent']:.1f}% | {m['F_seconds_per_bay_day']:.1f} / {r['F_seconds_per_bay_day']:.1f} | {m['O_seconds_per_bay_day']:.1f} / {r['O_seconds_per_bay_day']:.1f} | {100*audit['aggregation'][c]['primary_M60_fraction']:.3f}% |")
    rates=lambda k:f'{min(decreases[k]):.1f}-{max(decreases[k]):.1f}%'
    macro='\n'.join(f"| {label} | {v['macro_primary_means']['calls']:.1f} / {v['macro_fixed60_means']['calls']:.1f} | {v['macro_primary_means']['F']:.1f} / {v['macro_fixed60_means']['F']:.1f} | {v['macro_primary_means']['O']:.1f} / {v['macro_fixed60_means']['O']:.1f} | {v['bays_worse_F']} / {v['bays']} | {v['bays_worse_O']} / {v['bays']} |" for label,c in zip(labels,cells) for v in [audit['aggregation'][c]])
    controltable='\n'.join('| '+label+' | '+' | '.join(f'{value:.2f}%' for value in m)+' |' for label,m in zip(labels,matrix))
    report=f'''# Практичний результат: локальний ризик і калібрування розкладу

25.10.2026. Дослідницька фаза3. [Метод L.1-L.6](phase3-local-risk-method.md), [джерела й межі внеску](phase3-local-risk-sources.md), [числа](phase3-local-risk-results.csv), [короткий виклад для захисту](phase3-local-risk-defense-brief.md).

**Отримано авторський варіант із виміряним виграшем за кількістю вимірювань і двома помилками карти.** Для заздалегідь зафіксованого реалізованого вибору таблиць кількість вимірювань менша на{rates('calls')}, час помилкового показу «вільно» - на{rates('F')}, «зайнято» - на{rates('O')} від щохвилинного контролю. Це результати розроблення на вже відомих записах, не незалежне підтвердження на остаточних867 місцях.

Виграш має ціну: з'являються вільні епізоди від хвилини без нового виміру всередині. Початковий протоколv0.1 із нульовим M60 не виконано; його результати не переписано. Нова постановка щодо якості карти виділена в [окремій чернетці протоколуv0.2](phase4-display-protocol-draft.json), без автоматичного відкриття остаточного тесту.

## Що змінилося в методі

Для кожного місця оцінюємо, скільки секунд карта може помилятися після паузи заданої тривалості. Оцінка враховує виміряний стан, частину доби та спостережену історію. Нестійкі місцеві оцінки підтримуються спільними даними. Потім підбираємо ваги цілих причинних таблиць так, щоб на навчальних/налагоджувальних записах обидва часи помилки не перевищували90% від щохвилинного контролю. Це інженерний запас, не статистична гарантія.

Для конкретного місця один раз обирається таблиця за наперед фіксованим зерном; далі її інтервали залежать лише від уже зроблених вимірів і часу. Обраний варіант має α=500 та три складники з вагами0.294067,0.077468,0.628465. Вибір між α50/500 зроблено за навчальною цільовою функцією до нових перевірочних запусків. Повний опис і доведення лінійності сподіваних лічильників наведено у методі.

## Результати для карти та витрат

У таблиці F/O - секунди помилкового показу на місце-добу; наведено «метод / щохвилинний контроль». Критерії від доби та від7діб перекриваються, тому чотири рядки не є чотирма незалежними дослідженнями.

| Група / вікна | Вимірів на місце-добу | Скорочення | F: метод / контроль | O: метод / контроль | Вільні епізоди ≥60с без виміру |
|---|---:|---:|---:|---:|---:|
{chr(10).join(table)}

![Витрати та два часи помилки](figures/phase3-local-risk-results.png)

Це реалізований основний вибір із зерном20261025. Окреме точне сподівання за обранням таблиці дає скорочення11.6-22.4%. За всіма десятьма наперед заданими зернами обидва часи помилки менші за щохвилинні в кожному наборі; однак найменше скорочення вимірювань на256/від доби серед цих зерен дорівнює9.50%, тому стабільної для кожного зерна нижньої межі10% не заявляємо. Це не добір сприятливого зерна після результату.

На графіку подано точкові95% інтервали парного відбору цілих BayId,2000 повторів, умовні щодо вже вибраного методу. Вони не враховують усю історію пошуку й перенавчання, тому не є остаточним підтвердженням або поправленою на всі зіставлення статистикою. У найслабшому ресурсному рядку інтервал скорочення приблизно8.0-15.4%; число10% є виконаним критерієм точкової оцінки основного зерна, а не доведеною нижньою межею ефекту.

## Чи це більше, ніж перевага над слабким контролем

Порівняно зі спільною моделлю, моделлю лише місця/стану та локальною без згладжування за однакових даних і сітки дій. Їхні ваги для основних зіставлень добиралися на чотирьох навчальних/налагоджувальних наборах і фіксувалися перед новими запусками. Окремо розширено прості правила до900 визначень із паузами до300с в обох станах; обмежений старий банк не використовуємо як доказ переваги.900 визначень відповідають841 різній таблиці.

Для точного вирівнювання витрат додатково побудовано **ретроспективні оптимістичні межі**: контрольним вагам дозволено знати результат свого перевірочного набору, а очікувана кількість вимірювань точно дорівнює методу. Нижче - мінімальне неминуче перевищення принаймні однієї з двох помилок у відповідній контрольній родині. Це(t−1)×100%, не обов'язково перевищення обох помилок одночасно.

| Група | Спільна модель | Лише місце/стан | Без згладжування | Прості900 | Прості й усі попередні1226 |
|---|---:|---:|---:|---:|---:|
{controltable}

![Контролі за точного очікуваного бюджету](figures/phase3-local-risk-controls.png)

Навіть об'єднання257 спільних, персоналізованих лише за станом і незгладжених визначень у цій оптимістичній перевірці не повторило обидва F/O методу за того самого бюджету. Це конкретний ізольований ефект згладженого локального оцінювання в зафіксованій родині. Він не доводить переваги над усіма можливими алгоритмами або загальної новизни згладжування. Для ретроспективних меж не додаємо довірчих інтервалів як для незалежно обраних політик.

## Ціна виграшу та розподіл між місцями

![Пропуски та індивідуальні погіршення](figures/phase3-local-risk-tradeoffs.png)

Основний метод має ненульовий M60, у щохвилинного контролю він нульовий. Частка становить0.167-0.248% серед вільних епізодів від60с з урахуванням десяти початкових фаз. Це не частка часу й не відсоток повністю неправильних показів карти. Допустимий для реального продукту поріг не визначено. За початковим жорстким критерієм нульового M60 поліпшення над щохвилинним правилом не отримано.

Поліпшення середніх не означає виграш кожного місця. Нижче - рівновагові середні за BayId, де кожне місце має однакову вагу, та кількість місць із більшим особистим F/O. Основна таблиця вище використовує погоджене нормування на відому місце-добу.

| Група | Середнє N: метод / контроль | Середнє F | Середнє O | Місць із більшим F | Із більшим O |
|---|---:|---:|---:|---:|---:|
{macro}

Макросередні також поліпшені, але приблизно третина-дві п'ятих місць мають більший окремий F або O. Персональної гарантії або рівномірного поліпшення не заявляємо. На групах256 і512 відповідно11 і18 місць не мали дозволеної навчальної історії та використовували спільний резервний варіант.

## Відтворення та межі наукового висновку

Навчання:1063 місця, січень-червень2019, тільки дозволений train_development. Запитані1098 відомих ідентифікаторів;35 не мали потрібної історії. Використано30039 відомих навчальних вікон,2948585 інтервалів і45407244 корельованих навчальних точок. Вибір параметрів - початкові256/128 місць у чотирьох наборах. Перевірочні256/512 у липні-вересні вже використовувалися раніше; вони не є новою незалежною вибіркою.

Самодостатню [політику JSON](phase3-local-risk-policy.json) перевірено з окремим онлайн-інтерфейсом, який не бачить майбутніх станів. На12 відомих вікнах незалежний прямий симулятор відтворив усі17 лічильників і гістограми затримки. Нові місцеві навчальні історії можна буде додати зі збереженням заморожених спільних оцінок; точну рівність такого способу для наявних1063 місць перевірено. Зарезервовані історії та остаточні867 місць у цій роботі не читалися для оцінювання методу.

Первинний вибір однієї таблиці не пройшов власного10% критерію в усіх наборах. Наступне калібрування оголошено окремим планом після цього результату; незавершену технічну версію2 і виправлену версію3 з однаковою математичною постановкою збережено. Початковий протокол, усі невдалі кандидати й раніше отримані аналітичні результати не переписано.

**Обґрунтований внесок для обговорення:** удосконалення конкретного способу планування через L.1-L.6 та виміряний ефект локального згладжування й повного калібрування проти сильних контролів. Це вже власні відтворювані результати, а не перенесені числа зі статті. Загальні складові методу відомі; [зіставлення джерел](phase3-local-risk-sources.md) відокремлює їх від авторської спеціалізації. Світова першість або гарантована оцінка конкретної комісії не встановлюються.

Джерело записів: [City of Melbourne2019](https://data.melbourne.vic.gov.au/explore/dataset/on-street-car-parking-sensor-data-2019/information/), CC BY4.0. Показники стосуються відтворення сенсорної історії, не незалежної фізичної розмітки, точності ультразвуку або виміряного споживання батареї. Основний Google-документ і Canva не змінювалися. [Технічний журнал і контрольні суми](phase3-local-risk-verification.json).
'''
    (DOCS/'phase3-local-risk-report.md').write_text(clean(report),encoding='utf-8')
    brief=f'''# Коротке пояснення власного результату

Система може перевіряти кожне паркомісце щохвилини. Але місця мають різну активність: десь стан довго незмінний, десь автомобілі часто змінюються. Я досліджую, як вибирати час наступного вимірювання, щоб зменшити їхню кількість і водночас скоротити час неправильного показу на карті.

Для цього за історією конкретного місця оцінюється, скільки секунд карта може помилятися після паузи різної тривалості. Враховуються останній виміряний стан, час доби та попередні виміри. Якщо місцевих даних мало, оцінка спирається також на спільну історію інших місць. Потім налаштовується весь розклад: окремо контролюється помилковий показ «вільно» й «зайнято».

На двох відомих перевірочних групах, окремо для довших і коротших відомих вікон, зафіксований варіант робить на{rates('calls')} менше вимірювань, ніж перевірки щохвилини. Час помилкового показу «вільно» менший на{rates('F')}, а «зайнято» - на{rates('O')}. Це відносне скорочення часу помилок, а не така сама зміна загальної точності у процентних пунктах.

Перевірено також, звідки взявся виграш: метод порівняно зі спільною оцінкою, простішою персоналізацією та локальним оцінюванням без згладжування. За однакового очікуваного бюджету останні мають гіршу межу компромісу двох помилок. Самі адаптивні вимірювання, згладжування та лінійне програмування вже відомі. Власна частина - конкретний спосіб їх застосування до часових помилок паркомісця та перевірений ефект його деталей.

Є компроміс: близько0.17-0.25% вільних епізодів від хвилини залишаються без нового виміру всередині. Це не означає неправильний стан карти весь цей час. Також середній виграш не означає виграш кожного місця. За початковою вимогою нульових таких пропусків переваги немає.

Це власні результати відтворення відкритої сенсорної історії, без експерименту з автомобілем. Вони ще потребують незалежної перевірки на заздалегідь відокремлених867 місцях. Строк роботи батареї та фізична точність датчика з цих чисел не визначаються.

[Повний звіт і графіки](phase3-local-risk-report.md) · [Метод](phase3-local-risk-method.md) · [Джерела](phase3-local-risk-sources.md)
'''
    (DOCS/'phase3-local-risk-defense-brief.md').write_text(clean(brief),encoding='utf-8')
    evidence=read(BASE/'sources/download-receipt.json')
    scopes={'S17-Rezaei-2023':'Read primary problem3, model4, implementation5, methodology6, results7-8 and discussion/related/conclusion9-11; emphasized4.2,6.3-6.5 and tables3-7. No reproduction of experiments; graphical elements not all independently inspected.',
      'S18-Dias-2016':'Read technicalII-IV including actual selected state tuple(q,s,working-hour), syntheticV, recordedVI, conclusionVII. No numerical reproduction; temperature endpoint-quality objective is not F/O integral.',
      'S19-Gelman-2006':'Read all four main-text pages including partial/complete/no pooling2.2-2.3 and causal interpretation2.4/discussion3. No reproduction of radon example.'}
    for name,item in evidence.items():item['read_scope']=scopes[name]
    write_json(DOCS/'phase3-local-risk-source-evidence.json',{'created_on':'2026-10-25','sources':evidence,'search_not_exhaustive':True,
      'targeted_queries':['adaptive sampling parking sensors reinforcement learning interval','parking sampling hierarchical adaptive',
        'adaptive sampling partial pooling','sensor sampling interval shrinkage','parking sampling integrated error'],
      'unrelated_vehicle_path_planning_results_not_used':True,'own_method_is_not_a_generic_new_optimizer':True})
    write_json(DOCS/'phase3-local-risk-summary.json',{'created_on':'2026-10-25','headline':head,'primary_reduction_ranges_percent':{k:[min(v),max(v)] for k,v in decreases.items()},
      'primary_M60_fraction_range':[min(losses)/100,max(losses)/100],'point_estimate_usefulness_gate':result['gates'][head],
      'original_zero_M60_protocol_satisfied':False,'final_test_evaluated':False,'phase4_may_start':False})
    print('Report, brief, CSVs, source evidence and3scientific PNG/SVG figures written')


if __name__=='__main__':main()
