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

import { renderHook, act } from '@testing-library/react'
import { useConnectionFailureDetection } from '../useConnectionFailureDetection'

describe('useConnectionFailureDetection', () => {
  let mockOnConnectionFailure: jest.Mock
  let mockOnMaxRetriesReached: jest.Mock

  beforeEach(() => {
    mockOnConnectionFailure = jest.fn()
    mockOnMaxRetriesReached = jest.fn()
    jest.clearAllMocks()
  })

  it('should initialize with default values', () => {
    const { result } = renderHook(() => useConnectionFailureDetection())

    expect(result.current.isConnecting).toBe(false)
    expect(result.current.connectionError).toBe(null)
    expect(result.current.retryCount).toBe(0)
    expect(result.current.hasReachedMaxRetries).toBe(false)
  })

  it('should detect connection errors correctly', () => {
    const { result } = renderHook(() => useConnectionFailureDetection())

    // Test various connection error types
    const connectionErrors = [
      new Error('Network error occurred'),
      new Error('Connection failed to establish'),
      new Error('Failed to fetch resource'),
      new Error('net::ERR_CONNECTION_REFUSED'),
      new Error('CORS policy blocked request'),
      new Error('Looker embed initialization failed'),
      new Error('Unauthorized access'),
    ]

    connectionErrors.forEach(error => {
      expect(result.current.isConnectionError(error)).toBe(true)
    })

    // Test non-connection errors
    const nonConnectionErrors = [
      new Error('Invalid JSON format'),
      new Error('Validation failed'),
      new Error('Unknown processing error'),
    ]

    nonConnectionErrors.forEach(error => {
      expect(result.current.isConnectionError(error)).toBe(false)
    })
  })

  it('should handle connection failures and trigger callbacks', () => {
    const { result } = renderHook(() => 
      useConnectionFailureDetection({
        onConnectionFailure: mockOnConnectionFailure,
        onMaxRetriesReached: mockOnMaxRetriesReached,
        maxRetries: 2,
        enableLogging: false
      })
    )

    const testError = new Error('Connection failed')
    const context = {
      modelName: 'test_model',
      exploreId: 'test_explore',
      hostUrl: 'https://test.looker.com'
    }

    act(() => {
      result.current.handleError(testError, context)
    })

    expect(mockOnConnectionFailure).toHaveBeenCalledWith(
      expect.objectContaining({
        error: testError,
        context: {
          modelName: 'test_model',
          exploreId: 'test_explore',
          hostUrl: 'https://test.looker.com'
        },
        retryCount: 0
      })
    )

    expect(result.current.connectionError).not.toBe(null)
    expect(result.current.retryCount).toBe(1)
  })

  it('should reach max retries and call onMaxRetriesReached', () => {
    const { result } = renderHook(() => 
      useConnectionFailureDetection({
        onConnectionFailure: mockOnConnectionFailure,
        onMaxRetriesReached: mockOnMaxRetriesReached,
        maxRetries: 1,
        enableLogging: false
      })
    )

    const testError = new Error('Network error')

    // First failure
    act(() => {
      result.current.handleError(testError)
    })

    expect(result.current.retryCount).toBe(1)
    expect(result.current.hasReachedMaxRetries).toBe(false)

    // Second failure (should reach max retries)
    act(() => {
      result.current.handleError(testError)
    })

    expect(result.current.retryCount).toBe(1) // Should not increment beyond max
    expect(result.current.hasReachedMaxRetries).toBe(true)
    expect(mockOnMaxRetriesReached).toHaveBeenCalled()
  })

  it('should reset connection state properly', () => {
    const { result } = renderHook(() => 
      useConnectionFailureDetection({
        enableLogging: false
      })
    )

    // Trigger a failure first
    act(() => {
      result.current.handleError(new Error('Connection failed'))
    })

    expect(result.current.connectionError).not.toBe(null)
    expect(result.current.retryCount).toBe(1)

    // Reset the state
    act(() => {
      result.current.resetConnectionState()
    })

    expect(result.current.connectionError).toBe(null)
    expect(result.current.retryCount).toBe(0)
    expect(result.current.isConnecting).toBe(false)
  })

  it('should handle connection success', () => {
    const { result } = renderHook(() => 
      useConnectionFailureDetection({
        enableLogging: false
      })
    )

    // Simulate a failure followed by success
    act(() => {
      result.current.handleError(new Error('Network error'))
    })

    expect(result.current.connectionError).not.toBe(null)

    act(() => {
      result.current.handleConnectionSuccess()
    })

    expect(result.current.connectionError).toBe(null)
    expect(result.current.retryCount).toBe(0)
  })

  it('should not trigger retry for non-connection errors', () => {
    const { result } = renderHook(() => 
      useConnectionFailureDetection({
        onConnectionFailure: mockOnConnectionFailure,
        enableLogging: false
      })
    )

    const nonConnectionError = new Error('Validation failed')

    act(() => {
      const shouldRetry = result.current.handleError(nonConnectionError)
      expect(shouldRetry).toBe(false)
    })

    expect(mockOnConnectionFailure).not.toHaveBeenCalled()
    expect(result.current.connectionError).toBe(null)
  })
})
