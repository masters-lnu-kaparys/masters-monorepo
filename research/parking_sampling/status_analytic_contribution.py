"""Preserve live status bytes, then link the analytical review; no phase promotion."""
from pathlib import Path
from assess_analytic_contribution import WORK,read
from prepare_data import ROOT,DOCS,sha256
from run_phase3 import write_json


def main():
    history=WORK/'history';history.mkdir(exist_ok=True)
    mappings=list(read(DOCS/'phase3-budget-comparison-history.json')['historical_file_mapping'])
    for name in ('README.md','phase3-novelty-gate.json'):
        original=DOCS/name;snapshot=history/name
        expected=read(DOCS/'phase3-budget-comparison-history.json')['current_readme_sha256' if name=='README.md' else 'current_gate_sha256']
        if not snapshot.exists():
            assert sha256(original)==expected;snapshot.write_bytes(original.read_bytes())
        assert sha256(snapshot)==expected
        mappings.append({'original_path':original.relative_to(ROOT).as_posix(),
          'snapshot_path':snapshot.relative_to(ROOT).as_posix(),'snapshot_sha256':sha256(snapshot),
          'reason':'Analytical proof and prior-art assessment added; earlier status preserved byte-for-byte'})
    before=(history/'README.md').read_text(encoding='utf-8')
    begin=before.index('**Поточний стан:');end=before.index('**Досліджуємо вибір часу')
    current='''**Поточний стан: фаза 3 триває; оформлено [аналітичний кандидат на внесок](phase3-analytic-report.md).** Є точний клас розкладів, [доказ рекурсивної межі](phase3-analytic-method.md), [зіставлення з аналогами](phase3-analytic-sources.md) і [коротка постановка для керівника](phase3-supervisor-brief.md). Перевірено 2916 малих випадків з усіма допустимими цілочисловими паузами та ще 200 прикладів із довільним стартом. Рекурсивна межа строго сильніша на побудованому прикладі; на восьми вже використаних комірках Мельбурна вона дорівнює попередній H.3. Додаткового практичного виграшу нового уточнення немає. [Технічна перевірка](phase3-analytic-verification.json): 95 тестів; попередні журнали й результати збережено.

Це власний аналітичний результат для перевірки покриття на заданій історії; академічну новизну або новий кращий планувальник не встановлено. Загальні ідеї адаптації, часових обмежень і формальної перевірки відокремлено від конкретної формули. Попереднє [порівняння за бюджетом](phase3-budget-comparison-report.md) з269 визначеннями та додатком до326 збережено: невеликий умовний виграш C3 не скасовує його одного M60 на128/від доби. [C5](phase3-history-scheduler-report.md) не пройшов критерій корисності. M60 означає покриття епізоду виміром, а F/O - правильність карти. Остаточні867 місць і нові перевірочні групи не відкривали; [фаза4](phase3-novelty-gate.json) залишається закритою до остаточної заяви про внесок, обґрунтування метрик і фіксації протоколу.

'''
    text=before[:begin]+current+before[end:]
    old=next(line for line in text.splitlines() if line.startswith('| **3. Методи'))
    new='| **3. Методи, авторська модифікація і перевірка** | Збережено C0-C5 і порівняння за бюджетом. Уточнено аналітичну межу через обов\'язкові зайняті виміри та їхній вплив на спостережений вік. | [Доказ](phase3-analytic-method.md), [числа й незалежний перебір](phase3-analytic-report.md), [аналоги](phase3-analytic-sources.md), [постановка для керівника](phase3-supervisor-brief.md). | **Триває.** Математичний результат сформульовано й перевірено; нове уточнення не дало додаткового зменшення межі на використаних даних. Достатність вузького внеску й остаточний протокол ще не визначено. |'
    (DOCS/'README.md').write_text(text.replace(old,new),encoding='utf-8')
    gate=read(history/'phase3-novelty-gate.json')
    gate['status']='phase3_analytical_claim_documented_originality_and_final_protocol_unresolved'
    gate['completed_evidence']['analytic_proof']='Own R.1-R.4 result with end and recursive forced-observation resets; non-Zeno real-time assumptions, arbitrary-start corollary, O(n) count, strictness and non-tightness examples.2916 exact integer-grid cases and200 seeded arbitrary-start cases passed. No formal proof-assistant verification.'
    gate['completed_evidence']['analytic_recorded_data']='Eight unchanged known development cells; by-Bay old count equality verified. New recursive counts equal legacy H.3 everywhere; no additional empirical reduction.'
    gate['completed_evidence']['analytic_prior_art']='Relevant primary definitions/theorems of S14/S15/S16 reviewed with exact read-scope and archived hashes. Broad temporal-logic sampling guarantees, one-state duration constraints, uncertainty-aware verification are known. Narrow exact formula compared; world originality not established.'
    gate['completed_evidence']['verification']='95 tests passed; prior87/76/70/59 receipts preserved; old artifacts resolved unchanged or through explicit historical snapshots.'
    gate['remaining_before_phase4']=[
      'Assess the defensible academic scope of the documented analytical contribution; do not relabel it as a new superior scheduler or a world-first claim.',
      'Fix the final research requirement and preserve or explicitly version the original protocol. M60 is fresh in-episode observation coverage, not map accuracy;60seconds remains a design threshold. C3 original-protocol tuning M60 is retained.',
      'Freeze the complete final candidate set, code, comparisons, metrics and protocol before evaluating the867-bay final test. Prior development checks are not a fresh confirmation cohort.'
    ]
    gate['current_work']='phase3-analytic-report.md'
    write_json(DOCS/'phase3-novelty-gate.json',gate)
    write_json(DOCS/'phase3-analytic-history.json',{'created_on':'2026-10-25','historical_file_mapping':mappings,
      'current_readme_sha256':sha256(DOCS/'README.md'),'current_gate_sha256':sha256(DOCS/'phase3-novelty-gate.json')})


if __name__=='__main__':main()
