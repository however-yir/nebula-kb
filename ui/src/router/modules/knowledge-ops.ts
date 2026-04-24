const KnowledgeOpsRouter = {
  path: '/knowledge-ops',
  name: 'knowledge-ops',
  meta: {
    title: 'views.knowledgeOps.title',
    menu: true,
    icon: 'DataAnalysis',
    iconActive: 'DataLine',
    group: 'workspace',
    order: 0,
  },
  redirect: '/knowledge-ops',
  component: () => import('@/layout/layout-template/SimpleLayout.vue'),
  children: [
    {
      path: '/knowledge-ops',
      name: 'knowledge-ops-index',
      meta: {
        title: 'views.knowledgeOps.title',
        activeMenu: '/knowledge-ops',
        sameRoute: 'knowledge-ops',
      },
      component: () => import('@/views/knowledge-ops/index.vue'),
    },
  ],
}

export default KnowledgeOpsRouter
