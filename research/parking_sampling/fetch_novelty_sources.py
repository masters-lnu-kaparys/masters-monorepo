"""Keep a primary full-text source for the finite-period/duration novelty check."""
import json
import urllib.request
from pypdf import PdfReader
from prepare_data import ROOT,sha256

def main():
    folder=ROOT/'.codex-work/parking-novelty-audit-20261025/sources';folder.mkdir(parents=True,exist_ok=True)
    url='https://www.lopezbenitez.es/journals/IEEE_TWC_2019.pdf'
    path=folder/'S13-periodic-statistics-2019.pdf'
    if not path.exists():
        request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (academic literature review)'})
        with urllib.request.urlopen(request,timeout=45) as response:path.write_bytes(response.read())
    reader=PdfReader(path);target=path.with_suffix('.txt')
    target.write_text('\n\n'.join(f'--- PDF PAGE {i+1} ---\n'+(p.extract_text() or '') for i,p in enumerate(reader.pages)),encoding='utf-8')
    receipt={'source':'S13','primary_url':url,'discovered_on_author_publication_list':'https://www.lopezbenitez.es/research-publications.html',
      'alternate_repository_download':'HTTP403 at Oulu; used the public PDF linked by the author',
      'downloaded_on':'2026-10-25','pages':len(reader.pages),'pdf_sha256':sha256(path),'text_sha256':sha256(target)}
    (folder/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt))

if __name__=='__main__':main()
