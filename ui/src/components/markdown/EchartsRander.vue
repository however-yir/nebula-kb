<template>
  <div class="charts-container">
    <div ref="chartsRef" :style="style" v-resize="onResize"></div>
  </div>
</template>
<script lang="ts" setup>
import { onMounted, onBeforeUnmount, nextTick, watch, ref } from 'vue'
import * as echarts from 'echarts'

// ── props ──────────────────────────────────────────────────────────────────
const props = defineProps<{ option: string }>()

// ── refs ───────────────────────────────────────────────────────────────────
const chartsRef = ref<HTMLDivElement>()
const style = ref({ height: '220px', width: '100%' })

const ensureChart = (): echarts.ECharts | null => {
  if (!chartsRef.value) return null
  return echarts.getInstanceByDom(chartsRef.value) ?? echarts.init(chartsRef.value)
}

const applyOption = (raw: any) => {
  if (raw.actionType === 'EVAL') {
    const option = typeof raw.option === 'string' ? JSON.parse(raw.option) : raw.option
    if (raw.style) style.value = raw.style
    ensureChart()?.setOption(option, true)
    return
  }
  const chart = ensureChart()
  if (!chart) return
  if (raw.style) style.value = raw.style
  chart.setOption(raw.option ?? raw, true)
}

const initChart = () => {
  if (!chartsRef.value || !props.option) return
  try {
    applyOption(JSON.parse(props.option))
  } catch (e) {
    console.error('[ECharts] invalid option JSON', e)
  }
}

// ── resize 防抖 ────────────────────────────────────────────────────────────
let resizeTimer: ReturnType<typeof setTimeout> | null = null
const onResize = () => {
  if (resizeTimer) clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    echarts.getInstanceByDom(chartsRef.value!)?.resize()
  }, 100)
}

// ── 生命周期 ───────────────────────────────────────────────────────────────
watch(
  () => props.option,
  (val) => {
    if (val) nextTick(initChart)
  },
)

onMounted(() => nextTick(initChart))

onBeforeUnmount(() => {
  if (resizeTimer) clearTimeout(resizeTimer)
  if (chartsRef.value) echarts.getInstanceByDom(chartsRef.value)?.dispose()
})
</script>
<style lang="scss" scoped>
.charts-container {
  overflow-x: auto;
}
.charts-container::-webkit-scrollbar-track-piece {
  background-color: rgba(0, 0, 0, 0);
  border-left: 1px solid rgba(0, 0, 0, 0);
}
.charts-container::-webkit-scrollbar {
  width: 5px;
  height: 5px;
  -webkit-border-radius: 5px;
  -moz-border-radius: 5px;
  border-radius: 5px;
}
.charts-container::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.5);
  background-clip: padding-box;
  -webkit-border-radius: 5px;
  -moz-border-radius: 5px;
  border-radius: 5px;
  min-height: 28px;
}
.charts-container::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, 0.5);
  -webkit-border-radius: 5px;
  -moz-border-radius: 5px;
  border-radius: 5px;
}
</style>
