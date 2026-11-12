from fastapi import HTTPException
from src.models import ReviewMemo
from src.services.audit import record
from src.utils.csv_export import csv_response

def export_memo(db,id,actor):
 memo=db.get(ReviewMemo,id)
 if not memo:raise HTTPException(404,'说明不存在')
 if memo.status!='approved':raise HTTPException(409,'仅批准说明可导出')
 r=memo.result_snapshot;b=r['bootstrap'];ci=b['interval'];batch=r.get('batch',{});qf=batch.get('queued_fingerprint') or r.get('fingerprint','');cf=batch.get('current_fingerprint_at_memo','');match=batch.get('current_matches_queued_at_memo');match_text='' if match is None else ('一致' if match else '排队后资料已变更')
 rows=[[memo.name,r['source_study']['name'],batch.get('snapshot_version',''),qf,cf,match_text,r['fingerprint'],r['kappa'],r['pbar'],r['pe'],b['valid_repeats'],b['invalid_repeats'],ci[0] if ci else '',ci[1] if ci else '',item['reference'],item['agreement'],str(item['counts']),memo.interpretation,memo.next_step,memo.review_note] for item in r['items']]
 record(db,actor,'memo.exported',{'memo_id':id});return csv_response(f'rater-review-{id}.csv',rows,['复核说明','研究','快照版本','排队批次指纹','建说明时当前指纹','批次核对','结果指纹','Fleissκ','Pbar','Pe','有效重复','退化重复','经验区间下限','经验区间上限','试样','逐项P','类别计数','人工解释','下一步','审核意见'])
