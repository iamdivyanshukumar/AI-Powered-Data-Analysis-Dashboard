import { useEffect, useRef, useCallback } from 'react'

const useWebSocket = (url, options = {}) => {
  const socketRef = useRef(null)
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = options.maxReconnectAttempts || 5
  const reconnectInterval = options.reconnectInterval || 3000

  const connect = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      const socket = new WebSocket(url)
      
      socket.onopen = () => {
        console.log('WebSocket connected')
        reconnectAttemptsRef.current = 0
        options.onOpen?.()
      }

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          options.onMessage?.(data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      socket.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        options.onClose?.(event)
        
        // Attempt reconnection
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1
          setTimeout(() => {
            console.log(`Attempting reconnection (${reconnectAttemptsRef.current}/${maxReconnectAttempts})`)
            connect()
          }, reconnectInterval)
        }
      }

      socket.onerror = (error) => {
        console.error('WebSocket error:', error)
        options.onError?.(error)
      }

      socketRef.current = socket
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
    }
  }, [url, options])

  const send = useCallback((data) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(data))
      return true
    }
    return false
  }, [])

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close()
      socketRef.current = null
    }
  }, [])

  useEffect(() => {
    connect()
    
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    socket: socketRef.current,
    send,
    disconnect,
    reconnect: connect,
    isConnected: socketRef.current?.readyState === WebSocket.OPEN
  }
}

export default useWebSocket