const DEFAULT_PROJECT_URL = 'https://github.com/however-yir/LZKB'

function getRuntimeLink(key: string, fallback: string): string {
  const config = window.LZKB as Record<string, string | undefined> | undefined
  const value = config?.[key]
  if (typeof value === 'string' && value.trim().length > 0) {
    return value
  }
  return fallback
}

export const externalLinks = {
  projectUrl: getRuntimeLink('projectUrl', DEFAULT_PROJECT_URL),
  helpUrl: getRuntimeLink('helpUrl', `${DEFAULT_PROJECT_URL}/wiki`),
  contactUrl: getRuntimeLink('contactUrl', `${DEFAULT_PROJECT_URL}/issues`),
  pricingUrl: getRuntimeLink('pricingUrl', `${DEFAULT_PROJECT_URL}#readme`),
}

export function openExternalLink(url: string) {
  window.open(url, '_blank', 'noopener,noreferrer')
}

export function openPricingPage() {
  openExternalLink(externalLinks.pricingUrl)
}
