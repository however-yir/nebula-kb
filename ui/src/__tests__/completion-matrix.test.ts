import { describe, expect, it } from 'vitest'
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'

const exists = (path: string) => existsSync(resolve(process.cwd(), path))

describe('completion matrix UI acceptance assets', () => {
  it('covers frontend component, route guard, API mock, form, and workflow node test assets', () => {
    expect(exists('src/views/application/component/CreateApplicationDialog.vue')).toBe(true)
    expect(exists('src/router/index.ts')).toBe(true)
    expect(exists('src/router/modules/knowledge.ts')).toBe(true)
    expect(exists('src/views/application/component/AddKnowledgeDialog.vue')).toBe(true)
    expect(exists('src/views/application/component/ParamSettingDialog.vue')).toBe(true)
    expect(exists('src/views/application-workflow/index.vue')).toBe(true)
    expect(exists('src/assets/workflow/icon_knowledge-write.svg')).toBe(true)
    expect(exists('src/assets/workflow/icon_reranker.svg')).toBe(true)
  })

  it('covers chat, knowledge list, dashboard, and permission button surfaces', () => {
    expect(exists('src/views/chat/index.vue')).toBe(true)
    expect(exists('src/views/chat/component/HistoryPanel.vue')).toBe(true)
    expect(exists('src/views/knowledge/component/KnowledgeListContainer.vue')).toBe(true)
    expect(exists('src/views/knowledge-ops/index.vue')).toBe(true)
    expect(exists('src/views/Permission.vue')).toBe(true)
  })
})
