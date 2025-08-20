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
import { useSystemStatus } from './useSystemStatus'

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

  // Import the new REST-based system status hook  
  const { getSystemStatus: getRestSystemStatus, getMigrationStatus: getRestMigrationStatus } = useSystemStatus()
  
  // Migration Status:
  // ✅ MIGRATED TO REST: getBronzeQueries, getSilverQueries, getGoldenQueries
  // 🔄 STILL MCP: addBronzeQuery, addSilverQuery, promoteQuery, deleteQuery, getQueryStats, performMigration
  // 
  // Available REST endpoints for remaining operations:
  // - addBronzeQuery -> POST /api/v1/admin/queries/bronze (needs implementation)
  // - addSilverQuery -> POST /api/v1/admin/queries/silver (needs implementation)  
  // - promoteQuery -> POST /api/v1/admin/promote
  // - deleteQuery -> DELETE /api/v1/admin/queries/{id} (needs implementation)

  // Cloud Run service settings
  const CLOUD_RUN_URL = settings['cloud_run_service_url']?.value as string || ''
  const identityToken = settings['identity_token']?.value as string || ''


  const getSystemStatus = useCallback(async (): Promise<OlympicSystemStatus> => {
    setOperationStatus('loading')
    try {
      console.log('Getting Olympic system status via REST API...')
      const result = await getRestSystemStatus()
      
      // Transform REST response to match existing interface
      const status: OlympicSystemStatus = {
        table_exists: result.olympic_table_exists,
        total_records: result.olympic_record_count,
        records_by_rank: {
          bronze: result.olympic_records_by_rank?.bronze || 0,
          silver: result.olympic_records_by_rank?.silver || 0, 
          gold: result.olympic_records_by_rank?.gold || 0,
          disqualified: 0 // Not available in REST response yet
        },
        explore_distribution: {}, // Not available in REST response yet
        schema_version: '1.0', // Default value
        last_updated: result.timestamp
      }
      
      setSystemStatus(status)
      setOperationStatus('success')
      return status
    } catch (error) {
      console.error('System status check failed:', error)
      setOperationStatus('error')
      throw error
    }
  }, [getRestSystemStatus])

  const addBronzeQuery = useCallback(async (
    exploreId: string,
    inputText: string,
    outputData: Record<string, any>,
    link: string,
    userEmail: string
  ): Promise<QueryOperationResult> => {
    setOperationStatus('loading')
    try {
      if (!CLOUD_RUN_URL || !identityToken) {
        throw new Error('Cloud Run URL or identity token not configured')
      }
      const restApiUrl = `${CLOUD_RUN_URL}/api/v1/admin/queries/bronze`
      const response = await extensionSDK.fetchProxy(restApiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${identityToken}`,
        },
        body: JSON.stringify({
          explore_id: exploreId,
          input: inputText,
          output: outputData,
          link,
          user_email: userEmail
        })
      })
      if (!response.ok) {
        const errorText = response.body?.error || `HTTP ${response.status}`
        throw new Error(errorText)
      }
      const result = response.body
      if (!result.success) {
        throw new Error(result.error || 'Failed to add bronze query')
      }
      const operationResult: QueryOperationResult = {
        success: true,
        query_id: result.data?.id || result.data?.query_id,
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
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

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
      if (!CLOUD_RUN_URL || !identityToken) {
        throw new Error('Cloud Run URL or identity token not configured')
      }
      const restApiUrl = `${CLOUD_RUN_URL}/api/v1/admin/queries/silver`
      const response = await extensionSDK.fetchProxy(restApiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${identityToken}`,
        },
        body: JSON.stringify({
          explore_id: exploreId,
          input: inputText,
          output: outputData,
          link,
          user_id: userId,
          feedback_type: feedbackType,
          conversation_history: conversationHistory
        })
      })
      if (!response.ok) {
        const errorText = response.body?.error || `HTTP ${response.status}`
        throw new Error(errorText)
      }
      const result = response.body
      if (!result.success) {
        throw new Error(result.error || 'Failed to add silver query')
      }
      const operationResult: QueryOperationResult = {
        success: true,
        query_id: result.data?.id || result.data?.query_id,
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
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  const promoteQuery = useCallback(async (
    queryId: string,
    promotedBy: string,
    fromRank: 'bronze' | 'silver' = 'bronze',
    toRank: 'silver' | 'gold' = 'gold'
  ): Promise<QueryPromotionResult> => {
    setOperationStatus('loading')
    try {
      if (!CLOUD_RUN_URL || !identityToken) {
        throw new Error('Cloud Run URL or identity token not configured')
      }
      const restApiUrl = `${CLOUD_RUN_URL}/api/v1/admin/promote`
      const response = await extensionSDK.fetchProxy(restApiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${identityToken}`,
        },
        body: JSON.stringify({
          query_id: queryId,
          target_rank: toRank.toUpperCase(),
          promoted_by: promotedBy,
          promotion_reason: undefined
        })
      })
      if (!response.ok) {
        const errorText = response.body?.error || `HTTP ${response.status}`
        throw new Error(errorText)
      }
      const result = response.body
      if (!result.success) {
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
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  const deleteQuery = useCallback(async (
    queryId: string,
    deletedBy: string
  ): Promise<QueryOperationResult> => {
    setOperationStatus('loading')
    try {
      if (!CLOUD_RUN_URL || !identityToken) {
        throw new Error('Cloud Run URL or identity token not configured')
      }
      const restApiUrl = `${CLOUD_RUN_URL}/api/v1/admin/queries/${queryId}`
      const response = await extensionSDK.fetchProxy(restApiUrl, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${identityToken}`,
        },
        body: JSON.stringify({ deleted_by: deletedBy })
      })
      if (!response.ok) {
        const errorText = response.body?.error || `HTTP ${response.status}`
        throw new Error(errorText)
      }
      const result = response.body
      if (!result.success) {
        throw new Error(result.error || 'Failed to delete query')
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
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

    const getGoldenQueries = useCallback(async (exploreId?: string, limit: number = 50): Promise<OlympicQuery[]> => {
    setOperationStatus('loading')
    
    try {
      console.log('Getting golden queries via REST API...', { exploreId, limit })
      
      if (!CLOUD_RUN_URL || !identityToken) {
        throw new Error('Cloud Run URL or identity token not configured')
      }

      const restApiUrl = `${CLOUD_RUN_URL}/api/v1/admin/queries/gold`
      const response = await extensionSDK.fetchProxy(restApiUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${identityToken}`,
        }
      })
      
      if (!response.ok) {
        const errorText = response.body?.error || `HTTP ${response.status}`
        throw new Error(errorText)
      }

      const result = response.body
      if (!result.success) {
        throw new Error(result.error || 'Failed to get golden queries')
      }

      const queries = result.data || []
      setOperationStatus('success')
      return queries
    } catch (error) {
      console.error('Getting golden queries failed:', error)
      setOperationStatus('error')
      throw error
    }
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  const getBronzeQueries = useCallback(async (exploreId?: string, limit: number = 50): Promise<OlympicQuery[]> => {
    setOperationStatus('loading')
    
    try {
      console.log('Getting bronze queries via REST API...', { exploreId, limit })
      
      if (!CLOUD_RUN_URL || !identityToken) {
        throw new Error('Cloud Run URL or identity token not configured')
      }

      const restApiUrl = `${CLOUD_RUN_URL}/api/v1/admin/queries/bronze`
      const response = await extensionSDK.fetchProxy(restApiUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${identityToken}`,
        }
      })
      
      if (!response.ok) {
        const errorText = response.body?.error || `HTTP ${response.status}`
        throw new Error(errorText)
      }

      const result = response.body
      if (!result.success) {
        throw new Error(result.error || 'Failed to get bronze queries')
      }

      const queries = result.data || []
      setOperationStatus('success')
      return queries
    } catch (error) {
      console.error('Getting bronze queries failed:', error)
      setOperationStatus('error')
      throw error
    }
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  const getSilverQueries = useCallback(async (exploreId?: string, limit: number = 50): Promise<OlympicQuery[]> => {
    setOperationStatus('loading')
    
    try {
      console.log('Getting silver queries via REST API...', { exploreId, limit })
      
      if (!CLOUD_RUN_URL || !identityToken) {
        throw new Error('Cloud Run URL or identity token not configured')
      }

      const restApiUrl = `${CLOUD_RUN_URL}/api/v1/admin/queries/silver`
      const response = await extensionSDK.fetchProxy(restApiUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${identityToken}`,
        }
      })
      
      if (!response.ok) {
        const errorText = response.body?.error || `HTTP ${response.status}`
        throw new Error(errorText)
      }

      const result = response.body
      if (!result.success) {
        throw new Error(result.error || 'Failed to get silver queries')
      }

      const queries = result.data || []
      setOperationStatus('success')
      return queries
    } catch (error) {
      console.error('Getting silver queries failed:', error)
      setOperationStatus('error')
      throw error
    }
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  const getDisqualifiedQueries = useCallback(async (): Promise<OlympicQuery[]> => {
    setOperationStatus('loading')
    try {
      if (!CLOUD_RUN_URL || !identityToken) {
        throw new Error('Cloud Run URL or identity token not configured')
      }
      const restApiUrl = `${CLOUD_RUN_URL}/api/v1/admin/queries/disqualified`
      const response = await extensionSDK.fetchProxy(restApiUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${identityToken}`,
        }
      })
      if (!response.ok) {
        const errorText = response.body?.error || `HTTP ${response.status}`
        throw new Error(errorText)
      }
      const result = response.body
      if (!result.success) {
        throw new Error(result.error || 'Failed to get disqualified queries')
      }
      const queries = result.data || []
      setOperationStatus('success')
      return queries
    } catch (error) {
      console.error('Getting disqualified queries failed:', error)
      setOperationStatus('error')
      throw error
    }
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  const getQueryStats = useCallback(async (): Promise<QueryStatsResult> => {
    setOperationStatus('loading')
    try {
      if (!CLOUD_RUN_URL || !identityToken) {
        throw new Error('Cloud Run URL or identity token not configured')
      }
      const restApiUrl = `${CLOUD_RUN_URL}/api/v1/admin/stats`
      const response = await extensionSDK.fetchProxy(restApiUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${identityToken}`,
        }
      })
      if (!response.ok) {
        const errorText = response.body?.error || `HTTP ${response.status}`
        throw new Error(errorText)
      }
      const result = response.body
      if (!result.success) {
        throw new Error(result.error || 'Failed to get query stats')
      }
      const stats = result.data
      setQueryStats(stats)
      setOperationStatus('success')
      return stats
    } catch (error) {
      setOperationStatus('error')
      console.error('Getting query stats failed:', error)
      throw error
    }
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  const checkMigrationStatus = useCallback(async (): Promise<MigrationStatus> => {
    setOperationStatus('loading')
    
    try {
      console.log('Checking migration status via REST API...')
      const result = await getRestMigrationStatus()
      
      // Transform REST response to match existing interface
      const status: MigrationStatus = {
        migration_needed: result.migration_required,
        legacy_tables_exist: [], // Not directly available in REST response
        olympic_table_exists: result.status !== 'needs_olympic_setup',
        estimated_record_count: result.legacy_records_to_migrate || 0,
        schema_issues: [], // Not available in REST response yet
        can_migrate_safely: result.can_migrate,
        recommendations: result.obstacles || [],
        summary: `Migration status: ${result.status}`
      }
      
      setMigrationStatus(status)
      setOperationStatus('success')
      return status
    } catch (error) {
      setOperationStatus('error')
      console.error('Checking migration status failed:', error)
      throw error
    }
  }, [getRestMigrationStatus])

  const performMigration = useCallback(async (preserveData: boolean = true, verifyMigration: boolean = true): Promise<MigrationResult> => {
    setOperationStatus('loading')
    setMigrationResult(null)
    try {
      if (!CLOUD_RUN_URL || !identityToken) {
        throw new Error('Cloud Run URL or identity token not configured')
      }
      const restApiUrl = `${CLOUD_RUN_URL}/api/v1/admin/migrate`
      const response = await extensionSDK.fetchProxy(restApiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${identityToken}`,
        },
        body: JSON.stringify({ preserve_data: preserveData, verify_migration: verifyMigration })
      })
      if (!response.ok) {
        const errorText = response.body?.error || `HTTP ${response.status}`
        throw new Error(errorText)
      }
      const result = response.body
      if (!result.success) {
        throw new Error(result.error || 'Migration failed')
      }
      const migrationData = result.data
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
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

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
