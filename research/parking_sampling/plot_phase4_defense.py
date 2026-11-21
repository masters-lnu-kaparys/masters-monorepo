"""Supplementary presentation figures. Frozen policies/results are never changed."""
import hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from prepare_data import DOCS,sha256
from run_phase3 import write_json
from assess_analytic_contribution import read
from phase4_pipeline import WORK,LOCK,CATALOG,frozen_lock,load_final_bundle
from calibrated_schedule import CalibratedSchedule
from simulation import reference_simulate


def save(fig,name):
    for ext in ('png','svg'):fig.savefig(DOCS/f'figures/{name}.{ext}',dpi=200)
    plt.close(fig)


def main():
    lock=frozen_lock();results=read(WORK/'results.json');catalog=read(CATALOG)
    rows=results['cohorts']['primary_7_days']['policies'];navy='#25375d';cyan='#0099ac';orange='#d88843'
    fig,axes=plt.subplots(1,2,figsize=(12,6),layout='constrained')
    for ax,key,title in zip(axes,('F_seconds_per_bay_day','O_seconds_per_bay_day'),
      ('Помилковий показ «вільно»','Помилковий показ «зайнято»')):
        for name,row in rows.items():
            m=row['primary_metrics'];reference=name.startswith('fixed_');author=name=='author'
            ax.scatter(m['samples_per_bay_day'],m[key],s=120 if author else 50,
              c=orange if author else navy if reference else cyan,marker='*' if author else 's' if reference else 'o',
              alpha=1 if author or reference else .65,zorder=4 if author else 2)
        for name,text,offset in (('author','Авторський метод',(-8,16)),('fixed_60','Щохвилини',(10,-18)),
          ('fixed_5','Кожні 5 с',(-65,12)),('fixed_300','Кожні 300 с',(8,-18))):
            m=rows[name]['primary_metrics'];ax.annotate(text,(m['samples_per_bay_day'],m[key]),xytext=offset,
              textcoords='offset points',fontsize=9,color=orange if name=='author' else navy)
        ax.set_xscale('log');ax.set(title=title,xlabel='Вимірювань на місце-добу, логарифмічна шкала',ylabel='Секунд помилки на місце-добу')
        ax.spines[['top','right']].set_visible(False);ax.margins(x=.18,y=.12);ax.grid(alpha=.15)
    fig.suptitle('Витрати й помилки: всі 17 зафіксованих політик на 867 місцях',weight='bold',fontsize=13)
    fig.supxlabel('Основні вікна від 7 діб; реалізовані таблиці, зерно 20261025. Кожна точка - обчислений результат, не інтерполяція.\nКращий компроміс розташований нижче й лівіше. Пропуски вільних епізодів показуються окремо.',fontsize=9)
    axes[0].legend(handles=[Line2D([],[],color=orange,marker='*',ls='',label='Авторський метод'),
      Line2D([],[],color=navy,marker='s',ls='',label='Постійні інтервали'),
      Line2D([],[],color=cyan,marker='o',ls='',label='Інші зафіксовані політики')],fontsize=8,loc='upper right')
    save(fig,'phase4-resource-errors')
    d=load_final_bundle(lock,primary_only=True)
    w=min(range(len(d.starts)),key=lambda j:hashlib.sha256(f'phase4-illustration:{d.window_ids[j]}'.encode()).hexdigest())
    initial,_=d.phases(10);start=int(d.starts[w]+initial[w,0]);bi=int(d.bay_indexes[w]);bay=int(d.bays[bi]);lo,hi=d.offsets[w:w+2]
    ends=d.ends[lo:hi];states=d.states[lo:hi];weights=catalog['policies']['author']['weights']
    payload={'schema_version':1,'allocation_seed':20261025,'observed_run_edges_seconds':[60,300,900,3600,14400],
      'component_weights':weights,'components':{}}
    for name in weights:
        m=np.load(WORK/'models'/(name+'.npz'));table=m['tables'][bi].tolist()
        payload['components'][name]={'bay_tables':{str(bay):table},'pooled_fallback':table}
    policy=CalibratedSchedule(payload)
    ar,ah,ad=reference_simulate(ends,states,start,lambda o:(policy.next_pause(bay,o),False))
    fr,fh,fd=reference_simulate(ends,states,start,lambda o:(60,False))
    changes=ends[(ends>=start+300)&(ends<ends[-1]-600)]
    center=int(changes[0]) if len(changes) else start+300
    left=max(start,center-120);right=min(int(ends[-1]),center+600);grid=np.arange(left,right,dtype=np.int64)
    truth=states[np.searchsorted(ends,grid,side='right')]
    fig,axes=plt.subplots(3,1,figsize=(12,6),sharex=True,layout='constrained')
    axes[0].step(grid-center,truth,where='post',color=navy,lw=2)
    axes[0].set_title('Записаний сенсорний стан',loc='left',fontsize=11,color=navy)
    for ax,decisions,title,color in ((axes[1],fd,'Показ карти за вимірювання щохвилини',navy),
      (axes[2],ad,'Показ карти за авторським розкладом',cyan)):
        times=np.array([x[0] for x in decisions]);ss=np.array([x[1] for x in decisions]);held=ss[np.searchsorted(times,grid,side='right')-1]
        ax.step(grid-center,held,where='post',color=color,lw=2)
        ax.fill_between(grid-center,-.15,1.15,where=held!=truth,step='post',color=orange,alpha=.25)
        mask=(times>=left)&(times<right);ax.scatter(times[mask]-center,ss[mask],s=20,color=color,zorder=4)
        ax.set_title(title,loc='left',fontsize=11,color=color)
    for ax in axes:
        ax.set(yticks=[0,1],yticklabels=['Вільно','Зайнято'],ylim=(-.25,1.25));ax.spines[['top','right']].set_visible(False)
    axes[-1].set_xlabel('Час від обраної зміни стану, с' if len(changes) else 'Час від центру фрагмента, с')
    fig.suptitle(f'Один часовий приклад: паркомісце {bay}',weight='bold',fontsize=13)
    fig.supxlabel('Точки - виконані вимірювання. Помаранчеві ділянки - неправильний показ карти.\nВікно обрано за хешем; фрагмент біля першої зміни після 5 хв спостережень. Приклад не добирався за виграшем методу.',fontsize=9)
    save(fig,'phase4-timeline')
    write_json(DOCS/'phase4-supplementary-figures.json',{'created_on':'2026-10-25','entry_lock_sha256':sha256(LOCK),
      'frozen_results_sha256':sha256(WORK/'results.json'),'figure_code_sha256':sha256(__file__),
      'resource_plot':'All17 prelocked policies; primary allocation, primary windows. No fitted curve or new performance point.',
      'timeline':{'bay':bay,'window_id':d.window_ids[w],'selection':'minimum SHA256(phase4-illustration:{window_id}); first change after300seconds if available',
        'initial_phase':0,'left_local_seconds':left,'right_local_seconds':right,'author_whole_window_raw':ar.tolist(),'fixed60_whole_window_raw':fr.tolist(),
        'is_illustration_not_independent_effect_estimate':True}})
    print({'supplementary_figures':2,'illustration_bay':bay,'no_method_or_analysis_changes':True},flush=True)


if __name__=='__main__':main()
