"""Download an open publisher PDF for the targeted literature audit."""
import json
import urllib.request
from pypdf import PdfReader
from prepare_data import sha256
from stability_audit import WORK

def main():
    out=WORK/'sources';out.mkdir(parents=True,exist_ok=True)
    url='https://link.springer.com/content/pdf/10.1186/1687-1499-2013-9.pdf'
    path=out/'S12-Choi-Yoo-2013.pdf'
    if not path.exists():
        request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(request,timeout=45) as response:payload=response.read()
        if not payload.startswith(b'%PDF'):raise ValueError('Publisher did not return a PDF')
        path.write_bytes(payload)
    reader=PdfReader(path);target=path.with_suffix('.txt')
    target.write_text('\n\n'.join(f'--- PDF PAGE {i+1} ---\n'+(p.extract_text() or '') for i,p in enumerate(reader.pages)),encoding='utf-8')
    receipt={'created_on':'2026-10-25','source':'S12','primary_url':url,'pages':len(reader.pages),
      'pdf_sha256':sha256(path),'text_sha256':sha256(target)}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt))

if __name__=='__main__':main()
