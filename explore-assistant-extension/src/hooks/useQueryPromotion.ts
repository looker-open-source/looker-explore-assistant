import { useCallback, useContext } from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'
import { ExtensionContext } from '@looker/extension-sdk-react'

interface PromotionResult {
  new_query_id: string
  source_query_id: string
  source_table: string
  target_table: string
  promoted_by: string
}

interface QueriesResult {
  queries: any[]
  total: number
}

interface HistoryResult {
  history: any[]
  total: number
}

export const useQueryPromotion = () => {
  const { extensionSDK } = useContext(ExtensionContext)
  const { settings } = useSelector((state: RootState) => state.assistant as AssistantState)

  // Cloud Run service settings
  const CLOUD_RUN_URL = settings['cloud_run_service_url']?.value as string || ''
  const identityToken = settings['identity_token']?.value as string || ''

  const callPromotionAPI = useCallback(async (endpoint: string, options: RequestInit = {}) => {
    if (!CLOUD_RUN_URL) {
      throw new Error('Cloud Run service URL not configured')
    }

    if (!identityToken) {
      throw new Error('Identity token not available')
    }

    const url = `${CLOUD_RUN_URL}${endpoint}`
    console.log('Making promotion API request to:', url)

    try {
      // Try fetchProxy first (preferred)
      try {
        console.log('Attempting fetchProxy request...')
        const response = await extensionSDK.fetchProxy(url, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${identityToken}`,
          },
          ...options,
        })

        if (!response.ok) {
          const errorText = await response.text()
          throw new Error(`HTTP ${response.status}: ${errorText}`)
        }

        return await response.json()
      } catch (proxyError) {
        console.warn('fetchProxy failed, falling back to direct fetch...', proxyError)
        
        // Fallback to direct fetch
        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${identityToken}`,
          },
          ...options,
        })

        if (!response.ok) {
          const errorText = await response.text()
          throw new Error(`HTTP ${response.status}: ${errorText}`)
        }

        return await response.json()
      }
    } catch (error) {
      console.error('API call failed:', error)
      throw error
    }
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  const getQueriesForPromotion = useCallback(async (
    tableName: 'bronze' | 'silver',
    limit: number = 50,
    offset: number = 0
  ): Promise<QueriesResult> => {
    try {
      const endpoint = `/admin/queries/${tableName}?limit=${limit}&offset=${offset}`
      const result = await callPromotionAPI(endpoint)
      
      return {
        queries: result.queries || [],
        total: result.total || 0
      }
    } catch (error) {
      console.error(`Error fetching ${tableName} queries:`, error)
      throw error
    }
  }, [callPromotionAPI])

  const promoteQuery = useCallback(async (
    queryId: string,
    sourceTable: string,
    targetTable: string,
    reason: string = ''
  ): Promise<PromotionResult> => {
    try {
      const endpoint = '/admin/promote'
      const payload = {
        query_id: queryId,
        source_table: sourceTable,
        target_table: targetTable,
        reason: reason
      }

      console.log('Promoting query with payload:', payload)
      console.log('Using endpoint:', endpoint)
      console.log('Query ID type and value:', typeof queryId, queryId)
      console.log('Source table type and value:', typeof sourceTable, sourceTable)

      const result = await callPromotionAPI(endpoint, {
        method: 'POST',
        body: JSON.stringify(payload)
      })

      console.log('Query promoted successfully:', result)
      return result
    } catch (error) {
      console.error('Error promoting query:', error)
      throw error
    }
  }, [callPromotionAPI])

  const getPromotionHistory = useCallback(async (
    limit: number = 50,
    offset: number = 0
  ): Promise<HistoryResult> => {
    try {
      const endpoint = `/admin/promotion-history?limit=${limit}&offset=${offset}`
      const result = await callPromotionAPI(endpoint)
      
      return {
        history: result.history || [],
        total: result.total || 0
      }
    } catch (error) {
      console.error('Error fetching promotion history:', error)
      throw error
    }
  }, [callPromotionAPI])

  return {
    getQueriesForPromotion,
    promoteQuery,
    getPromotionHistory
  }
}
