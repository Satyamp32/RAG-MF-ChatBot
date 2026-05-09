import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Bot, User, Copy, ExternalLink, TrendingUp } from 'lucide-react'
import { toast } from 'react-hot-toast'

import MessageBubble from './MessageBubble'
import SourceCitation from './SourceCitation'
import ConfidenceBadge from './ConfidenceBadge'
import LoadingDots from './LoadingDots'
import { Message } from '@/types/chat'
import { cn } from '@/lib/utils'

interface ChatInterfaceProps {
  messages: Message[]
  isLoading: boolean
  onSendMessage: (message: string) => void
}

const suggestedPrompts = [
  {
    icon: TrendingUp,
    text: 'What is the expense ratio of HDFC Equity Fund?',
    category: 'Performance Metrics'
  },
  {
    icon: TrendingUp,
    text: 'What is the minimum SIP amount for Axis Bluechip Fund?',
    category: 'Investment Details'
  },
  {
    icon: TrendingUp,
    text: 'Tell me about the exit load of ICICI Prudential Fund',
    category: 'Exit & Taxation'
  },
  {
    icon: TrendingUp,
    text: 'What is the risk level of SBI Small Cap Fund?',
    category: 'Risk Analysis'
  }
]

export default function ChatInterface({ messages, isLoading, onSendMessage }: ChatInterfaceProps) {
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmedInput = input.trim()
    
    if (!trimmedInput || isLoading) return
    
    onSendMessage(trimmedInput)
    setInput('')
    setIsTyping(false)
    
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    setIsTyping(e.target.value.length > 0)
    
    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(e.target.scrollHeight, 120)}px`
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard')
  }

  const handleSuggestedPrompt = (prompt: string) => {
    onSendMessage(prompt)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-4">
        <AnimatePresence>
          {messages.map((message, index) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className={cn(
                'flex',
                message.role === 'user' ? 'justify-end' : 'justify-start'
              )}
            >
              <div className={cn(
                'max-w-[80%] flex items-start gap-3',
                message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
              )}>
                {/* Avatar */}
                <div className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
                  message.role === 'user' 
                    ? 'bg-accent text-white' 
                    : 'bg-background-tertiary text-text'
                )}>
                  {message.role === 'user' ? (
                    <User className="w-4 h-4" />
                  ) : (
                    <Bot className="w-4 h-4" />
                  )}
                </div>

                {/* Message Content */}
                <div className="flex-1 space-y-3">
                  <MessageBubble message={message} />
                  
                  {/* Source Citation */}
                  {message.source && (
                    <SourceCitation 
                      source={message.source}
                      lastUpdated={message.lastUpdated}
                    />
                  )}
                  
                  {/* Confidence Badge */}
                  {message.confidence && (
                    <ConfidenceBadge confidence={message.confidence} />
                  )}
                  
                  {/* Copy Button */}
                  <button
                    onClick={() => copyToClipboard(message.content)}
                    className="flex items-center gap-2 text-text-secondary hover:text-text transition-colors text-sm"
                  >
                    <Copy className="w-3 h-3" />
                    Copy
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Loading Indicator */}
        {isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-start gap-3"
          >
            <div className="w-8 h-8 rounded-full bg-background-tertiary text-text flex items-center justify-center">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-background-card rounded-2xl rounded-bl-sm p-4">
              <LoadingDots />
            </div>
          </motion.div>
        )}
      </div>

      {/* Suggested Prompts */}
      {messages.length === 0 && !isLoading && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mb-6"
        >
          <h3 className="text-text-secondary font-medium mb-4">Try asking about:</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {suggestedPrompts.map((prompt, index) => (
              <motion.button
                key={index}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleSuggestedPrompt(prompt.text)}
                className="card-hover p-4 text-left text-left group"
              >
                <div className="flex items-start gap-3">
                  <prompt.icon className="w-5 h-5 text-accent mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-text text-sm font-medium group-hover:text-accent transition-colors">
                      {prompt.text}
                    </p>
                    <p className="text-text-muted text-xs mt-1">
                      {prompt.category}
                    </p>
                  </div>
                </div>
              </motion.button>
            ))}
          </div>
        </motion.div>
      )}

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex gap-3">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask about mutual funds..."
            className="input-field w-full resize-none min-h-[48px] max-h-[120px] pr-12"
            rows={1}
            disabled={isLoading}
          />
          
          {/* Send Button */}
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className={cn(
              'absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-200',
              (input.trim() && !isLoading)
                ? 'bg-accent hover:bg-accent-hover text-white'
                : 'bg-background-tertiary text-text-muted cursor-not-allowed'
            )}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  )
}
