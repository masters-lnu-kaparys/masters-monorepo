"""Report the fixed analytical audit without changing older reports or experiments."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from assess_analytic_contribution import WORK,read,NAMES
from prepare_data import DOCS,sha256
from run_phase3 import write_json


def main():
    result=read(WORK/'recorded-counts.json');finite=read(WORK/'finite-enumeration.json')
    target=DOCS/'phase3-analytic-counts.csv'
    with target.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['cell','bays','windows',*NAMES])
        for name,row in result['cells'].items():writer.writerow([name,row['bays'],row['windows'],*[row['counts'][n] for n in NAMES]])
    fig=plt.figure(figsize=(12.6,6.8),layout='constrained')
    grid=fig.add_gridspec(2,2,height_ratios=(1.35,1),width_ratios=(1.8,1))
    ax=fig.add_subplot(grid[0,:]);edges=[0,6,12,16,22,23,27,30];states=[1,0,1,0,1,0,1]
    colors={1:'#25375d',0:'#d9f0f2'}
    for a,b,state in zip(edges[:-1],edges[1:],states):
        ax.broken_barh([(a,b-a)],(0,.75),facecolors=colors[state],edgecolor='white',linewidth=1.4)
    ax.plot([6,16],[-.14,-.14],'o',color='#0099ac',markersize=8,clip_on=False)
    ax.annotate('Початкову зайнятість бачить перший вимір\nПісля її кінця: r = 6',(6,-.14),xytext=(.5,-.77),
                arrowprops={'arrowstyle':'->','color':'#68758a'},fontsize=10,va='top')
    ax.annotate('Тривалість 4 = τ; початок 12 − r = 6 ≤ A\nОбов’язкове спостереження; нове r = 16',
                (14,.75),xytext=(7.6,1.28),arrowprops={'arrowstyle':'->','color':'#0099ac'},fontsize=10,va='bottom')
    ax.annotate('Цільовий вільний епізод\n[23, 27), D = τ',(25,.75),xytext=(22.2,1.28),
                arrowprops={'arrowstyle':'->','color':'#68758a'},fontsize=10,va='bottom')
    ax.set(xlim=(0,30),ylim=(-1.4,1.9),yticks=[],xticks=edges,xlabel='Умовний час; τ = 4, G = 6, A = 8')
    ax.spines[['top','left','right']].set_visible(False)
    ax.legend(handles=[Patch(facecolor=colors[1],label='Зайнято'),Patch(facecolor=colors[0],label='Вільно')],
              loc='lower right',ncol=2,frameon=False,fontsize=10)
    ax.set_title('Рекурсивна опора виключає потенційний пропуск',loc='left',weight='bold',fontsize=14,pad=18)
    bx=fig.add_subplot(grid[1,0]);labels=['Пара B + D','Попередня H.3','Кінець зайнятості','Рекурсивна R.3','Точний максимум*']
    values=[1,1,1,0,0];bx.barh(labels[::-1],values[::-1],color=['#0099ac','#0099ac','#b7c1d1','#b7c1d1','#b7c1d1'])
    bx.set(xlim=(-.03,1.22),xticks=[0,1],xlabel='Верхня межа / точний максимум кількості пропусків')
    for i,v in enumerate(values[::-1]):bx.text(v+.03,i,str(v),va='center',weight='bold')
    bx.spines[['top','right','left']].set_visible(False);bx.tick_params(axis='y',length=0)
    cx=fig.add_subplot(grid[1,1]);cx.axis('off')
    cx.text(0,1,'Пояснення різниці',weight='bold',fontsize=12,va='top',color='#25375d')
    cx.text(0,.81,'Без нового скидання: 22 − 6 = 16 > A.\nЗ новим скиданням: 22 − 16 = 6 ≤ A.\nДовга пауза перед ціллю неможлива.',fontsize=11,va='top',linespacing=1.7)
    cx.text(0,.31,'Побудований приклад, не фізичний дослід.\n* Усі допустимі цілочислові паузи.\nНа восьми комірках Мельбурна R.3 = H.3.',fontsize=10,va='top',color='#53627a',linespacing=1.65)
    for suffix in ('png','svg'):fig.savefig(DOCS/'figures'/('phase3-analytic-reset.'+suffix),dpi=200)
    plt.close(fig)
    table='\n'.join('| '+name+' | '+' | '.join(str(row['counts'][n]) for n in NAMES)+' |' for name,row in result['cells'].items())
    report=f'''# Перевірка аналітичного кандидата на внесок

25.10.2026. Фаза 3. [План до запуску](phase3-analytic-contribution-plan.json), [метод і доказ](phase3-analytic-method.md), [аналоги](phase3-analytic-sources.md), [коротка постановка для керівника](phase3-supervisor-brief.md).

**Отримано конкретне посилення верхньої межі пропусків.** Опора переноситься на кінець гарантовано поміченої зайнятості; додано послідовне встановлення таких спостережень за віком показів. Це аналітична перевірка класу розкладів на заданій історії. Новий кращий планувальник або підтверджена світова новизна з цього не випливають.

## Незалежна перевірка

Перебрано {finite['grid']['cases']} випадків із п'ятьма інтервалами тривалістю 1,2,3, двома початковими станами, двома стартами і трьома наборами параметрів. Динамічна програма розглядає кожну дозволену цілочислову паузу, а не тільки C3: {finite['grid']['reachable_states']} станів і {finite['grid']['transitions_examined']} переходів. У кожному випадку перевірено максимум пропусків, порядок чотирьох меж і незалежний підрахунок за знайденим розкладом. Суперечностей не знайдено.

У цій сітці поліпшення через кінець інтервалу є у {finite['grid']['end_strict_cases']} випадках; окремого рекурсивного поліпшення немає. Строгість саме рекурсивного кроку показує окремий довший побудований приклад: межі 1,1,1,0 і точний максимум 0. Також наведено приклад, де нова межа 2, а точний максимум лише 1: додатний лічильник не є доказом досяжності. Перевірено ще 200 зафіксовано випадкових шестисегментних прикладів із довільним стартом, зокрема застосовність межі повного вікна до пізнішого старту.

Цілочисловий перебір доповнює письмовий доказ для дійсних часових моментів, а не замінює його. Це не перевірка доказу у формальній системі на кшталт Lean/Coq.

![Побудований приклад рекурсивної опори](figures/phase3-analytic-reset.png)

## Незмінені дані та параметри

Використано тільки вже відомі навчальні й перевірочні групи, τ=60 с, G=75 с, A=900 с. Нових правил не налаштовували. Нижче - кількість окремих записаних епізодів, без множення на початкові зсуви. Критерій від доби включає вікна від семи діб; ці рядки не незалежні.

| Комірка | Цільові епізоди | Пара B+D | Попередня H.3 | Кінець інтервалу | Рекурсивна R.3 |
|---|---:|---:|---:|---:|---:|
{table}

Старі лічильники відтворено точно для кожного паркомісця. **На всіх восьми комірках R.3 дорівнює H.3: додаткового емпіричного зменшення немає.** Порівняно з грубою парною межею врахування історії вже давало зменшення; саме новий рекурсивний крок на цих даних нічого додатково не виключив. [Машинні числа](phase3-analytic-counts.csv).

У двох основних перевірочних групах U_R=0: за припущень теореми це підтверджує покриття цільових епізодів для всього класу й довільного початку всередині заданих вікон. На інших рядках додатні межі не гарантують пропусків. Попередній фактичний M60 C3 на налаштовувальних 128 місцях у вікнах від доби збережено; новий результат його не скасовує.

## Що можна стверджувати зараз

Є відтворюваний авторський аналітичний результат із припущеннями, доведенням, строгими прикладами та межами застосування. Відомі загальні ідеї адаптивного планування, мінімальних тривалостей і формальної перевірки відокремлено від конкретного лічильника. Точну достатність цього внеску для магістерської належить обговорити з керівником; не можна підмінити її кількістю тестів.

M60 стосується свіжого виміру всередині епізоду, а F/O - помилкового стану карти. Фізична точність сенсора, енергія та перенесення на майбутню парковку не перевірялися цим аудитом. [Офіційні дані](https://data.melbourne.vic.gov.au/explore/dataset/on-street-car-parking-sensor-data-2019/information/) є сенсорними записами, а не незалежною розміткою реальних автомобілів.

Основний Google-документ і презентації не змінювалися. Остаточні 867 місць не оцінювалися. Фаза 4 залишається закритою до фіксації остаточної заяви про внесок, обґрунтування метрик і повного протоколу. [Окремий журнал технічної перевірки](phase3-analytic-verification.json) зберігає результати тестів і контрольних сум; попередні журнали не переписуються.
'''
    (DOCS/'phase3-analytic-report.md').write_text(report,encoding='utf-8')
    sources=read(WORK/'sources/download-receipt.json');sources['S16-Hung-Giang-1996']=read(WORK/'sources/S16-download-receipt.json')
    scopes={
      'S14-Furia-Rossi-2010':{'read':'Abstract, introduction, section2.1, section3.1 definitions11-14, theorem15 statement and proof opening, section4 overview, proposition26 and section4.2 algorithm/incompleteness, sections5.2-5.3',
          'not_claimed':'Entire43-page proof and all examples independently checked; numerical reproduction',
          'version_note':'arXiv v2 stamp2010-04-06 and journal2010; PDF generated header2021 is not used as publication year'},
      'S15-Mehrabian-2023':{'read':'Abstract/introduction; section4.1; section5.1 signal/sampling assumptions; section5.4 guarantee scope; section6.4 opening measurement-error sources',
          'not_claimed':'Full18-page technical review, independent proof of every TTL rule, or reproduction of hardware experiment'},
      'S16-Hung-Giang-1996':{'read':'Abstract/introduction; section3 regular-grid semantics, definition1, theorem1 and its proof, corollary1, theorem2 and verification explanation, PDF pages5-8',
          'not_claimed':'Full20-page review of limit/digitization results or Biphase Mark case study',
          'version_note':'Author site describes technical report50 from1995 published as LNCS1135 pages188-207 in1996'}}
    for name,item in sources.items():item.update(scopes[name])
    write_json(DOCS/'phase3-analytic-source-evidence.json',{'created_on':'2026-10-25','sources':sources,
      'search_queries':['sampling runtime verification missed events','sampling invariance non-Berkeley temporal logic',
         'state dependent sampling minimum duration event detection','sampling event duration deterministic missed events',
         'Furia Rossi sampling invariance adaptive','Van Hung Giang sampling1996 duration calculus'],
      'search_not_exhaustive':True,'S11_abstract_only_status_retained':True,
      'claim':'Own derived R.3 count; exact equality not found in the explicitly read formulas; not proof of world originality'})
    print('Analytical report, CSV, primary-source evidence, PNG/SVG written')


if __name__=='__main__':main()
