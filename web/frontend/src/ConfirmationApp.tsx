import { useState } from 'react'

export type ConfirmationDataSource = {
  confirm: (token: string) => Promise<{ message: string }>
}

const httpConfirmationDataSource: ConfirmationDataSource = {
  async confirm(token) {
    const response = await fetch('/api/subscriptions/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    })
    const body = await response.json()
    if (!response.ok) throw new Error(body.detail ?? 'Unable to confirm this subscription.')
    return body
  },
}

function ConfirmationIcon({ status }: { status: 'ready' | 'success' | 'error' }) {
  if (status === 'success') {
    return (
      <svg aria-hidden="true" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="m5 12 4 4L19 6" />
      </svg>
    )
  }

  if (status === 'error') {
    return (
      <svg aria-hidden="true" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v4m0 4h.01M10.3 4.3 2.6 17.6A1.6 1.6 0 0 0 4 20h16a1.6 1.6 0 0 0 1.4-2.4L13.7 4.3a2 2 0 0 0-3.4 0Z" />
      </svg>
    )
  }

  return (
    <svg aria-hidden="true" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 6.8 12 13l9-6.2M5 19h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2Z" />
    </svg>
  )
}

function ConfirmationApp({
  dataSource = httpConfirmationDataSource,
  initialToken,
}: {
  dataSource?: ConfirmationDataSource
  initialToken?: string
}) {
  const [token] = useState(
    () => initialToken ?? new URLSearchParams(window.location.search).get('subscription_token') ?? '',
  )
  const [status, setStatus] = useState<'ready' | 'loading' | 'success' | 'error'>(token ? 'ready' : 'error')
  const [message, setMessage] = useState(token ? '' : 'This confirmation link is missing or invalid.')

  async function confirmSubscription() {
    setStatus('loading')
    setMessage('')
    try {
      const body = await dataSource.confirm(token)
      setMessage(body.message)
      setStatus('success')
      const url = new URL(window.location.href)
      url.searchParams.delete('subscription_token')
      window.history.replaceState({}, '', url)
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : 'Unable to confirm this subscription.')
      setStatus('error')
    }
  }

  const iconStatus = status === 'loading' ? 'ready' : status

  return (
    <div className="confirmation-app">
      <header className="border-b border-slate-200 bg-white">
        <div className="site-header-inner page-shell">
          <a className="site-brand" href="/" aria-label="NBA MVP Predictor home">
            <span className="logo-mark" aria-hidden="true">🏀</span>
            <p className="site-title">NBA MVP Predictions</p>
          </a>
        </div>
      </header>

      <main className="confirmation-main">
        <section className={`confirmation-panel confirmation-panel-${iconStatus}`}>
          <span className="confirmation-icon">
            <ConfirmationIcon status={iconStatus} />
          </span>

          {status === 'success' ? (
            <>
              <h1>Subscription confirmed</h1>
              <p>{message}</p>
              <a className="confirmation-home-link" href="/">View the latest predictions</a>
            </>
          ) : (
            <>
              <h1>{status === 'error' ? 'Could not confirm subscription' : 'Confirm your subscription'}</h1>
              <p>
                {message || 'Confirm that you want to receive NBA MVP predictions by email during the season.'}
              </p>
              {token && (
                <button
                  className="subscribe-button confirmation-button"
                  type="button"
                  disabled={status === 'loading'}
                  onClick={confirmSubscription}
                >
                  {status === 'loading' ? 'Confirming…' : status === 'error' ? 'Try again' : 'Confirm subscription'}
                </button>
              )}
            </>
          )}
        </section>
      </main>
    </div>
  )
}

export default ConfirmationApp
