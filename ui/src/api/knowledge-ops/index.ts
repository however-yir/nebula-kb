import { get } from '@/request/index'
import type { Result } from '@/request/Result'

const prefix = '/workspace'

const getDashboard = (
  workspaceId: string,
  range = '30D',
  loading?: any,
): Promise<Result<any>> => {
  return get(`${prefix}/${workspaceId}/knowledge_ops`, { range }, loading)
}

export default {
  getDashboard,
}
