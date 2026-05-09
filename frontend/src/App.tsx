import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Menu, X, Bot, User, Clock, ExternalLink, TrendingUp } from 'lucide-react'
import { Toaster, toast } from 'react-hot-toast'

import ChatInterface from '@/components/ChatInterface'
import Sidebar from '@/components/Sidebar'
import Header from '@/components/Header'
import LoadingSkeleton from '@/components/LoadingSkeleton'
import { useChat } from '@/hooks/useChat'
import { useApi } from '@/hooks/useApi'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { messages, isLoading, sendMessage, clearMessages } = useChat()
  const { healthCheck, isHealthy } = useApi()

  useEffect(() => {
    // Check API health on mount
    healthCheck()
  }, [healthCheck])

  return (
    <div className="min-h-screen bg-background text-text flex flex-col">
      {/* Header */}
      <Header 
        onMenuToggle={() => setSidebarOpen(!sidebarOpen)}
        isHealthy={isHealthy}
      />

      <div className="flex flex-1 relative">
        {/* Sidebar */}
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div
              initial={{ x: -300 }}
              animate={{ x: 0 }}
              exit={{ x: -300 }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 left-0 z-50 lg:hidden"
            >
              <Sidebar 
                onClose={() => setSidebarOpen(false)}
                onClearChat={clearMessages}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Desktop Sidebar */}
        <div className="hidden lg:block">
          <Sidebar 
            onClose={() => {}}
            onClearChat={clearMessages}
          />
        </div>

        {/* Main Content */}
        <main className="flex-1 lg:ml-80">
          <div className="max-w-4xl mx-auto px-4 py-6">
            {/* Welcome Section */}
            {messages.length === 0 && !isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="text-center py-12"
              >
                <div className="mb-8">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-accent rounded-2xl mb-4">
                    <Bot className="w-8 h-8 text-white" />
                  </div>
                  <h1 className="text-3xl font-bold text-text mb-2">
                    Mutual Fund Assistant
                  </h1>
                  <p className="text-text-secondary text-lg max-w-md mx-auto">
                    Get factual information about mutual funds with AI-powered insights and reliable source attribution.
                  </p>
                </div>

                {/* Feature Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl mx-auto">
                  <motion.div
                    whileHover={{ scale: 1.02 }}
                    className="card-hover p-6 text-left"
                  >
                    <TrendingUp className="w-6 h-6 text-accent mb-3" />
                    <h3 className="font-semibold text-text mb-2">Smart Retrieval</h3>
                    <p className="text-text-secondary text-sm">
                      Advanced hybrid search with dense and sparse retrieval for accurate results
                    </p>
                  </motion.div>

                  <motion.div
                    whileHover={{ scale: 1.02 }}
                    className="card-hover p-6 text-left"
                  >
                    <Clock className="w-6 h-6 text-accent mb-3" />
                    <h3 className="font-semibold text-text mb-2">Real-time Data</h3>
                    <p className="text-text-secondary text-sm">
                      Up-to-date mutual fund information from reliable sources
                    </p>
                  </motion.div>

                  <motion.div
                    whileHover={{ scale: 1.02 }}
                    className="card-hover p-6 text-left"
                  >
                    <ExternalLink className="w-6 h-6 text-accent mb-3" />
                    <h3 className="font-semibold text-text mb-2">Source Attribution</h3>
                    <p className="text-text-secondary text-sm">
                      Every answer includes verified sources and confidence scores
                    </p>
                  </motion.div>
                </div>
              </motion.div>
            )}

            {/* Chat Interface */}
            <ChatInterface 
              messages={messages}
              isLoading={isLoading}
              onSendMessage={sendMessage}
            />

            {/* Loading State */}
            {isLoading && messages.length === 0 && (
              <LoadingSkeleton />
            )}
          </div>
        </main>
      </div>

      {/* Mobile Menu Overlay */}
      {sidebarOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  )
}

export default App
