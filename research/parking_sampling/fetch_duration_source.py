"""Archive the primary duration-calculus antecedent found through S14 references."""
import json
import urllib.request
from pypdf import PdfReader
from prepare_data import ROOT,sha256


if __name__=='__main__':
    folder=ROOT/'.codex-work/parking-analytic-contribution-20261025/sources'
    path=folder/'S16-Hung-Giang-1996.pdf'
    url='https://uet.vnu.edu.vn/~dvh/publications/paper-report50.pdf'
    if not path.exists():
        with urllib.request.urlopen(url,timeout=45) as r:payload=r.read()
        assert payload.startswith(b'%PDF');path.write_bytes(payload)
    reader=PdfReader(path);target=path.with_suffix('.txt')
    target.write_text('\n\n'.join(f'--- PDF PAGE {i+1} ---\n'+(p.extract_text() or '') for i,p in enumerate(reader.pages)),encoding='utf-8')
    receipt={'primary_pdf':url,'doi':'https://doi.org/10.1007/3-540-61648-9_41',
      'author_metadata':'https://uet.vnu.edu.vn/~dvh/publications_2.html','pages':len(reader.pages),
      'pdf_sha256':sha256(path),'text_sha256':sha256(target),'download_is_not_read_scope':True}
    (folder/'S16-download-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))
