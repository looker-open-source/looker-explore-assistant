import { useContext, useEffect, useRef } from 'react'
import { ExtensionContext } from '@looker/extension-sdk-react'

export const useOAuthConnectionCheck = () => {
  const { core40SDK } = useContext(ExtensionContext)
  
  // Track if we've already checked connections to prevent multiple calls
  const hasCheckedConnections = useRef(false)

  const findOAuthConnections = async () => {
    if (!core40SDK) {
      console.error('Core40 SDK is not available')
      return null
    }

    try {
      console.log('Getting all connections to identify OAuth connections...')
      
      let connectionTestResults: any[] = []
      
      // Get all connections using the standard SDK method
      const sdkConnections = await core40SDK.ok(
        core40SDK.all_connections()
      )
      console.log('Standard SDK connections:', sdkConnections)
      
      // Identify OAuth connections directly from all_connections() response
      console.log('Identifying OAuth connections from all_connections() data...')
      const oauthConnectionsToTest = new Map<string, any>() // Map of oauth_application_id -> connection
      
      // Filter connections that have oauth_application_id (real OAuth connections)
      for (const conn of sdkConnections) {
        if (conn.oauth_application_id && conn.oauth_application_id !== null) {
          const oauthId = conn.oauth_application_id
          
          // Only keep the first connection for each unique OAuth application ID to avoid duplicates
          if (!oauthConnectionsToTest.has(oauthId)) {
            oauthConnectionsToTest.set(oauthId, conn)
            console.log(`Found OAuth connection: ${conn.name} with OAuth App ID: ${oauthId}`)
          } else {
            console.log(`Skipping duplicate OAuth App ID ${oauthId} for connection: ${conn.name}`)
          }
        }
      }
      
      console.log(`Found ${oauthConnectionsToTest.size} unique OAuth connections to test`)
      
      // Test connections to determine OAuth status
      console.log('Testing unique OAuth connections to determine authentication status...')
      connectionTestResults = []
      
      // Test the unique OAuth connections
      if (oauthConnectionsToTest.size > 0) {
        console.log(`Testing ${oauthConnectionsToTest.size} unique OAuth connections...`)
        
        for (const [oauthAppId, conn] of oauthConnectionsToTest) {
          try {
            console.log(`Testing OAuth connection: ${conn.name} (OAuth App ID: ${oauthAppId})`)
            const testResult = await core40SDK.ok(
              core40SDK.test_connection(conn.name!)
            )
            
            // test_connection returns an array, so get the first result
            const firstResult = Array.isArray(testResult) ? testResult[0] : testResult
            
            const connectionResult = {
              name: conn.name,
              dialect: conn.dialect_name,
              database: conn.database,
              oauthAppId: oauthAppId,
              oauthAppName: conn.oauth_application_name,
              testStatus: firstResult?.status || 'unknown',
              message: firstResult?.message || 'No message',
              needsAuth: firstResult?.status === 'error' && 
                        (firstResult?.message?.toLowerCase().includes('oauth') ||
                         firstResult?.message?.toLowerCase().includes('auth') ||
                         firstResult?.message?.toLowerCase().includes('login') ||
                         firstResult?.message?.toLowerCase().includes('credential') ||
                         firstResult?.message?.toLowerCase().includes('unauthorized')),
              testResult: firstResult
            }
            
            connectionTestResults.push(connectionResult)
            console.log(`OAuth connection ${conn.name} test result:`, connectionResult)
            
          } catch (testError: any) {
            console.log(`Failed to test OAuth connection ${conn.name}:`, testError?.message || testError)
            
            // Some test failures might indicate auth issues
            const authRelatedError = testError?.message && (
              testError.message.toLowerCase().includes('oauth') ||
              testError.message.toLowerCase().includes('auth') ||
              testError.message.toLowerCase().includes('login') ||
              testError.message.toLowerCase().includes('credential') ||
              testError.message.toLowerCase().includes('unauthorized')
            )
            
            connectionTestResults.push({
              name: conn.name,
              dialect: conn.dialect_name,
              database: conn.database,
              oauthAppId: oauthAppId,
              oauthAppName: conn.oauth_application_name,
              testStatus: 'error',
              message: testError?.message || 'Test failed',
              needsAuth: authRelatedError,
              testResult: null
            })
          }
        }
      } else {
        console.log('No OAuth connections found to test')
      }
      
      // Summary of connections that need authentication
      const connectionsNeedingAuth = connectionTestResults.filter(result => result.needsAuth)
      if (connectionsNeedingAuth.length > 0) {
        console.log('🔐 OAuth connections that need authentication:')
        connectionsNeedingAuth.forEach(conn => {
          console.log(`  - ${conn.name} (${conn.dialect}) - OAuth App: ${conn.oauthAppName || conn.oauthAppId}`)
          console.log(`    Message: ${conn.message}`)
        })
      }
      
      const successfulConnections = connectionTestResults.filter(result => result.testStatus === 'success')
      if (successfulConnections.length > 0) {
        console.log('✅ Successfully authenticated OAuth connections:')
        successfulConnections.forEach(conn => {
          console.log(`  - ${conn.name} (${conn.dialect}) - OAuth App: ${conn.oauthAppName || conn.oauthAppId}`)
        })
      }
      
      const failedConnections = connectionTestResults.filter(result => 
        result.testStatus === 'error' && !result.needsAuth)
      if (failedConnections.length > 0) {
        console.log('❌ OAuth connections with other errors:')
        failedConnections.forEach(conn => {
          console.log(`  - ${conn.name} (${conn.dialect}) - ${conn.message}`)
        })
      }
      
      // Provide actionable summary
      if (connectionsNeedingAuth.length > 0) {
        console.log(`\n📋 SUMMARY: Found ${connectionsNeedingAuth.length} OAuth connection(s) that need user authentication`)
        const uniqueOAuthApps = [...new Set(connectionsNeedingAuth.map(c => c.oauthAppId))]
        console.log(`   Unique OAuth applications requiring auth: ${uniqueOAuthApps.length}`)
      } else if (successfulConnections.length > 0) {
        console.log(`\n📋 SUMMARY: All ${successfulConnections.length} OAuth connections are properly authenticated`)
      } else {
        console.log('\n📋 SUMMARY: No OAuth connections found or tested')
      }
      
      return {
        standardConnections: sdkConnections,
        oauthConnectionsToTest: Array.from(oauthConnectionsToTest.values()),
        connectionTestResults,
      }
      
    } catch (error) {
      console.error('Error in findOAuthConnections:', error)
      return null
    }
  }

  useEffect(() => {
    // Only run the connection check once per app session
    if (!hasCheckedConnections.current && core40SDK) {
      hasCheckedConnections.current = true
      console.log('🔍 Running OAuth connection check (once per session)...')
      findOAuthConnections()
    }
  }, [core40SDK]) // Only depend on core40SDK availability

  return {
    findOAuthConnections, // Export for manual calls if needed
    hasCheckedConnections: hasCheckedConnections.current
  }
}
