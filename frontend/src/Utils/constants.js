export const APP_NAME = 'AutoVizAI 2.0'
export const APP_VERSION = '2.0.0'
export const APP_DESCRIPTION = 'Agentic Data Science IDE'

export const ANALYSIS_TYPES = {
  COMPREHENSIVE: 'comprehensive_eda',
  QUICK: 'quick_analysis',
  TIME_SERIES: 'time_series',
  ML: 'machine_learning',
  CUSTOM: 'custom'
}

export const CELL_TYPES = {
  CODE: 'code',
  MARKDOWN: 'markdown'
}

export const VISUALIZATION_TYPES = {
  SCATTER: 'scatter',
  LINE: 'line',
  BAR: 'bar',
  HISTOGRAM: 'histogram',
  BOX: 'box',
  HEATMAP: 'heatmap',
  PIE: 'pie'
}

export const EXPORT_FORMATS = {
  IPYNB: 'ipynb',
  HTML: 'html',
  PDF: 'pdf',
  PY: 'py'
}

export const ERROR_MESSAGES = {
  UPLOAD_FAILED: 'Failed to upload file. Please try again.',
  ANALYSIS_FAILED: 'Analysis failed. Please check your data and try again.',
  NETWORK_ERROR: 'Network error. Please check your connection.',
  SESSION_EXPIRED: 'Session expired. Please login again.'
}

export const SUCCESS_MESSAGES = {
  UPLOAD_SUCCESS: 'File uploaded successfully!',
  ANALYSIS_SUCCESS: 'Analysis completed successfully!',
  NOTEBOOK_CREATED: 'Notebook created successfully!',
  CELL_EXECUTED: 'Cell executed successfully!'
}