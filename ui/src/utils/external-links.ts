import { getNebulaRuntime } from '@/utils/nebula-runtime'

const DEFAULT_PROJECT_URL = 'https://github.com/however-yir/nebula-kb'

function getRuntimeLink(key: string, fallback: string): string {
  const config = getNebulaRuntime() as unknown as Record<string, string | undefined>
  const value = config?.[key]
  if (typeof value === 'string' && value.trim().length > 0) {
    return value
  }
  return fallback
}

export const externalLinks = {
  projectUrl: getRuntimeLink('projectUrl', DEFAULT_PROJECT_URL),
  helpUrl: getRuntimeLink('helpUrl', 'https://docs.nebulakb.ai'),
  contactUrl: getRuntimeLink('contactUrl', `${DEFAULT_PROJECT_URL}/issues`),
  pricingUrl: getRuntimeLink('pricingUrl', 'https://nebulakb.ai/pricing'),
  officialSiteUrl: getRuntimeLink('officialSiteUrl', 'https://nebulakb.ai'),
  docsUrl: getRuntimeLink('docsUrl', 'https://docs.nebulakb.ai'),
}

export function openExternalLink(url: string) {
  window.open(url, '_blank', 'noopener,noreferrer')
}

export function openPricingPage() {
  openExternalLink(externalLinks.pricingUrl)
}
