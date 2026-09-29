import exifr from 'exifr'

const DATE_TAGS = ['DateTimeOriginal', 'CreateDate', 'DateTimeDigitized']

const pad = (value) => String(value).padStart(2, '0')

const isValidDateParts = (year, month, day) => {
  const date = new Date(year, month - 1, day)
  return (
    date.getFullYear() === year &&
    date.getMonth() === month - 1 &&
    date.getDate() === day
  )
}

const formatDateParts = (year, month, day) => {
  if (!isValidDateParts(year, month, day)) return null
  return `${year}-${pad(month)}-${pad(day)}`
}

export const normalizeExifDate = (value) => {
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    return formatDateParts(
      value.getFullYear(),
      value.getMonth() + 1,
      value.getDate()
    )
  }

  if (typeof value !== 'string') return null

  const match = value.trim().match(/^(\d{4})[:-](\d{1,2})[:-](\d{1,2})/)
  if (!match) return null

  return formatDateParts(
    Number(match[1]),
    Number(match[2]),
    Number(match[3])
  )
}

export const extractShootDate = async (file) => {
  if (!file) return null

  const metadata = await exifr.parse(file, DATE_TAGS)
  for (const tag of DATE_TAGS) {
    const date = normalizeExifDate(metadata?.[tag])
    if (date) return date
  }

  return null
}
