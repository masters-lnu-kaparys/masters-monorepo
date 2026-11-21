"""Archive primary open sources without claiming that downloading equals reading."""
import json
import urllib.request
from pypdf import PdfReader
from prepare_data import ROOT,sha256

WORK=ROOT/'.codex-work/parking-analytic-contribution-20261025'
SOURCES={
 'S14-Furia-Rossi-2010':('https://arxiv.org/pdf/0911.5642v2','https://doi.org/10.1145/1838552.1838560'),
 'S15-Mehrabian-2023':('https://mpslab-asu.github.io/publications/papers/Mehrabian2023MICPRO.pdf','https://doi.org/10.1016/j.micpro.2023.104890')}


def main():
    folder=WORK/'sources';folder.mkdir(parents=True,exist_ok=True);rows={}
    for name,(url,doi) in SOURCES.items():
        path=folder/(name+'.pdf')
        if not path.exists():
            request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(request,timeout=45) as r:payload=r.read()
            if not payload.startswith(b'%PDF'):raise ValueError('Not a primary PDF: '+name)
            path.write_bytes(payload)
        reader=PdfReader(path);text=path.with_suffix('.txt')
        text.write_text('\n\n'.join(f'--- PDF PAGE {i+1} ---\n'+(p.extract_text() or '') for i,p in enumerate(reader.pages)),encoding='utf-8')
        rows[name]={'primary_pdf':url,'doi':doi,'pages':len(reader.pages),'pdf_sha256':sha256(path),'text_sha256':sha256(text),
                    'download_is_not_read_scope':True}
    (folder/'download-receipt.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(rows))


if __name__=='__main__':main()
