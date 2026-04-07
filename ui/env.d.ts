/// <reference types="vite/client" />
declare module 'katex'
interface Window {
  sendMessage: ?((message: string, other_params_data: any) => void)
  chatUserProfile: ?(() => any)
  LZKB: {
    prefix: string
    chatPrefix?: string
    projectUrl?: string
    helpUrl?: string
    contactUrl?: string
    pricingUrl?: string
  }
}
