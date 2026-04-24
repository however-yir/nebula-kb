/// <reference types="vite/client" />
declare module 'katex'
interface Window {
  sendMessage?: ((message: string, other_params_data: any) => void) | null
  chatUserProfile?: (() => any) | null
  NEBULA: {
    prefix: string
    chatPrefix?: string
    projectUrl?: string
    helpUrl?: string
    contactUrl?: string
    pricingUrl?: string
    officialSiteUrl?: string
    docsUrl?: string
  }
  LZKB: Window['NEBULA']
}
