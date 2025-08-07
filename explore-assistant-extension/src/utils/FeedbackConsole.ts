import { useFeedback } from '../hooks/useFeedback'

/**
 * Console-based feedback viewer for debugging and quick inspection
 */
export class FeedbackConsole {
  private feedback: ReturnType<typeof useFeedback>

  constructor(feedbackHook: ReturnType<typeof useFeedback>) {
    this.feedback = feedbackHook
  }

  /**
   * View recent feedback in the browser console
   */
  async viewRecentFeedback(limit: number = 10): Promise<void> {
    console.log('🔍 Loading recent feedback...')
    
    try {
      const history = await this.feedback.getFeedbackHistory({ limit })
      
      if (history.length === 0) {
        console.log('📭 No feedback found')
        return
      }

      console.log(`📋 Found ${history.length} feedback entries:`)
      console.table(history.map((feedback: any) => ({
        Type: this.getFeedbackEmoji(feedback.feedback_type || feedback.feedbackType),
        Query: feedback.original_prompt?.substring(0, 50) + '...',
        Explore: feedback.explore_id || feedback.exploreId,
        User: feedback.user_id || feedback.userId,
        Date: feedback.created_at ? new Date(feedback.created_at).toLocaleDateString() : 'N/A'
      })))

      // Show detailed stats
      const stats = this.calculateStats(history)
      console.log('📊 Feedback Statistics:', stats)
      
    } catch (error) {
      console.error('❌ Failed to load feedback:', error)
    }
  }

  /**
   * View feedback for a specific explore
   */
  async viewExploreeFeedback(exploreId: string, limit: number = 20): Promise<void> {
    console.log(`🔍 Loading feedback for ${exploreId}...`)
    
    try {
      const history = await this.feedback.getFeedbackHistory({ exploreId, limit })
      
      if (history.length === 0) {
        console.log(`📭 No feedback found for ${exploreId}`)
        return
      }

      console.log(`📋 Found ${history.length} feedback entries for ${exploreId}:`)
      
      history.forEach((feedback: any, index: number) => {
        console.log(`\n${index + 1}. ${this.getFeedbackEmoji(feedback.feedback_type || feedback.feedbackType)} ${feedback.feedback_type || feedback.feedbackType}`)
        console.log(`   Query: "${feedback.original_prompt}"`)
        console.log(`   User: ${feedback.user_id || feedback.userId}`)
        
        if (feedback.user_comment) {
          console.log(`   Comment: "${feedback.user_comment}"`)
        }
        
        if (feedback.issues && feedback.issues.length > 0) {
          console.log(`   Issues: ${feedback.issues.join(', ')}`)
        }
        
        if (feedback.suggested_improvements) {
          console.log(`   Suggestions: ${JSON.stringify(feedback.suggested_improvements)}`)
        }
      })

      const stats = this.calculateStats(history)
      console.log('\n📊 Statistics for this explore:', stats)
      
    } catch (error) {
      console.error('❌ Failed to load explore feedback:', error)
    }
  }

  /**
   * View query statistics
   */
  async viewQueryStats(): Promise<void> {
    console.log('🔍 Loading query statistics...')
    
    try {
      const stats = await this.feedback.getQueryStats()
      console.log('📊 Query Statistics:', stats)
    } catch (error) {
      console.error('❌ Failed to load query stats:', error)
    }
  }

  /**
   * Test feedback submission (useful for development)
   */
  async testFeedbackSubmission(): Promise<void> {
    console.log('🧪 Testing feedback submission...')
    
    try {
      // Test positive feedback
      const positiveResult = await this.feedback.submitPositiveFeedback({
        queryId: 'test-' + Date.now(),
        userInput: 'Test query for positive feedback',
        response: JSON.stringify({ test: 'response' }),
        feedbackNotes: 'This is a test of positive feedback'
      })
      
      console.log('✅ Positive feedback test:', positiveResult ? 'SUCCESS' : 'FAILED')

      // Test negative feedback
      const negativeResult = await this.feedback.submitNegativeFeedback({
        queryId: 'test-' + Date.now(),
        userInput: 'Test query for negative feedback',
        response: JSON.stringify({ test: 'response' }),
        issues: ['Wrong fields', 'Incorrect filters'],
        improvementSuggestions: 'Please use better field selection',
        feedbackNotes: 'This is a test of negative feedback'
      })
      
      console.log('❌ Negative feedback test:', negativeResult ? 'SUCCESS' : 'FAILED')
      
    } catch (error) {
      console.error('🚫 Feedback testing failed:', error)
    }
  }

  private getFeedbackEmoji(type: string): string {
    switch (type) {
      case 'positive': return '👍'
      case 'negative': return '👎'
      case 'refinement': return '⚡'
      case 'alternative': return '🔄'
      default: return '❓'
    }
  }

  private calculateStats(history: any[]): any {
    const total = history.length
    const positive = history.filter(f => (f.feedback_type || f.feedbackType) === 'positive').length
    const negative = history.filter(f => (f.feedback_type || f.feedbackType) === 'negative').length
    const refinement = history.filter(f => (f.feedback_type || f.feedbackType) === 'refinement').length
    const alternative = history.filter(f => (f.feedback_type || f.feedbackType) === 'alternative').length
    
    return {
      total,
      positive: `${positive} (${Math.round((positive/total)*100)}%)`,
      negative: `${negative} (${Math.round((negative/total)*100)}%)`,
      refinement,
      alternative,
      satisfaction_rate: `${Math.round((positive/total)*100)}%`
    }
  }
}

/**
 * Global function to create feedback console in browser dev tools
 */
export const createFeedbackConsole = (feedbackHook: ReturnType<typeof useFeedback>): FeedbackConsole => {
  const console = new FeedbackConsole(feedbackHook)
  
  // Make it available globally for debugging
  if (typeof window !== 'undefined') {
    (window as any).feedbackConsole = console
  }
  
  return console
}

/**
 * Usage in browser console:
 * 
 * // View recent feedback
 * feedbackConsole.viewRecentFeedback()
 * 
 * // View feedback for specific explore
 * feedbackConsole.viewExploreeFeedback('ecommerce:order_items')
 * 
 * // View query stats
 * feedbackConsole.viewQueryStats()
 * 
 * // Test feedback submission
 * feedbackConsole.testFeedbackSubmission()
 */
