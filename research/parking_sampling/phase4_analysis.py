"""Reported metrics and paired confidence intervals for the held-out cohort."""
import numpy as np


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
