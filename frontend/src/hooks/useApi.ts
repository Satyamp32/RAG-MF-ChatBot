import { useState, useCallback, useEffect } from 'react'
import { ApiResponse } from '@/types/chat'
import { toast } from 'react-hot-toast'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export function useApi() {
  const [isHealthy, setIsHealthy] = useState(false)
  const [lastCheck, setLastCheck] = useState<Date | null>(null)

  const healthCheck = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`)
      
      if (response.ok) {
        setIsHealthy(true)
        setLastCheck(new Date())
        return true
      } else {
        setIsHealthy(false)
        setLastCheck(new Date())
        return false
      }
    } catch (error) {
      console.error('Health check failed:', error)
      setIsHealthy(false)
      setLastCheck(new Date())
      return false
    }
  }, [])

  useEffect(() => {
    // Initial health check
    healthCheck()

    // Set up periodic health checks
    const interval = setInterval(healthCheck, 30000) // Check every 30 seconds

    return () => clearInterval(interval)
  }, [healthCheck])

  return {
    isHealthy,
    lastCheck,
    healthCheck,
    apiBaseUrl: API_BASE_URL
  }
}
