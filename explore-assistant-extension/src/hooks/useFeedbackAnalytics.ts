import { useState, useCallback } from 'react'
import { useFeedback, FeedbackType } from './useFeedback'

export interface FeedbackAnalytics {
  totalFeedback: number
  positiveFeedback: number
  negativeFeedback: number
  refinementRequests: number
  alternativeRequests: number
  satisfactionRate: number
  topIssues: Array<{ issue: string; count: number }>
  recentTrend: 'improving' | 'declining' | 'stable'
}

export interface FeedbackEntry {
  id: string
  queryId: string
  exploreId: string
  originalPrompt: string
  generatedParams: any
  feedbackType: FeedbackType
  userId: string
  userComment?: string
  suggestedImprovements?: any
  issues?: string[]
  createdAt: string
}

export const useFeedbackAnalytics = () => {
  const [analytics, setAnalytics] = useState<FeedbackAnalytics | null>(null)
  const [recentFeedback, setRecentFeedback] = useState<FeedbackEntry[]>([])
  const [loading, setLoading] = useState(false)
  
  const { getFeedbackHistory, getQueryStats } = useFeedback()

  const analyzeFeedback = useCallback(async (exploreId?: string, limit: number = 100) => {
    setLoading(true)
    try {
      // Get feedback history
      const feedbackHistory = await getFeedbackHistory({
        exploreId,
        limit
      })

      // Get query stats (for future use)
      await getQueryStats()

      // Calculate analytics with proper typing
      const totalFeedback = feedbackHistory.length
      const positiveFeedback = feedbackHistory.filter((f: any) => f.feedbackType === 'positive' || f.feedback_type === 'positive').length
      const negativeFeedback = feedbackHistory.filter((f: any) => f.feedbackType === 'negative' || f.feedback_type === 'negative').length
      const refinementRequests = feedbackHistory.filter((f: any) => f.feedbackType === 'refinement' || f.feedback_type === 'refinement').length
      const alternativeRequests = feedbackHistory.filter((f: any) => f.feedbackType === 'alternative' || f.feedback_type === 'alternative').length
      
      const satisfactionRate = totalFeedback > 0 ? Math.round((positiveFeedback / totalFeedback) * 100) : 0

      // Extract top issues from negative feedback
      const allIssues: string[] = []
      feedbackHistory
        .filter((f: any) => (f.feedbackType === 'negative' || f.feedback_type === 'negative') && f.issues)
        .forEach((f: any) => {
          if (f.issues) {
            allIssues.push(...f.issues)
          }
        })

      const issueCounts = allIssues.reduce((acc, issue) => {
        acc[issue] = (acc[issue] || 0) + 1
        return acc
      }, {} as Record<string, number>)

      const topIssues = Object.entries(issueCounts)
        .map(([issue, count]) => ({ issue, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 5)

      // Calculate trend (simplified - based on recent vs older feedback)
      const recentCount = Math.min(10, Math.floor(totalFeedback / 2))
      const recentFeedbackEntries = feedbackHistory.slice(0, recentCount)
      const olderFeedbackEntries = feedbackHistory.slice(recentCount, recentCount * 2)
      
      const recentPositiveRate = recentFeedbackEntries.length > 0 ? 
        recentFeedbackEntries.filter((f: any) => f.feedbackType === 'positive' || f.feedback_type === 'positive').length / recentFeedbackEntries.length : 0
      const olderPositiveRate = olderFeedbackEntries.length > 0 ? 
        olderFeedbackEntries.filter((f: any) => f.feedbackType === 'positive' || f.feedback_type === 'positive').length / olderFeedbackEntries.length : 0

      let recentTrend: 'improving' | 'declining' | 'stable' = 'stable'
      if (recentPositiveRate > olderPositiveRate + 0.1) {
        recentTrend = 'improving'
      } else if (recentPositiveRate < olderPositiveRate - 0.1) {
        recentTrend = 'declining'
      }

      const analyticsData: FeedbackAnalytics = {
        totalFeedback,
        positiveFeedback,
        negativeFeedback,
        refinementRequests,
        alternativeRequests,
        satisfactionRate,
        topIssues,
        recentTrend
      }

      setAnalytics(analyticsData)
      setRecentFeedback(feedbackHistory.slice(0, 20)) // Keep latest 20 for display

      return analyticsData
    } catch (error) {
      console.error('Failed to analyze feedback:', error)
      throw error
    } finally {
      setLoading(false)
    }
  }, [getFeedbackHistory, getQueryStats])

  const getFeedbackSummary = () => {
    if (!analytics) return null
    
    return {
      overall: `${analytics.satisfactionRate}% satisfaction rate`,
      summary: `${analytics.totalFeedback} total feedback entries`,
      trend: analytics.recentTrend === 'improving' ? '📈 Improving' : 
             analytics.recentTrend === 'declining' ? '📉 Declining' : '➡️ Stable',
      topIssue: analytics.topIssues[0]?.issue || 'No major issues identified',
      needsAttention: analytics.satisfactionRate < 70 || analytics.recentTrend === 'declining'
    }
  }

  return {
    analytics,
    recentFeedback,
    loading,
    analyzeFeedback,
    getFeedbackSummary
  }
}

export default useFeedbackAnalytics
