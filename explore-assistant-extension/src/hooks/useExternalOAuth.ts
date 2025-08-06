import { useContext, useCallback, useRef, useState, useEffect } from 'react'
import { useSelector } from 'react-redux'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'

export const useExternalOAuth = () => {
  const { extensionSDK, core40SDK } = useContext(ExtensionContext)
  const { settings, oauth } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )
  
  // Track if we've already opened the external window to prevent duplicates
  const hasOpenedWindow = useRef(false)
  const hasAutoExecuted = useRef(false) // Track if we've run the auto execution
  const [connectionTestResult, setConnectionTestResult] = useState<boolean | null>(null)
  const [isTestingConnection, setIsTestingConnection] = useState(false)
  const [testQueryUrl, setTestQueryUrl] = useState<string | null>(null)
  
  const EXTERNAL_OAUTH_CONNECTION_ID = settings['external_oauth_connection_id']?.value as string || '22'

  const testConnection = useCallback(async (): Promise<boolean> => {
    setIsTestingConnection(true)
    try {
      console.log('Testing OAuth connection by finding connection with oauth_test in name...')
      
      // First, get all connections to find one with 'oauth_test' in the name
      const connections = await core40SDK.ok(core40SDK.all_connections())
      
      if (!connections || !Array.isArray(connections)) {
        console.log('Failed to fetch connections')
        setConnectionTestResult(false)
        return false
      }
      
      // Find a connection with 'oauth_test' in the name
      const oauthTestConnection = connections.find(conn => 
        conn.name && conn.name.toLowerCase().includes('oauth_test')
      )
      
      if (!oauthTestConnection) {
        console.log('No connection found with "oauth_test" in name')
        setConnectionTestResult(true)
        return true
      }
      
      console.log(`Found OAuth test connection: ${oauthTestConnection.name}`)
      
      // Now find a model/explore that uses this connection for testing  
      const models = await core40SDK.ok(core40SDK.all_lookml_models({ fields: 'name,explores' }))
      
      if (!models || !Array.isArray(models)) {
        console.log('Failed to fetch models')
        setConnectionTestResult(false)
        return false
      }
      
      // Search through models and explores to find one using our OAuth test connection
      let testModel: any = null
      let testExplore: any = null
      
      for (const model of models) {
        if (model.explores && model.explores.length > 0) {
          // Check each explore in this model
          for (const navExplore of model.explores) {
            try {
              // Get full explore details to check connection_name
              const fullExplore = await core40SDK.ok(
                core40SDK.lookml_model_explore({
                  lookml_model_name: model.name!,
                  explore_name: navExplore.name!,
                  fields: 'connection_name,name'
                })
              )
              
              if (fullExplore && fullExplore.connection_name === oauthTestConnection.name) {
                testModel = model
                testExplore = fullExplore
                console.log(`Found matching explore: ${model.name}:${navExplore.name} using connection ${fullExplore.connection_name}`)
                break
              }
            } catch (error) {
              console.log(`Error fetching explore details for ${model.name}:${navExplore.name}:`, error)
              continue
            }
          }
          if (testModel && testExplore) break
        }
      }
      
      if (!testModel || !testExplore) {
        console.log(`No explore found using connection ${oauthTestConnection.name}. Aborting ouath backend test.`)
        setConnectionTestResult(true)
        return true
      }
      console.log(`Testing with model: ${testModel.name}, explore: ${testExplore.name}`)
      
      // Run a simple "SELECT 1" equivalent query using dynamic fields
      const testQuery = await core40SDK.run_inline_query({
        result_format: 'json',
        body: {
          model: testModel.name!,
          view: testExplore.name!,
          fields: ["test_field"],
          limit: "1",
          column_limit: "1",
          vis_config: {},
          filter_config: {},
          dynamic_fields: "[{\"category\":\"dimension\",\"expression\":\"1\",\"label\":\"Test Field\",\"value_format\":null,\"value_format_name\":\"id\",\"dimension\":\"test_field\",\"_kind_hint\":\"dimension\",\"_type_hint\":\"number\"}]"
        }
      })
      
      console.log('OAuth connection test query result:', testQuery)
      
      // Set test query URL for reference
      const extensionHostUrl = extensionSDK?.lookerHostData?.hostUrl || 'https://looker.mycompany.com'
      const fullUrl = `${extensionHostUrl}/api/4.0/queries/models/${testModel.name}/views/${testExplore.name}/run/json`
      setTestQueryUrl(fullUrl)
      
      // Check if the query was successful
      if (testQuery.ok) {
        console.log('OAuth connection test successful - query executed without errors')
        setConnectionTestResult(true)
        return true
      } else {
        console.log('OAuth connection test failed:', testQuery.error)
        setConnectionTestResult(false)
        return false
      }
    } catch (error) {
      console.error('Failed to test OAuth connection:', error)
      setConnectionTestResult(false)
      return false
    } finally {
      setIsTestingConnection(false)
    }
  }, [extensionSDK, core40SDK])

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

    // Test the connection first
    console.log('Testing connection before opening external OAuth window...')
    const connectionIsValid = await testConnection()
    
    if (connectionIsValid) {
      console.log('Connection is already valid - no need to open external OAuth window')
      return false
    }
    
    console.log('Connection test failed or OAuth needs refresh - proceeding to open OAuth window')

    try {
      const host_name = extensionSDK?.lookerHostData?.hostOrigin || 'https://looker.mycompany.com'
      const extensionId = extensionSDK.lookerHostData?.extensionId
      const extensionContext = extensionSDK?.lookerHostData?.route 
      const redirect_uri = encodeURIComponent(`${host_name}/extensions/${extensionId}${extensionContext}`)
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
