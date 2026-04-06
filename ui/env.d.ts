/// <reference types="vite/client" />
declare module 'katex'
interface Window {
  sendMessage: ?((message: string, other_params_data: any) => void)
  chatUserProfile: ?(() => any)
  LZKB: {
    prefix: string
    chatPrefix: string
  }
  MaxKB?: {
    prefix: string
    chatPrefix: string
  }
}
