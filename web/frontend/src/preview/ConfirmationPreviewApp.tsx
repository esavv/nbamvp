import ConfirmationApp from '../ConfirmationApp.tsx'
import type { ConfirmationDataSource } from '../ConfirmationApp.tsx'

const previewConfirmationDataSource: ConfirmationDataSource = {
  async confirm() {
    await new Promise((resolve) => window.setTimeout(resolve, 900))
    return { message: "You're subscribed! The next NBA MVP prediction will arrive by email." }
  },
}

function ConfirmationPreviewApp() {
  return <ConfirmationApp dataSource={previewConfirmationDataSource} initialToken="preview-token" />
}

export default ConfirmationPreviewApp
