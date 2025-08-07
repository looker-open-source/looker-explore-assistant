import React, { useState, useEffect } from 'react'
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  Grid,
  Button,
  Chip,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@material-ui/core'
import {
  Refresh as RefreshIcon,
  ThumbUp,
  ThumbDown,
  Feedback as FeedbackIcon,
  ExpandMore,
  Visibility,
  BarChart,
  TrendingUp,
  TrendingDown,
  Timeline
} from '@material-ui/icons'
import { useFeedback, FeedbackType } from '../../hooks/useFeedback'

interface FeedbackEntry {
  id: string
  query_id: string
  explore_id: string
  original_prompt: string
  generated_params: any
  feedback_type: FeedbackType
  user_id: string
  user_comment?: string
  suggested_improvements?: any
  created_at: string
}

interface FeedbackStats {
  total_feedback: number
  positive_count: number
  negative_count: number
  refinement_count: number
  alternative_count: number
  top_explores: Array<{ explore_id: string; count: number }>
  recent_trends: Array<{ date: string; positive: number; negative: number }>
}

const FeedbackDashboard: React.FC = () => {
  const [feedbackHistory, setFeedbackHistory] = useState<FeedbackEntry[]>([])
  const [stats, setStats] = useState<FeedbackStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({
    exploreId: '',
    userId: '',
    feedbackType: '' as FeedbackType | '',
    limit: 50
  })
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackEntry | null>(null)

  const { getFeedbackHistory, getQueryStats, isLoading } = useFeedback()

  const loadFeedbackData = async () => {
    setLoading(true)
    try {
      // Get feedback history
      const history = await getFeedbackHistory({
        exploreId: filters.exploreId || undefined,
        userId: filters.userId || undefined,
        feedbackType: filters.feedbackType || undefined,
        limit: filters.limit
      })

      // Get query statistics
      const queryStats = await getQueryStats()

      setFeedbackHistory(history)
      
      // Calculate stats from history
      const stats: FeedbackStats = {
        total_feedback: history.length,
        positive_count: history.filter(f => f.feedback_type === 'positive').length,
        negative_count: history.filter(f => f.feedback_type === 'negative').length,
        refinement_count: history.filter(f => f.feedback_type === 'refinement').length,
        alternative_count: history.filter(f => f.feedback_type === 'alternative').length,
        top_explores: getTopExplores(history),
        recent_trends: getRecentTrends(history)
      }
      
      setStats(stats)
    } catch (error) {
      console.error('Failed to load feedback data:', error)
    } finally {
      setLoading(false)
    }
  }

  const getTopExplores = (history: FeedbackEntry[]): Array<{ explore_id: string; count: number }> => {
    const exploreCounts = history.reduce((acc, feedback) => {
      acc[feedback.explore_id] = (acc[feedback.explore_id] || 0) + 1
      return acc
    }, {} as Record<string, number>)

    return Object.entries(exploreCounts)
      .map(([explore_id, count]) => ({ explore_id, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5)
  }

  const getRecentTrends = (history: FeedbackEntry[]): Array<{ date: string; positive: number; negative: number }> => {
    const last7Days = Array.from({ length: 7 }, (_, i) => {
      const date = new Date()
      date.setDate(date.getDate() - i)
      return date.toISOString().split('T')[0]
    }).reverse()

    return last7Days.map(date => {
      const dayFeedback = history.filter(f => f.created_at?.startsWith(date))
      return {
        date,
        positive: dayFeedback.filter(f => f.feedback_type === 'positive').length,
        negative: dayFeedback.filter(f => f.feedback_type === 'negative').length
      }
    })
  }

  const getFeedbackIcon = (type: FeedbackType) => {
    switch (type) {
      case 'positive': return <ThumbUp color="primary" />
      case 'negative': return <ThumbDown color="secondary" />
      case 'refinement': return <FeedbackIcon color="action" />
      case 'alternative': return <Timeline color="action" />
    }
  }

  const getFeedbackColor = (type: FeedbackType) => {
    switch (type) {
      case 'positive': return 'primary'
      case 'negative': return 'secondary'
      case 'refinement': return 'default'
      case 'alternative': return 'default'
    }
  }

  useEffect(() => {
    loadFeedbackData()
  }, [])

  return (
    <Container maxWidth="lg">
      <Box p={4}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
          <Typography variant="h4">
            Feedback Dashboard
          </Typography>
          <Button
            variant="contained"
            color="primary"
            startIcon={<RefreshIcon />}
            onClick={loadFeedbackData}
            disabled={loading}
          >
            {loading ? 'Loading...' : 'Refresh'}
          </Button>
        </Box>

        {/* Statistics Cards */}
        {stats && (
          <Grid container spacing={3} mb={4}>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center">
                    <BarChart color="primary" />
                    <Box ml={2}>
                      <Typography variant="h4">{stats.total_feedback}</Typography>
                      <Typography variant="body2" color="textSecondary">
                        Total Feedback
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center">
                    <TrendingUp style={{ color: '#4caf50' }} />
                    <Box ml={2}>
                      <Typography variant="h4" style={{ color: '#4caf50' }}>
                        {stats.positive_count}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Positive ({Math.round((stats.positive_count / stats.total_feedback) * 100) || 0}%)
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center">
                    <TrendingDown style={{ color: '#f44336' }} />
                    <Box ml={2}>
                      <Typography variant="h4" style={{ color: '#f44336' }}>
                        {stats.negative_count}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Negative ({Math.round((stats.negative_count / stats.total_feedback) * 100) || 0}%)
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center">
                    <FeedbackIcon color="action" />
                    <Box ml={2}>
                      <Typography variant="h4">
                        {stats.refinement_count + stats.alternative_count}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        Improvement Requests
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* Filters */}
        <Card style={{ marginBottom: '24px' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Filters
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="Explore ID"
                  value={filters.exploreId}
                  onChange={(e) => setFilters({ ...filters, exploreId: e.target.value })}
                  placeholder="e.g., ecommerce:order_items"
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="User ID"
                  value={filters.userId}
                  onChange={(e) => setFilters({ ...filters, userId: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth>
                  <InputLabel>Feedback Type</InputLabel>
                  <Select
                    value={filters.feedbackType}
                    onChange={(e) => setFilters({ ...filters, feedbackType: e.target.value as FeedbackType })}
                  >
                    <MenuItem value="">All Types</MenuItem>
                    <MenuItem value="positive">Positive</MenuItem>
                    <MenuItem value="negative">Negative</MenuItem>
                    <MenuItem value="refinement">Refinement</MenuItem>
                    <MenuItem value="alternative">Alternative</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  fullWidth
                  label="Limit"
                  type="number"
                  value={filters.limit}
                  onChange={(e) => setFilters({ ...filters, limit: parseInt(e.target.value) })}
                />
              </Grid>
            </Grid>
            <Box mt={2}>
              <Button variant="contained" onClick={loadFeedbackData} disabled={loading}>
                Apply Filters
              </Button>
            </Box>
          </CardContent>
        </Card>

        {/* Top Explores */}
        {stats && stats.top_explores.length > 0 && (
          <Card style={{ marginBottom: '24px' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Most Active Explores
              </Typography>
              <Box>
                {stats.top_explores.map((explore, index) => (
                  <Box key={explore.explore_id} display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Typography variant="body1">
                      {index + 1}. {explore.explore_id}
                    </Typography>
                    <Chip label={`${explore.count} feedback`} size="small" />
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        )}

        {/* Feedback History Table */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Feedback History ({feedbackHistory.length} entries)
            </Typography>
            
            {loading ? (
              <Box display="flex" justifyContent="center" p={4}>
                <CircularProgress />
              </Box>
            ) : (
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Type</TableCell>
                      <TableCell>Explore</TableCell>
                      <TableCell>Query</TableCell>
                      <TableCell>User</TableCell>
                      <TableCell>Date</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {feedbackHistory.map((feedback) => (
                      <TableRow key={feedback.id}>
                        <TableCell>
                          <Box display="flex" alignItems="center">
                            {getFeedbackIcon(feedback.feedback_type)}
                            <Box ml={1}>
                              <Chip
                                label={feedback.feedback_type}
                                color={getFeedbackColor(feedback.feedback_type)}
                                size="small"
                              />
                            </Box>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" noWrap>
                            {feedback.explore_id}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" noWrap style={{ maxWidth: 200 }}>
                            {feedback.original_prompt}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {feedback.user_id}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {feedback.created_at ? new Date(feedback.created_at).toLocaleDateString() : 'N/A'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Tooltip title="View Details">
                            <IconButton 
                              size="small" 
                              onClick={() => setSelectedFeedback(feedback)}
                            >
                              <Visibility />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Card>

        {/* Feedback Detail Dialog */}
        {selectedFeedback && (
          <Card style={{ marginTop: '24px' }}>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">Feedback Details</Typography>
                <Button onClick={() => setSelectedFeedback(null)}>Close</Button>
              </Box>
              
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2">Original Query:</Typography>
                  <Typography variant="body2" paragraph>
                    {selectedFeedback.original_prompt}
                  </Typography>
                  
                  <Typography variant="subtitle2">Explore:</Typography>
                  <Typography variant="body2" paragraph>
                    {selectedFeedback.explore_id}
                  </Typography>
                  
                  <Typography variant="subtitle2">Feedback Type:</Typography>
                  <Box mb={2}>
                    <Chip
                      label={selectedFeedback.feedback_type}
                      color={getFeedbackColor(selectedFeedback.feedback_type)}
                      icon={getFeedbackIcon(selectedFeedback.feedback_type)}
                    />
                  </Box>
                </Grid>
                
                <Grid item xs={12} md={6}>
                  {selectedFeedback.user_comment && (
                    <>
                      <Typography variant="subtitle2">User Comment:</Typography>
                      <Typography variant="body2" paragraph>
                        {selectedFeedback.user_comment}
                      </Typography>
                    </>
                  )}
                  
                  {selectedFeedback.suggested_improvements && (
                    <>
                      <Typography variant="subtitle2">Suggested Improvements:</Typography>
                      <pre style={{ fontSize: '12px', background: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
                        {JSON.stringify(selectedFeedback.suggested_improvements, null, 2)}
                      </pre>
                    </>
                  )}
                </Grid>
                
                <Grid item xs={12}>
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Typography variant="subtitle2">Generated Parameters</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <pre style={{ fontSize: '12px', background: '#f5f5f5', padding: '8px', borderRadius: '4px', width: '100%' }}>
                        {JSON.stringify(selectedFeedback.generated_params, null, 2)}
                      </pre>
                    </AccordionDetails>
                  </Accordion>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        )}
      </Box>
    </Container>
  )
}

export default FeedbackDashboard
