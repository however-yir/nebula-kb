import DOMPurify from 'dompurify'

/**
 * Sanitize HTML to prevent XSS. Use with v-html directives.
 */
export function safeHtml(dirty: string): string {
  if (!dirty) return ''
  return DOMPurify.sanitize(dirty, {
    USE_PROFILES: { html: true },
  })
}
