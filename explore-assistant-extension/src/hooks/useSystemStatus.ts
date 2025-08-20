/**
 * Hook for system status using REST API endpoints
 * 
 * Replaces MCP tool calls with direct REST API calls for better
 * performance, error handling, and type safety.
 */
import { useCallback, useState, useContext } from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'
import { ExtensionContext } from '@looker/extension-sdk-react'

interface SystemStatusResponse {
  success: boolean
  data: {
    system_status: 'operational' | 'partial' | 'degraded' | 'error'
    timestamp: string
    project_id: string
    dataset_id: string
    components: {
      bigquery: 'operational' | 'degraded' | 'error' | 'unavailable'
      olympic_system: 'operational' | 'degraded' | 'error' | 'unavailable' 
      vector_search: 'operational' | 'degraded' | 'error' | 'unavailable'
      legacy_tables: 'operational' | 'degraded' | 'error' | 'unavailable'
    }
    olympic_available: boolean
    olympic_table_exists: boolean
    olympic_record_count: number
    olympic_records_by_rank: {
      bronze: number
      silver: number
      gold: number
    }
    legacy_tables: {
      [tableName: string]: {
        exists: boolean
        record_count: number
        created?: string
        modified?: string
        explore_field?: string
      }
    }
    total_legacy_records: number
    recommendations: string[]
  }
  error?: string
}

interface MigrationStatusResponse {
  success: boolean
  data: {
    migration_ready: boolean
    migration_required: boolean
    can_migrate: boolean
    status: 'fully_migrated' | 'partial_migration' | 'needs_olympic_setup' | 'clean_start' | 'error'
    legacy_records_to_migrate?: number
    obstacles?: string[]
  }
  error?: string
}

interface HealthCheckResponse {
  success: boolean
  data: {
    status: 'healthy' | 'unhealthy'
    timestamp: string
    bigquery_connection: 'operational' | 'failed'
  }
  error?: string
}

export const useSystemStatus = () => {
  const { extensionSDK } = useContext(ExtensionContext)
  const { settings } = useSelector((state: RootState) => state.assistant as AssistantState)
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Cloud Run service settings
  const CLOUD_RUN_URL = settings['cloud_run_service_url']?.value as string || ''
  const identityToken = settings['identity_token']?.value as string || ''

  const makeRestCall = useCallback(async (endpoint: string): Promise<any> => {
    if (!CLOUD_RUN_URL) {
      throw new Error('Cloud Run URL not configured')
    }
    
    if (!identityToken) {
      throw new Error('Identity token not available')
    }

    const url = `${CLOUD_RUN_URL}${endpoint}`
    console.log('Making REST API request:', url)

    try {
      // Try fetchProxy first (preferred for Looker extensions)
      try {
        const response = await extensionSDK.fetchProxy(url, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${identityToken}`,
          }
        })

        console.log('REST API response:', response)

        if (!response.ok) {
          const errorText = response.body?.error || `HTTP ${response.status}`
          throw new Error(errorText)
        }

        return response.body
      } catch (proxyError) {
        console.warn('fetchProxy failed, falling back to direct fetch...', proxyError)
        
        // Fallback to direct fetch
        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${identityToken}`,
          }
        })

        if (!response.ok) {
          const errorText = await response.text()
          throw new Error(`HTTP ${response.status}: ${errorText}`)
        }

        return await response.json()
      }
    } catch (error) {
      console.error('REST API call failed:', error)
      throw error
    }
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  const getSystemStatus = useCallback(async (): Promise<SystemStatusResponse['data']> => {
    setLoading(true)
    setError(null)
    
    try {
      console.log('Getting system status via REST API...')
      const result = await makeRestCall('/api/v1/system-status')
      
      if (!result.success) {
        throw new Error(result.error || 'Failed to get system status')
      }

      setLoading(false)
      return result.data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      setError(errorMessage)
      setLoading(false)
      console.error('System status check failed:', err)
      throw err
    }
  }, [makeRestCall])

  const getMigrationStatus = useCallback(async (): Promise<MigrationStatusResponse['data']> => {
    setLoading(true)
    setError(null)
    
    try {
      console.log('Getting migration status via REST API...')
      const result = await makeRestCall('/api/v1/system-status/migration')
      
      if (!result.success) {
        throw new Error(result.error || 'Failed to get migration status')
      }

      setLoading(false)
      return result.data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      setError(errorMessage)
      setLoading(false)
      console.error('Migration status check failed:', err)
      throw err
    }
  }, [makeRestCall])

  const getQuickHealthCheck = useCallback(async (): Promise<HealthCheckResponse['data']> => {
    setLoading(true)
    setError(null)
    
    try {
      console.log('Getting quick health check via REST API...')
      const result = await makeRestCall('/api/v1/system-status/health')
      
      if (!result.success) {
        throw new Error(result.error || 'Failed to get health status')
      }

      setLoading(false)
      return result.data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      setError(errorMessage)
      setLoading(false)
      console.error('Health check failed:', err)
      throw err
    }
  }, [makeRestCall])

  const resetState = useCallback(() => {
    setLoading(false)
    setError(null)
  }, [])

  return {
    // State
    loading,
    error,
    
    // Actions
    getSystemStatus,
    getMigrationStatus,
    getQuickHealthCheck,
    resetState,
    
    // Utilities
    isReady: !!(CLOUD_RUN_URL && identityToken)
  }
}