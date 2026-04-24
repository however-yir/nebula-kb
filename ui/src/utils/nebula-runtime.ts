export interface NebulaRuntime {
  prefix: string
  chatPrefix: string
  projectUrl: string
  helpUrl: string
  contactUrl: string
  pricingUrl: string
  officialSiteUrl: string
  docsUrl: string
}

export const NEBULA_LOCALE_KEY = 'NEBULA-locale'
export const LZKB_LEGACY_LOCALE_KEY = 'LZKB-locale'

const DEFAULT_RUNTIME: NebulaRuntime = {
  prefix: '/admin',
  chatPrefix: '/chat',
  projectUrl: 'https://github.com/however-yir/nebula-kb',
  helpUrl: 'https://docs.nebulakb.ai',
  contactUrl: 'https://github.com/however-yir/nebula-kb/issues',
  pricingUrl: 'https://nebulakb.ai/pricing',
  officialSiteUrl: 'https://nebulakb.ai',
  docsUrl: 'https://docs.nebulakb.ai',
}

export function getNebulaRuntime(): NebulaRuntime {
  const runtime: NebulaRuntime = {
    ...DEFAULT_RUNTIME,
    ...(window.LZKB || {}),
    ...(window.NEBULA || {}),
  }

  window.NEBULA = runtime
  window.LZKB = runtime
  return runtime
}

export function getNebulaPrefix(fallback = '/admin') {
  return getNebulaRuntime().prefix || fallback
}

export function getNebulaChatPrefix(fallback = '/chat') {
  return getNebulaRuntime().chatPrefix || fallback
}

export function migrateNebulaLocale() {
  const currentLocale = localStorage.getItem(NEBULA_LOCALE_KEY)
  const legacyLocale = localStorage.getItem(LZKB_LEGACY_LOCALE_KEY)
  if (!currentLocale && legacyLocale) {
    localStorage.setItem(NEBULA_LOCALE_KEY, legacyLocale)
  }
}

export function getStoredNebulaLocale() {
  migrateNebulaLocale()
  return localStorage.getItem(NEBULA_LOCALE_KEY) || localStorage.getItem(LZKB_LEGACY_LOCALE_KEY)
}
