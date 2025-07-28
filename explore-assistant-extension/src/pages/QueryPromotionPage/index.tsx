import React, { useState, useEffect, useCallback, useContext } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Alert,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  CircularProgress,
  Tabs,
  Tab,
  IconButton,
  Tooltip,
} from '@mui/material'
import {
  WorkspacePremium as PromoteIcon,
  Visibility as ViewIcon,
  Launch as LaunchIcon,
} from '@mui/icons-material'
import { useHistory } from 'react-router-dom'
import { ExtensionContext } from '@looker/extension-sdk-react'
import Sidebar from '../AgentPage/Sidebar'
import { useQueryPromotion } from '../../hooks/useQueryPromotion'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`promotion-tabpanel-${index}`}
      aria-labelledby={`promotion-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  )
}

const QueryPromotionPage: React.FC = () => {
  const { extensionSDK } = useContext(ExtensionContext)
  const [sidebarExpanded, setSidebarExpanded] = useState(false)
  const [tabValue, setTabValue] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [queries, setQueries] = useState<any[]>([])
  const [promotionHistory, setPromotionHistory] = useState<any[]>([])
  const history = useHistory()

  const { getQueriesForPromotion, promoteQuery, getPromotionHistory } = useQueryPromotion()

  const toggleSidebar = () => {
    setSidebarExpanded(!sidebarExpanded)
  }

  const navigateBack = () => {
    history.push('/index')
  }

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
    setQueries([]) // Clear queries when switching tabs
    if (newValue === 2) {
      loadPromotionHistory()
    } else {
      loadQueries(newValue === 0 ? 'bronze' : 'silver')
    }
  }

  const loadQueries = useCallback(async (tableName: 'bronze' | 'silver') => {
    setLoading(true)
    setError(null)
    try {
      console.log(`Loading ${tableName} queries...`)
      const result = await getQueriesForPromotion(tableName, 50, 0)
      console.log(`Loaded ${result.queries.length} ${tableName} queries:`, result)
      setQueries(result.queries || [])
      if (result.queries.length === 0) {
        setError(`No ${tableName} queries found. The table may be empty or the API may not be properly configured.`)
      }
    } catch (err) {
      console.error(`Error loading ${tableName} queries:`, err)
      setError(`Failed to load ${tableName} queries: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }, [getQueriesForPromotion])

  const loadPromotionHistory = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      console.log('Loading promotion history...')
      const result = await getPromotionHistory(50, 0)
      console.log(`Loaded ${result.history.length} promotion history items:`, result)
      setPromotionHistory(result.history || [])
      if (result.history.length === 0) {
        setError('No promotion history found.')
      }
    } catch (err) {
      console.error('Error loading promotion history:', err)
      setError(`Failed to load promotion history: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }, [getPromotionHistory])

  // Load initial data
  useEffect(() => {
    if (tabValue === 2) {
      loadPromotionHistory()
    } else {
      loadQueries(tabValue === 0 ? 'bronze' : 'silver')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tabValue])

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString()
    } catch {
      return dateString
    }
  }

  const constructLookerUrl = (query: any) => {
    const hostUrl = extensionSDK?.lookerHostData?.hostUrl
    if (!hostUrl) return null
    
    // For silver queries, use share_url if available
    if (query.share_url) {
      return query.share_url
    }
    
    // For bronze queries, construct URL from query_slug
    if (query.query_slug) {
      return `${hostUrl}/x/${query.query_slug}`
    }
    
    return null
  }

  const renderQueryTable = (tableQueries: any[]) => {
    if (tableQueries.length === 0) {
      return (
        <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 4 }}>
          No queries found in this table.
        </Typography>
      )
    }

    return (
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Explore</TableCell>
              <TableCell>Question</TableCell>
              <TableCell>User</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {tableQueries.map((query, index) => (
              <TableRow key={query.id || index}>
                <TableCell>
                  <Chip label={query.explore_key || 'Unknown'} size="small" />
                </TableCell>
                <TableCell>
                  <Typography variant="body2" noWrap style={{ maxWidth: 200 }}>
                    {query.input_question || query.suggested_new_prompt || 'No question available'}
                  </Typography>
                </TableCell>
                <TableCell>{query.user_email || 'Unknown'}</TableCell>
                <TableCell>{formatDate(query.created_at)}</TableCell>
                <TableCell>
                  <Box display="flex" gap={1}>
                    {constructLookerUrl(query) && (
                      <Tooltip title="Open in Looker">
                        <IconButton 
                          size="small" 
                          onClick={() => extensionSDK.openBrowserWindow(constructLookerUrl(query)!, '_blank')}
                        >
                          <LaunchIcon />
                        </IconButton>
                      </Tooltip>
                    )}
                    <Tooltip title="Promote to Golden">
                      <IconButton size="small" color="primary">
                        <PromoteIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    )
  }

  const renderPromotionHistoryTable = () => {
    if (promotionHistory.length === 0) {
      return (
        <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 4 }}>
          No promotion history found.
        </Typography>
      )
    }

    return (
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Source Query ID</TableCell>
              <TableCell>Source Table</TableCell>
              <TableCell>Target Table</TableCell>
              <TableCell>Promoted By</TableCell>
              <TableCell>Promoted At</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {promotionHistory.map((item, index) => (
              <TableRow key={item.id || index}>
                <TableCell>
                  <Typography variant="body2" style={{ fontFamily: 'monospace' }}>
                    {item.source_query_id ? item.source_query_id.substring(0, 8) + '...' : 'Unknown'}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip label={item.source_table || 'Unknown'} size="small" color="info" />
                </TableCell>
                <TableCell>
                  <Chip label={item.target_table || 'Unknown'} size="small" color="success" />
                </TableCell>
                <TableCell>{item.promoted_by || 'Unknown'}</TableCell>
                <TableCell>{formatDate(item.promoted_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    )
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar expanded={sidebarExpanded} toggleDrawer={toggleSidebar} />
      
      <div className={`flex-1 transition-all duration-300 ${sidebarExpanded ? 'ml-80' : 'ml-16'}`}>
        <Box sx={{ width: '100%', p: 3 }}>
          <Typography variant="h4" gutterBottom>
            Query Promotion Management
          </Typography>
          
          <Typography variant="body1" color="text.secondary" gutterBottom>
            Manage and promote queries from bronze and silver tables to golden queries for training data.
          </Typography>

          {error && (
            <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {success && (
            <Alert severity="success" onClose={() => setSuccess(null)} sx={{ mb: 2 }}>
              {success}
            </Alert>
          )}

          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
            <Tabs value={tabValue} onChange={handleTabChange}>
              <Tab label="Bronze Queries" />
              <Tab label="Silver Queries" />
              <Tab label="Promotion History" />
            </Tabs>
          </Box>

          <TabPanel value={tabValue} index={0}>
            <Card>
              <CardContent>
                <Grid container spacing={2} alignItems="center" sx={{ mb: 2 }}>
                  <Grid item>
                    <Typography variant="h6">Bronze Queries</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Historical queries captured from user interactions
                    </Typography>
                  </Grid>
                  <Grid item xs />
                  <Grid item>
                    <Button 
                      variant="outlined" 
                      onClick={() => loadQueries('bronze')}
                      disabled={loading}
                    >
                      Refresh
                    </Button>
                  </Grid>
                </Grid>

                {loading ? (
                  <Box display="flex" justifyContent="center" p={4}>
                    <CircularProgress />
                  </Box>
                ) : (
                  renderQueryTable(queries)
                )}
              </CardContent>
            </Card>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <Card>
              <CardContent>
                <Grid container spacing={2} alignItems="center" sx={{ mb: 2 }}>
                  <Grid item>
                    <Typography variant="h6">Silver Queries</Typography>
                    <Typography variant="body2" color="text.secondary">
                      User-corrected queries with validated results
                    </Typography>
                  </Grid>
                  <Grid item xs />
                  <Grid item>
                    <Button 
                      variant="outlined" 
                      onClick={() => loadQueries('silver')}
                      disabled={loading}
                    >
                      Refresh
                    </Button>
                  </Grid>
                </Grid>

                {loading ? (
                  <Box display="flex" justifyContent="center" p={4}>
                    <CircularProgress />
                  </Box>
                ) : (
                  renderQueryTable(queries)
                )}
              </CardContent>
            </Card>
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <Card>
              <CardContent>
                <Grid container spacing={2} alignItems="center" sx={{ mb: 2 }}>
                  <Grid item>
                    <Typography variant="h6">Promotion History</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Audit trail of all query promotions
                    </Typography>
                  </Grid>
                  <Grid item xs />
                  <Grid item>
                    <Button 
                      variant="outlined" 
                      onClick={loadPromotionHistory}
                      disabled={loading}
                    >
                      Refresh
                    </Button>
                  </Grid>
                </Grid>

                {loading ? (
                  <Box display="flex" justifyContent="center" p={4}>
                    <CircularProgress />
                  </Box>
                ) : (
                  renderPromotionHistoryTable()
                )}
              </CardContent>
            </Card>
          </TabPanel>

          <Box mt={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Navigation
                </Typography>
                <Button 
                  variant="contained" 
                  onClick={navigateBack}
                  sx={{ mr: 2 }}
                >
                  Back to Conversations
                </Button>
              </CardContent>
            </Card>
          </Box>
        </Box>
      </div>
    </div>
  )
}

export default QueryPromotionPage
