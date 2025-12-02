import axios from 'axios'

// 1. GLOBAL INSTANCE (For normal JSON requests)
const axiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  withCredentials: false
})

// Add Token to Global Instance
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('autovizai_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 403) {
      localStorage.removeItem('autovizai_token')
      localStorage.removeItem('autovizai_user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

const apiService = {
  login: (credentials) => axiosInstance.post('/auth/login', credentials),
  register: (userData) => axiosInstance.post('/auth/register', userData),
  logout: () => axiosInstance.post('/auth/logout'),

  // --- THE FIX: ISOLATED UPLOAD REQUEST ---
  uploadFile: (formData) => {
    // We create a fresh axios call here. 
    // This ensures NO global 'application/json' headers interfere.
    const token = localStorage.getItem('autovizai_token')

    return axios.post('/api/data/upload', formData, {
      headers: {
        'Authorization': token ? `Bearer ${token}` : undefined,
        // Explicitly undefined allows the browser to generate the boundary
        'Content-Type': undefined
      }
    })
  },

  createGhostCell: (notebookId, data) =>
    axiosInstance.post(`/notebook/${notebookId}/ghost_cell`, data),

  getLiveVariables: (notebookId) =>
    axiosInstance.get(`/notebook/${notebookId}/live_variables`),

  createNotebook: (data) => axiosInstance.post('/data/create', data),

  updateNotebookCell: (notebookId, data) =>
    axiosInstance.post(`/notebook/${notebookId}/update`, data),

  addNotebookCell: (notebookId, data) =>
    axiosInstance.post(`/notebook/${notebookId}/add_cell`, data),

  deleteNotebookCell: (notebookId, data) =>
    axiosInstance.post(`/notebook/${notebookId}/delete_cell`, data),

  processNotebookInstruction: (notebookId, data) =>
    axiosInstance.post(`/notebook/${notebookId}/process_instruction`, data),

  executeNotebookCell: (notebookId, data) =>
    axiosInstance.post(`/notebook/${notebookId}/execute`, data),

  exportNotebook: (notebookId, data) =>
    axiosInstance.post(`/notebook/${notebookId}/export`, data)
}

export const api = apiService

// Default export for other import styles
export default apiService