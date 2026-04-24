<template>
  <svg
    v-if="!isDefaultTheme"
    class="custom-logo-color"
    :height="height"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 48 48"
    fill="none"
  >
    <rect x="4" y="4" width="40" height="40" rx="12" stroke="currentColor" stroke-width="2.8" />
    <circle cx="24" cy="18.5" r="6.2" fill="currentColor" fill-opacity="0.95" />
    <path
      d="M16.8 29.2C19.4 24.4 28.6 24.4 31.2 29.2"
      stroke="currentColor"
      stroke-width="2.8"
      stroke-linecap="round"
    />
    <circle cx="16.5" cy="16" r="1.8" fill="currentColor" fill-opacity="0.82" />
    <circle cx="31.5" cy="16" r="1.8" fill="currentColor" fill-opacity="0.82" />
  </svg>
  <img v-else src="@/assets/logo/logo.svg" :height="height" alt="NebulaKB" />
</template>
<script setup lang="ts">
import { computed } from 'vue'
import useStore from '@/stores'
defineOptions({ name: 'LogoIcon' })

defineProps({
  height: {
    type: String,
    default: '36px'
  }
})
const { theme } = useStore()
const isDefaultTheme = computed(() => {
  return theme.isDefaultTheme()
})
</script>
<style lang="scss" scoped>
.custom-logo-color {
  color: var(--el-color-primary);
}
</style>
