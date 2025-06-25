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

import React from 'react'
import { renderHook, act } from '@testing-library/react'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { useCheckForConnectionFailure } from '../useCheckForConnectionFailure'

// Mock the ExtensionContext
const mockExtensionSDK = {
  openBrowserWindow: jest.fn(),
}

const MockExtensionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const contextValue = {
    extensionSDK: mockExtensionSDK,
  }

  return (
    <ExtensionContext.Provider value={contextValue as any}>
      {children}
    </ExtensionContext.Provider>
  )
}

describe('useCheckForConnectionFailure', () => {
  let mockCustomFailureHandler: jest.Mock

  beforeEach(() => {
    mockCustomFailureHandler = jest.fn()
    mockExtensionSDK.openBrowserWindow.mockClear()
    jest.clearAllMocks()
  })

  const renderHookWithProvider = (options = {}) =>
    renderHook(() => useCheckForConnectionFailure(options), {
      wrapper: MockExtensionProvider,
    })

  it('should initialize with default values', () => {
    const { result } = renderHookWithProvider()

    expect(result.current.isConnecting).toBe(false)
    expect(result.current.connectionError).toBe(null)
    expect(result.current.retryCount).toBe(0)
    expect(result.current.hasReachedMaxRetries).toBe(false)
  })

  it('should detect database connection errors correctly', () => {
    const { result } = renderHookWithProvider()

    // Test database connection errors
    const databaseErrors = [
      new Error('Database connection failed'),
      new Error('Connection to database timed out'),
      new Error('BigQuery authentication failed'),
      new Error('Looker connection test failed'),
      new Error('Invalid connection credentials'),
      new Error('Access denied for database user'),
    ]

    databaseErrors.forEach(error => {
      expect(result.current.isDatabaseConnectionError(error)).toBe(true)
    })

    // Test non-database errors
    const nonDatabaseErrors = [
      new Error('JSON parsing failed'),
      new Error('Invalid configuration'),
      new Error('Generic network error'),
    ]

    nonDatabaseErrors.forEach(error => {
      expect(result.current.isDatabaseConnectionError(error)).toBe(false)
    })
  })

  it('should open accounts page when database connection fails after max retries', () => {
    const { result } = renderHookWithProvider({
      maxRetries: 1,
      enableLogging: false,
      openAccountsPageOnFailure: true,
    })

    const databaseError = new Error('Database connection failed')

    // First failure
    act(() => {
      result.current.handleError(databaseError)
    })

    expect(mockExtensionSDK.openBrowserWindow).not.toHaveBeenCalled()

    // Second failure (reaches max retries)
    act(() => {
      result.current.handleError(databaseError)
    })

    expect(mockExtensionSDK.openBrowserWindow).toHaveBeenCalledWith('/accounts', '_blank')
  })

  it('should not open accounts page for non-database errors', () => {
    const { result } = renderHookWithProvider({
      maxRetries: 1,
      enableLogging: false,
      openAccountsPageOnFailure: true,
    })

    const nonDatabaseError = new Error('Generic network error')

    // First failure
    act(() => {
      result.current.handleError(nonDatabaseError)
    })

    // Second failure (reaches max retries)
    act(() => {
      result.current.handleError(nonDatabaseError)
    })

    expect(mockExtensionSDK.openBrowserWindow).not.toHaveBeenCalled()
  })

  it('should call custom failure handler', () => {
    const { result } = renderHookWithProvider({
      customFailureHandler: mockCustomFailureHandler,
      enableLogging: false,
    })

    const testError = new Error('Connection failed')

    act(() => {
      result.current.handleError(testError)
    })

    expect(mockCustomFailureHandler).toHaveBeenCalledWith(
      expect.objectContaining({
        error: testError,
        retryCount: 0,
      })
    )
  })

  it('should not open accounts page when disabled', () => {
    const { result } = renderHookWithProvider({
      maxRetries: 1,
      enableLogging: false,
      openAccountsPageOnFailure: false,
    })

    const databaseError = new Error('Database connection failed')

    // First failure
    act(() => {
      result.current.handleError(databaseError)
    })

    // Second failure (reaches max retries)
    act(() => {
      result.current.handleError(databaseError)
    })

    expect(mockExtensionSDK.openBrowserWindow).not.toHaveBeenCalled()
  })

  it('should provide openAccountsPage utility function', () => {
    const { result } = renderHookWithProvider()

    act(() => {
      result.current.openAccountsPage()
    })

    expect(mockExtensionSDK.openBrowserWindow).toHaveBeenCalledWith('/accounts', '_blank')
  })

  it('should handle errors when opening accounts page fails', () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {})
    mockExtensionSDK.openBrowserWindow.mockImplementation(() => {
      throw new Error('Failed to open window')
    })

    const { result } = renderHookWithProvider({
      enableLogging: true,
    })

    act(() => {
      result.current.openAccountsPage()
    })

    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('[CheckForConnectionFailure] Failed to open accounts page:'),
      expect.any(Error)
    )

    consoleSpy.mockRestore()
  })
})
