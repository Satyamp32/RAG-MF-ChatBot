import { useState, useCallback } from 'react'
import { Message, ChatState } from '@/types/chat'
import { sendMessage as sendApiMessage } from '@/services/api'

export function useChat() {
  const [state, setState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    error: null
  })

  const sendMessage = useCallback(async (message: string) => {
    if (!message.trim()) return

    setState(prev => ({ ...prev, isLoading: true, error: null }))

    try {
      const response = await sendApiMessage(message)
      
      const newMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: response.answer || 'I apologize, but I couldn\'t find an answer to your question.',
        timestamp: new Date(),
        source: response.source,
        lastUpdated: response.last_updated,
        confidence: response.confidence
      }

      const userMessage: Message = {
        id: (Date.now() - 1).toString(),
        role: 'user',
        content: message,
        timestamp: new Date()
      }

      setState(prev => ({
        ...prev,
        messages: [...prev.messages, userMessage, newMessage],
        isLoading: false
      }))
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'An error occurred'
      }))
    }
  }, [])

  const clearMessages = useCallback(() => {
    setState({
      messages: [],
      isLoading: false,
      error: null
    })
  }, [])

  return {
    ...state,
    sendMessage,
    clearMessages
  }
}
