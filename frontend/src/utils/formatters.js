/**
 * Shared formatting utilities for Diamond Salón — Atelier Contable (owner: P1).
 *
 * Rules (SRS RF-GEN-04, RNF-03):
 * - All monetary values display as $#,##0.00 using exact string/integer digit
 *   formatting without floating-point drift.
 * - Dates display as dd/mm/yy in tables and dd/mm/yyyy in forms/details.
 */

export function formatMoney(value, { showSign = false, currencySymbol = '$' } = {}) {
  if (value === null || value === undefined || value === '') {
    return `${currencySymbol}0.00`
  }

  const rawStr = String(value).trim()
  const isNegative = rawStr.startsWith('-')
  const clean = rawStr.replace(/[^0-9.]/g, '')
  if (!clean) return `${currencySymbol}0.00`

  const [intPartRaw = '0', decPartRaw = ''] = clean.split('.')
  // Pad or round 2 decimal places from string digits
  let cents = BigInt(intPartRaw || '0') * 100n
  const dec2 = (decPartRaw + '00').slice(0, 2)
  const thirdDigit = decPartRaw.length >= 3 ? Number(decPartRaw[2]) : 0
  cents += BigInt(dec2)
  if (thirdDigit >= 5) {
    cents += 1n
  }

  const absInt = (cents / 100n).toString()
  const absDec = (cents % 100n).toString().padStart(2, '0')
  const withCommas = absInt.replace(/\B(?=(\d{3})+(?!\d))/g, ',')

  const signPrefix = isNegative ? '-' : showSign && cents > 0n ? '+' : ''
  return `${signPrefix}${currencySymbol}${withCommas}.${absDec}`
}

function parseIsoParts(value) {
  if (!value) return null
  const str = String(value).trim()
  const match = str.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (match) {
    return { year: match[1], month: match[2], day: match[3] }
  }
  const d = new Date(str)
  if (Number.isNaN(d.getTime())) return null
  return {
    year: String(d.getFullYear()),
    month: String(d.getMonth() + 1).padStart(2, '0'),
    day: String(d.getDate()).padStart(2, '0'),
  }
}

/** Table date format: dd/mm/yy (RF-GEN-04) */
export function formatDateShort(value) {
  const parts = parseIsoParts(value)
  if (!parts) return '—'
  return `${parts.day}/${parts.month}/${parts.year.slice(-2)}`
}

/** Form / detail date format: dd/mm/yyyy (RF-GEN-04) */
export function formatDateLong(value) {
  const parts = parseIsoParts(value)
  if (!parts) return '—'
  return `${parts.day}/${parts.month}/${parts.year}`
}

/** Timestamp format: dd/mm/yy HH:mm */
export function formatDateTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return formatDateShort(value)
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const year = String(d.getFullYear()).slice(-2)
  const hours = String(d.getHours()).padStart(2, '0')
  const mins = String(d.getMinutes()).padStart(2, '0')
  return `${day}/${month}/${year} ${hours}:${mins}`
}
