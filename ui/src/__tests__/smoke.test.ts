import { describe, it, expect } from 'vitest'

describe('Smoke tests', () => {
  it('vitest runs', () => {
    expect(1 + 1).toBe(2)
  })

  it('can resolve modules', () => {
    expect(() => import('vue')).not.toThrow()
  })
})
