"""Strong simple controls and explicitly labeled expected-budget comparisons."""
from dataclasses import dataclass
from itertools import product
import numpy as np
from scipy.optimize import linprog
from simulation import AGES, BASE_ACTIONS
from policies import constant_policy, Policy


@dataclass
class Definition:
    policy: Policy
    groups: tuple


def definitions():
    result=[]
    for free,occupied in product(BASE_ACTIONS,repeat=2):
        p=constant_policy(int(free),int(occupied))
        result.append(Definition(p,('fixed','state','pooled') if free==occupied else ('state','pooled')))
    for fe,fa,fl,oe,ol in product((30,45,60),(300,900),(60,75,90),(30,45,60),(45,60)):
        if fe>fl or oe>ol:continue
        table=np.empty(48,np.int64)
        for state in range(2):
            early,edge,late=(fe,fa,fl) if state==0 else (oe,300,ol)
            for tb in range(4):
                for ab,age in enumerate((0,*AGES)):
                    table[(state*4+tb)*6+ab]=early if age<edge else late
        name=f'two_stage_F{fe}_{fa}_{fl}_O{oe}_300_{ol}'
        p=Policy(name,'two_stage',1,np.array([60,60],np.int64),table,np.zeros(48,np.int64),False,True,
                 {'free':[fe,fa,fl],'occupied':[oe,300,ol]})
        result.append(Definition(p,('two_stage','pooled')))
    for budget in (960,1200,1320,1440,1680,1920,2400,2880):
        p=Policy(f'S2_{budget}','S2',2,np.array([60,60],np.int64),np.full(48,60,np.int64),np.zeros(48,np.int64),
                 False,False,{'budget':budget})
        result.append(Definition(p,('S2','pooled')))
    for cap,label in ((75,'C3'),(72,'C4')):
        table=np.r_[np.tile([30,30,45,cap,cap,cap],4),np.tile([30,30,60,60,60,60],4)].astype(np.int64)
        p=Policy(label,label,1,np.array([60,60],np.int64),table,np.zeros(48,np.int64),False,True,{'free_cap':cap})
        result.append(Definition(p,()))
    return result


def choose_mixture(control_raw, target_raw, exact_resource=False):
    """Fit minimax F/O ratio with one weight vector across cells.

    control_raw: [cell, policy,17]; target_raw: [cell,17]. For hindsight
    envelopes caller supplies one cell and exact_resource=True explicitly.
    """
    controls=np.asarray(control_raw,dtype=float);target=np.asarray(target_raw,dtype=float)
    if controls.ndim!=3 or target.shape!=(controls.shape[0],17) or controls.shape[2]!=17:
        raise ValueError('Expected [cell,policy,17] and [cell,17]')
    if controls.shape[1]==0 or np.any(controls<0) or np.any(target<0) or not np.all(np.isfinite(controls)) or not np.all(np.isfinite(target)):
        raise ValueError('Finite nonnegative counters and at least one control required')
    if np.any(target[:,[0,1,2,3]]<=0):raise ValueError('Positive exposure, resource and target errors required')
    if not np.allclose(controls[:,:,0],target[:,None,0],rtol=0,atol=0):
        raise ValueError('Unequal exposure; cannot mix raw metrics')
    if exact_resource and len(target)!=1:raise ValueError('Exact hindsight envelope expects one cell')
    k=controls.shape[1]
    inequalities=[];limits=[];equalities=[np.r_[np.ones(k),0.]];rhs=[1.]
    for cell in range(len(target)):
        resource=np.r_[controls[cell,:,1]/target[cell,1],0.]
        if exact_resource:equalities.append(resource);rhs.append(1.)
        else:inequalities.append(resource);limits.append(1.)
        for index in (2,3):
            inequalities.append(np.r_[controls[cell,:,index]/target[cell,index],-1.]);limits.append(0.)
    objective=np.r_[np.zeros(k),1.]
    fit=linprog(objective,A_ub=np.array(inequalities),b_ub=np.array(limits),
                A_eq=np.array(equalities),b_eq=np.array(rhs),bounds=(0,None),method='highs')
    if not fit.success:raise ValueError('Mixture LP failed: '+fit.message)
    weights=fit.x[:k].copy()
    weights[weights<1e-12]=0
    weights/=weights.sum()
    expected=np.einsum('p,cpj->cj',weights,controls)
    ratios=expected[:,1]/target[:,1]
    if exact_resource:
        if not np.allclose(ratios,1,rtol=0,atol=1e-7):raise ArithmeticError('Budget equality residual')
    elif np.max(ratios)>1+1e-7:raise ArithmeticError('Budget cap residual')
    value=float(np.max(expected[:,2:4]/target[:,2:4]))
    if abs(value-fit.fun)>1e-6:raise ArithmeticError('Objective residual')
    return {'weights':weights,'max_error_ratio':value,'resource_ratios':ratios,
            'expected_raw':expected,'exact_expected_budget':bool(exact_resource)}


def bootstrap_comparison(candidate,control,draws=2000,seed=20261025):
    """Pointwise descriptive paired BayId intervals, including mixture expectations."""
    a=np.asarray(candidate,dtype=float);b=np.asarray(control,dtype=float)
    if a.ndim!=2 or a.shape!=b.shape or a.shape[1]!=17 or not np.allclose(a[:,0],b[:,0]):
        raise ValueError('Aligned whole-bay counters with equal exposure required')
    rng=np.random.default_rng(seed)
    weights=rng.multinomial(len(a),np.full(len(a),1/len(a)),size=draws)
    aa=weights@a;bb=weights@b;days=aa[:,0]/86400
    values={'resource_difference_percent':100*(aa[:,1]/bb[:,1]-1),
      'F_difference_seconds_per_day':(aa[:,2]-bb[:,2])/days,
      'O_difference_seconds_per_day':(aa[:,3]-bb[:,3])/days}
    return {key:np.quantile(value,[.025,.975]).tolist() for key,value in values.items()}


def metrics(raw):
    r=np.asarray(raw,dtype=float);days=r[0]/86400
    return {'samples_per_bay_day':float(r[1]/days),'F_seconds_per_bay_day':float(r[2]/days),
            'O_seconds_per_bay_day':float(r[3]/days),'M60_expected_count':float(r[14]),
            'eligible60_episode_phases':float(r[9])}
