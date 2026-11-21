"""Inspectable policy tables; runtime decisions need no unsampled source state."""
from dataclasses import dataclass
import itertools
from pathlib import Path
import numpy as np
from simulation import ACTIONS,BASE_ACTIONS
from markov_baseline import solve_occupation_lp

@dataclass
class Policy:
    name:str
    family:str
    kind:int
    delays:np.ndarray
    lookup:np.ndarray
    fallback:np.ndarray
    use_time:bool=True
    use_run:bool=True
    parameters:dict|None=None

def constant_policy(free,occupied=None):
    occupied=free if occupied is None else occupied
    return Policy(f'fixed_{free}' if free==occupied else f'state_{free}_{occupied}',
      'fixed' if free==occupied else 'state',0,np.array([free,occupied],np.int64),np.full(48,5,np.int64),np.zeros(48,np.int64),False,False,
      {'free_seconds':int(free),'occupied_seconds':int(occupied)})

def risk_policy(name,family,model,free_cap,occupied_cap,miss_cap,*,normalize_misses=False,duration_profile=True):
    lookup=np.full(48,5,np.int64);fallback=np.ones(48,np.int64)
    caps=np.array([10.,3.,1.,.5,.25])*miss_cap
    for ctx in range(48):
        for k,d in enumerate(ACTIONS):
            if model['n'][ctx,k]<50 or model['pf'][ctx,k]>free_cap or model['po'][ctx,k]>occupied_cap:continue
            risks=model['pm'][ctx,k]/d if normalize_misses else model['pm'][ctx,k]
            feasible=np.all(risks<=caps) if duration_profile else risks[0]<=caps[0]
            if feasible:lookup[ctx]=d;fallback[ctx]=0
    return Policy(name,family,1,np.array([5,5],np.int64),lookup,fallback,bool(model['use_time']),bool(model['use_run']),
      {'free_cap':free_cap,'occupied_cap':occupied_cap,'miss_base_cap':miss_cap,
       'miss_profile_multipliers':[10,3,1,.5,.25],'normalize_misses':normalize_misses,'duration_profile':duration_profile})

def legacy_policy(model,free_cap,miss_cap):
    lookup=np.full(48,5,np.int64);fallback=np.ones(48,np.int64)
    for ctx in range(48):
        for k,d in enumerate(ACTIONS):
            if model['n'][ctx,k]>=50 and model['pf'][ctx,k]<=free_cap and model['pm'][ctx,k]<=miss_cap:
                lookup[ctx]=d;fallback[ctx]=0
    return Policy(f'C0_{free_cap}_{miss_cap}','C0',1,np.array([5,5],np.int64),lookup,fallback,True,True,
      {'free_cap':free_cap,'miss_cap':miss_cap,'training':'archived original pilot table; historical control only'})

def policy_grid(models,config,legacy_model):
    result=[]
    for d in BASE_ACTIONS:result.append(constant_policy(int(d)))
    for free,occupied in itertools.product(BASE_ACTIONS,repeat=2):
        if free!=occupied:result.append(constant_policy(int(free),int(occupied)))
    for family,model_name,normal,profile in [('C1','full',False,True),('C2','full',True,True),
          ('C2_no_duration','full',True,False),('C2_no_time','without_time',True,True),('C2_no_run','without_run',True,True)]:
        miss_grid=config['raw_miss_caps'] if not normal else config['rate_miss_caps_per_second']
        for f,o,m in itertools.product(config['error_fraction_caps'],config['error_fraction_caps'],miss_grid):
            result.append(risk_policy(f'{family}_{f}_{o}_{m}',family,models[model_name],f,o,m,normalize_misses=normal,duration_profile=profile))
    for f,m in itertools.product(config['legacy_free_caps'],config['legacy_miss_caps']):
        result.append(legacy_policy(legacy_model,f,m))
    for budget in config['s2_budgets_samples_per_bay_day']:
        result.append(Policy(f'S2_{budget}','S2',2,np.array([5,5],np.int64),np.full(48,5,np.int64),np.zeros(48,np.int64),False,False,{'budget':budget}))
    return result

def matrix_for_bay(counts,global_counts,pseudo=50):
    global_matrix=(global_counts+.5)/(global_counts.sum(axis=1)[:,None]+1)
    return (counts+pseudo*global_matrix)/(counts.sum(axis=1)[:,None]+pseudo)

def s2_cdfs(training_bays,counts,target_bays,budget):
    by_id={int(b):i for i,b in enumerate(training_bays)};global_counts=counts.sum(axis=0)
    cdfs=np.empty((len(target_bays),2,len(BASE_ACTIONS)));notes=[]
    for j,bay in enumerate(target_bays):
        local=counts[by_id[int(bay)]] if int(bay) in by_id else np.zeros((2,2))
        p=matrix_for_bay(local,global_counts)
        solution=solve_occupation_lp(p,BASE_ACTIONS//5,mean_interval_min=(86400/budget)/5)
        cdfs[j]=np.cumsum(np.asarray(solution['probabilities']),axis=1);cdfs[j,:,-1]=1.
        notes.append({'bay':int(bay),'transition_matrix':p.tolist(),'frequency_per_day_model':solution['sampling_frequency']*86400/5,
          'age_seconds_per_decision_model':solution['average_age_per_decision']*5,'flow_residual':solution['max_flow_residual']})
    return cdfs,notes
