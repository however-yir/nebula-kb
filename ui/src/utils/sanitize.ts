import sanitizeHtml from 'sanitize-html'

const defaultAllowedTags = [
  'b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code', 'pre',
  'table', 'thead', 'tbody', 'tr', 'th', 'td', 'span', 'div',
  'img', 'sup', 'sub', 'hr', 'details', 'summary',
]

export function safeHtml(dirty: string, options?: sanitizeHtml.IOptions): string {
  return sanitizeHtml(dirty, {
    allowedTags: options?.allowedTags ?? defaultAllowedTags,
    allowedAttributes: {
      a: ['href', 'target', 'rel'],
      img: ['src', 'alt', 'width', 'height'],
      span: ['style', 'class'],
      div: ['style', 'class'],
      code: ['class'],
      pre: ['class'],
      td: ['style', 'colspan', 'rowspan'],
      th: ['style', 'colspan', 'rowspan'],
      ...(options?.allowedAttributes ?? {}),
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

export function safeMarked(markdown: string): Promise<string> {
  const { marked } = require('marked')
  return Promise.resolve(marked(markdown)).then((raw: string) => safeHtml(raw))
}
