import { describe, it, expect } from 'vitest'

describe('Smoke tests', () => {
  it('app module loads', async () => {
    const app = await import('@/main')
    expect(app).toBeDefined()
  })

  it('router config has routes', async () => {
    const router = await import('@/router')
    expect(router).toBeDefined()
  })
})
