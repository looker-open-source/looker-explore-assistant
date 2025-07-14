import { useContext, useCallback, useRef, useState } from 'react'
import { useSelector } from 'react-redux'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'

export const useExternalOAuth = () => {
  const { extensionSDK, core40SDK } = useContext(ExtensionContext)
  const { settings } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )
  
  // Track if we've already opened the external window to prevent duplicates
  const hasOpenedWindow = useRef(false)
  const [connectionTestResult, setConnectionTestResult] = useState<boolean | null>(null)
  const [isTestingConnection, setIsTestingConnection] = useState(false)
  
  const EXTERNAL_OAUTH_CONNECTION_ID = settings['external_oauth_connection_id']?.value as string || '22'
  const EXTERNAL_CONNECTION_NAME = settings['external_connection_using_oauth']?.value as string || ''

  const testConnection = useCallback(async (): Promise<boolean> => {
    if (!EXTERNAL_CONNECTION_NAME) {
      console.log('No external connection name configured for testing')
      return false
    }

    setIsTestingConnection(true)
    try {
      console.log(`Testing connection: ${EXTERNAL_CONNECTION_NAME}`)
      
      // Test the connection using the Looker SDK
      // Use plain array - the SDK should handle DelimArray conversion internally
      const response = await core40SDK.test_connection(
        EXTERNAL_CONNECTION_NAME,
        'connect' as any
      )
      
      console.log('Connection test response:', response)
      
      // Check if the connection test was successful
      if (response.ok && Array.isArray(response.value)) {
        const connectTest = response.value.find(test => test.name === 'connect')
        const isSuccessful = connectTest?.status === 'success'
        
        setConnectionTestResult(isSuccessful)
        
        if (isSuccessful) {
          console.log('Connection test successful - OAuth connection is valid')
        } else {
          console.log('Connection test failed:', connectTest?.message || 'Unknown error')
        }
        
        return isSuccessful
      } else {
        console.error('Invalid response from connection test:', response)
        setConnectionTestResult(false)
        return false
      }
    } catch (error) {
      console.error('Failed to test connection:', error)
      setConnectionTestResult(false)
      return false
    } finally {
      setIsTestingConnection(false)
    }
  }, [core40SDK, EXTERNAL_CONNECTION_NAME])

  const openExternalOAuthWindow = useCallback(async () => {
    // Prevent opening multiple windows
    if (hasOpenedWindow.current) {
      console.log('External OAuth window already opened, skipping duplicate')
      return false
    }

    if (!EXTERNAL_OAUTH_CONNECTION_ID) {
      console.log('No external OAuth connection ID configured')
      return false
    }

    // If we have a connection name, test it first
    if (EXTERNAL_CONNECTION_NAME) {
      console.log('Testing connection before opening external OAuth window...')
      const connectionIsValid = await testConnection()
      
      if (connectionIsValid) {
        console.log('Connection is already valid - no need to open external OAuth window')
        return false
      }
      
      console.log('Connection test failed or connection needs refresh - proceeding to open OAuth window')
    } else {
      console.log('No connection name configured for testing - proceeding to open OAuth window')
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
  }, [extensionSDK, EXTERNAL_OAUTH_CONNECTION_ID, EXTERNAL_CONNECTION_NAME, testConnection])

  const resetWindowState = useCallback(() => {
    hasOpenedWindow.current = false
    setConnectionTestResult(null)
  }, [])

  return {
    openExternalOAuthWindow,
    testConnection,
    resetWindowState,
    hasOpenedWindow: hasOpenedWindow.current,
    connectionTestResult,
    isTestingConnection
  }
}
