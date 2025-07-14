import { useContext, useCallback, useRef } from 'react'
import { useSelector } from 'react-redux'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'

export const useExternalOAuth = () => {
  const { extensionSDK } = useContext(ExtensionContext)
  const { settings } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )
  
  // Track if we've already opened the external window to prevent duplicates
  const hasOpenedWindow = useRef(false)
  
  const EXTERNAL_OAUTH_CONNECTION_ID = settings['external_oauth_connection_id']?.value as string || '22'

  const openExternalOAuthWindow = useCallback(() => {
    // Prevent opening multiple windows
    if (hasOpenedWindow.current) {
      console.log('External OAuth window already opened, skipping duplicate')
      return false
    }

    if (!EXTERNAL_OAUTH_CONNECTION_ID) {
      console.log('No external OAuth connection ID configured')
      return false
    }

    try {
      console.log(`Opening external OAuth window for connection ID: ${EXTERNAL_OAUTH_CONNECTION_ID}`)
      extensionSDK.openBrowserWindow(`https://looker-poc.micron.com/external_oauth/authenticate/${EXTERNAL_OAUTH_CONNECTION_ID}`)
      hasOpenedWindow.current = true
      return true
    } catch (error) {
      console.error('Failed to open external OAuth window:', error)
      return false
    }
  }, [extensionSDK, EXTERNAL_OAUTH_CONNECTION_ID])

  const resetWindowState = useCallback(() => {
    hasOpenedWindow.current = false
  }, [])

  return {
    openExternalOAuthWindow,
    resetWindowState,
    hasOpenedWindow: hasOpenedWindow.current
  }
}
