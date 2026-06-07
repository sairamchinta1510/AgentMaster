import { StrictMode, Component, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null };
  static getDerivedStateFromError(e: Error) { return { error: e }; }
  render() {
    if (this.state.error) {
      const err = this.state.error as Error;
      return (
        <div style={{ background: '#0a0a0a', color: '#f87171', fontFamily: 'monospace', padding: '2rem', height: '100vh' }}>
          <div style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>⚠ Runtime Error</div>
          <pre style={{ background: '#1a1a1a', padding: '1rem', borderRadius: '8px', whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>
            {err.message}{'\n\n'}{err.stack}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
