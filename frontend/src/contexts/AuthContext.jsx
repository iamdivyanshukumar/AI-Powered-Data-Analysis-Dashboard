import React, { createContext, useContext, useState, useEffect } from 'react'
import { api } from '../services/api'
import toast from 'react-hot-toast'

export const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check for stored user session
    const storedUser = localStorage.getItem('autovizai_user')
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser))
      } catch (error) {
        console.error('Failed to parse stored user:', error)
        localStorage.removeItem('autovizai_user')
      }
    }
    setLoading(false)
  }, [])

  const login = async (username, password) => {
    try {
      const response = await api.login({ username, password })
      
      if (response.data.success) {
        const userData = response.data.user
        setUser(userData)
        localStorage.setItem('autovizai_user', JSON.stringify(userData))
        localStorage.setItem('autovizai_token', response.data.token)
        
        toast.success('Login successful!')
        return { success: true }
      } else {
        toast.error(response.data.error || 'Login failed')
        return { success: false, error: response.data.error }
      }
    } catch (error) {
      console.error('Login error:', error)
      toast.error('Login failed. Please try again.')
      return { success: false, error: error.message }
    }
  }

  const register = async (username, email, password) => {
    try {
      const response = await api.register({ username, email, password })
      
      if (response.data.success) {
        toast.success('Registration successful! Please login.')
        return { success: true }
      } else {
        toast.error(response.data.error || 'Registration failed')
        return { success: false, error: response.data.error }
      }
    } catch (error) {
      console.error('Registration error:', error)
      toast.error('Registration failed. Please try again.')
      return { success: false, error: error.message }
    }
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem('autovizai_user')
    localStorage.removeItem('autovizai_token')
    toast.success('Logged out successfully')
  }

  const value = {
    user,
    loading,
    login,
    register,
    logout,
    isAuthenticated: !!user
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}