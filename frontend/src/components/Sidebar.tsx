import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Trash2, Settings, HelpCircle, Sparkles } from 'lucide-react'
import { toast } from 'react-hot-toast'

interface SidebarProps {
  onClose: () => void
  onClearChat: () => void
}

const menuItems = [
  {
    icon: Sparkles,
    label: 'New Chat',
    action: 'clear'
  },
  {
    icon: Settings,
    label: 'Settings',
    action: 'settings'
  },
  {
    icon: HelpCircle,
    label: 'Help',
    action: 'help'
  }
]

const suggestedQuestions = [
  {
    category: 'Performance',
    questions: [
      'What is the expense ratio of HDFC Equity Fund?',
      'Tell me about the returns of Axis Bluechip Fund',
      'How has Nifty 50 performed recently?'
    ]
  },
  {
    category: 'Investment Details',
    questions: [
      'What is the minimum SIP amount?',
      'What is the lock-in period for ELSS funds?',
      'How to invest in mutual funds online?'
    ]
  },
  {
    category: 'Risk & Taxation',
    questions: [
      'What is exit load in mutual funds?',
      'How are mutual fund returns taxed?',
      'What is the risk level of small-cap funds?'
    ]
  }
]

export default function Sidebar({ onClose, onClearChat }: SidebarProps) {
  const handleClearChat = () => {
    onClearChat()
    toast.success('Chat history cleared')
  }

  const handleQuestionClick = (question: string) => {
    // This would send the question to the chat
    // For now, just show a toast
    toast.info('Question copied to chat input')
    onClose()
  }

  return (
    <motion.div
      initial={{ x: -300 }}
      animate={{ x: 0 }}
      exit={{ x: -300 }}
      transition={{ type: 'spring', damping: 25, stiffness: 200 }}
      className="fixed inset-y-0 left-0 z-50 w-80 bg-background-card border-r border-border lg:block"
    >
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold text-text">Menu</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-background-hover rounded-lg transition-colors"
          >
            <X className="w-4 h-4 text-text-secondary" />
          </button>
        </div>

        {/* Menu Items */}
        <div className="p-4 space-y-2">
          {menuItems.map((item, index) => (
            <motion.button
              key={index}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                if (item.action === 'clear') {
                  handleClearChat()
                } else {
                  toast.info(`${item.label} coming soon`)
                }
              }}
              className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-background-hover transition-colors text-left"
            >
              <item.icon className="w-5 h-5 text-accent" />
              <span className="text-text font-medium">{item.label}</span>
            </motion.button>
          ))}
        </div>

        {/* Suggested Questions */}
        <div className="flex-1 overflow-y-auto p-4">
          <h3 className="text-sm font-medium text-text-secondary mb-4">Suggested Questions</h3>
          <div className="space-y-4">
            {suggestedQuestions.map((category, categoryIndex) => (
              <div key={categoryIndex} className="mb-6">
                <h4 className="text-xs font-medium text-text-muted uppercase tracking-wider mb-3">
                  {category.category}
                </h4>
                <div className="space-y-2">
                  {category.questions.map((question, questionIndex) => (
                    <motion.button
                      key={questionIndex}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => handleQuestionClick(question)}
                      className="w-full text-left p-3 rounded-lg bg-background-tertiary hover:bg-background-hover transition-colors text-sm"
                    >
                      {question}
                    </motion.button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border">
          <div className="text-xs text-text-muted space-y-2">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-success rounded-full"></div>
              <span>API Connected</span>
            </div>
            <div className="text-text-tertiary">
              Version 1.0.0
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
