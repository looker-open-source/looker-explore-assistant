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

import { useCallback, useState, useRef } from 'react'

export interface ConnectionFailureInfo {
  error: Error
  timestamp: Date
  queryUrl?: string
  retryCount: number
  context?: {
    modelName?: string
    exploreId?: string
    hostUrl?: string
  }
}

export interface UseConnectionFailureDetectionOptions {
  maxRetries?: number
  retryDelay?: number
  onConnectionFailure?: (info: ConnectionFailureInfo) => void
  onMaxRetriesReached?: (info: ConnectionFailureInfo) => void
  enableLogging?: boolean
}

export const useConnectionFailureDetection = (
  options: UseConnectionFailureDetectionOptions = {}
) => {
  const {
    maxRetries = 3,
    retryDelay = 1000,
    onConnectionFailure,
    onMaxRetriesReached,
    enableLogging = true,
  } = options

  const [isConnecting, setIsConnecting] = useState(false)
  const [connectionError, setConnectionError] = useState<ConnectionFailureInfo | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const logError = useCallback((message: string, error?: Error | any, context?: any) => {
    if (enableLogging) {
      console.error(`[ConnectionFailureDetection] ${message}`, error, context)
    }
  }, [enableLogging])

  const logInfo = useCallback((message: string, context?: any) => {
    if (enableLogging) {
      console.log(`[ConnectionFailureDetection] ${message}`, context)
    }
  }, [enableLogging])

  const clearRetryTimeout = useCallback(() => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
  }, [])

  const resetConnectionState = useCallback(() => {
    setConnectionError(null)
    setRetryCount(0)
    setIsConnecting(false)
    clearRetryTimeout()
  }, [clearRetryTimeout])

  const handleConnectionFailure = useCallback((
    error: Error,
    context?: {
      modelName?: string
      exploreId?: string
      hostUrl?: string
      queryUrl?: string
    }
  ) => {
    const failureInfo: ConnectionFailureInfo = {
      error,
      timestamp: new Date(),
      queryUrl: context?.queryUrl,
      retryCount,
      context: {
        modelName: context?.modelName,
        exploreId: context?.exploreId,
        hostUrl: context?.hostUrl,
      }
    }

    logError('Connection failure detected', error, failureInfo)
    
    setConnectionError(failureInfo)
    onConnectionFailure?.(failureInfo)

    if (retryCount >= maxRetries) {
      logError(`Maximum retries (${maxRetries}) reached for connection`, error, failureInfo)
      onMaxRetriesReached?.(failureInfo)
      setIsConnecting(false)
      return false // Don't retry
    }

    // Schedule retry
    const nextRetryCount = retryCount + 1
    setRetryCount(nextRetryCount)
    
    logInfo(`Scheduling retry ${nextRetryCount}/${maxRetries} in ${retryDelay}ms`, failureInfo)
    
    retryTimeoutRef.current = setTimeout(() => {
      logInfo(`Executing retry ${nextRetryCount}/${maxRetries}`)
      // The actual retry logic will be handled by the caller
    }, retryDelay)

    return true // Should retry
  }, [retryCount, maxRetries, retryDelay, onConnectionFailure, onMaxRetriesReached, logError, logInfo])

  const handleConnectionSuccess = useCallback(() => {
    logInfo('Connection successful, resetting failure state')
    resetConnectionState()
  }, [resetConnectionState, logInfo])

  const setConnecting = useCallback((connecting: boolean) => {
    setIsConnecting(connecting)
    if (connecting) {
      logInfo('Connection attempt started')
    }
  }, [logInfo])

  // Check if error is a connection-related error
  const isConnectionError = useCallback((error: Error): boolean => {
    const errorMessage = error.message.toLowerCase()
    const connectionErrorPatterns = [
      'network error',
      'connection failed',
      'connection refused',
      'timeout',
      'failed to fetch',
      'net::err_',
      'cors',
      'embed sdk',
      'looker embed',
      'unauthorized',
      'forbidden'
    ]

    return connectionErrorPatterns.some(pattern => 
      errorMessage.includes(pattern) || 
      error.name.toLowerCase().includes(pattern)
    )
  }, [])

  // Enhanced error handler that detects connection failures specifically
  const handleError = useCallback((
    error: Error,
    context?: {
      modelName?: string
      exploreId?: string
      hostUrl?: string
      queryUrl?: string
    }
  ) => {
    if (isConnectionError(error)) {
      return handleConnectionFailure(error, context)
    } else {
      logError('Non-connection error detected', error, context)
      return false // Don't retry for non-connection errors
    }
  }, [isConnectionError, handleConnectionFailure, logError])

  return {
    // State
    isConnecting,
    connectionError,
    retryCount,
    hasReachedMaxRetries: retryCount >= maxRetries,
    
    // Actions
    handleError,
    handleConnectionFailure,
    handleConnectionSuccess,
    setConnecting,
    resetConnectionState,
    clearRetryTimeout,
    
    // Utilities
    isConnectionError,
  }
}
