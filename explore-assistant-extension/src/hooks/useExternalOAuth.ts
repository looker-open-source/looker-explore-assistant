import { useContext, useCallback, useRef, useState, useEffect } from 'react'
import { useSelector } from 'react-redux'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'

export const useExternalOAuth = () => {
  const { extensionSDK, core40SDK } = useContext(ExtensionContext)
  const { settings, examples, oauth } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )
  
  // Track if we've already opened the external window to prevent duplicates
  const hasOpenedWindow = useRef(false)
  const hasAutoExecuted = useRef(false) // Track if we've run the auto execution
  const [connectionTestResult, setConnectionTestResult] = useState<boolean | null>(null)
  const [isTestingConnection, setIsTestingConnection] = useState(false)
  const [testQueryUrl, setTestQueryUrl] = useState<string | null>(null)
  
  const EXTERNAL_OAUTH_CONNECTION_ID = settings['external_oauth_connection_id']?.value as string || '22'

  // Helper function to get the first golden query for testing
  const getFirstGoldenQuery = useCallback(() => {
    const exploreEntries = examples.exploreEntries
    if (!exploreEntries || exploreEntries.length === 0) {
      return null
    }
    
    // Get the first entry that has both explore_id and output
    const firstEntry = exploreEntries.find(entry => 
      entry['golden_queries.explore_id'] && entry['golden_queries.output']
    )
    
    if (!firstEntry) {
      return null
    }
    
    return {
      exploreId: firstEntry['golden_queries.explore_id'],
      output: firstEntry['golden_queries.output']
    }
  }, [examples.exploreEntries])

  const testConnection = useCallback(async (): Promise<boolean> => {
    const goldenQuery = getFirstGoldenQuery()
    if (!goldenQuery) {
      console.log('No golden queries available for testing')
      setConnectionTestResult(false)
      return false
    }

    setIsTestingConnection(true)
    try {
      const [modelName, exploreName] = goldenQuery.exploreId.split(':')
      console.log(`Testing with simple query on ${modelName}:${exploreName}`)
      
      // Create a test query URL for reference
      const extensionHostUrl = extensionSDK?.lookerHostData?.hostUrl || 'https://looker.mycompany.com'
      const fullUrl = `${extensionHostUrl}/api/4.0/queries/models/${modelName}/views/${exploreName}/run/json?fields=one&sorts=one&limit=500`
      setTestQueryUrl(fullUrl)
      console.log('Generated test query URL:', fullUrl)
      
      // Run a simple test query using run_inline_query with static parameters
      const response = await core40SDK.run_inline_query({
        result_format: 'json',
        body: {
          model: modelName,
          view: exploreName,
          fields: ["one"],
          sorts: ["one"],
          limit: "500",
          column_limit: "50",
          vis_config: {},
          filter_config: {},
          dynamic_fields: "[{\"category\":\"dimension\",\"expression\":\"1\",\"label\":\"One\",\"value_format\":null,\"value_format_name\":\"id\",\"dimension\":\"one\",\"_kind_hint\":\"dimension\",\"_type_hint\":\"number\"}]"
        }
      })
      
      console.log('Test query response:', response)
      
      // Check if the query was successful
      if (response.ok) {
        console.log('Test query successful - OAuth connection is valid')
        setConnectionTestResult(true)
        return true
      } else {
        console.log('Test query failed:', response.error)
        setConnectionTestResult(false)
        return false
      }
    } catch (error) {
      console.error('Failed to test with simple query:', error)
      setConnectionTestResult(false)
      return false
    } finally {
      setIsTestingConnection(false)
    }
  }, [getFirstGoldenQuery, extensionSDK, core40SDK])

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

    // Test the connection using golden query first
    console.log('Testing connection with golden query before opening external OAuth window...')
    const connectionIsValid = await testConnection()
    
    if (connectionIsValid) {
      console.log('Connection is already valid - no need to open external OAuth window')
      return false
    }
    
    console.log('Connection test failed or OAuth needs refresh - proceeding to open OAuth window')

    try {
      const host_uri = extensionSDK?.lookerHostData?.hostUrl || 'https://looker.mycompany.com'
      const host_name = extensionSDK?.lookerHostData?.hostOrigin || 'https://looker.mycompany.com'
      const redirect_uri = encodeURIComponent(host_uri)
      console.log(`Opening external OAuth window for connection ID: ${EXTERNAL_OAUTH_CONNECTION_ID}?redirect_uri=${redirect_uri}`)
      extensionSDK.openBrowserWindow(`${host_name}/external_oauth/authenticate/${EXTERNAL_OAUTH_CONNECTION_ID}?redirect_uri=${redirect_uri}`)
      hasOpenedWindow.current = true
      return true
    } catch (error) {
      console.error('Failed to open external OAuth window:', error)
      return false
    }
  }, [extensionSDK, EXTERNAL_OAUTH_CONNECTION_ID, testConnection])

  const resetWindowState = useCallback(() => {
    hasOpenedWindow.current = false
    setConnectionTestResult(null)
  }, [])

  const resetAutoExecution = useCallback(() => {
    hasAutoExecuted.current = false
  }, [])

  // Auto-execute external OAuth after Google OAuth completes
  useEffect(() => {
    const autoExecuteExternalOAuth = async () => {
      // Only run once per session
      if (hasAutoExecuted.current) {
        return
      }

      // Must have Google OAuth token and external connection ID configured
      const hasGoogleToken = !!settings['identity_token']?.value
      const hasExternalConnectionId = !!EXTERNAL_OAUTH_CONNECTION_ID
      
      if (!hasGoogleToken || !hasExternalConnectionId) {
        return
      }

      // If Google OAuth is still authenticating, wait for it to complete
      if (oauth.isAuthenticating) {
        return
      }

      // For the case where there's already a valid token, we also need to check
      // if the BigQuery examples are loaded (which means the app is ready)
      const hasExploreEntries = examples.exploreEntries && examples.exploreEntries.length > 0
      
      // If we have a valid token but no explore entries yet, wait for them to load
      if (oauth.hasValidToken && !hasExploreEntries) {
        return
      }

      // If we don't have a valid token yet, wait for OAuth to complete
      if (!oauth.hasValidToken) {
        return
      }

      console.log('Auto-executing external OAuth after Google OAuth completion...')
      hasAutoExecuted.current = true

      try {
        // Test the connection first
        const connectionIsValid = await testConnection()
        
        if (!connectionIsValid) {
          // Only open external OAuth window if connection test fails
          console.log('Connection test failed, auto-opening external OAuth window...')
          await openExternalOAuthWindow()
        } else {
          console.log('Connection test passed, no external OAuth needed')
        }
      } catch (error) {
        console.error('Error in auto external OAuth execution:', error)
      }
    }

    autoExecuteExternalOAuth()
  }, [
    settings['identity_token']?.value,
    EXTERNAL_OAUTH_CONNECTION_ID,
    oauth.isAuthenticating,
    oauth.hasValidToken,
    examples.exploreEntries, // Add this dependency to trigger when examples load
    testConnection,
    openExternalOAuthWindow
  ])

  return {
    openExternalOAuthWindow,
    testConnection,
    resetWindowState,
    resetAutoExecution,
    hasOpenedWindow: hasOpenedWindow.current,
    connectionTestResult,
    isTestingConnection,
    testQueryUrl
  }
}
