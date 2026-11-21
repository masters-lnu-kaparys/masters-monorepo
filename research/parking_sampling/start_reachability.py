"""Exact individual-episode coverage for a finite free-run prefix and plateau.

Offline source queries never enter the runtime controller. Each positive answer
has its own initialization; the count is NOT a simultaneous worst-case count.
"""
from bisect import bisect_right
from dataclasses import dataclass
import numpy as np
from episode_certificate import _validated_trace


@dataclass(frozen=True)
class FreeProfile:
    prefix_pauses:tuple
    plateau:int
    tau:int

    def __post_init__(self):
        if type(self.plateau)!=int or type(self.tau)!=int or not 0<self.tau<=self.plateau:
            raise ValueError('Positive integer tau<=plateau required')
        if any(type(d)!=int or not 0<d<=self.tau for d in self.prefix_pauses):
            raise ValueError('Every prefix pause must be a positive integer<=tau')

    @property
    def ages(self):return (0,*np.cumsum(self.prefix_pauses,dtype=np.int64).tolist())

    def free_pause(self,age):
        ages=self.ages
        # Only these ages occur within an uninterrupted observed free run.
        if age>=ages[-1]:return self.plateau
        try:return self.prefix_pauses[ages.index(age)]
        except ValueError:raise ValueError('Unreachable observed free age')


def c3_profile(cap):
    pauses=[];age=0
    while age<900:
        d=30 if age<300 else 45;pauses.append(d);age+=d
    return FreeProfile(tuple(pauses),int(cap),60)


def validate_trace(ends,states,start,profile):
    if type(start) not in (int,np.int64,np.int32):raise ValueError('Integer source-window start required')
    return _validated_trace(ends,states,start,profile.tau,profile.plateau-profile.tau)


def late_free_witness(ends,states,start,t,profile,stats=None):
    """Return a complete observed-free run ending at t, or None.

    A prefix ends at one of t,t-G,t-2G,... . Once one of those required free
    samples is occupied, no still earlier entry can reach t on this plateau.
    """
    ages=profile.ages;length=ages[-1];u=int(t);G=profile.plateau
    stats={} if stats is None else stats
    stats.setdefault('plateau_nodes',0);stats.setdefault('source_queries',0);stats.setdefault('prefix_attempts',0)
    def is_free(time):
        stats['source_queries']+=1
        return int(states[bisect_right(ends,time)])==0
    while u-length>=start:
        stats['plateau_nodes']+=1
        if not is_free(u):return None
        stats['prefix_attempts']+=1;root=u-length
        if all(is_free(root+age) for age in ages[:-1]):
            samples=[root+age for age in ages]
            samples.extend(range(u+G,t+1,G))
            return {'initial_start':int(root),'last_free_sample':int(t),'plateau_entry':int(u),
                    'sample_times_through_last_free':list(map(int,samples)),'next_sample':int(t+G)}
        u-=G
    return None


def episode_reachability(ends,states,start,profile):
    ends,states=validate_trace(ends,states,start,profile)
    edges=ends.tolist();source=states.tolist();first=bisect_right(edges,start)
    stats={'candidate_last_samples':0,'plateau_nodes':0,'source_queries':0,'prefix_attempts':0}
    eligible=0;generic=0;rows=[]
    for i in range(first+1,len(edges)-1):
        if source[i]!=0:continue
        a=edges[i-1];b=edges[i]
        if b-a<profile.tau:continue
        eligible+=1
        if i==first+1:continue
        p=edges[i-2]
        if b-p>=profile.plateau:continue
        generic+=1;witness=None
        for t in range(max(start,b-profile.plateau),p):
            stats['candidate_last_samples']+=1
            witness=late_free_witness(edges,source,start,t,profile,stats)
            if witness is not None:break
        rows.append({'source_index':i,'a':a,'b':b,'preceding_busy_start':p,'attainable':witness is not None,
                     'witness':witness})
    return {'eligible':eligible,'generic_pair_bound':generic,'attainable_episodes':sum(row['attainable'] for row in rows),
            'risky_episodes':rows,'operations':stats}


def forward_samples(ends,states,start,profile,occupied_pause=None):
    """Independent simple forward recurrence; supports fractional starts for QA."""
    occupied_pause=profile.tau if occupied_pause is None else occupied_pause
    if type(occupied_pause)!=int or not 0<occupied_pause<=profile.tau:raise ValueError('Invalid occupied pause')
    t=start;held=-1;run=start;samples=[]
    while t<ends[-1]:
        state=states[bisect_right(ends,t)]
        if state!=held:run=t
        held=state;samples.append(t)
        pause=occupied_pause if state else profile.free_pause(t-run)
        t+=pause
    return samples


def forward_missed_indices(ends,states,start,profile):
    samples=forward_samples(ends,states,start,profile);first=bisect_right(ends,start)
    return {i for i in range(first+1,len(ends)-1) if states[i]==0 and ends[i]-ends[i-1]>=profile.tau
            and not any(ends[i-1]<=t<ends[i] for t in samples)}
