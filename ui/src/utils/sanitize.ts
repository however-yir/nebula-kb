import sanitizeHtml from 'sanitize-html'

const defaultAllowedTags = [
  'b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code', 'pre',
  'table', 'thead', 'tbody', 'tr', 'th', 'td', 'span', 'div',
  'img', 'sup', 'sub', 'hr', 'details', 'summary',
]

export function safeHtml(dirty: string, options?: Record<string, unknown>): string {
  return sanitizeHtml(dirty, {
    allowedTags: (options?.allowedTags as string[]) ?? defaultAllowedTags,
    allowedAttributes: {
      a: ['href', 'target', 'rel'],
      img: ['src', 'alt', 'width', 'height'],
      span: ['style', 'class'],
      div: ['style', 'class'],
      code: ['class'],
      pre: ['class'],
      td: ['style', 'colspan', 'rowspan'],
      th: ['style', 'colspan', 'rowspan'],
      ...((options?.allowedAttributes as Record<string, string[]>) ?? {}),
    },
    allowedSchemes: ['http', 'https', 'mailto'],
    ...options,
  })
}

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

export async function safeMarked(markdown: string): Promise<string> {
  const { marked } = await import('marked')
  const raw = await marked.parse(markdown)
  return safeHtml(raw)
}
