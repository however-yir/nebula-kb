import { get } from 'lodash'

type RowData = Record<string, any>

const TEMPLATE_EXPR = /^\s*`([\s\S]*)`\s*$/
const ROW_PATH_EXPR = /^\s*row\.([A-Za-z0-9_.[\]-]+)\s*$/
const NUMBER_FORMAT_EXPR =
  /^\s*parseFloat\(row\.([A-Za-z0-9_.[\]-]+)\)\.toLocaleString\("([^"]+)",\{style:\s*"([^"]+)",maximumFractionDigits:\s*(\d+)\}\)\s*$/

function resolveTerm(term: string, row: RowData) {
  const numberFormatMatch = term.match(NUMBER_FORMAT_EXPR)
  if (numberFormatMatch) {
    const [, path, locale, style, digits] = numberFormatMatch
    const value = Number.parseFloat(get(row, path))
    if (Number.isNaN(value)) return ''
    return value.toLocaleString(locale, {
      style: style as Intl.NumberFormatOptions['style'],
      maximumFractionDigits: Number.parseInt(digits, 10),
    })
  }

  const rowPathMatch = term.match(ROW_PATH_EXPR)
  if (rowPathMatch) {
    return get(row, rowPathMatch[1], '')
  }

  return ''
}

export function renderSafeExpression(expression: string, row: RowData) {
  if (!expression) return ''

  const templateMatch = expression.match(TEMPLATE_EXPR)
  if (templateMatch) {
    return templateMatch[1].replace(/\$\{([^}]+)\}/g, (_match, term) =>
      String(resolveTerm(term, row)),
    )
  }

  const rowPathMatch = expression.match(ROW_PATH_EXPR)
  if (rowPathMatch) {
    return get(row, rowPathMatch[1], '')
  }

  return get(row, expression, '')
}

export function normalizeDynamicFormResponse(response: any) {
  const data = response?.data ?? response
  if (Array.isArray(data)) return data
  if (data?.shared_model || data?.model) {
    return [
      ...(data.shared_model || []).map((model: any) => ({ ...model, type: 'share' })),
      ...(data.model || []).map((model: any) => ({ ...model, type: 'workspace' })),
    ]
  }
  return data
}
