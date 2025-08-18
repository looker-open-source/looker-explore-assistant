/**
 * Hook for managing Olympic Queries system - unified table approach
 * 
 * This hook provides functionality to interact with the single olympic_queries table
 * which handles Bronze/Silver/Gold query ranks in a unified structure instead of
 * separate tables. Supports adding queries, promoting between ranks, and getting
 * query statistics.
 */
import { useCallback, useState } from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'
import { useContext } from 'react'
import { ExtensionContext } from '@looker/extension-sdk-react'

interface OlympicQuery {
  id: string
  explore_id: string
  input: string
  output: Record<string, any>
  rank: 'bronze' | 'silver' | 'gold' | 'disqualified'
  created_at: string
  updated_at: string
  link?: string
  promoted_by?: string
  promoted_at?: string
  promotion_reason?: string
  
  // Bronze-specific fields
  user_email?: string
  query_run_count?: number
  session_id?: string
  
  // Silver-specific fields
  user_id?: string
  feedback_type?: string
  feedback_score?: number
  conversation_history?: string | Record<string, any>  // Can be JSON string or parsed object
  user_corrections?: Record<string, any>
  
  // Gold-specific fields
  training_weight?: number
  validation_status?: string
  example_category?: string
}

interface OlympicSystemStatus {
  table_exists: boolean
  total_records: number
  records_by_rank: {
    bronze: number
    silver: number
    gold: number
    disqualified: number
  }
  explore_distribution: Record<string, number>
  schema_version: string
  last_updated?: string
}

interface QueryOperationResult {
  success: boolean
  query_id?: string
  system: 'olympic' | 'legacy'
  errors?: string[]
  warnings?: string[]
  metadata?: Record<string, any>
}

interface QueryPromotionResult {
  success: boolean
  query_id: string
  from_rank: string
  to_rank: string
  promoted_by: string
  promoted_at: string
  errors?: string[]
}

interface QueryStatsResult {
  total_queries: number
  queries_by_rank: {
    bronze: number
    silver: number
    gold: number
  }
  queries_by_explore: Record<string, {
    bronze: number
    silver: number
    gold: number
  }>
  recent_activity: {
    queries_added_today: number
    queries_promoted_today: number
  }
}

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

export const useOlympicQueries = () => {
  const { extensionSDK } = useContext(ExtensionContext)
  const { settings } = useSelector((state: RootState) => state.assistant as AssistantState)
  const [operationStatus, setOperationStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [systemStatus, setSystemStatus] = useState<OlympicSystemStatus | null>(null)
  const [lastOperationResult, setLastOperationResult] = useState<QueryOperationResult | null>(null)
  const [queryStats, setQueryStats] = useState<QueryStatsResult | null>(null)
  const [migrationStatus, setMigrationStatus] = useState<MigrationStatus | null>(null)
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

    console.log('Making Olympic MCP tool request:', { toolName, args })

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
          const errorText = await response.body
          throw new Error(`HTTP ${response.status}: ${errorText}`)
        }

        return response.body
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
      console.error('Olympic MCP tool call failed:', error)
      throw error
    }
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  const getSystemStatus = useCallback(async (): Promise<OlympicSystemStatus> => {
    setOperationStatus('loading')
    try {
      console.log('Getting Olympic system status...')
      const result = await callMCPTool('get_system_status', {})
      
      if (result.status !== 'success') {
        throw new Error(result.error || 'Failed to get system status')
      }

      const status = result.result
      setSystemStatus(status)
      setOperationStatus('success')
      return status
    } catch (error) {
      console.error('System status check failed:', error)
      setOperationStatus('error')
      throw error
    }
  }, [callMCPTool])

  const addBronzeQuery = useCallback(async (
    exploreId: string,
    inputText: string,
    outputData: Record<string, any>,
    link: string,
    userEmail: string
  ): Promise<QueryOperationResult> => {
    setOperationStatus('loading')
    
    try {
      console.log('Adding bronze query...', { exploreId, inputText })
      const result = await callMCPTool('add_bronze_query', {
        explore_id: exploreId,
        input: inputText,
        output: JSON.stringify(outputData),
        link,
        user_email: userEmail
      })
      
      if (result.status !== 'success') {
        throw new Error(result.error || 'Failed to add bronze query')
      }

      const operationResult: QueryOperationResult = {
        success: true,
        query_id: result.result.query_id || result.result.id,
        system: 'olympic'
      }
      
      setLastOperationResult(operationResult)
      setOperationStatus('success')
      return operationResult
    } catch (error) {
      setOperationStatus('error')
      const errorResult: QueryOperationResult = {
        success: false,
        system: 'olympic',
        errors: [error instanceof Error ? error.message : String(error)]
      }
      setLastOperationResult(errorResult)
      console.error('Adding bronze query failed:', error)
      throw error
    }
  }, [callMCPTool])

  const addSilverQuery = useCallback(async (
    exploreId: string,
    inputText: string,
    outputData: Record<string, any>,
    link: string,
    userId: string,
    feedbackType: string,
    conversationHistory?: Record<string, any>[]
  ): Promise<QueryOperationResult> => {
    setOperationStatus('loading')
    
    try {
      console.log('Adding silver query...', { exploreId, inputText, feedbackType })
      const result = await callMCPTool('add_silver_query', {
        explore_id: exploreId,
        input: inputText,
        output: JSON.stringify(outputData),
        link,
        user_id: userId,
        feedback_type: feedbackType,
        conversation_history: conversationHistory ? JSON.stringify(conversationHistory) : undefined
      })
      
      if (result.status !== 'success') {
        throw new Error(result.error || 'Failed to add silver query')
      }

      const operationResult: QueryOperationResult = {
        success: true,
        query_id: result.result.query_id || result.result.id,
        system: 'olympic'
      }
      
      setLastOperationResult(operationResult)
      setOperationStatus('success')
      return operationResult
    } catch (error) {
      setOperationStatus('error')
      const errorResult: QueryOperationResult = {
        success: false,
        system: 'olympic',
        errors: [error instanceof Error ? error.message : String(error)]
      }
      setLastOperationResult(errorResult)
      console.error('Adding silver query failed:', error)
      throw error
    }
  }, [callMCPTool])

  const promoteQuery = useCallback(async (
    queryId: string,
    promotedBy: string,
    fromRank: 'bronze' | 'silver' = 'bronze', // Default to bronze if not specified
    toRank: 'silver' | 'gold' = 'gold' // Default to gold if not specified
  ): Promise<QueryPromotionResult> => {
    setOperationStatus('loading')
    
    try {
      console.log('Promoting query...', { queryId, fromRank, toRank })
      const result = await callMCPTool('promote_query_flexible', {
        query_id: queryId,
        from_rank: fromRank,
        to_rank: toRank,
        promoted_by: promotedBy
      })
      
      if (result.status !== 'success') {
        throw new Error(result.error || 'Failed to promote query')
      }

      const promotionResult: QueryPromotionResult = {
        success: true,
        query_id: queryId,
        from_rank: fromRank,
        to_rank: toRank,
        promoted_by: promotedBy,
        promoted_at: new Date().toISOString()
      }
      
      setOperationStatus('success')
      return promotionResult
    } catch (error) {
      setOperationStatus('error')
      console.error('Query promotion failed:', error)
      throw error
    }
  }, [callMCPTool])

  const deleteQuery = useCallback(async (
    queryId: string,
    deletedBy: string
  ): Promise<QueryOperationResult> => {
    setOperationStatus('loading')
    
    try {
      console.log('Deleting query...', { queryId, deletedBy })
      const result = await callMCPTool('delete_olympic_query', {
        query_id: queryId,
        confirm_delete: true
      })
      
      // Check for backend error response
      if (result.error) {
        throw new Error(result.error)
      }
      
      // Check for success in the direct response structure
      if (!result.success) {
        throw new Error(result.message || 'Failed to delete query')
      }

      const operationResult: QueryOperationResult = {
        success: true,
        query_id: queryId,
        system: 'olympic'
      }
      
      setLastOperationResult(operationResult)
      setOperationStatus('success')
      return operationResult
    } catch (error) {
      setOperationStatus('error')
      const errorResult: QueryOperationResult = {
        success: false,
        system: 'olympic',
        errors: [error instanceof Error ? error.message : String(error)]
      }
      setLastOperationResult(errorResult)
      console.error('Query deletion failed:', error)
      throw error
    }
  }, [callMCPTool])

    const getGoldenQueries = useCallback(async (exploreId?: string, limit: number = 50): Promise<OlympicQuery[]> => {
    setOperationStatus('loading')
    
    try {
      console.log('Getting golden queries...', { exploreId, limit })
      const result = await callMCPTool('get_queries_by_rank', {
        rank: 'gold',
        explore_id: exploreId,
        limit
      })
      
      if (result.status !== 'success') {
        throw new Error(result.error || 'Failed to get golden queries')
      }

      const queries = result.result?.queries || []
      setOperationStatus('success')
      return queries
    } catch (error) {
      console.error('Getting golden queries failed:', error)
      setOperationStatus('error')
      throw error
    }
  }, [callMCPTool])

  const getBronzeQueries = useCallback(async (exploreId?: string, limit: number = 50): Promise<OlympicQuery[]> => {
    setOperationStatus('loading')
    
    try {
      console.log('Getting bronze queries...', { exploreId, limit })
      const result = await callMCPTool('get_queries_by_rank', {
        rank: 'bronze',
        explore_id: exploreId,
        limit
      })
      
      if (result.status !== 'success') {
        throw new Error(result.error || 'Failed to get bronze queries')
      }

      const queries = result.result?.queries || []
      setOperationStatus('success')
      return queries
    } catch (error) {
      console.error('Getting bronze queries failed:', error)
      setOperationStatus('error')
      throw error
    }
  }, [callMCPTool])

  const getSilverQueries = useCallback(async (exploreId?: string, limit: number = 50): Promise<OlympicQuery[]> => {
    setOperationStatus('loading')
    
    try {
      console.log('Getting silver queries...', { exploreId, limit })
      const result = await callMCPTool('get_queries_by_rank', {
        rank: 'silver',
        explore_id: exploreId,
        limit
      })
      
      if (result.status !== 'success') {
        throw new Error(result.error || 'Failed to get silver queries')
      }

      const queries = result.result?.queries || []
      setOperationStatus('success')
      return queries
    } catch (error) {
      console.error('Getting silver queries failed:', error)
      setOperationStatus('error')
      throw error
    }
  }, [callMCPTool])

  const getDisqualifiedQueries = useCallback(async (exploreId?: string, limit: number = 50): Promise<OlympicQuery[]> => {
    setOperationStatus('loading')
    try {
      console.log('Getting disqualified queries...', { exploreId, limit })
      const result = await callMCPTool('get_queries_by_rank', {
        rank: 'disqualified',
        explore_id: exploreId,
        limit: limit
      })
      
      if (!result || result.error) {
        throw new Error(result.error || 'Failed to get disqualified queries')
      }
      
      const queries = result.result?.queries || []
      console.log(`Retrieved ${queries.length} disqualified queries`)
      setOperationStatus('success')
      return queries
    } catch (error) {
      console.error('Getting disqualified queries failed:', error)
      setOperationStatus('error')
      throw error
    }
  }, [callMCPTool])

  const getQueryStats = useCallback(async (): Promise<QueryStatsResult> => {
    setOperationStatus('loading')
    
    try {
      console.log('Getting query stats...')
      const result = await callMCPTool('get_query_stats', {})
      
      if (result.status !== 'success') {
        throw new Error(result.error || 'Failed to get query stats')
      }

      const stats = result.result
      setQueryStats(stats)
      setOperationStatus('success')
      return stats
    } catch (error) {
      setOperationStatus('error')
      console.error('Getting query stats failed:', error)
      throw error
    }
  }, [callMCPTool])

  const checkMigrationStatus = useCallback(async (): Promise<MigrationStatus> => {
    setOperationStatus('loading')
    
    try {
      console.log('Checking migration status...')
      const result = await callMCPTool('check_migration_status', {})
      
      if (result.status !== 'success') {
        throw new Error(result.error || 'Failed to check migration status')
      }

      const status = result.result
      setMigrationStatus(status)
      setOperationStatus('success')
      return status
    } catch (error) {
      setOperationStatus('error')
      console.error('Checking migration status failed:', error)
      throw error
    }
  }, [callMCPTool])

  const performMigration = useCallback(async (preserveData: boolean = true, verifyMigration: boolean = true): Promise<MigrationResult> => {
    setOperationStatus('loading')
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
        setOperationStatus('success')
      } else {
        setOperationStatus('error')
      }
      
      return migrationData
    } catch (error) {
      setOperationStatus('error')
      console.error('Migration failed:', error)
      throw error
    }
  }, [callMCPTool])

  const resetState = useCallback(() => {
    setOperationStatus('idle')
    setSystemStatus(null)
    setLastOperationResult(null)
    setQueryStats(null)
    setMigrationStatus(null)
    setMigrationResult(null)
  }, [])

  return {
    // State
    operationStatus,
    systemStatus,
    lastOperationResult,
    queryStats,
    migrationStatus,
    migrationResult,
    
    // Actions
    getSystemStatus,
    addBronzeQuery,
    addSilverQuery,
    promoteQuery,
    deleteQuery,
    getGoldenQueries,
    getBronzeQueries,
    getSilverQueries,
    getDisqualifiedQueries,
    getQueryStats,
    checkMigrationStatus,
    performMigration,
    resetState,
    
    // Utilities
    isReady: !!(CLOUD_RUN_URL && identityToken),
    isOlympicSystemAvailable: systemStatus?.table_exists ?? false,
    totalQueries: systemStatus?.total_records ?? 0,
    migrationNeeded: migrationStatus?.migration_needed ?? false,
    canMigrateSafely: migrationStatus?.can_migrate_safely ?? false
  }
}
