// Compatibility wrapper: re-export the API service object as `api`
// This file ensures existing imports like `import { api } from '../services/apiService'`
// continue to work while the concrete implementation lives in `api.js`.
import apiService from './api'

// Named export expected by many modules
export const api = apiService

// Default export for other import styles
export default apiService
