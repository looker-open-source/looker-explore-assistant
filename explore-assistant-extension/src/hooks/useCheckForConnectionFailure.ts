/*

MIT License

Copyright (c) 2023 Looker Data Sciences, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

*/

import { useCallback, useContext } from 'react'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { useConnectionFailureDetection, ConnectionFailureInfo } from './useConnectionFailureDetection'

export interface UseCheckForConnectionFailureOptions {
  maxRetries?: number
  retryDelay?: number
  enableLogging?: boolean
  openAccountsPageOnFailure?: boolean
  customFailureHandler?: (info: ConnectionFailureInfo) => void
}

/**
 * Hook that combines connection failure detection with automatic opening of accounts page
 * when connection failures occur. This is specifically designed for ExploreEmbed components
 * that need to handle database connection issues.
 */
export const useCheckForConnectionFailure = (
  options: UseCheckForConnectionFailureOptions = {}
) => {
  const {
    maxRetries = 3,
    retryDelay = 2000,
    enableLogging = true,
    openAccountsPageOnFailure = true,
    customFailureHandler,
  } = options

  const { extensionSDK } = useContext(ExtensionContext)

  const handleConnectionFailure = useCallback((info: ConnectionFailureInfo) => {
    if (enableLogging) {
      console.warn('[CheckForConnectionFailure] Connection failure detected:', {
        error: info.error.message,
        retryCount: info.retryCount,
        timestamp: info.timestamp,
        context: info.context
      })
    }

    // Call custom failure handler if provided
    if (customFailureHandler) {
      customFailureHandler(info)
    }

    // Check if this is a database-level connection error
    const isDatabaseError = isDatabaseConnectionError(info.error)
    
    if (isDatabaseError && enableLogging) {
      console.warn('[CheckForConnectionFailure] Database connection error detected')
    }
  }, [enableLogging, customFailureHandler])

  const handleMaxRetriesReached = useCallback((info: ConnectionFailureInfo) => {
    if (enableLogging) {
      console.error('[CheckForConnectionFailure] Maximum retries reached:', {
        error: info.error.message,
        retryCount: info.retryCount,
        timestamp: info.timestamp,
        context: info.context
      })
    }

    // Check if this is a database-level connection error
    const isDatabaseError = isDatabaseConnectionError(info.error)
    
    if (isDatabaseError && openAccountsPageOnFailure) {
      if (enableLogging) {
        console.info('[CheckForConnectionFailure] Opening accounts page due to database connection failure')
      }
      
      try {
        extensionSDK?.openBrowserWindow('/accounts', '_blank')
      } catch (error) {
        if (enableLogging) {
          console.error('[CheckForConnectionFailure] Failed to open accounts page:', error)
        }
      }
    }
  }, [extensionSDK, enableLogging, openAccountsPageOnFailure])

  const connectionFailureDetection = useConnectionFailureDetection({
    maxRetries,
    retryDelay,
    onConnectionFailure: handleConnectionFailure,
    onMaxRetriesReached: handleMaxRetriesReached,
    enableLogging,
  })

  return {
    ...connectionFailureDetection,
    // Additional utilities specific to this hook
    isDatabaseConnectionError,
    openAccountsPage: useCallback(() => {
      try {
        extensionSDK?.openBrowserWindow('/accounts', '_blank')
      } catch (error) {
        if (enableLogging) {
          console.error('[CheckForConnectionFailure] Failed to open accounts page:', error)
        }
      }
    }, [extensionSDK, enableLogging]),
  }
}

/**
 * Determines if an error is specifically a database connection error
 * that would benefit from opening the accounts page.
 */
const isDatabaseConnectionError = (error: Error): boolean => {
  const errorMessage = error.message.toLowerCase()
  const errorName = error.name.toLowerCase()
  
  // Database-specific error patterns
  const databaseErrorPatterns = [
    'database connection',
    'database error',
    'connection to database',
    'database unavailable',
    'database timeout',
    'sql error',
    'query failed',
    'connection pool',
    'database server',
    'connection refused',
    'connection timeout',
    'access denied',
    'authentication failed',
    'unauthorized',
    'invalid credentials',
    'permission denied',
    'bigquery',
    'snowflake',
    'redshift',
    'postgres',
    'mysql',
    'oracle',
    'mssql',
    'sqlite'
  ]

  // Looker-specific database error patterns
  const lookerDatabaseErrorPatterns = [
    'looker connection',
    'looker database',
    'explore connection',
    'model connection',
    'connection test failed',
    'invalid connection',
    'connection configuration'
  ]

  const allPatterns = [...databaseErrorPatterns, ...lookerDatabaseErrorPatterns]
  
  return allPatterns.some(pattern => 
    errorMessage.includes(pattern) || 
    errorName.includes(pattern)
  )
}
