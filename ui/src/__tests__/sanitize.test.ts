import { describe, expect, it } from 'vitest'
import { safeHtml, safeMarked } from '@/utils/sanitize'

describe('safe HTML rendering', () => {
  it('removes script tags and event handlers', () => {
    const html = safeHtml('<p onclick="alert(1)">hello</p><script>alert(2)</script>')

    expect(html).toContain('<p>hello</p>')
    expect(html).not.toContain('onclick')
    expect(html).not.toContain('<script')
  })

  it('removes javascript URLs from links', () => {
    const html = safeHtml('<a href="javascript:alert(1)">bad</a><a href="https://example.com">ok</a>')

    expect(html).toContain('<a>bad</a>')
    expect(html).toContain('href="https://example.com"')
    expect(html).not.toContain('javascript:')
  })

  it('sanitizes markdown output before preview rendering', async () => {
    const html = await safeMarked('[safe](https://example.com) <img src=x onerror=alert(1)>')

    expect(html).toContain('href="https://example.com"')
    expect(html).not.toContain('onerror')
  })
})
