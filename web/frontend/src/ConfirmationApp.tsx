import { useCallback, useEffect, useRef, useState } from 'react'

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
  if (status === 'ready') {
    return <span className="confirmation-spinner" />
  }

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

  return null
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
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>(token ? 'loading' : 'error')
  const [message, setMessage] = useState(token ? '' : 'This confirmation link is missing or invalid.')
  const confirmationStarted = useRef(false)

  const confirmSubscription = useCallback(async () => {
    setStatus('loading')
    setMessage('')
    try {
      await dataSource.confirm(token)
      setMessage("You're subscribed! The next prediction will arrive by email.")
      setStatus('success')
      const url = new URL(window.location.href)
      url.searchParams.delete('subscription_token')
      window.history.replaceState({}, '', url)
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : 'Unable to confirm this subscription.')
      setStatus('error')
    }
  }, [dataSource, token])

  useEffect(() => {
    if (!token || confirmationStarted.current) return
    confirmationStarted.current = true

    // The email link only loads this page. Link scanners that only fetch the URL cannot trigger the POST.
    void confirmSubscription()
  }, [confirmSubscription, token])

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
              <a className="confirmation-home-link" href="/">Return to home</a>
            </>
          ) : (
            <>
              <h1>{status === 'error' ? 'Could not confirm subscription' : 'Confirming subscription...'}</h1>
              {status === 'error' && (
                <>
                  <p>{message}</p>
                  <a className="confirmation-home-link" href="/">Return to home</a>
                </>
              )}
            </>
          )}
        </section>
      </main>
    </div>
  )
}

export default ConfirmationApp
