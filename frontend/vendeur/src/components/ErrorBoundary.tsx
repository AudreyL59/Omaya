import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
  errorInfo: ErrorInfo | null
}

/**
 * Capture les exceptions React non gérées pour éviter que toute l'app
 * disparaisse (page blanche). Affiche un fallback avec le message d'erreur
 * pour faciliter le diagnostic.
 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, errorInfo: null }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log console (visible en F12) + state pour rendu
    console.error('[ErrorBoundary]', error)
    console.error('[ErrorBoundary] componentStack:', errorInfo.componentStack)
    this.setState({ errorInfo })
  }

  handleReset = () => {
    this.setState({ error: null, errorInfo: null })
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (!this.state.error) return this.props.children

    const err = this.state.error
    const stack = this.state.errorInfo?.componentStack || ''

    return (
      <div className="min-h-screen flex items-center justify-center p-6 bg-gray-50">
        <div className="max-w-2xl w-full bg-white rounded-xl border border-red-200 shadow-sm">
          <div className="px-6 py-4 border-b border-red-100 bg-red-50 rounded-t-xl flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-600" />
            <h2 className="font-semibold text-red-900">Une erreur est survenue</h2>
          </div>
          <div className="p-6 space-y-4">
            <p className="text-sm text-gray-700">
              L'application a rencontré une erreur inattendue. Tu peux essayer de
              recharger ou de revenir en arrière.
            </p>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-xs font-mono text-gray-800 overflow-auto max-h-64">
              <div className="font-semibold text-red-700 mb-1">{err.name}: {err.message}</div>
              {err.stack && (
                <pre className="whitespace-pre-wrap text-gray-600 text-[11px] leading-relaxed">
                  {err.stack}
                </pre>
              )}
              {stack && (
                <pre className="whitespace-pre-wrap text-gray-500 text-[11px] leading-relaxed mt-2 pt-2 border-t border-gray-200">
                  {stack}
                </pre>
              )}
            </div>
            <div className="flex gap-2">
              <button
                onClick={this.handleReload}
                className="flex items-center gap-1.5 px-3 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800"
              >
                <RefreshCw className="w-4 h-4" />
                Recharger la page
              </button>
              <button
                onClick={this.handleReset}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50"
              >
                Réessayer
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }
}
