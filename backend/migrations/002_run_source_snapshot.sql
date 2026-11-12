-- 运行资料批次冻结：排队时刻保存试样、逐票与参数快照，worker只按该批次计算。
-- ORM create_all 负责新建库结构；已存在的 MySQL 库可手动执行下列语句（JSON 列在 MySQL 8 可用）：
ALTER TABLE agreement_runs
  ADD COLUMN source_snapshot JSON NULL AFTER config,
  ADD COLUMN queued_fingerprint VARCHAR(64) NULL AFTER source_snapshot;
-- 旧运行（本迁移前创建）source_snapshot 为 NULL：
--   * 已完成：保留原结果，但结果页/复核流程明确提示缺少排队原始资料，不能以当前资料补齐；
--   * 未完成：worker 直接失败并给出同样提示，需重新排队生成新运行。
-- 复核说明 review_memos.result_snapshot 内新增 batch 块（快照版本、排队指纹、建说明时当前指纹、是否一致）。
