import { ApiResponse } from '@/types/chat'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function sendMessage(query: string): Promise<ApiResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        use_groq: 'auto',
        top_k: 10,
        include_metadata: true
      }),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data: ApiResponse = await response.json()
    return data
  } catch (error) {
    console.error('API Error:', error)
    return {
      status: 'error',
      error: error instanceof Error ? error.message : 'Unknown error',
      timestamp: new Date().toISOString()
    }
  }
}

export async function healthCheck(): Promise<{ status: string; components: any }> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`)
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data = await response.json()
    return data
  } catch (error) {
    console.error('Health check error:', error)
    return {
      status: 'error',
      components: {}
    }
  }
}

export async function getApiInfo(): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/meta`)
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data = await response.json()
    return data
  } catch (error) {
    console.error('API info error:', error)
    return null
  }
}
