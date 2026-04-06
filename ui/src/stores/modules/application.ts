import { defineStore } from 'pinia'
const useApplicationStore = defineStore('application', {
  state: () => ({
    location: `${window.location.origin}${window.LZKB.chatPrefix ? window.LZKB.chatPrefix : window.LZKB.prefix}/`,
  }),
  actions: {},
})

export default useApplicationStore
