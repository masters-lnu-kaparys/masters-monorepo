"""Archive two primary adaptive-sampling papers for a scoped literature review."""
import urllib.request
from pypdf import PdfReader
from prepare_data import ROOT,sha256
from run_phase3 import write_json


if __name__=='__main__':
    folder=ROOT/'.codex-work/parking-local-risk-20261025/sources';folder.mkdir(parents=True,exist_ok=True)
    papers={
      'S17-Rezaei-2023':('https://people.cs.pitt.edu/~muk21/website_files/rl-cam/paper.pdf','10.1145/3584949'),
      'S18-Dias-2016':('https://arxiv.org/pdf/1606.02193v2','10.1109/WF-IoT.2016.7845391'),
      'S19-Gelman-2006':('https://stat.columbia.edu/~gelman/research/published/multi2.pdf','10.1198/004017005000000661')}
    receipt={}
    for name,(url,doi) in papers.items():
        p=folder/(name+'.pdf')
        if not p.exists():
            req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req,timeout=45) as r:payload=r.read()
            assert payload.startswith(b'%PDF');p.write_bytes(payload)
        reader=PdfReader(p);t=p.with_suffix('.txt');t.write_text('\n\n'.join(f'--- PDF PAGE{i+1} ---\n'+(page.extract_text() or '') for i,page in enumerate(reader.pages)),encoding='utf-8')
        receipt[name]={'url':url,'doi':doi,'pages':len(reader.pages),'pdf_sha256':sha256(p),'text_sha256':sha256(t),'download_does_not_establish_read_scope':True}
        print(name+' downloaded '+str(len(reader.pages))+'pages',flush=True)
    write_json(folder/'download-receipt.json',receipt)
