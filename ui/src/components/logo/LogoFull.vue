<template>
  <img v-if="theme.themeInfo?.loginLogo" :src="fileURL" alt="custom-logo" :height="height" class="mr-8" />
  <template v-else>
    <svg
      v-if="!isDefaultTheme"
      viewBox="0 0 260 52"
      xmlns="http://www.w3.org/2000/svg"
      :height="height"
      class="custom-logo-color"
    >
      <rect x="4" y="4" width="44" height="44" rx="12" stroke="currentColor" stroke-width="3" />
      <circle cx="26" cy="20" r="7" fill="currentColor" fill-opacity="0.95" />
      <path d="M18 32C20.8 26.8 31.2 26.8 34 32" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
      <circle cx="18" cy="17" r="2.1" fill="currentColor" fill-opacity="0.82" />
      <circle cx="34" cy="17" r="2.1" fill="currentColor" fill-opacity="0.82" />
      <text
        x="62"
        y="30"
        font-family="Segoe UI, Arial, sans-serif"
        font-size="24"
        font-weight="700"
        fill="currentColor"
      >
        NebulaKB
      </text>
      <text
        x="62"
        y="43"
        font-family="Segoe UI, Arial, sans-serif"
        font-size="11"
        font-weight="600"
        letter-spacing="0.08em"
        fill="currentColor"
        fill-opacity="0.72"
      >
        KNOWLEDGE OS
      </text>
    </svg>
    <img v-else src="@/assets/logo/NebulaKB-logo.svg" :height="height" alt="NebulaKB" />
  </template>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import useStore from '@/stores'
defineOptions({ name: 'LogoFull' })

defineProps({
  height: {
    type: String,
    default: '36px',
  },
})
const { theme } = useStore()
const isDefaultTheme = computed(() => {
  return theme.isDefaultTheme()
})

const fileURL = computed(() => {
  if (theme.themeInfo) {
    if (typeof theme.themeInfo?.loginLogo === 'string') {
      return theme.themeInfo?.loginLogo
    } else {
      return URL.createObjectURL(theme.themeInfo?.loginLogo)
    }
  } else {
    return ''
  }
})
</script>
<style lang="scss" scoped>
.custom-logo-color {
  color: var(--el-color-primary);
}
</style>
