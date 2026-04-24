import { defineStore } from 'pinia'
const useApplicationStore = defineStore('application', {
  state: () => ({
    location: `${window.location.origin}${window.NEBULA.chatPrefix ? window.NEBULA.chatPrefix : window.NEBULA.prefix}/`,
  }),
  actions: {},
})

export default useApplicationStore
