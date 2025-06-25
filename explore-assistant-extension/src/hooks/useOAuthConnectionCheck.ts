import { useContext, useEffect, useRef } from 'react'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { DelimArray } from '@looker/sdk-rtl'

export const useConnectionCheck = () => {
  const { core40SDK, extensionSDK, lookerHostData } = useContext(ExtensionContext)
  
  // Track if we've already checked connections to prevent multiple calls
  const hasCheckedConnections = useRef(false)

  const testAllConnections = async () => {
    if (!core40SDK) {
      console.error('Core40 SDK is not available')
      return null
    }

    try {
      console.log('Getting all connections to test for authentication issues...')
      
      let connectionTestResults: any[] = []
      
      // Get all connections using the standard SDK method
      const sdkConnections = await core40SDK.ok(
        core40SDK.all_connections()
      )
      console.log('Standard SDK connections:', sdkConnections)
      
      // Test all connections to identify any authentication issues
      console.log('Testing all connections to identify authentication issues...')
      connectionTestResults = []
      
      for (const conn of sdkConnections) {
        try {
          console.log(`Testing connection: ${conn.name}`)
          const testResult = await core40SDK.ok(
            // @ts-ignore
            core40SDK.test_connection(conn.name!, 'connect')
          )
          
          // test_connection returns an array, so get the first result
          const firstResult = Array.isArray(testResult) ? testResult[0] : testResult
          
          const connectionResult = {
            name: conn.name,
            dialect: conn.dialect_name,
            database: conn.database,
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
          
          // Log results based on status
          if (connectionResult.testStatus === 'success') {
            console.log(`✅ Connection ${conn.name} test successful`)
          } else if (connectionResult.needsAuth) {
            console.log(`🔐 Connection ${conn.name} needs authentication: ${connectionResult.message}`)
          } else if (connectionResult.testStatus === 'error') {
            console.log(`❌ Connection ${conn.name} test failed: ${connectionResult.message}`)
          }
          
        } catch (testError: any) {
          console.log(`Failed to test connection ${conn.name}:`, testError?.message || testError)
          
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
            testStatus: 'error',
            message: testError?.message || 'Test failed',
            needsAuth: authRelatedError,
            testResult: null
          })
        }
      }
      
      // Summary of connections that need authentication
      const connectionsNeedingAuth = connectionTestResults.filter(result => result.needsAuth)
      if (connectionsNeedingAuth.length > 0) {
        console.log('🔐 Connections that need authentication:')
        connectionsNeedingAuth.forEach(conn => {
          console.log(`  - ${conn.name} (${conn.dialect})`)
          console.log(`    Message: ${conn.message}`)
        })
      }
      
      const successfulConnections = connectionTestResults.filter(result => result.testStatus === 'success')
      if (successfulConnections.length > 0) {
        console.log('✅ Successfully authenticated connections:')
        successfulConnections.forEach(conn => {
          console.log(`  - ${conn.name} (${conn.dialect})`)
        })
      }
      
      const failedConnections = connectionTestResults.filter(result => 
        result.testStatus === 'error' && !result.needsAuth)
      if (failedConnections.length > 0) {
        console.log('❌ Connections with other errors:')
        failedConnections.forEach(conn => {
          console.log(`  - ${conn.name} (${conn.dialect}) - ${conn.message}`)
        })
      }
      
      // Provide actionable summary
      if (connectionsNeedingAuth.length > 0) {
        console.log(`\n📋 SUMMARY: Found ${connectionsNeedingAuth.length} connection(s) that need user authentication`)
        
        // Open a browser window to help user authenticate
        if (extensionSDK?.openBrowserWindow && lookerHostData?.hostOrigin) {
          try {
            const accountUrl = `${lookerHostData.hostOrigin}/account`
            console.log('Opening browser window to help with authentication:', accountUrl)
            extensionSDK.openBrowserWindow('/account', '_blank')
          } catch (browserError) {
            console.log('Failed to open browser window:', browserError)
          }
        }
      } else if (successfulConnections.length > 0) {
        console.log(`\n📋 SUMMARY: All tested connections are properly authenticated`)
      } else {
        console.log('\n📋 SUMMARY: No successful connections found')
      }
      
      return {
        standardConnections: sdkConnections,
        connectionTestResults,
      }
      
    } catch (error) {
      console.error('Error in testAllConnections:', error)
      return null
    }
  }

  useEffect(() => {
    // Only run the connection check once per app session
    if (!hasCheckedConnections.current && core40SDK) {
      hasCheckedConnections.current = true
      console.log('🔍 Running connection check (once per session)...')
      testAllConnections()
    }
  }, [core40SDK]) // Only depend on core40SDK availability

  return {
    testAllConnections, // Export for manual calls if needed
    hasCheckedConnections: hasCheckedConnections.current
  }
}
