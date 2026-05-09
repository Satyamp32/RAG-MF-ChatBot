# Mutual Fund RAG ChatBot Frontend

A premium dark-themed React frontend for the Mutual Fund RAG ChatBot, built with modern technologies and best practices.

## Features

### 🎨 Design & UI
- **Stitch-Inspired Dark Theme**: Premium dark theme with carefully crafted color palette
- **Responsive Design**: Mobile-first approach with breakpoints for all screen sizes
- **Smooth Animations**: Framer Motion for fluid transitions and micro-interactions
- **Modern Components**: Reusable UI primitives with consistent design system
- **Loading States**: Beautiful skeleton screens and loading indicators
- **Streaming Support**: Real-time response streaming with typing indicators

### 🔧 Technical Stack
- **React 18**: Modern React with hooks and functional components
- **TypeScript**: Full type safety and IntelliSense support
- **Vite**: Fast development server and optimized builds
- **TailwindCSS**: Utility-first CSS with custom design system
- **Framer Motion**: Production-ready animation library
- **Lucide React**: Beautiful icon library
- **React Hot Toast**: Elegant notification system

### 📱 Responsive Features
- **Mobile-First**: Optimized for mobile devices
- **Touch-Friendly**: Large tap targets and touch interactions
- **Adaptive Layout**: Sidebar collapses on mobile, full width on desktop
- **Flexible Grid**: Responsive grid layouts for all screen sizes

### 🛡️ Performance Optimizations
- **Code Splitting**: Automatic code splitting with React.lazy
- **Tree Shaking**: Dead code elimination in production builds
- **Image Optimization**: Lazy loading and optimization
- **Bundle Analysis**: Built-in bundle analyzer
- **Caching**: Component-level caching strategies

## Project Structure

```
frontend/
├── public/                 # Static assets
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── ChatInterface.tsx
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   ├── MessageBubble.tsx
│   │   ├── SourceCitation.tsx
│   │   ├── ConfidenceBadge.tsx
│   │   ├── LoadingDots.tsx
│   │   └── LoadingSkeleton.tsx
│   ├── hooks/           # Custom React hooks
│   │   ├── useChat.ts
│   │   └── useApi.ts
│   ├── services/        # API integration
│   │   └── api.ts
│   ├── types/          # TypeScript type definitions
│   │   └── chat.ts
│   ├── lib/            # Utility functions
│   │   └── utils.ts
│   ├── styles/         # Global styles
│   │   └── globals.css
│   ├── App.tsx         # Main application component
│   └── main.tsx        # Application entry point
├── package.json          # Dependencies and scripts
├── vite.config.ts        # Vite configuration
├── tailwind.config.js   # TailwindCSS configuration
├── tsconfig.json        # TypeScript configuration
└── README.md            # This file
```

## Getting Started

### Prerequisites
- Node.js 16+ 
- npm or yarn package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   # or
   yarn install
   ```

3. **Environment setup**
   ```bash
   cp .env.example .env
   # Edit .env with your API configuration
   ```

### Development

1. **Start development server**
   ```bash
   npm run dev
   # or
   yarn dev
   ```

2. **Access the application**
   - Open http://localhost:3000 in your browser
   - The app will automatically reload on changes

### Building for Production

```bash
npm run build
# or
yarn build
```

The build will be created in the `dist/` directory.

### Environment Variables

Create a `.env` file in the root directory:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Component Overview

### Core Components

#### ChatInterface
Main chat interface with:
- Message input with auto-resize
- Streaming response display
- Suggested prompt cards
- Copy to clipboard functionality
- Mobile-optimized layout

#### Sidebar
Collapsible sidebar featuring:
- Navigation menu
- Suggested questions by category
- Chat history management
- API connection status

#### Header
Sticky header with:
- Application branding
- Health status indicator
- Mobile menu toggle
- Responsive navigation

#### Message Components
- **MessageBubble**: Styled message bubbles with animations
- **SourceCitation**: Clickable source links with metadata
- **ConfidenceBadge**: Visual confidence indicators
- **LoadingDots**: Animated loading indicators
- **LoadingSkeleton**: Beautiful skeleton screens

### Hooks

#### useChat
Chat state management with:
- Message history
- Loading states
- Error handling
- Message sending logic

#### useApi
API integration with:
- Health checking
- Error handling
- Response parsing
- Automatic retries

### Design System

#### Color Palette
- **Background**: Deep blacks (#0a0a0a, #111111, #1a1a1a)
- **Text**: High contrast whites (#ffffff, #a0a0a0, #808080)
- **Accent**: Professional blue (#3b82f6, #2563eb, #1e3a8a)
- **Success**: Green (#10b981, #064e3b)
- **Warning**: Orange (#f59e0b, #451a03)
- **Error**: Red (#ef4444, #450a0a)

#### Typography
- **Font**: Inter font family
- **Sizes**: Responsive type scale
- **Weights**: 300, 400, 500, 600, 700

#### Animations
- **Entrances**: Fade-in, slide-up effects
- **Loading**: Shimmer and pulse animations
- **Interactions**: Hover and tap animations
- **Transitions**: Smooth state transitions

### API Integration

#### Backend Connection
- **Base URL**: Configurable API endpoint
- **Health Checks**: Periodic health monitoring
- **Error Handling**: Graceful error recovery
- **Request Queue**: Prevent duplicate requests

#### Response Handling
- **Streaming**: Real-time response streaming
- **Parsing**: Automatic response structure parsing
- **Validation**: Response validation and sanitization
- **Caching**: Response caching for performance

## Performance Features

### Optimization Strategies
- **Lazy Loading**: Components loaded on demand
- **Memoization**: Expensive computations cached
- **Debouncing**: Input validation debounced
- **Virtual Scrolling**: Large lists optimized
- **Bundle Splitting**: Code split by route

### Monitoring

### Development Tools
- **Hot Reload**: Instant development feedback
- **Error Overlay**: Development error display
- **Bundle Analyzer**: Build size optimization
- **Performance Metrics**: Runtime performance tracking

## Browser Support

### Modern Browsers
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Mobile Support
- iOS Safari 14+
- Chrome Mobile 90+
- Samsung Internet 8+

## Contributing

### Development Guidelines
1. **Component Structure**: Follow established patterns
2. **Type Safety**: Maintain TypeScript compliance
3. **Performance**: Optimize for 60fps animations
4. **Accessibility**: WCAG 2.1 AA compliance
5. **Mobile-First**: Test on all screen sizes

### Code Style
- **ESLint**: Consistent code formatting
- **Prettier**: Automated code formatting
- **TypeScript**: Strict type checking
- **Comments**: Document complex logic

## Deployment

### Production Build
```bash
npm run build
# Output: dist/ directory
# Ready for deployment to any static hosting
```

### Environment Configuration
```bash
# Production
VITE_API_BASE_URL=https://your-api-domain.com

# Development
VITE_API_BASE_URL=http://localhost:8000
```

## Security Features

### Implementation
- **CORS**: Configured for API communication
- **Content Security**: CSP headers implemented
- **Input Validation**: XSS prevention
- **API Keys**: Environment variable storage
- **Error Handling**: No sensitive data exposure

### Best Practices
- **HTTPS**: Enforce secure connections
- **Rate Limiting**: Prevent API abuse
- **Input Sanitization**: Clean user inputs
- **Error Boundaries**: Graceful error handling

## Troubleshooting

### Common Issues

#### Build Errors
- **TypeScript**: Check type definitions
- **Dependencies**: Verify package versions
- **Environment**: Check .env configuration

#### Runtime Issues
- **API Connection**: Verify backend is running
- **CORS**: Check API configuration
- **Performance**: Monitor bundle size

### Debug Mode
```bash
# Enable detailed logging
VITE_DEBUG=true

# Start development server
npm run dev
```

## Future Enhancements

### Planned Features
- **Offline Support**: Service Worker implementation
- **Push Notifications**: Real-time alerts
- **Advanced Search**: Filter and sort capabilities
- **User Preferences**: Customizable settings
- **Analytics**: Usage tracking (privacy-focused)
- **A/B Testing**: Feature rollout testing

### Technical Debt
- **Test Coverage**: Increase to 90%+
- **Bundle Size**: Optimize below 1MB
- **Performance**: 60fps animations on all devices
- **Accessibility**: Full WCAG compliance

---

Built with ❤️ using React, TypeScript, Vite, and TailwindCSS
