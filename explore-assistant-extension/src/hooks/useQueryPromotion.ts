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

    console.log('Making MCP tool request:', { toolName, args })

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
      console.error('MCP tool call failed:', error)
      throw error
    }
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  const getQueriesForPromotion = useCallback(async (
    tableName: 'bronze' | 'silver',
    limit: number = 50,
    offset: number = 0
  ): Promise<QueriesResult> => {
    try {
      console.log(`Getting queries for promotion from ${tableName} table...`)
      
      const result = await callMCPTool('get_queries_by_rank', {
        rank: tableName,
        limit: limit,
        offset: offset
      })
      
      if (result.error) {
        throw new Error(result.error)
      }
      
      return {
        queries: result.queries || [],
        total: result.total || 0
      }
    } catch (error) {
      console.error(`Error fetching ${tableName} queries:`, error)
      throw error
    }
  }, [callMCPTool])

  const promoteQuery = useCallback(async (
    queryId: string,
    sourceTable: string,
    targetTable: string = 'golden',
    reason: string = ''
  ): Promise<PromotionResult> => {
    try {
      console.log('Promoting query with MCP tool:', { queryId, sourceTable, targetTable, reason })
      
      const result = await callMCPTool('promote_to_gold', {
        query_id: queryId,
        promoted_by: 'user' // You might want to get actual user info
      })

      if (result.error) {
        throw new Error(result.error)
      }

      console.log('Query promoted successfully:', result)
      
      return {
        new_query_id: result.new_query_id || result.query_id,
        source_query_id: queryId,
        source_table: sourceTable,
        target_table: 'gold', // Olympic system uses 'gold' instead of 'golden'
        promoted_by: result.promoted_by || 'user'
      }
    } catch (error) {
      console.error('Error promoting query:', error)
      throw error
    }
  }, [callMCPTool])

  const getPromotionHistory = useCallback(async (
    limit: number = 50,
    offset: number = 0
  ): Promise<HistoryResult> => {
    try {
      console.log('Getting promotion history...')
      
      const result = await callMCPTool('get_promotion_history', {
        limit: limit,
        offset: offset
      })
      
      if (result.error) {
        throw new Error(result.error)
      }
      
      return {
        history: result.history || [],
        total: result.total || 0
      }
    } catch (error) {
      console.error('Error fetching promotion history:', error)
      throw error
    }
  }, [callMCPTool])

  return {
    getQueriesForPromotion,
    promoteQuery,
    getPromotionHistory
  }
}
