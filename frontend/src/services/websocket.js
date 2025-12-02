import { useEffect, useRef, useState } from 'react'

class WebSocketService {
  constructor() {
    this.socket = null
    this.listeners = new Map()
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
  }

  connect(url) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      this.socket = new WebSocket(url)

      this.socket.onopen = () => {
        console.log('WebSocket connected')
        this.reconnectAttempts = 0
        this.emit('connected')
      }

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.emit('message', data)
          
          // Emit specific event types
          if (data.type) {
            this.emit(data.type, data)
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      this.socket.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        this.emit('disconnected', event)
        
        // Attempt reconnection
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts += 1
          setTimeout(() => {
            console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
            this.connect(url)
          }, 3000)
        }
      }

      this.socket.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.emit('error', error)
      }
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.close()
      this.socket = null
    }
  }

  send(data) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data))
      return true
    }
    return false
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event).add(callback)
    
    // Return unsubscribe function
    return () => {
      const callbacks = this.listeners.get(event)
      if (callbacks) {
        callbacks.delete(callback)
      }
    }
  }

  off(event, callback) {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      callbacks.delete(callback)
    }
  }

  emit(event, data) {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`Error in ${event} callback:`, error)
        }
      })
    }
  }

  isConnected() {
    return this.socket?.readyState === WebSocket.OPEN
  }
}

// Singleton instance
const websocketService = new WebSocketService()

// React hook for using WebSocket
export const useWebSocket = (url, handlers = {}) => {
  const [isConnected, setIsConnected] = useState(false)
  const handlersRef = useRef(handlers)

  useEffect(() => {
    handlersRef.current = handlers
  }, [handlers])

  useEffect(() => {
    websocketService.connect(url)

    const unsubscribeConnected = websocketService.on('connected', () => {
      setIsConnected(true)
      handlersRef.current.onConnected?.()
    })

    const unsubscribeDisconnected = websocketService.on('disconnected', () => {
      setIsConnected(false)
      handlersRef.current.onDisconnected?.()
    })

    const unsubscribeMessage = websocketService.on('message', (data) => {
      handlersRef.current.onMessage?.(data)
    })

    // Subscribe to specific event types from handlers
    const eventUnsubscribers = Object.entries(handlers)
      .filter(([key]) => key.startsWith('on'))
      .map(([key, handler]) => {
        const event = key.replace('on', '').toLowerCase()
        return websocketService.on(event, handler)
      })

    return () => {
      unsubscribeConnected()
      unsubscribeDisconnected()
      unsubscribeMessage()
      eventUnsubscribers.forEach(unsubscribe => unsubscribe())
    }
  }, [url])

  return {
    send: websocketService.send.bind(websocketService),
    isConnected,
    socket: websocketService.socket
  }
}

export default websocketService