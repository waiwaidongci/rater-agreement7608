from fastapi import HTTPException
from src.models import ReviewMemo
from src.services.audit import record
from src.utils.csv_export import csv_response

def export_memo(db,id,actor):
 memo=db.get(ReviewMemo,id)
 if not memo:raise HTTPException(404,'说明不存在')
 if memo.status!='approved':raise HTTPException(409,'仅批准说明可导出')
 r=memo.result_snapshot;b=r['bootstrap'];ci=b['interval'];rows=[[memo.name,r['source_study']['name'],r['fingerprint'],r['kappa'],r['pbar'],r['pe'],b['valid_repeats'],b['invalid_repeats'],ci[0] if ci else '',ci[1] if ci else '',item['reference'],item['agreement'],str(item['counts']),memo.interpretation,memo.next_step,memo.review_note] for item in r['items']]
 record(db,actor,'memo.exported',{'memo_id':id});return csv_response(f'rater-review-{id}.csv',rows,['复核说明','研究','指纹','Fleissκ','Pbar','Pe','有效重复','退化重复','经验区间下限','经验区间上限','试样','逐项P','类别计数','人工解释','下一步','审核意见'])
