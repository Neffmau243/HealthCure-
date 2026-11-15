export const parsePresion = (texto) => {
  const match = /^(\d{2,3})\s*\/\s*(\d{2,3})$/.exec(String(texto ?? '').trim())
  return match ? {sistolica:Number(match[1]),diastolica:Number(match[2])} : null
}
