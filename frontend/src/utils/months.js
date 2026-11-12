export const MONTH_SHORT_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

export const MONTH_NAMES_ES = [
  'Enero',
  'Febrero',
  'Marzo',
  'Abril',
  'Mayo',
  'Junio',
  'Julio',
  'Agosto',
  'Septiembre',
  'Octubre',
  'Noviembre',
  'Diciembre',
]

/** Compress [1,2,3,5,7,8] into "Ene–Mar, May, Jul–Ago". */
export function describeMonths(months) {
  const sorted = [...new Set(months)].sort((a, b) => a - b)
  const ranges = []
  for (const m of sorted) {
    const last = ranges[ranges.length - 1]
    if (last && m === last[1] + 1) last[1] = m
    else ranges.push([m, m])
  }
  return ranges
    .map(([a, b]) => (a === b ? MONTH_SHORT_ES[a - 1] : `${MONTH_SHORT_ES[a - 1]}–${MONTH_SHORT_ES[b - 1]}`))
    .join(', ')
}
