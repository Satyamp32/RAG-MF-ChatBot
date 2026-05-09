export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  source?: string
  lastUpdated?: string
  confidence?: number
  chunks?: Chunk[]
}

export interface Chunk {
  chunk_id: string
  scheme_id: string
  section: string
  text: string
  score: number
  confidence: number
  source: string
  rerank_score?: number
  rerank_rank?: number
}

export interface ChatState {
  messages: Message[]
  isLoading: boolean
  error: string | null
}

export interface ApiResponse {
  status: 'success' | 'error' | 'blocked'
  answer?: string
  source?: string
  last_updated?: string
  confidence?: number
  chunks?: Chunk[]
  error?: string
  blocked_reason?: string
  timestamp: string
}
