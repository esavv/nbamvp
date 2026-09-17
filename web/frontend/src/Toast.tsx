import { Toast as BaseToast } from '@base-ui/react/toast'
import { toast } from './toast-manager.ts'

function StatusIcon({ type }: { type: string | undefined }) {
  if (type === 'success') {
    return (
      <svg aria-hidden="true" className="toast-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="m5 12 4 4L19 6" />
      </svg>
    )
  }

  return (
    <svg aria-hidden="true" className="toast-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v4m0 4h.01M10.3 4.3 2.6 17.6A1.6 1.6 0 0 0 4 20h16a1.6 1.6 0 0 0 1.4-2.4L13.7 4.3a2 2 0 0 0-3.4 0Z" />
    </svg>
  )
}

function ToastList() {
  const { toasts } = BaseToast.useToastManager()

  return toasts.map((item) => (
    <BaseToast.Root key={item.id} toast={item} className="toast-root">
      <BaseToast.Content className="toast-content">
        <span className="toast-status" aria-hidden="true">
          <StatusIcon type={item.type} />
        </span>
        <div className="toast-copy">
          <BaseToast.Title className="toast-title" />
          <BaseToast.Description className="toast-description" />
        </div>
        <BaseToast.Close className="toast-close" aria-label="Dismiss notification">
          <svg aria-hidden="true" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="m6 6 12 12M18 6 6 18" />
          </svg>
        </BaseToast.Close>
      </BaseToast.Content>
    </BaseToast.Root>
  ))
}

export function Toaster() {
  return (
    <BaseToast.Provider toastManager={toast} timeout={6000}>
      <BaseToast.Portal>
        <BaseToast.Viewport className="toast-viewport">
          <ToastList />
        </BaseToast.Viewport>
      </BaseToast.Portal>
    </BaseToast.Provider>
  )
}
