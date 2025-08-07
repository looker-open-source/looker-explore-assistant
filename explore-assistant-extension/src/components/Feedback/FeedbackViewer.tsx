import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  CircularProgress,
  Divider
} from '@material-ui/core'
import {
  ThumbUp,
  ThumbDown,
  Feedback as FeedbackIcon,
  Timeline,
  Refresh as RefreshIcon
} from '@material-ui/icons'
import { useFeedback, FeedbackType } from '../../hooks/useFeedback'

interface FeedbackViewerProps {
  exploreId?: string
  limit?: number
  showStats?: boolean
  compact?: boolean
}

interface FeedbackEntry {
  id: string
  query_id: string
  explore_id: string
  original_prompt: string
  feedback_type: FeedbackType
  user_id: string
  user_comment?: string
  created_at: string
}

const FeedbackViewer: React.FC<FeedbackViewerProps> = ({
  exploreId,
  limit = 10,
  showStats = true,
  compact = false
}) => {
  const [feedbackHistory, setFeedbackHistory] = useState<FeedbackEntry[]>([])
  const [loading, setLoading] = useState(false)
  const { getFeedbackHistory } = useFeedback()

  const loadFeedback = async () => {
    setLoading(true)
    try {
      const history = await getFeedbackHistory({
        exploreId,
        limit
      })
      setFeedbackHistory(history)
    } catch (error) {
      console.error('Failed to load feedback:', error)
    } finally {
      setLoading(false)
    }
  }

  const getFeedbackIcon = (type: FeedbackType) => {
    switch (type) {
      case 'positive': return <ThumbUp style={{ color: '#4caf50' }} />
      case 'negative': return <ThumbDown style={{ color: '#f44336' }} />
      case 'refinement': return <FeedbackIcon color="action" />
      case 'alternative': return <Timeline color="action" />
    }
  }

  const getFeedbackStats = () => {
    const total = feedbackHistory.length
    const positive = feedbackHistory.filter(f => f.feedback_type === 'positive').length
    const negative = feedbackHistory.filter(f => f.feedback_type === 'negative').length
    return { total, positive, negative, satisfaction: total > 0 ? Math.round((positive / total) * 100) : 0 }
  }

  useEffect(() => {
    loadFeedback()
  }, [exploreId, limit])

  const stats = getFeedbackStats()

  return (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant={compact ? "subtitle1" : "h6"}>
            {exploreId ? `Feedback for ${exploreId}` : 'Recent Feedback'}
          </Typography>
          <Button
            size="small"
            startIcon={<RefreshIcon />}
            onClick={loadFeedback}
            disabled={loading}
          >
            Refresh
          </Button>
        </Box>

        {showStats && stats.total > 0 && (
          <Box mb={2}>
            <Box display="flex" style={{ gap: '8px' }} mb={1}>
              <Chip 
                size="small" 
                label={`${stats.total} total`} 
              />
              <Chip 
                size="small" 
                label={`${stats.positive} positive`} 
                style={{ backgroundColor: '#e8f5e8', color: '#2e7d32' }}
              />
              <Chip 
                size="small" 
                label={`${stats.negative} negative`} 
                style={{ backgroundColor: '#ffebee', color: '#c62828' }}
              />
              <Chip 
                size="small" 
                label={`${stats.satisfaction}% satisfaction`} 
                color={stats.satisfaction >= 70 ? 'primary' : stats.satisfaction >= 50 ? 'default' : 'secondary'}
              />
            </Box>
            <Divider />
          </Box>
        )}

        {loading ? (
          <Box display="flex" justifyContent="center" p={2}>
            <CircularProgress size={24} />
          </Box>
        ) : feedbackHistory.length === 0 ? (
          <Typography variant="body2" color="textSecondary" align="center" style={{ padding: '16px' }}>
            No feedback available yet
          </Typography>
        ) : (
          <List dense={compact}>
            {feedbackHistory.map((feedback, index) => (
              <React.Fragment key={feedback.id}>
                <ListItem>
                  <ListItemIcon>
                    {getFeedbackIcon(feedback.feedback_type)}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box>
                        <Typography variant={compact ? "body2" : "body1"} noWrap>
                          {feedback.original_prompt}
                        </Typography>
                        <Box display="flex" style={{ gap: '8px' }} mt={0.5}>
                          <Chip size="small" label={feedback.feedback_type} />
                          {!exploreId && (
                            <Chip size="small" label={feedback.explore_id} variant="outlined" />
                          )}
                        </Box>
                      </Box>
                    }
                    secondary={
                      <Box>
                        {feedback.user_comment && (
                          <Typography variant="caption" display="block">
                            "{feedback.user_comment}"
                          </Typography>
                        )}
                        <Typography variant="caption" color="textSecondary">
                          {feedback.user_id} • {feedback.created_at ? 
                            new Date(feedback.created_at).toLocaleDateString() : 'Recently'}
                        </Typography>
                      </Box>
                    }
                  />
                </ListItem>
                {index < feedbackHistory.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        )}
      </CardContent>
    </Card>
  )
}

export default FeedbackViewer
