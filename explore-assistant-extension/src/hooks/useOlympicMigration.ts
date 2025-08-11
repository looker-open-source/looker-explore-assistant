import { useCallback, useState } from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'
import { useContext } from 'react'
import { ExtensionContext } from '@looker/extension-sdk-react'

interface MigrationStatus {
  migration_needed: boolean
  legacy_tables_exist: Array<{
    table: string
    record_count: number
    explore_field: 'explore_id' | 'explore_key' | null
    needs_mapping: boolean
    available_fields: string[]
  }>
  olympic_table_exists: boolean
  olympic_record_count?: number
  estimated_record_count: number
  schema_issues: Array<{
    table: string
    issue: string
    fixable: boolean
    severity: 'low' | 'medium' | 'high' | 'critical'
  }>
  can_migrate_safely: boolean
  recommendations: string[]
  summary?: string
}

interface MigrationResult {
  started_at: string
  migration_id: string
  steps_completed: string[]
  records_migrated: number
  schema_fixes_applied: string[]
  archived_tables: Array<{
    original: string
    archive: string
  }>
  verification_results?: {
    valid: boolean
    errors: string[]
    warnings: string[]
    stats: Record<string, any>
    data_integrity_checks: Record<string, any>
  }
  errors: string[]
  warnings: string[]
  success: boolean
  completed_at?: string
  failed_at?: string
  summary?: string
}

interface SystemStatus {
  olympic_available: boolean
  olympic_records?: number
  olympic_explore_field?: string
  legacy_tables: Record<string, {
    records: number
    explore_field: string
  }>
  field_mappings: Record<string, string>
  recommendations: string[]
  migration_recommendation?: string
}

export const useOlympicMigration = () => {
  const { extensionSDK } = useContext(ExtensionContext)
  const { settings } = useSelector((state: RootState) => state.assistant as AssistantState)
  const [migrationStatus, setMigrationStatus] = useState<'idle' | 'checking' | 'migrating' | 'complete' | 'error'>('idle')
  const [statusDetails, setStatusDetails] = useState<MigrationStatus | null>(null)
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [migrationResult, setMigrationResult] = useState<MigrationResult | null>(null)

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

    console.log('Making Olympic migration MCP tool request:', { toolName, args })

    try {
      // Try fetchProxy first (preferred)
      try {
        console.log('Attempting fetchProxy request...')
        const response = await extensionSDK.fetchProxy(CLOUD_RUN_URL, {
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
      } catch (proxyError) {
        console.warn('fetchProxy failed, falling back to direct fetch...', proxyError)
        
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
      console.error('Olympic migration MCP tool call failed:', error)
      throw error
    }
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  const checkMigrationNeeded = useCallback(async (): Promise<boolean> => {
    setMigrationStatus('checking')
    try {
      console.log('Checking Olympic migration status...')
      const result = await callMCPTool('check_migration_status', {})
      
      if (result.status !== 'success') {
        throw new Error(result.error || 'Failed to check migration status')
      }

      setStatusDetails(result.result)
      setMigrationStatus('idle')
      return result.result.migration_needed
    } catch (error) {
      console.error('Migration check failed:', error)
      setMigrationStatus('error')
      throw error
    }
  }, [callMCPTool])

  const getSystemStatus = useCallback(async (): Promise<SystemStatus> => {
    try {
      console.log('Getting Olympic system status...')
      const result = await callMCPTool('get_system_status', {})
      
      if (result.status !== 'success') {
        throw new Error(result.error || 'Failed to get system status')
      }

      setSystemStatus(result.result)
      return result.result
    } catch (error) {
      console.error('System status check failed:', error)
      throw error
    }
  }, [callMCPTool])

  const performMigration = useCallback(async (preserveData: boolean = true, verifyMigration: boolean = true): Promise<MigrationResult> => {
    setMigrationStatus('migrating')
    setMigrationResult(null)
    
    try {
      console.log('Starting Olympic migration...', { preserveData, verifyMigration })
      const result = await callMCPTool('migrate_to_olympic_system', { 
        preserve_data: preserveData,
        verify_migration: verifyMigration 
      })
      
      if (result.status !== 'success') {
        throw new Error(result.error || 'Migration failed')
      }

      const migrationData = result.result
      setMigrationResult(migrationData)
      
      if (migrationData.success) {
        setMigrationStatus('complete')
      } else {
        setMigrationStatus('error')
      }
      
      return migrationData
    } catch (error) {
      setMigrationStatus('error')
      console.error('Migration failed:', error)
      throw error
    }
  }, [callMCPTool])

  const testFlexibleOperations = useCallback(async () => {
    try {
      console.log('Testing flexible operations...')
      
      // Test adding a bronze query
      const testQuery = {
        explore_id: 'test:migration_ui',
        input_text: 'Test query from migration UI',
        output_data: '{"test": "migration_ui"}',
        link: 'https://test.com/migration-ui',
        user_email: 'migration-ui@test.com'
      }

      const addResult = await callMCPTool('add_bronze_query_flexible', testQuery)
      if (addResult.status !== 'success') {
        throw new Error('Failed to add test query')
      }

      // Test getting golden queries
      const getResult = await callMCPTool('get_golden_queries_flexible', { limit: 5 })
      if (getResult.status !== 'success') {
        throw new Error('Failed to get golden queries')
      }

      return {
        add_query: addResult.result,
        get_queries: getResult.result
      }
    } catch (error) {
      console.error('Flexible operations test failed:', error)
      throw error
    }
  }, [callMCPTool])

  const resetMigrationState = useCallback(() => {
    setMigrationStatus('idle')
    setStatusDetails(null)
    setSystemStatus(null)
    setMigrationResult(null)
  }, [])

  return {
    // State
    migrationStatus,
    statusDetails,
    systemStatus,
    migrationResult,
    
    // Actions
    checkMigrationNeeded,
    getSystemStatus,
    performMigration,
    testFlexibleOperations,
    resetMigrationState,
    
    // Utilities
    isReady: !!(CLOUD_RUN_URL && identityToken),
    canMigrate: statusDetails?.can_migrate_safely ?? false,
    migrationNeeded: statusDetails?.migration_needed ?? false
  }
}
