import { useCallback, useState, useContext } from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'
import { ExtensionContext } from '@looker/extension-sdk-react'

interface VectorSystemStatus {
  timestamp: string
  system_status: 'operational' | 'needs_setup' | 'degraded' | 'partial' | 'unknown'
  components: {
    bigquery_connection: string
    embedding_model: string
    field_values_table: string
    vector_index: string
  }
  statistics: {
    total_rows?: number
    unique_fields?: number
    unique_explores?: number
    unique_models?: number
    table_name?: string
    project_id?: string
    dataset_id?: string
  }
  recommendations: string[]
}

interface VectorSetupResult {
  started_at: string
  completed_at?: string
  steps: string[]
  success: boolean
  errors: string[]
  statistics: Record<string, any>
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

  const callRestEndpoint = useCallback(async (endpoint: string, options: RequestInit = {}): Promise<any> => {
    if (!CLOUD_RUN_URL) {
      throw new Error('Cloud Run URL not configured')
    }
    if (!identityToken) {
      throw new Error('Identity token not available')
    }
    
    const url = `${CLOUD_RUN_URL}${endpoint}`
    const requestOptions: RequestInit = {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${identityToken}`,
      },
      ...options,
    }

    try {
      // Try fetchProxy first
      try {
        console.log('Making fetchProxy request to:', url, 'with options:', requestOptions)
        const response = await extensionSDK.fetchProxy(url, requestOptions)
        console.log('fetchProxy response status:', response.status, 'ok:', response.ok)
        
        if (!response.ok) {
          const errorText = typeof response.body === 'string' ? response.body : JSON.stringify(response.body)
          console.error('fetchProxy failed with status:', response.status, 'body:', errorText)
          throw new Error(`HTTP ${response.status}: ${errorText}`)
        }
        
        // fetchProxy returns the parsed response directly in .body
        console.log('fetchProxy success, returning body:', response.body)
        return response.body
      } catch (proxyError) {
        console.warn('fetchProxy failed, falling back to direct fetch...', proxyError)
        
        // Fallback to direct fetch
        const response = await fetch(url, {
          ...requestOptions,
          mode: 'cors',
          credentials: 'omit',
        })
        
        if (!response.ok) {
          const errorText = await response.text()
          console.error('Direct fetch failed with status:', response.status, 'text:', errorText)
          throw new Error(`HTTP ${response.status}: ${errorText}`)
        }
        
        const result = await response.json()
        console.log('Direct fetch success, returning result:', result)
        return result
      }
    } catch (error) {
      console.error('Vector REST call failed:', error)
      throw error
    }
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  const getVectorSystemStatus = useCallback(async (): Promise<VectorSystemStatus> => {
    setOperationStatus('loading')
    try {
      const result = await callRestEndpoint('/api/v1/admin/vector-search/status')
      if (!result.success) {
        throw new Error(result.error?.message || 'Failed to get vector system status')
      }
      const status = result.data
      setSystemStatus(status)
      
      // Set operation status based on system_status, not just API success
      if (status.system_status === 'operational') {
        setOperationStatus('success')
      } else if (status.system_status === 'degraded' || status.system_status === 'partial') {
        setOperationStatus('error') // Show as error to indicate issues
      } else {
        setOperationStatus('idle') // needs_setup, unknown, etc.
      }
      
      return status
    } catch (error) {
      setOperationStatus('error')
      throw error
    }
  }, [callRestEndpoint])

  const setupVectorSystem = useCallback(async (options?: { force_refresh?: boolean, focus_explore?: string }): Promise<VectorSetupResult> => {
    setOperationStatus('loading')
    try {
      const result = await callRestEndpoint('/api/v1/admin/vector-search/setup', {
        method: 'POST',
        body: JSON.stringify(options || {})
      })
      if (!result.success) {
        throw new Error(result.error?.message || 'Failed to setup vector system')
      }
      const setup = result.data
      setSetupResult(setup)
      setOperationStatus('success')
      return setup
    } catch (error) {
      setOperationStatus('error')
      throw error
    }
  }, [callRestEndpoint])

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
    isVectorSystemAvailable: systemStatus?.system_status === 'operational' ?? false
  }
}
