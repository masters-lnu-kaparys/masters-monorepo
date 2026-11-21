"""Create the all-start diagnostic report and a source-witness scientific figure."""
import csv
import re
from datetime import datetime,timedelta
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from prepare_data import ROOT,DOCS
from run_phase3 import write_json
from assess_start_reachability import WORK
from assess_analytic_contribution import read
from data_access import load_bundle


def stamp(second):return (datetime(1970,1,1)+timedelta(seconds=int(second))).strftime('%d.%m.%Y %H:%M:%S')


def main():
    results=read(WORK/'recorded-reachability.json');small=read(WORK/'independent-start-enumeration.json')
    positives=read(WORK/'positive-witnesses.json');unique={(x['bay'],x['a'],x['b']) for x in positives}
    with (DOCS/'phase3-start-reachability-counts.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['cell','eligible','generic_pair_bound','recursive_bound','attainable_episodes'])
        for cell,row in results['cells'].items():writer.writerow([cell,*row['counts'].values()])
    with (DOCS/'phase3-start-reachability-witnesses.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['cohort','window_criterion','bay','window_id','free_a_local','free_b_local',
          'busy_duration_seconds','free_duration_seconds','initial_start_local','offset_from_window_start_seconds','last_free_sample_local','next_sample_local'])
        for x in positives:
            w=x['witness'];writer.writerow([x['cohort'],x['window_criterion'],x['bay'],x['window_id'],stamp(x['a']),stamp(x['b']),
              x['a']-x['preceding_busy_start'],x['b']-x['a'],stamp(w['initial_start']),x['initial_offset_seconds'],
              stamp(w['last_free_sample']),stamp(w['next_sample'])])
    # Read only the same known development witness window for the source timeline.
    chosen=next(x for x in positives if x['cohort']=='check512')
    data=load_bundle(('validation_development',),bay_filter=[chosen['bay']],primary_only=False)
    w=data.window_ids.index(chosen['window_id']);lo,hi=data.offsets[w:w+2];ends=data.ends[lo:hi];states=data.states[lo:hi]
    starts=np.r_[data.starts[w],ends[:-1]];a=chosen['a'];b=chosen['b'];left=a-160;right=b+30
    fig,axes=plt.subplots(1,2,figsize=(14,6.7),gridspec_kw={'width_ratios':[1.25,1.3]},layout='constrained')
    labels=[];rows=[]
    for cohort,uk in (('training256','Навчальні 256'),('tuning128','Налаштування 128'),('check256','Перевірка 256'),('check512','Перевірка 512')):
        for win,desc in (('primary_7_days','від 7 діб'),('sensitivity_1_day','від доби')):
            labels.append(uk+' / '+desc);rows.append(results['cells'][cohort+'_'+win+'_C3']['counts'])
    ax=axes[0];y=np.arange(len(rows));height=.23
    for offset,key,color,label in ((-.25,'generic_pair_bound','#c7d0dc','Парна межа'),
       (0,'recursive_bound','#7792ae','Межа з історією'),(.25,'attainable_episodes','#0099ac','Точна досяжність')):
        values=[r[key] for r in rows];ax.barh(y+offset,values,height,color=color,label=label)
        for yy,v in zip(y+offset,values):ax.text(v+.08,yy,str(v),va='center',fontsize=9)
    ax.set(yticks=y,yticklabels=labels,xlim=(0,12.2),xlabel='Кількість окремих епізодів');ax.invert_yaxis()
    ax.set_title('C3/75: які пропуски справді можливі',loc='left',weight='bold',fontsize=12)
    ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='y',length=0)
    ax.legend(loc='lower right',fontsize=9,frameon=False)
    bx=axes[1];colors={0:'#d9f0f2',1:'#25375d'}
    for begin,end,state in zip(starts,ends,states):
        aa=max(begin,left);bb=min(end,right)
        if bb>aa:bx.broken_barh([(aa-a,bb-aa)],(.62,.55),facecolors=colors[int(state)],edgecolor='white')
    samples=[d[0] for d in chosen['reference_decisions'] if left<=d[0]<=right]
    bx.scatter(np.array(samples)-a,np.full(len(samples),.35),color='#e58932',s=40,zorder=4)
    for t in (chosen['witness']['last_free_sample'],chosen['witness']['next_sample']):
        bx.axvline(t-a,ymin=.16,ymax=.72,color='#e58932',ls='--',lw=1)
    bx.annotate('Останній вимір\nпоказав «вільно»',(-15,.35),xytext=(-151,-.1),
      arrowprops={'arrowstyle':'->','color':'#65768c'},fontsize=10,va='top')
    bx.annotate('Наступний вимір\nточно в кінці епізоду',(60,.35),xytext=(0,-.1),
      arrowprops={'arrowstyle':'->','color':'#65768c'},fontsize=10,va='top')
    bx.text(-150,1.5,'Зайнятість 13 с, потім вільний епізод 60 с.\nМіж сусідніми вимірами C3 минуло 75 с.',fontsize=10,linespacing=1.6)
    bx.text(-150,-.88,'BayId 5608, '+stamp(a)+'\nПочаток роботи: '+stamp(chosen['witness']['initial_start'])+
      '\nДжерело станів - сенсорний запис Мельбурна.\nПоказ «вільно» зберігався у вільному епізоді.',fontsize=9,va='top',linespacing=1.7,color='#53627a')
    bx.set(xlim=(-160,90),ylim=(-2.0,2.4),yticks=[],xlabel='Секунди від початку цільового вільного епізоду',xticks=[-150,-90,-15,0,60,90])
    bx.set_title('Відтворюваний приклад із групи 512',loc='left',weight='bold',fontsize=12)
    bx.spines[['top','right','left']].set_visible(False)
    bx.legend(handles=[Patch(facecolor=colors[1],label='Записано «зайнято»'),Patch(facecolor=colors[0],label='Записано «вільно»')],
      loc='upper left',bbox_to_anchor=(0,1.0),fontsize=9,frameon=False)
    fig.suptitle('Довільний початок роботи та покриття епізодів вимірюваннями',fontsize=15,weight='bold')
    fig.supxlabel('Для кожного досяжного епізоду може бути свій початок; критерії вікон перекриваються. C4/72: нуль у всіх восьми комірках.',fontsize=9)
    for ext in ('png','svg'):fig.savefig(DOCS/'figures'/('phase3-start-reachability.'+ext),dpi=200)
    plt.close(fig)
    table='\n'.join('| '+label+' | '+' | '.join(str(r[k]) for k in ('eligible','generic_pair_bound','recursive_bound','attainable_episodes'))+' |' for label,r in zip(labels,rows))
    operations={k:sum(v['operations'][k] for v in results['cells'].values()) for k in next(iter(results['cells'].values()))['operations']}
    report=f'''# Точна перевірка C3/C4 за всіх моментів початку роботи

25.10.2026. Фаза 3. [План](phase3-start-reachability-plan.json), [виведення й припущення](phase3-start-reachability-method.md), [таблиця](phase3-start-reachability-counts.csv), [конкретні старти](phase3-start-reachability-witnesses.csv).

**Для C3 знайдено можливі пропуски, яких не виявляв попередній перебір початкових зсувів на перевірочних групах.** Вони відтворюються, якщо почати роботу пізніше у відомому вікні. Це не змінює результат попереднього досліду: він перевіряв старти лише в межах першої години. Нове питання ширше: довільний початок у межах усього вікна з початковим виміром і скиданням спостереженого віку.

На тих самих даних C4/72 має нуль для всіх цільових епізодів і всіх початків за припущень методу: у жодної допустимої пари B+D немає значення меншого за72с. Це підтвердження на записі, а не гарантія для майбутніх фізичних паркувань.

## Що саме перевірено

Точний етап розглядає всі можливі виміри, які могли б оточувати ризиковий епізод, і встановлює досяжність потрібної історії показів. За цілих меж джерела та цілих пауз запуск із дробовою частиною часу має те саме покриття, що цілий запуск. Тому область охоплює також дійсні моменти старту; це випливає з доведення, а не лише з перевірки двох дробових зсувів.

Використано незмінені C3/75 і C4/72, навчальні256, налаштовувальні128 та вже відомі перевірочні256/512 місць; окремо від7діб та віддоби. Нових груп і остаточних867 місць не відкривали. Записані мітки часу є локальними цивільними секундами, не підтвердженим UTC.

## Результати для C3

| Група / вікна | Цільових епізодів | Парна межа | Рекурсивна межа | Точно досяжні епізоди |
|---|---:|---:|---:|---:|
{table}

«Точно досяжні» означає: **для кожного такого епізоду існує принаймні один початок із пропуском**. Це не число пропусків одного спільного запуску, не частота збоїв і не ймовірність. Критерій віддоби включає вікна від7діб; рядки не незалежні. Усього збережено{len(positives)} рядків зі свідченнями, які відповідають{len(unique)} різним записаним епізодам. Частина епізодів уже була відома з попередніх перевірок, тому не називаємо всі{len(unique)} нововиявленими.

Точний етап уточнив консервативні додатні межі, наприклад навчальні256/віддоби: 6 потенційних за R.3, але лише2 індивідуально досяжні для C3. Для перевірочних256/віддоби: 2 і1. Перевірочні512/віддоби: є1 досяжний епізод, хоча попередній перебір стартів першої години не давав пропусків. Нуль основних перевірочних вікон від7діб збережено.

![Покриття й відтворюваний приклад](figures/phase3-start-reachability.png)

## Незалежна перевірка та обчислювальний обсяг

Зворотний пошук зіставлено з незалежним прямим перебором кожного цілого старту на486 п'ятиінтервальних траєкторіях і трьох коротких шаблонах:1458 випадків «траєкторія-шаблон». Додано100 зафіксовано випадкових восьмиінтервальних траєкторій з тими самими трьома шаблонами. Разом{small['combined']['trace_profile_cases']} випадків, {small['combined']['integer_initializations']} цілих та{small['combined']['fractional_initializations']} дробових запусків. Множини досяжних епізодів збіглися. Це перевірка реалізації, окремо від письмового доведення.

Кожен додатний випадок на даних відтворено старим незалежним симулятором із зафіксованою таблицею політики; перевірено всі виміри до цілі та відсутність виміру всередині неї. Для16 комірок «дані-правило» після проходу по записаних інтервалах знадобилося {operations['candidate_last_samples']} кандидатів останнього виміру, {operations['plateau_nodes']} кроків довгої стадії та {operations['source_queries']} запитів стану в точному етапі. Повний прохід по джерелу в ці лічильники не входить. Це не виміряний коефіцієнт прискорення над попереднім дослідом: вони мають різні області стартів.

[Технічний журнал](phase3-start-reachability-verification.json) містить тести й контрольні суми; попередні95 тестів і результати збережено.

## Практичний зміст і внесок

Маємо конкретне доповнення до аналітичної межі: якщо вона додатна, для фіксованого правила можна отримати точну відповідь і відтворюваний контрприклад. Це знімає невизначеність між «верхня межа залишає ризик» і «такий запуск справді існує». Метод виявив обмеження попередньої перевірки початкових зсувів. Правила C3/C4 не переналаштовувалися.

Це дослідницький результат **перевірки адаптивних розкладів**. Нової переваги онлайн-планувальника за витратами чи F/O цим не встановлено. Загальна перевірка досяжності, дискретизація та генерація контрприкладів давно відомі; власним є наведене спеціальне зведення S.1-S.2 для шаблону пауз і його перевірка на цій постановці. [Зіставлення з первинними працями](phase3-analytic-sources.md) не доводить світової новизни конкретної формули.

У всіх знайдених прикладах останній показ до цільового звільнення був «вільно». Тому відсутність виміру в епізоді не дорівнює цілком неправильному показу карти. Для наведеного BayId5608 пропущено коротку зайнятість13с, а карта у наступні60с вільного епізоду залишалася вільною. Мета свіжого підтвердження епізоду потребує окремого обґрунтування; поліпшення точності карти з цих чисел не випливає.

Джерело: [City of Melbourne2019](https://data.melbourne.vic.gov.au/explore/dataset/on-street-car-parking-sensor-data-2019/information/), CC BY4.0; це сенсорні записи. Фізична точність ультразвуку й споживання батареї тут не вимірювалися. Основний Google-документ і Canva не змінювалися. Фаза4 залишається закритою: точний перевіряльник не підміняє незавершений критерій внеску поліпшеного планування та фіксацію остаточного протоколу.
'''
    report=re.sub(r'(?<=[а-яіїєґА-ЯІЇЄҐ])(?=\d)|(?<=\d)(?=[а-яіїєґА-ЯІЇЄҐ])',' ',report)
    report=report.replace('віддоби','від доби').replace('лише2','лише 2').replace('271 кроків','271 крок довгої стадії').replace('довгої стадії довгої стадії','довгої стадії')
    (DOCS/'phase3-start-reachability-report.md').write_text(report,encoding='utf-8')
    write_json(DOCS/'phase3-start-reachability-summary.json',{'created_on':'2026-10-25','cells':{k:v['counts'] for k,v in results['cells'].items()},
      'positive_rows':len(positives),'distinct_positive_recorded_episodes':len(unique),'operations':operations,
      'small_validation_cases':small['combined'],'fixed_policy_reconstruction_verified':True,
      'novel_superior_scheduler_claimed':False,'final_test_evaluated':False,'phase4_may_start':False})
    print('All-start report, CSVs, summary, PNG/SVG written')


if __name__=='__main__':main()
