// Format number with commas
export const formatNumber = (num, decimals = 0) => {
  if (num === null || num === undefined) return 'N/A'
  
  const number = typeof num === 'string' ? parseFloat(num) : num
  
  if (isNaN(number)) return 'N/A'
  
  return number.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })
}

// Format percentage
export const formatPercentage = (num, decimals = 1) => {
  if (num === null || num === undefined) return 'N/A'
  
  const number = typeof num === 'string' ? parseFloat(num) : num
  
  if (isNaN(number)) return 'N/A'
  
  return number.toFixed(decimals) + '%'
}

// Format duration
export const formatDuration = (seconds) => {
  if (seconds < 1) {
    return (seconds * 1000).toFixed(0) + 'ms'
  } else if (seconds < 60) {
    return seconds.toFixed(2) + 's'
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`
  } else {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
  }
}

// Truncate text
export const truncateText = (text, maxLength = 100) => {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

// Capitalize first letter
export const capitalize = (str) => {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

// Convert snake_case to Title Case
export const snakeToTitle = (str) => {
  if (!str) return ''
  return str
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

// Convert camelCase to Title Case
export const camelToTitle = (str) => {
  if (!str) return ''
  return str
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, str => str.toUpperCase())
    .trim()
}