import { useCallback, useState, useContext } from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'
import { ExtensionContext } from '@looker/extension-sdk-react'

interface VectorSystemStatus {
  table_exists: boolean
  model_exists: boolean
  table_row_count?: number
  model_training_state?: string
  last_updated?: string
  errors?: string[]
  warnings?: string[]
  details?: Record<string, any>
}

interface VectorSetupResult {
  success: boolean
  created_table?: boolean
  created_model?: boolean
  errors?: string[]
  warnings?: string[]
  details?: Record<string, any>
}

export const useVectorSearchSetup = () => {
  const { extensionSDK } = useContext(ExtensionContext)
  const { settings } = useSelector((state: RootState) => state.assistant as AssistantState)
  const [operationStatus, setOperationStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [systemStatus, setSystemStatus] = useState<VectorSystemStatus | null>(null)
  const [setupResult, setSetupResult] = useState<VectorSetupResult | null>(null)

  // Cloud Run service settings
  const CLOUD_RUN_URL = settings['cloud_run_service_url']?.value as string || ''
  const identityToken = settings['identity_token']?.value as string || ''

  const callMCPTool = useCallback(async (toolName: string, args: any): Promise<any> => {
    if (!CLOUD_RUN_URL) {
      throw new Error('Cloud Run URL not configured')
    }
    if (!identityToken) {
      throw new Error('Identity token not available')
    }
    const requestBody = {
      tool_name: toolName,
      arguments: args
    }
    try {
      // Try fetchProxy first
      try {
        const response = await extensionSDK.fetchProxy(CLOUD_RUN_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${identityToken}`,
          },
          body: JSON.stringify(requestBody)
        })
        if (!response.ok) {
          const errorText = await response.body
          throw new Error(`HTTP ${response.status}: ${errorText}`)
        }
        return response.body
      } catch (proxyError) {
        // Fallback to direct fetch
        const response = await fetch(CLOUD_RUN_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${identityToken}`,
          },
          body: JSON.stringify(requestBody)
        })
        if (!response.ok) {
          const errorText = await response.text()
          throw new Error(`HTTP ${response.status}: ${errorText}`)
        }
        return await response.json()
      }
    } catch (error) {
      console.error('Vector MCP tool call failed:', error)
      throw error
    }
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  const getVectorSystemStatus = useCallback(async (): Promise<VectorSystemStatus> => {
    setOperationStatus('loading')
    try {
      const result = await callMCPTool('check_vector_search_status', {})
      if (result.status !== 'success') {
        throw new Error(result.error || 'Failed to get vector system status')
      }
      const status = result.result
      setSystemStatus(status)
      setOperationStatus('success')
      return status
    } catch (error) {
      setOperationStatus('error')
      throw error
    }
  }, [callMCPTool])

  const setupVectorSystem = useCallback(async (): Promise<VectorSetupResult> => {
    setOperationStatus('loading')
    try {
      const result = await callMCPTool('setup_vector_system', {})
      if (result.status !== 'success') {
        throw new Error(result.error || 'Failed to setup vector system')
      }
      const setup = result.result
      setSetupResult(setup)
      setOperationStatus('success')
      return setup
    } catch (error) {
      setOperationStatus('error')
      throw error
    }
  }, [callMCPTool])

  const resetState = useCallback(() => {
    setOperationStatus('idle')
    setSystemStatus(null)
    setSetupResult(null)
  }, [])

  return {
    operationStatus,
    systemStatus,
    setupResult,
    getVectorSystemStatus,
    setupVectorSystem,
    resetState,
    isReady: !!(CLOUD_RUN_URL && identityToken),
    isVectorSystemAvailable: systemStatus?.table_exists ?? false
  }
}
