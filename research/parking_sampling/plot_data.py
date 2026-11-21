"""Descriptive training-data figures only; never opens final-test interval data."""
from __future__ import annotations
import argparse
from datetime import datetime,timedelta
import json
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from prepare_data import ROOT,DOCS,START,quote,sha256

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workdir',type=Path,required=True)
    args=parser.parse_args()
    work=args.workdir.resolve()
    source=work/'prepared/train_development.parquet'
    dest=DOCS/'figures'
    dest.mkdir(exist_ok=True)
    con=duckdb.connect()
    con.execute("SET memory_limit='1GB'")
    con.execute('SET threads=2')
    con.execute(f'CREATE VIEW observations AS SELECT * FROM read_parquet({quote(source.as_posix())}) WHERE is_primary')
    bays,windows=con.execute('SELECT count(DISTINCT bay),count(DISTINCT window_id) FROM observations').fetchone()
    con.execute('''CREATE TABLE hourly AS
      SELECT hour_start,sum(least(end_local_seconds,hour_start+3600)-greatest(start_local_seconds,hour_start)) covered_seconds,
        sum((least(end_local_seconds,hour_start+3600)-greatest(start_local_seconds,hour_start))*state) occupied_seconds
      FROM observations,
        LATERAL generate_series((start_local_seconds//3600)*3600,((end_local_seconds-1)//3600)*3600,3600) h(hour_start)
      GROUP BY hour_start ORDER BY hour_start''')
    con.execute(f"COPY hourly TO {quote((work/'prepared/descriptive-training-hourly.csv').as_posix())} (HEADER,DELIMITER ',')")
    rows=con.execute('SELECT * FROM hourly ORDER BY hour_start').fetchall()
    occupancy=np.full((24,181),np.nan)
    coverage=np.full_like(occupancy,np.nan)
    for stamp,known,occupied in rows:
        day=(stamp-START)//86400;hour=(stamp%86400)//3600
        if 0<=day<181:
            occupancy[hour,day]=occupied/known if known else np.nan
            coverage[hour,day]=known/(bays*3600)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,constrained_layout=True)
    palette=plt.get_cmap('viridis').copy();palette.set_bad('#e1e5ea')
    for ax,values,title,label in zip(axes,[occupancy,coverage],['Зайнятість серед доступних спостережень','Частка доступного часу включених місць'],['Частка часу зайнятості','Частка покриття']):
        im=ax.imshow(values,origin='lower',aspect='auto',extent=(-.5,180.5,-.5,23.5),vmin=0,vmax=1,cmap=palette,interpolation='nearest')
        ax.set_title(title,loc='left',fontweight='bold',pad=10)
        ax.set_ylabel('Година доби');ax.set_yticks([0,6,12,18,23])
        fig.colorbar(im,ax=ax,label=label,pad=.02)
    starts=[0,31,59,90,120,151]
    axes[-1].set_xticks(starts,['Січень','Лютий','Березень','Квітень','Травень','Червень'])
    axes[-1].set_xlabel('2019 рік; сірий колір означає відсутність придатних даних')
    fig.suptitle(f'Навчальна історія: {bays} паркомісць, {windows} неперервних вікон',fontsize=15,fontweight='bold')
    fig.supxlabel('Дані: City of Melbourne, 2019 (S5). Обчислення автора. Вікна від 7 діб; остаточний тест не використано.',fontsize=9)
    outputs=[]
    for ext in ['png','svg']:
        path=dest/f'phase2-training-occupancy.{ext}';fig.savefig(path,dpi=180);outputs.append(path)
    plt.close(fig)
    durations=con.execute('''SELECT state,end_local_seconds-start_local_seconds duration FROM observations
      WHERE start_local_seconds>window_start AND end_local_seconds<window_end''').fetchnumpy()
    fig,ax=plt.subplots(figsize=(10,5.4),constrained_layout=True)
    counts={}
    for state,label,color in [(0,'Вільно','#008f9f'),(1,'Зайнято','#284775')]:
        values=np.sort(durations['duration'][durations['state']==state])
        counts[str(state)]=int(len(values))
        x,frequency=np.unique(values,return_counts=True)
        y=np.cumsum(frequency)/len(values)
        ax.step(x,y,where='post',linewidth=2,color=color,label=f'{label}: {len(values):,} епізодів'.replace(',',' '))
    ax.set_xscale('log');ax.set_ylim(0,1.02);ax.set_xlim(left=1)
    ax.set_xticks([1,10,30,60,300,1800,7200,86400],["1 с","10 с","30 с","1 хв","5 хв","30 хв","2 год","1 доба"])
    ax.set_xlabel('Тривалість епізоду; логарифмічна шкала')
    ax.set_ylabel('Частка епізодів не довших за вказаний час')
    ax.set_title('Тривалості станів у навчальній історії',loc='left',fontsize=15,fontweight='bold',pad=12)
    ax.grid(alpha=.2);ax.legend(loc='lower right')
    fig.supxlabel('Дані: City of Melbourne, 2019 (S5). Обчислення автора. Крайні обрізані епізоди виключено.',fontsize=9)
    for ext in ['png','svg']:
        path=dest/f'phase2-training-durations.{ext}';fig.savefig(path,dpi=180);outputs.append(path)
    plt.close(fig)
    metadata={'scope':'descriptive training_development primary windows only; no final-test intervals or policy outcomes read','source':'S5 City of Melbourne 2019','input':source.relative_to(ROOT).as_posix(),'input_sha256':sha256(source),'plot_code_sha256':sha256(Path(__file__)),'bays':bays,'windows':windows,'complete_episode_counts':counts,'matplotlib_version':matplotlib.__version__,'numpy_version':np.__version__,'outputs':[{ 'path':p.relative_to(ROOT).as_posix(),'sha256':sha256(p)} for p in outputs]}
    (dest/'phase2-figure-manifest.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
