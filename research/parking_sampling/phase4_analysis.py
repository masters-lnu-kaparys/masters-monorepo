"""Predeclared paired Bay-level analysis, with no final winner selection."""
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from prepare_data import DOCS,sha256
from run_phase3 import write_json
from assess_analytic_contribution import read
from phase4_pipeline import WORK,LOCK,CATALOG,COHORT,frozen_lock,aggregate_components


def metric_summary(raw,hist=None):
    r=np.asarray(raw,dtype=float);days=r[0]/86400
    if days<=0:raise ValueError('Positive exposure required')
    result={'samples_per_bay_day':float(r[1]/days),'F_seconds_per_bay_day':float(r[2]/days),
      'O_seconds_per_bay_day':float(r[3]/days),'vacancies':{}}
    for i,t in enumerate((0,30,60,120,300)):
        result['vacancies'][str(t)]={'eligible':float(r[7+i]),'missed':float(r[12+i]),
          'missed_fraction':float(r[12+i]/r[7+i]) if r[7+i] else None}
    if hist is not None:
        h=np.asarray(hist,dtype=float);cdf=np.cumsum(h)
        result['detected_vacancy_delay_seconds']={str(q):int(np.searchsorted(cdf,q*cdf[-1])) if cdf[-1]>0 else None for q in (.5,.95)}
    return result


def paired_intervals(candidate,reference,reps=5000,seed=20261018):
    a=np.asarray(candidate,dtype=float);b=np.asarray(reference,dtype=float)
    if a.shape!=b.shape or a.ndim!=2 or a.shape[1]!=17 or not len(a):raise ValueError('Aligned Bay counters required')
    if not np.array_equal(a[:,0],b[:,0]) or np.any(b[:,0]<=0) or b[:,1].sum()<=0:raise ValueError('Matched positive exposure required')
    rng=np.random.default_rng(seed);draws=np.empty((reps,3))
    for start in range(0,reps,100):
        end=min(start+100,reps);ix=rng.integers(0,len(a),size=(end-start,len(a)))
        aa=a[ix].sum(axis=1);bb=b[ix].sum(axis=1);days=bb[:,0]/86400
        draws[start:end,0]=100*(1-aa[:,1]/bb[:,1]);draws[start:end,1:]=(aa[:,2:4]-bb[:,2:4])/days[:,None]
    labels=('calls_reduction_percent','F_difference_seconds_per_bay_day','O_difference_seconds_per_bay_day')
    return {'unit':'whole BayId, all windows and initialization phases retained together','repetitions':reps,'seed':seed,
      'pointwise95':dict(zip(labels,np.quantile(draws,[.025,.975],axis=0).T.tolist())),
      'bonferroni_joint3_approx95':dict(zip(labels,np.quantile(draws,[.05/6,1-.05/6],axis=0).T.tolist())),
      'limitations':'Approximate percentile intervals conditional on frozen training and model selection; cross-Bay spatial dependence is not modeled. Bonferroni does not repair invalid marginal coverage.'}


def success_gate(candidate,reference,intervals):
    a=np.asarray(candidate);b=np.asarray(reference);reduction=100*(1-a[1]/b[1])
    j=intervals['bonferroni_joint3_approx95']
    return {'point_estimate_display_success':bool(reduction>=10 and a[2]<=b[2] and a[3]<=b[3]),
      'joint3_interval_support':bool(j['calls_reduction_percent'][0]>0 and j['F_difference_seconds_per_bay_day'][1]<0 and j['O_difference_seconds_per_bay_day'][1]<0),
      'original_zero_M60_satisfied':bool(a[14]<=b[14]),'calls_reduction_percent':float(reduction)}


def summarize_bays(candidate,reference,training_bays,bays):
    days=reference[:,0]/86400;ar=candidate[:,1:4]/days[:,None];br=reference[:,1:4]/days[:,None]
    groups={};supported=np.isin(bays,training_bays)
    for name,mask in (('history_supported',supported),('no_history',~supported)):
        groups[name]={'bays':int(mask.sum()),'method':metric_summary(candidate[mask].sum(axis=0)) if mask.any() else None,
          'fixed60':metric_summary(reference[mask].sum(axis=0)) if mask.any() else None}
    return {'bays':len(bays),'macro_method_NFO':ar.mean(axis=0).tolist(),'macro_fixed60_NFO':br.mean(axis=0).tolist(),
      'more_calls_bays':int(np.sum(ar[:,0]>br[:,0])),'worse_F_bays':int(np.sum(ar[:,1]>br[:,1])),
      'worse_O_bays':int(np.sum(ar[:,2]>br[:,2])),'history_supported_bays':int(np.isin(bays,training_bays).sum()),
      'no_history_bays':int((~supported).sum()),'history_groups':groups}


def main():
    frozen_lock();catalog=read(CATALOG);cohort=read(COHORT);bays=np.array(cohort['bay_ids'])
    training=np.load(WORK/'local-training-statistics.npz');out={};csvrows=[]
    for label in ('primary_7_days','sensitivity_1_day'):
        folder=WORK/label;names=list(catalog['components']);values=[];hists=[];receipts={}
        for name in names:
            p=folder/(name+'.npz');meta=read(p.with_suffix('.json'));assert sha256(p)==meta['arrays_sha256']
            a=np.load(p);np.testing.assert_array_equal(a['bays'],bays)
            values.append(a['by_bay_phase'].sum(axis=1));hists.append(a['histograms']);receipts[name]=meta['arrays_sha256']
        values=np.array(values);hists=np.array(hists);reference=values[names.index('fixed_60')];rh=hists[names.index('fixed_60')]
        assert np.all(values[:,:,0]==reference[:,0])
        policies={};contrasts={};arrays={}
        for key,policy in catalog['policies'].items():
            expected,eh,primary,ph,choices=aggregate_components(values,hists,bays,names,policy['weights'])
            arrays[key]=(expected,primary);er=expected.sum(axis=0);pr=primary.sum(axis=0)
            policies[key]={'weights':policy['weights'],'expected_raw':er.tolist(),'primary_raw':pr.tolist(),
              'expected_metrics':metric_summary(er,eh.sum(axis=0)),'primary_metrics':metric_summary(pr,ph.sum(axis=0)),
              'primary_allocation':choices,'bay_summary':summarize_bays(primary,reference,training['bays'],bays)}
            for allocation,raw,hist in (('primary',pr,ph),('expected',er,eh)):
                m=metric_summary(raw,hist.sum(axis=0));csvrows.append([label,key,allocation,m['samples_per_bay_day'],m['F_seconds_per_bay_day'],m['O_seconds_per_bay_day'],raw[14],raw[9]])
        expected,primary=arrays['author'];ci=paired_intervals(primary,reference)
        seeds=[]
        for seed in range(20261025,20261035):
            _,_,by,hist,_=aggregate_components(values,hists,bays,names,catalog['policies']['author']['weights'],seed)
            r=by.sum(axis=0);seeds.append({'seed':seed,'raw':r.tolist(),'metrics':metric_summary(r,hist.sum(axis=0))})
        for key,(e,p) in arrays.items():
            if key=='author':continue
            contrasts[key]={'candidate_primary_minus_control_primary':paired_intervals(primary,p),
              'candidate_expected_minus_control_expected':paired_intervals(expected,e),
              'control_expected_budget_no_larger':bool(e[:,1].sum()<=expected[:,1].sum()+1e-6),
              'control_primary_budget_no_larger':bool(p[:,1].sum()<=primary[:,1].sum()),
              'expected_calls_ratio_control_over_author':float(e[:,1].sum()/expected[:,1].sum()),
              'primary_calls_ratio_control_over_author':float(p[:,1].sum()/primary[:,1].sum()),
              'no_multiple_comparison_adjustment_for_secondary_control_claims':True}
        out[label]={'policies':policies,'author_vs_fixed60_intervals':ci,
          'success':success_gate(primary.sum(axis=0),reference.sum(axis=0),ci),'author_all10_allocation_seeds':seeds,
          'contrasts':contrasts,'component_arrays_sha256':receipts}
        np.savez_compressed(folder/'policy-bay-counters.npz',names=np.array(list(arrays)),bays=bays,
          expected=np.stack([x[0] for x in arrays.values()]),primary=np.stack([x[1] for x in arrays.values()]))
    results={'created_on':'2026-10-25','entry_lock_sha256':sha256(LOCK),'training_receipt_sha256':sha256(WORK/'training-receipt.json'),
      'primary_candidate':'author','cohorts':out,'final_test_evaluated':True,'method_retuned':False,
      'primary_success':out['primary_7_days']['success'],'sensitivity_is_not_an_independent_replication':True}
    write_json(WORK/'results.json',results)
    write_json(DOCS/'phase4-display-results.json',results)
    with (DOCS/'phase4-display-results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['windows','policy','allocation','N_per_bay_day','F_seconds_per_bay_day','O_seconds_per_bay_day','M60_count','eligible60']);w.writerows(csvrows)
    render_report(results)
    print('Final analysis written; primary result: '+str(results['primary_success']),flush=True)


def render_report(result):
    rows=[];fig,axes=plt.subplots(1,3,figsize=(13,5),layout='constrained')
    labels=['Вікна від 7 діб','Вікна від доби']
    for i,(label,data) in enumerate(result['cohorts'].items()):
        a=data['policies']['author']['primary_metrics'];b=data['policies']['fixed_60']['primary_metrics'];v=a['vacancies']['60']
        red=100*(1-a['samples_per_bay_day']/b['samples_per_bay_day'])
        miss=f"{100*v['missed_fraction']:.3f}%" if v['missed_fraction'] is not None else 'немає даних'
        rows.append(f"| {labels[i]} | {a['samples_per_bay_day']:.1f} / {b['samples_per_bay_day']:.1f} | {red:.2f}% | {a['F_seconds_per_bay_day']:.1f} / {b['F_seconds_per_bay_day']:.1f} | {a['O_seconds_per_bay_day']:.1f} / {b['O_seconds_per_bay_day']:.1f} | {miss} |")
        j=data['author_vs_fixed60_intervals']['bonferroni_joint3_approx95']
        for ax,key,point in zip(axes,('calls_reduction_percent','F_difference_seconds_per_bay_day','O_difference_seconds_per_bay_day'),
          (red,a['F_seconds_per_bay_day']-b['F_seconds_per_bay_day'],a['O_seconds_per_bay_day']-b['O_seconds_per_bay_day'])):
            lo,hi=j[key];ax.errorbar(point,i,xerr=[[max(0,point-lo)],[max(0,hi-point)]],fmt='o',capsize=5,color='#0099ac')
            ax.annotate(f'{point:.2f}',(point,i),xytext=(0,-16),textcoords='offset points',ha='center')
    for ax,title in zip(axes,('Скорочення вимірювань, %','Зміна помилкового «вільно», с','Зміна помилкового «зайнято», с')):
        ax.axvline(0,color='#9ca8b7',ls='--');ax.set(yticks=(0,1),yticklabels=labels,ylim=(1.5,-.5),title=title)
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Незалежне відкладене оцінювання за зафіксованим протоколом',weight='bold')
    fig.supxlabel('867 місць. Основне зерно 20261025. Набори вікон перекриваються.\nІнтервали 98,333% для трьох основних показників; наближений парний bootstrap за місцями.',fontsize=9)
    for ext in ('png','svg'):fig.savefig(DOCS/f'figures/phase4-display-results.{ext}',dpi=200)
    plt.close(fig)
    gate=result['primary_success'];status='виконано' if gate['point_estimate_display_success'] else 'не виконано'
    joint='отримано' if gate['joint3_interval_support'] else 'не отримано'
    table='\n'.join(rows)
    report=f'''# Остаточне оцінювання розкладу вимірювань

Протокол [v0.2](phase4-display-protocol.md) і [фіксація до відкриття тесту](phase4-display-entry-lock.json). Числа та рішення не використовувалися для переналаштування методу.

Основний точковий критерій: **{status}**. Спільну інтервальну підтримку покращення трьох показників **{joint}**. Ці два рішення показано окремо; навіть позитивний результат не доводить світової першості або універсальної переваги.

| Відомі вікна | Виміри: метод / щохвилини | Скорочення | F: метод / щохвилини | O: метод / щохвилини | Вільні епізоди від хвилини без виміру |
|---|---:|---:|---:|---:|---:|
{table}

F/O - секунди на відому місце-добу. Обидва відбори використовують ті самі 867 місць, а їхні вікна перекриваються. M60 є наявністю нового виміру всередині вільного епізоду; він не дорівнює частці неправильних показів карти. Початковий протокол нульових пропусків збережено як окрему постановку.

![Основний результат і спільні інтервали](figures/phase4-display-results.png)

[Повні лічильники, контрольні зіставлення, всі десять зерен, пропуски за п'ятьма тривалостями й індивідуальні погіршення](phase4-display-results.json), [таблиця CSV](phase4-display-results.csv). Не обирати інше зерно чи конкурента за цими результатами. Ретроспективне вирівнювання бюджету не використовується для основного висновку.

Навчальна історія місць - січень-червень, оцінювання - жовтень-грудень 2019. Спільні оцінки та ваги заморожено до читання тестових станів. Контролер бачить власні виміри; історія між ними використовується лише симулятором. Повторний відбір цілих місць зберігає внутрішні часові залежності, але не моделює просторову залежність між сусідніми місцями. Інтервали наближені й умовні щодо навчання. Правила відбору [зафіксовано до оцінювання](phase4-display-cohort.json).

Джерела методу й статистичних рішень наведено у [протоколі](phase4-display-protocol.md). Це відтворення відкритої сенсорної історії; споживання батареї та фізична точність ультразвуку тут не вимірювалися.
'''
    (DOCS/'phase4-display-report.md').write_text(report,encoding='utf-8')
