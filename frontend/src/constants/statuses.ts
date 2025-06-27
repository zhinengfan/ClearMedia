// 定义可用的文件状态
export const FILE_STATUSES = [
  { value: 'PENDING', label: '待处理', color: 'pending' },
  { value: 'QUEUED', label: '队列中', color: 'processing' },
  { value: 'PROCESSING', label: '处理中', color: 'processing' },
  { value: 'COMPLETED', label: '已完成', color: 'completed' },
  { value: 'FAILED', label: '失败', color: 'failed' },
  { value: 'CONFLICT', label: '冲突', color: 'conflict' },
  { value: 'NO_MATCH', label: '无匹配', color: 'no-match' },
] as const;
