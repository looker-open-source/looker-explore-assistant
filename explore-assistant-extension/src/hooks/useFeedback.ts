import { useState, useContext } from 'react'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { useSelector } from 'react-redux'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'

export type FeedbackType = 'positive' | 'negative' | 'refinement' | 'alternative'

interface FeedbackData {
  queryId?: string
  exploreId: string
  originalPrompt: string
  generatedParams: any
  shareUrl: string
  feedbackType: FeedbackType
  userId: string
  userComment?: string
  suggestedImprovements?: any
  issues?: string[]
  conversationContext?: string
}

interface ExplicitFeedbackData {
  queryId: string
  userInput: string
  response: string
  exploreKey?: string  // Add explore_key for Olympic integration
  feedbackNotes?: string
}

interface NegativeFeedbackData extends ExplicitFeedbackData {
  issues: string[]
  improvementSuggestions?: string
}

interface ImprovementRequestData {
  queryId: string
  originalInput: string
  originalResponse: string
  improvementRequest: string
  context?: string
}

interface FeedbackHistoryFilters {
  exploreId?: string
  userId?: string
  feedbackType?: FeedbackType
  limit?: number
}

export const useFeedback = () => {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const { settings } = useSelector((state: RootState) => state.assistant as AssistantState)
  const extensionContext = useContext(ExtensionContext)
  // Utility to update the hostname in a URL to match the extension context host
  function updateUrlHostname(originalUrl: string): string {
    try {
      const url = new URL(originalUrl)
      // Use hostOrigin if available, else fallback to window.location.origin
      const hostOrigin = extensionContext?.lookerHostData?.hostOrigin || window.location.origin
      const parsedHost = new URL(hostOrigin)
      url.protocol = parsedHost.protocol
      url.hostname = parsedHost.hostname
      url.port = parsedHost.port // will be empty string if not present
      return url.toString()
    } catch {
      return originalUrl
    }
  }
  
  // Get Cloud Run settings
  const CLOUD_RUN_URL = settings['cloud_run_service_url']?.value as string || ''
  const identityToken = settings['identity_token']?.value as string || ''

  const callMCPTool = async (toolName: string, args: any): Promise<any> => {
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

    const response = await fetch(CLOUD_RUN_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${identityToken}`,
      },
      body: JSON.stringify(requestBody)
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const result = await response.json()
    
    if (result.error) {
      throw new Error(result.error)
    }

    return result
  }

  // Enhanced explicit feedback methods
  const submitPositiveFeedback = async (data: ExplicitFeedbackData): Promise<boolean> => {
    setIsSubmitting(true)
    
    try {
      const response = await fetch(`${CLOUD_RUN_URL}/api/v1/feedback/positive`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${identityToken}`,
        },
        body: JSON.stringify({
          query_id: data.queryId,
          user_input: data.userInput,
          response: data.response,
          explore_key: data.exploreKey,
          feedback_notes: data.feedbackNotes
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return true
    } catch (error) {
      console.error('Failed to submit positive feedback:', error)
      return false
    } finally {
      setIsSubmitting(false)
    }
  }

  const submitNegativeFeedback = async (data: NegativeFeedbackData): Promise<boolean> => {
    setIsSubmitting(true)
    
    try {
      const response = await fetch(`${CLOUD_RUN_URL}/api/v1/feedback/negative`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${identityToken}`,
        },
        body: JSON.stringify({
          query_id: data.queryId,
          user_input: data.userInput,
          response: data.response,
          explore_key: data.exploreKey,
          issues: data.issues,
          improvement_suggestions: data.improvementSuggestions
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return true
    } catch (error) {
      console.error('Failed to submit negative feedback:', error)
      return false
    } finally {
      setIsSubmitting(false)
    }
  }

  const requestResponseImprovement = async (data: ImprovementRequestData): Promise<boolean> => {
    setIsSubmitting(true)
    
    try {
      await callMCPTool('request_response_improvement', {
        query_id: data.queryId,
        original_input: data.originalInput,
        original_response: data.originalResponse,
        improvement_request: data.improvementRequest,
        context: data.context
      })

      return true
    } catch (error) {
      console.error('Failed to request improvement:', error)
      return false
    } finally {
      setIsSubmitting(false)
    }
  }

  const submitFeedback = async (feedbackData: FeedbackData): Promise<boolean> => {
    setIsSubmitting(true)
    try {
      if (!CLOUD_RUN_URL) {
        throw new Error('Cloud Run URL not configured')
      }
      if (!identityToken) {
        throw new Error('Identity token not available')
      }
      // Replace shareUrl hostname with extension context host
      const updatedShareUrl = updateUrlHostname(feedbackData.shareUrl)
      const requestBody = {
        tool_name: 'add_feedback_query',
        arguments: {
          explore_id: feedbackData.exploreId,
          original_prompt: feedbackData.originalPrompt,
          generated_params: feedbackData.generatedParams,
          share_url: updatedShareUrl,
          feedback_type: feedbackData.feedbackType,
          user_id: feedbackData.userId,
          conversation_context: null, // TODO: Add conversation context from state
          user_comment: feedbackData.userComment,
          suggested_improvements: typeof feedbackData.suggestedImprovements === 'string'
            ? feedbackData.suggestedImprovements
            : JSON.stringify(feedbackData.suggestedImprovements),
          issues: feedbackData.issues || (feedbackData.feedbackType === 'negative' ? ['User marked as unhelpful'] : null),
          query_id: feedbackData.queryId
        }
      }
      const response = await fetch(CLOUD_RUN_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${identityToken}`,
        },
        body: JSON.stringify(requestBody)
      })
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const result = await response.json()
      if (result.error || result.status !== 'success') {
        throw new Error(result.error || 'Failed to submit feedback')
      }
      return true
    } catch (error) {
      console.error('Failed to submit feedback:', error)
      return false
    } finally {
      setIsSubmitting(false)
    }
  }

  const getFeedbackHistory = async (filters: FeedbackHistoryFilters = {}) => {
    setIsLoading(true)
    
    try {
      if (!CLOUD_RUN_URL) {
        throw new Error('Cloud Run URL not configured')
      }
      
      if (!identityToken) {
        throw new Error('Identity token not available')
      }

      const requestBody = {
        tool_name: 'get_query_feedback_history',
        arguments: {
          explore_id: filters.exploreId,
          user_id: filters.userId,
          feedback_type: filters.feedbackType,
          limit: filters.limit || 20
        }
      }

      const response = await fetch(CLOUD_RUN_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${identityToken}`,
        },
        body: JSON.stringify(requestBody)
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      
      if (result.error) {
        throw new Error(result.error)
      }

      return result.feedback_history || []
    } catch (error) {
      console.error('Failed to get feedback history:', error)
      return []
    } finally {
      setIsLoading(false)
    }
  }

  const getQueryStats = async () => {
    try {
      if (!CLOUD_RUN_URL) {
        throw new Error('Cloud Run URL not configured')
      }
      
      if (!identityToken) {
        throw new Error('Identity token not available')
      }

      const requestBody = {
        tool_name: 'get_query_stats',
        arguments: {}
      }

      const response = await fetch(CLOUD_RUN_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${identityToken}`,
        },
        body: JSON.stringify(requestBody)
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      
      if (result.error) {
        throw new Error(result.error)
      }

      return result.query_statistics || {}
    } catch (error) {
      console.error('Failed to get query stats:', error)
      return {}
    }
  }

  return {
    submitFeedback,
    submitPositiveFeedback,
    submitNegativeFeedback,
    requestResponseImprovement,
    getFeedbackHistory,
    getQueryStats,
    isSubmitting,
    isLoading
  }
}

export default useFeedback
