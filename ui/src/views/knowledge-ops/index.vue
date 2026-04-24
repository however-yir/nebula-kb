<template>
  <div class="knowledge-ops-page">
    <section class="ops-hero">
      <div>
        <el-tag effect="plain" type="success">NebulaKB</el-tag>
        <h1>知识运营中枢</h1>
        <p>把分散知识从接入、治理、检索、回答到反馈迭代纳入同一套可观测闭环。</p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" :icon="Connection">知识接入向导</el-button>
        <el-button :icon="DocumentChecked">发布前验收</el-button>
      </div>
    </section>

    <section class="metric-grid">
      <div v-for="metric in metrics" :key="metric.label" class="metric-card">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <small :class="metric.trend > 0 ? 'up' : 'down'">
          {{ metric.trend > 0 ? '+' : '' }}{{ metric.trend }}%
        </small>
      </div>
    </section>

    <section class="ops-section">
      <div class="section-title">
        <h2>知识资产生命周期</h2>
        <el-tag>5 分钟上线</el-tag>
      </div>
      <div class="lifecycle">
        <div v-for="(stage, index) in lifecycle" :key="stage.name" class="lifecycle-step">
          <div class="step-index">{{ index + 1 }}</div>
          <h3>{{ stage.name }}</h3>
          <p>{{ stage.desc }}</p>
          <el-progress :percentage="stage.progress" :show-text="false" />
        </div>
      </div>
    </section>

    <el-tabs v-model="activeTab" class="ops-tabs">
      <el-tab-pane label="运营看板" name="command">
        <div class="dashboard-grid">
          <section class="ops-panel wide">
            <div class="section-title">
              <h2>知识新鲜度</h2>
              <el-segmented v-model="freshnessRange" :options="['7D', '30D', '90D']" />
            </div>
            <div class="freshness-chart">
              <div v-for="item in freshness" :key="item.name">
                <span>{{ item.name }}</span>
                <div class="bar-track">
                  <i :style="{ width: `${item.value}%`, background: item.color }"></i>
                </div>
                <b>{{ item.value }}%</b>
              </div>
            </div>
          </section>

          <section class="ops-panel">
            <div class="section-title">
              <h2>知识冲突检测</h2>
              <el-badge :value="12" type="danger" />
            </div>
            <div v-for="item in conflicts" :key="item.title" class="issue-row">
              <div>
                <strong>{{ item.title }}</strong>
                <span>{{ item.source }}</span>
              </div>
              <el-tag :type="item.level === '高' ? 'danger' : 'warning'">{{ item.level }}</el-tag>
            </div>
          </section>

          <section class="ops-panel">
            <div class="section-title">
              <h2>来源可信度评分</h2>
              <el-button link type="primary" @click="activeTab = 'trace'">追溯链路</el-button>
            </div>
            <div v-for="source in sources" :key="source.name" class="score-row">
              <span>{{ source.name }}</span>
              <el-rate v-model="source.score" disabled allow-half />
            </div>
          </section>

          <section class="ops-panel wide">
            <div class="section-title">
              <h2>文档过期自动提醒</h2>
              <el-tag type="warning">本周 7 份</el-tag>
            </div>
            <el-table :data="expiringDocs" size="small" height="210">
              <el-table-column prop="name" label="文档" />
              <el-table-column prop="owner" label="负责人" width="110" />
              <el-table-column prop="expiresIn" label="到期" width="110" />
              <el-table-column prop="action" label="动作" width="120" />
            </el-table>
          </section>
        </div>
      </el-tab-pane>

      <el-tab-pane label="可观测" name="observe">
        <div class="dashboard-grid">
          <section class="ops-panel wide">
            <div class="section-title">
              <h2>数据源健康巡检</h2>
              <el-button :icon="Refresh" @click="healthPulse += 1">巡检</el-button>
            </div>
            <el-table :data="dataSources" size="small" height="250">
              <el-table-column prop="name" label="数据源" />
              <el-table-column prop="latency" label="延迟" width="100" />
              <el-table-column prop="lastSync" label="最近同步" width="130" />
              <el-table-column label="状态" width="110">
                <template #default="{ row }">
                  <el-tag :type="row.status === '健康' ? 'success' : 'warning'">
                    {{ row.status }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </section>
          <section class="ops-panel">
            <div class="section-title">
              <h2>检索链路可观测</h2>
              <span>#{{ healthPulse }}</span>
            </div>
            <div v-for="stage in retrievalStages" :key="stage.name" class="trace-stage">
              <span>{{ stage.name }}</span>
              <el-progress :percentage="stage.value" />
            </div>
          </section>
          <section class="ops-panel">
            <h2>SLO 与错误预算</h2>
            <div class="budget-ring">
              <strong>72%</strong>
              <span>剩余错误预算</span>
            </div>
            <el-alert title="回答 API 过去 24 小时可用性 99.93%" type="success" :closable="false" />
          </section>
          <section class="ops-panel wide">
            <div class="section-title">
              <h2>问答命中率日报</h2>
              <el-tag type="success">自动发送</el-tag>
            </div>
            <div class="hit-rate">
              <div v-for="day in hitRateDaily" :key="day.day">
                <span>{{ day.day }}</span>
                <i :style="{ height: `${day.rate}%` }"></i>
                <b>{{ day.rate }}%</b>
              </div>
            </div>
          </section>
        </div>
      </el-tab-pane>

      <el-tab-pane label="质量闭环" name="quality">
        <div class="dashboard-grid">
          <section class="ops-panel">
            <h2>提示词版本管理 + 回滚</h2>
            <el-timeline>
              <el-timeline-item
                v-for="version in promptVersions"
                :key="version.name"
                :timestamp="version.time"
              >
                <span>{{ version.name }}</span>
                <el-button link type="primary">回滚</el-button>
              </el-timeline-item>
            </el-timeline>
          </section>
          <section class="ops-panel">
            <div class="section-title">
              <h2>工作流灰度发布</h2>
              <el-switch v-model="grayRelease" />
            </div>
            <el-slider v-model="grayPercent" :step="5" show-stops />
            <small>{{ grayPercent }}% 租户进入新版工作流</small>
          </section>
          <section class="ops-panel">
            <h2>在线 A/B 实验框架</h2>
            <div v-for="exp in experiments" :key="exp.name" class="issue-row">
              <strong>{{ exp.name }}</strong>
              <el-tag>{{ exp.winner }}</el-tag>
            </div>
          </section>
          <section class="ops-panel">
            <h2>回答质量自动评测任务</h2>
            <el-progress type="dashboard" :percentage="88" />
            <p>事实一致性、引用完整性、拒答边界已纳入每日任务。</p>
          </section>
          <section class="ops-panel wide">
            <div class="section-title">
              <h2>RAG 离线基准测试集管理</h2>
              <el-button :icon="Collection">新增测试集</el-button>
            </div>
            <el-table :data="benchmarks" size="small" height="220">
              <el-table-column prop="name" label="测试集" />
              <el-table-column prop="cases" label="样本" width="90" />
              <el-table-column prop="score" label="最近得分" width="120" />
              <el-table-column prop="owner" label="Owner" width="120" />
            </el-table>
          </section>
          <section class="ops-panel">
            <h2>低质量回答回流标注</h2>
            <div class="feedback-loop">
              <span>用户差评</span>
              <span>人工标注</span>
              <span>样本回流</span>
              <span>再次评测</span>
            </div>
          </section>
        </div>
      </el-tab-pane>

      <el-tab-pane label="权限与安全" name="security">
        <div class="dashboard-grid">
          <section class="ops-panel">
            <div class="section-title">
              <h2>PII 脱敏策略中心</h2>
              <el-switch v-model="piiMasking" />
            </div>
            <el-checkbox-group v-model="piiRules">
              <el-checkbox-button label="手机号" />
              <el-checkbox-button label="身份证" />
              <el-checkbox-button label="邮箱" />
            </el-checkbox-group>
          </section>
          <section class="ops-panel">
            <h2>审计日志防篡改存储</h2>
            <div class="chain-row" v-for="log in auditLogs" :key="log.hash">
              <span>{{ log.action }}</span>
              <code>{{ log.hash }}</code>
            </div>
          </section>
          <section class="ops-panel">
            <h2>API 密钥细粒度权限</h2>
            <el-table :data="apiScopes" size="small" height="190">
              <el-table-column prop="scope" label="Scope" />
              <el-table-column prop="level" label="权限" width="100" />
            </el-table>
          </section>
          <section class="ops-panel">
            <h2>SSO 组映射到角色策略</h2>
            <div v-for="role in ssoRoles" :key="role.group" class="issue-row">
              <span>{{ role.group }}</span>
              <el-tag>{{ role.role }}</el-tag>
            </div>
          </section>
          <section class="ops-panel">
            <h2>按部门的知识权限模板</h2>
            <div v-for="dept in departments" :key="dept.name" class="score-row">
              <span>{{ dept.name }}</span>
              <el-tag type="info">{{ dept.template }}</el-tag>
            </div>
          </section>
          <section class="ops-panel">
            <div class="section-title">
              <h2>多租户数据隔离策略</h2>
              <el-switch v-model="tenantIsolation" />
            </div>
            <p>租户级索引、对象存储前缀、审计链路隔离已启用。</p>
          </section>
          <section class="ops-panel wide">
            <h2>租户级品牌配置</h2>
            <div class="brand-row">
              <div v-for="brand in tenantBrands" :key="brand.name" class="brand-chip">
                <i :style="{ background: brand.color }"></i>
                <span>{{ brand.name }}</span>
                <small>{{ brand.domain }}</small>
              </div>
            </div>
          </section>
        </div>
      </el-tab-pane>

      <el-tab-pane label="模板与交付" name="growth">
        <div class="dashboard-grid">
          <section class="ops-panel wide">
            <div class="section-title">
              <h2>场景化助手模板市场</h2>
              <el-input v-model="templateKeyword" :prefix-icon="Search" placeholder="搜索模板" />
            </div>
            <div class="template-grid">
              <div v-for="tpl in filteredTemplates" :key="tpl.name" class="template-card">
                <el-tag>{{ tpl.industry }}</el-tag>
                <h3>{{ tpl.name }}</h3>
                <p>{{ tpl.desc }}</p>
              </div>
            </div>
          </section>
          <section class="ops-panel">
            <h2>行业模板包</h2>
            <el-check-tag v-for="pack in industryPacks" :key="pack" checked>{{ pack }}</el-check-tag>
          </section>
          <section class="ops-panel">
            <h2>知识接入向导</h2>
            <el-steps :active="3" direction="vertical" finish-status="success">
              <el-step title="连接数据源" />
              <el-step title="选择权限模板" />
              <el-step title="运行首轮评测" />
            </el-steps>
          </section>
          <section class="ops-panel">
            <h2>发布前一键验收流水线</h2>
            <el-progress :percentage="94" status="success" />
            <p>Schema、权限、检索、生成质量、回滚点全部通过。</p>
          </section>
          <section class="ops-panel">
            <h2>备份恢复演练自动化</h2>
            <el-result icon="success" title="最近演练成功" sub-title="RTO 18m / RPO 4m" />
          </section>
        </div>
      </el-tab-pane>

      <el-tab-pane label="引用追溯链路" name="trace">
        <section class="ops-panel wide">
          <div class="section-title">
            <h2>引用可追溯链路</h2>
            <el-tag type="success">证据链完整</el-tag>
          </div>
          <el-timeline>
            <el-timeline-item
              v-for="node in citationChain"
              :key="node.title"
              :timestamp="node.time"
              placement="top"
            >
              <h3>{{ node.title }}</h3>
              <p>{{ node.detail }}</p>
              <el-tag>{{ node.owner }}</el-tag>
            </el-timeline-item>
          </el-timeline>
        </section>
      </el-tab-pane>

      <el-tab-pane label="视觉系统" name="design">
        <section class="ops-panel wide">
          <div class="section-title">
            <h2>产品视觉设计系统</h2>
            <el-tag>品牌资产锁定</el-tag>
          </div>
          <div class="design-system">
            <div>
              <h3>字体</h3>
              <p>PingFang SC / AlibabaPuHuiTi / Inter fallback</p>
            </div>
            <div>
              <h3>色板</h3>
              <span v-for="color in palette" :key="color" :style="{ background: color }"></span>
            </div>
            <div>
              <h3>图标规范</h3>
              <p>Element Plus 线性图标优先，业务图标纳入 AppIcon 注册表。</p>
            </div>
          </div>
        </section>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  Collection,
  Connection,
  DocumentChecked,
  Refresh,
  Search,
} from '@element-plus/icons-vue'
import KnowledgeOpsApi from '@/api/knowledge-ops'
import useStore from '@/stores'

const activeTab = ref('command')
const freshnessRange = ref('30D')
const healthPulse = ref(1)
const grayRelease = ref(true)
const grayPercent = ref(20)
const piiMasking = ref(true)
const piiRules = ref(['手机号', '身份证'])
const tenantIsolation = ref(true)
const templateKeyword = ref('')
const dashboardLoading = ref(false)
const { user } = useStore()

const metrics = ref([
  { label: '知识新鲜度', value: '86%', trend: 7.4 },
  { label: '冲突待处理', value: '12', trend: -18.2 },
  { label: '问答命中率', value: '78.4%', trend: 5.1 },
  { label: '错误预算', value: '72%', trend: 2.6 },
])

const lifecycle = ref([
  { name: '接入', desc: '文件、网页、数据库、业务系统接入', progress: 92 },
  { name: '治理', desc: '脱敏、去重、冲突、可信度评分', progress: 81 },
  { name: '发布', desc: '灰度、验收、回滚、版本留痕', progress: 76 },
  { name: '问答', desc: '召回、重排、生成全链路可观测', progress: 88 },
  { name: '反馈', desc: '低质量回答回流标注与评测', progress: 69 },
])

const freshness = ref([
  { name: '制度文档', value: 91, color: '#14b8a6' },
  { name: '客服知识', value: 84, color: '#3370ff' },
  { name: '制造工艺', value: 73, color: '#f97316' },
  { name: '法务条款', value: 89, color: '#7c3aed' },
])

const conflicts = ref([
  { title: '退款时效口径不一致', source: '客服知识库 vs 法务条款', level: '高' },
  { title: '质检抽样比例存在旧版本', source: '制造 SOP', level: '中' },
  { title: 'API 计费说明出现重复定义', source: '官网文档', level: '中' },
])

const sources = ref([
  { name: '合同主库', score: 4.5 },
  { name: '客服 SOP', score: 4 },
  { name: '生产工艺 Wiki', score: 3.5 },
])

const expiringDocs = ref([
  { name: 'Q2 退款政策', owner: 'CS Ops', expiresIn: '3 天', action: '自动催办' },
  { name: '供应商 NDA 模板', owner: 'Legal', expiresIn: '5 天', action: '发起复核' },
  { name: 'CNC 点检 SOP', owner: 'MFG', expiresIn: '7 天', action: '班组确认' },
])

const dataSources = ref([
  { name: 'Confluence / CS Handbook', latency: '230ms', lastSync: '4 分钟前', status: '健康' },
  { name: 'SharePoint / Legal', latency: '410ms', lastSync: '12 分钟前', status: '健康' },
  { name: 'MES 工艺库', latency: '1.8s', lastSync: '42 分钟前', status: '需关注' },
])

const retrievalStages = ref([
  { name: '召回 Recall@20', value: 82 },
  { name: '重排 NDCG@5', value: 76 },
  { name: '生成引用完整率', value: 91 },
])

const hitRateDaily = ref([
  { day: 'Mon', rate: 73 },
  { day: 'Tue', rate: 76 },
  { day: 'Wed', rate: 75 },
  { day: 'Thu', rate: 81 },
  { day: 'Fri', rate: 78 },
])

const promptVersions = ref([
  { name: 'v4.8 引用优先', time: '今天 09:20' },
  { name: 'v4.7 降低幻觉', time: '昨天 18:04' },
  { name: 'v4.6 行业术语增强', time: '04-21 11:30' },
])

const experiments = ref([
  { name: '客服助手重排阈值', winner: 'B 组 +6.1%' },
  { name: '法务拒答策略', winner: 'A 组稳定' },
])

const benchmarks = ref([
  { name: '客服 Top 200 问法', cases: 200, score: '86.7', owner: 'CS Ops' },
  { name: '法务红线问答', cases: 88, score: '91.4', owner: 'Legal' },
  { name: '制造异常处置', cases: 132, score: '79.2', owner: 'MFG' },
])

const auditLogs = ref([
  { action: 'policy.updated', hash: '0x9a31...c8f2' },
  { action: 'prompt.rollback', hash: '0x1bc4...87d0' },
  { action: 'dataset.exported', hash: '0xae90...b13a' },
])

const apiScopes = ref([
  { scope: 'knowledge:read', level: '只读' },
  { scope: 'answer:evaluate', level: '任务' },
  { scope: 'tenant:brand', level: '管理' },
])

const ssoRoles = ref([
  { group: 'okta-legal', role: '法务知识管理员' },
  { group: 'okta-cs-lead', role: '客服运营负责人' },
  { group: 'okta-mfg-user', role: '制造现场用户' },
])

const departments = ref([
  { name: '法务部', template: '合同/合规只读 + 审批' },
  { name: '客服部', template: 'FAQ 编辑 + 发布申请' },
  { name: '制造部', template: 'SOP 只读 + 异常标注' },
])

const tenantBrands = ref([
  { name: 'Nebula Core', color: '#14b8a6', domain: 'core.nebulakb.ai' },
  { name: 'Acme White-label', color: '#3370ff', domain: 'kb.acme.com' },
  { name: 'Factory Desk', color: '#f97316', domain: 'qa.factory.internal' },
])

const templates = ref([
  { name: '合同审阅助手', industry: '法务', desc: '条款冲突、引用追溯、风险边界。' },
  { name: '售后坐席助手', industry: '客服', desc: '命中率日报、低质回答回流、渠道知识同步。' },
  { name: '工艺异常助手', industry: '制造', desc: 'SOP 追溯、设备告警关联、班组权限模板。' },
])

const filteredTemplates = computed(() =>
  templates.value.filter((tpl) => `${tpl.name}${tpl.industry}`.includes(templateKeyword.value)),
)

const industryPacks = ref(['法务', '客服', '制造'])

const citationChain = ref([
  {
    title: '回答片段',
    detail: '“保修期内的设备异常优先走快速换新流程。”',
    owner: '售后助手',
    time: '生成于 10:42',
  },
  {
    title: '引用段落',
    detail: '售后政策 v2026.04 / 第 3.2 节 / 段落 #184',
    owner: 'CS Ops',
    time: '召回于 10:42',
  },
  {
    title: '源文件版本',
    detail: 'Warranty_Policy_2026Q2.pdf / sha256: 9a31c8f2',
    owner: '法务部',
    time: '同步于 09:55',
  },
  {
    title: '审批记录',
    detail: 'Legal-approval-4821 / 双人复核 / 不可变更审计链',
    owner: 'Legal',
    time: '04-22 16:10',
  },
])

const palette = ref(['#14b8a6', '#3370ff', '#f97316', '#7c3aed', '#111827', '#f5f6f7'])

function applyDashboard(data: any) {
  metrics.value = data.metrics || metrics.value
  lifecycle.value = data.lifecycle || lifecycle.value
  freshness.value = data.freshness || freshness.value
  conflicts.value = data.conflicts || conflicts.value
  sources.value = data.source_credibility || sources.value
  expiringDocs.value = data.expiring_documents || expiringDocs.value
  dataSources.value = data.data_source_health || dataSources.value
  retrievalStages.value = data.retrieval_observability || retrievalStages.value
  hitRateDaily.value = data.qa_hit_rate_daily || hitRateDaily.value
  promptVersions.value = data.prompt_versions || promptVersions.value
  grayRelease.value = data.workflow_gray_release?.enabled ?? grayRelease.value
  grayPercent.value = data.workflow_gray_release?.percent ?? grayPercent.value
  experiments.value = data.ab_experiments || experiments.value
  benchmarks.value = data.rag_benchmarks || benchmarks.value
  auditLogs.value = data.tamper_proof_audit || auditLogs.value
  apiScopes.value = data.api_key_scopes || apiScopes.value
  ssoRoles.value = data.sso_role_mapping || ssoRoles.value
  departments.value = data.department_permission_templates || departments.value
  tenantIsolation.value = data.tenant_isolation?.enabled ?? tenantIsolation.value
  tenantBrands.value = data.tenant_branding || tenantBrands.value
  templates.value = data.assistant_templates || templates.value
  industryPacks.value = data.industry_template_packs || industryPacks.value
  piiMasking.value = data.pii_policy?.enabled ?? piiMasking.value
  piiRules.value = data.pii_policy?.rules || piiRules.value
  citationChain.value = data.citation_chain || citationChain.value
  palette.value = data.visual_system?.palette || palette.value
}

onMounted(() => {
  KnowledgeOpsApi.getDashboard(user.getWorkspaceId() || 'default', freshnessRange.value, dashboardLoading)
    .then((res) => applyDashboard(res.data))
    .catch(() => {
      // Keep local defaults when the backend is unavailable in static preview mode.
    })
})
</script>

<style lang="scss" scoped>
.knowledge-ops-page {
  padding: 24px;
  min-height: calc(100vh - var(--app-header-height));
  background: #f5f6f7;
}

.ops-hero,
.ops-section,
.ops-panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.ops-hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  padding: 28px;

  h1 {
    margin: 12px 0 8px;
    font-size: 30px;
    line-height: 1.2;
    font-weight: 700;
  }

  p {
    max-width: 680px;
    color: var(--app-text-color-secondary);
    line-height: 1.7;
  }
}

.hero-actions {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.metric-grid,
.dashboard-grid,
.template-grid,
.brand-row,
.design-system {
  display: grid;
  gap: 16px;
}

.metric-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 16px 0;
}

.metric-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 18px;

  span,
  small {
    display: block;
    color: var(--app-text-color-secondary);
  }

  strong {
    display: block;
    margin: 10px 0 4px;
    font-size: 28px;
  }

  .up {
    color: #0f9f6e;
  }

  .down {
    color: #d97706;
  }
}

.ops-section,
.ops-panel {
  padding: 20px;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.lifecycle {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.lifecycle-step {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  min-height: 156px;

  h3 {
    margin: 12px 0 8px;
  }

  p {
    min-height: 42px;
    color: var(--app-text-color-secondary);
    line-height: 1.5;
  }
}

.step-index {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #fff;
  background: #111827;
  font-weight: 700;
}

.ops-tabs {
  margin-top: 16px;
}

.dashboard-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.wide {
  grid-column: span 2;
}

.freshness-chart > div,
.issue-row,
.score-row,
.trace-stage,
.chain-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #f0f2f5;
}

.freshness-chart > div:last-child,
.issue-row:last-child,
.score-row:last-child,
.chain-row:last-child {
  border-bottom: 0;
}

.bar-track {
  flex: 1;
  height: 10px;
  border-radius: 999px;
  background: #edf0f3;
  overflow: hidden;

  i {
    display: block;
    height: 100%;
    border-radius: inherit;
  }
}

.issue-row {
  align-items: flex-start;

  div span,
  > span {
    color: var(--app-text-color-secondary);
  }
}

.budget-ring {
  width: 156px;
  height: 156px;
  margin: 16px auto;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #fff 0 58%, transparent 59%),
    conic-gradient(#14b8a6 0 72%, #e5e7eb 72% 100%);

  strong,
  span {
    grid-area: 1 / 1;
  }

  strong {
    margin-top: -22px;
    font-size: 30px;
  }

  span {
    margin-top: 32px;
    color: var(--app-text-color-secondary);
  }
}

.hit-rate {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  height: 170px;
  align-items: end;

  div {
    display: grid;
    grid-template-rows: auto 1fr auto;
    height: 100%;
    text-align: center;
    color: var(--app-text-color-secondary);
  }

  i {
    align-self: end;
    display: block;
    border-radius: 6px 6px 0 0;
    background: linear-gradient(180deg, #3370ff, #14b8a6);
  }
}

.feedback-loop {
  display: grid;
  gap: 10px;

  span {
    padding: 10px 12px;
    border-radius: 8px;
    background: #f5f8ff;
    border: 1px solid #dbe7ff;
  }
}

.chain-row code {
  color: #3370ff;
}

.brand-row {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.brand-chip,
.template-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
}

.brand-chip {
  display: grid;
  gap: 6px;

  i {
    width: 28px;
    height: 28px;
    border-radius: 8px;
  }

  small {
    color: var(--app-text-color-secondary);
  }
}

.template-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.template-card p,
.ops-panel p {
  color: var(--app-text-color-secondary);
  line-height: 1.6;
}

.design-system {
  grid-template-columns: repeat(3, minmax(0, 1fr));

  > div {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 16px;
  }

  span {
    display: inline-block;
    width: 36px;
    height: 36px;
    border-radius: 8px;
    margin-right: 8px;
    border: 1px solid #e5e7eb;
  }
}

@media (max-width: 1180px) {
  .metric-grid,
  .dashboard-grid,
  .lifecycle,
  .template-grid,
  .brand-row,
  .design-system {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .wide {
    grid-column: span 2;
  }
}

@media (max-width: 720px) {
  .knowledge-ops-page {
    padding: 12px;
  }

  .ops-hero,
  .metric-grid,
  .dashboard-grid,
  .lifecycle,
  .template-grid,
  .brand-row,
  .design-system {
    grid-template-columns: 1fr;
  }

  .ops-hero {
    display: grid;
  }

  .wide {
    grid-column: span 1;
  }
}
</style>
