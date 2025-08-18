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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  LinearProgress,
} from '@mui/material'
import {
  WorkspacePremium as PromoteIcon,
  Visibility as ViewIcon,
  Launch as LaunchIcon,
  CloudSync as MigrationIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material'
import { useHistory } from 'react-router-dom'
import { ExtensionContext } from '@looker/extension-sdk-react'
import Sidebar from '../AgentPage/Sidebar'
import { useOlympicQueries } from '../../hooks/useOlympicMigration'

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
  const [migrationDialogOpen, setMigrationDialogOpen] = useState(false)
  const history = useHistory()

  const {
    operationStatus,
    systemStatus,
    lastOperationResult,
    migrationStatus,
    migrationResult,
    getSystemStatus,
    addBronzeQuery,
    addSilverQuery,
    promoteQuery,
    deleteQuery,
    getGoldenQueries,
    getBronzeQueries,
    getSilverQueries,
    getDisqualifiedQueries,
    checkMigrationStatus,
    performMigration,
    resetState,
    isReady,
    isOlympicSystemAvailable,
    totalQueries,
    migrationNeeded,
    canMigrateSafely
  } = useOlympicQueries()

  const toggleSidebar = () => {
    setSidebarExpanded(!sidebarExpanded)
  }

  const navigateBack = () => {
    history.push('/index')
  }

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
    setQueries([]) // Clear queries when switching tabs
    const rankMapping = ['bronze', 'silver', 'gold', 'disqualified', 'statistics']
    const rank = rankMapping[newValue] || 'bronze'
    if (rank !== 'statistics') {
      loadQueries(rank as 'bronze' | 'silver' | 'gold' | 'disqualified')
    }
  }

  const loadQueries = useCallback(async (rank: 'bronze' | 'silver' | 'gold' | 'disqualified') => {
    setLoading(true)
    setError(null)
    try {
      console.log(`Loading ${rank} queries...`)
      
      let result
      if (rank === 'gold') {
        result = await getGoldenQueries(undefined, 50)
      } else if (rank === 'bronze') {
        result = await getBronzeQueries(undefined, 50)
      } else if (rank === 'silver') {
        result = await getSilverQueries(undefined, 50)
      } else if (rank === 'disqualified') {
        result = await getDisqualifiedQueries(undefined, 50)
      }
      
      console.log(`Loaded ${result?.length || 0} ${rank} queries:`, result)
      setQueries(result || [])
      if (!result || result.length === 0) {
        setError(`No ${rank} queries found. The Olympic table may be empty or the API may not be properly configured.`)
      }
    } catch (err) {
      console.error(`Error loading ${rank} queries:`, err)
      setError(`Failed to load ${rank} queries: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }, [getGoldenQueries, getBronzeQueries, getSilverQueries, getDisqualifiedQueries])

  // Load initial data and system status
  useEffect(() => {
    if (isReady) {
      getSystemStatus().catch(console.error)
    }
  }, [isReady, getSystemStatus])

  useEffect(() => {
    const rankMapping = ['bronze', 'silver', 'gold', 'disqualified', 'statistics']
    const rank = rankMapping[tabValue] || 'bronze'
    if (rank !== 'statistics') {
      loadQueries(rank as 'bronze' | 'silver' | 'gold' | 'disqualified')
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

  const handlePromoteQuery = async (query: any) => {
    setLoading(true)
    setError(null)
    setSuccess(null)
    
    try {
      console.log('Promoting query:', query)
      
      // Determine promotion path based on current tab
      const rankMapping = ['bronze', 'silver', 'gold'] as const
      const currentRank = rankMapping[tabValue] || 'bronze'
      
      // Determine target rank (bronze -> silver, silver -> gold)
      const targetRank = currentRank === 'bronze' ? 'silver' : 'gold'
      
      const result = await promoteQuery(query.id, 'system', currentRank, targetRank)
      
      console.log('Promotion result:', result)
      setSuccess(`Successfully promoted query ${query.id.substring(0, 8)}... from ${currentRank} to ${targetRank}`)
      
      // Refresh the current view
      loadQueries(currentRank)
      
    } catch (err) {
      console.error('Error promoting query:', err)
      setError(`Failed to promote query: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteQuery = async (query: any) => {
    // Confirm deletion
    if (!window.confirm(`Are you sure you want to delete this query? This action cannot be undone.\n\nQuery: ${query.input || query.input_question || 'Unknown query'}`)) {
      return
    }

    setLoading(true)
    setError(null)
    setSuccess(null)
    
    try {
      console.log('Deleting query:', query)
      
      const result = await deleteQuery(query.id, 'user')
      
      console.log('Deletion result:', result)
      setSuccess(`Successfully deleted query ${query.id.substring(0, 8)}...`)
      
      // Refresh the current view
      const rankMapping = ['bronze', 'silver', 'gold', 'disqualified'] as const
      const currentRank = rankMapping[tabValue] || 'bronze'
      loadQueries(currentRank)
      
    } catch (err) {
      console.error('Error deleting query:', err)
      setError(`Failed to delete query: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  const renderQueryTable = (tableQueries: any[]) => {
    if (tableQueries.length === 0) {
      return (
        <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 4 }}>
          No queries found in this rank.
        </Typography>
      )
    }

    const renderConversationHistory = (conversationHistory: any) => {
      if (!conversationHistory) {
        return (
          <Typography variant="body2" color="text.secondary" style={{ fontStyle: 'italic' }}>
            No conversation history available
          </Typography>
        )
      }

      let historyData
      try {
        // Handle both string and object formats
        historyData = typeof conversationHistory === 'string' 
          ? JSON.parse(conversationHistory) 
          : conversationHistory
      } catch (e) {
        return (
          <Typography variant="body2" color="text.secondary" style={{ fontStyle: 'italic' }}>
            Invalid conversation history format
          </Typography>
        )
      }

      // Extract meaningful content from conversation history
      const renderHistoryContent = (data: any) => {
        if (data?.conversation_context) {
          return (
            <Typography variant="body2" style={{ 
              maxWidth: 300, 
              wordWrap: 'break-word',
              whiteSpace: 'pre-wrap',
              fontSize: '0.875rem'
            }}>
              {data.conversation_context}
            </Typography>
          )
        }
        
        if (data?.feedback_details) {
          const { feedback_type, user_comment, issues } = data.feedback_details
          return (
            <Box>
              {feedback_type && (
                <Chip 
                  label={feedback_type} 
                  size="small" 
                  color={feedback_type === 'positive' ? 'success' : 'error'}
                  sx={{ mb: 1, mr: 1 }}
                />
              )}
              {user_comment && (
                <Typography variant="body2" style={{ 
                  maxWidth: 300, 
                  wordWrap: 'break-word',
                  whiteSpace: 'pre-wrap',
                  fontSize: '0.875rem',
                  marginTop: 4
                }}>
                  {user_comment}
                </Typography>
              )}
              {issues && Array.isArray(issues) && issues.length > 0 && (
                <Typography variant="caption" color="text.secondary" style={{ 
                  maxWidth: 300, 
                  wordWrap: 'break-word',
                  display: 'block',
                  marginTop: 4
                }}>
                  Issues: {issues.join(', ')}
                </Typography>
              )}
            </Box>
          )
        }

        // Fallback for other formats
        return (
          <Typography variant="body2" style={{ 
            maxWidth: 300, 
            wordWrap: 'break-word',
            whiteSpace: 'pre-wrap',
            fontSize: '0.875rem'
          }}>
            {typeof data === 'string' ? data : JSON.stringify(data, null, 2)}
          </Typography>
        )
      }

      return renderHistoryContent(historyData)
    }

    return (
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell style={{ width: '180px' }}>Explore</TableCell>
              <TableCell style={{ width: '250px' }}>Question</TableCell>
              <TableCell style={{ width: '300px' }}>Conversation History</TableCell>
              <TableCell style={{ width: '120px' }}>Created</TableCell>
              <TableCell style={{ width: '100px' }}>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {tableQueries.map((query, index) => (
              <TableRow key={query.id || index}>
                <TableCell>
                  <Typography variant="body2" style={{ 
                    maxWidth: 180, 
                    wordWrap: 'break-word',
                    whiteSpace: 'normal',
                    fontSize: '0.875rem',
                    fontWeight: 500
                  }}>
                    {query.explore_id || 'Unknown'}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" style={{ 
                    maxWidth: 250, 
                    wordWrap: 'break-word',
                    whiteSpace: 'normal'
                  }}>
                    {query.input || query.input_question || 'No question available'}
                  </Typography>
                </TableCell>
                <TableCell>
                  {renderConversationHistory(query.conversation_history)}
                </TableCell>
                <TableCell>{formatDate(query.created_at)}</TableCell>
                <TableCell>
                  <Box display="flex" gap={1}>
                    {query.link && (
                      <Tooltip title="Open in Looker">
                        <IconButton 
                          size="small" 
                          onClick={() => extensionSDK.openBrowserWindow(query.link, '_blank')}
                        >
                          <LaunchIcon />
                        </IconButton>
                      </Tooltip>
                    )}
                    {query.rank !== 'gold' && query.rank !== 'disqualified' && (
                      <Tooltip title="Promote to Gold">
                        <IconButton 
                          size="small" 
                          color="primary"
                          onClick={() => handlePromoteQuery(query)}
                          disabled={loading}
                        >
                          <PromoteIcon />
                        </IconButton>
                      </Tooltip>
                    )}
                    <Tooltip title="Delete Query">
                      <IconButton 
                        size="small" 
                        color="error"
                        onClick={() => handleDeleteQuery(query)}
                        disabled={loading}
                      >
                        <DeleteIcon />
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

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar expanded={sidebarExpanded} toggleDrawer={toggleSidebar} />
      
      <div className={`flex-1 transition-all duration-300 ${sidebarExpanded ? 'ml-80' : 'ml-16'}`}>
        <Box sx={{ width: '100%', p: 3 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Box>
              <Typography variant="h4" gutterBottom>
                Olympic Query Management
              </Typography>
              <Typography variant="body1" color="text.secondary" gutterBottom>
                Manage queries across Bronze, Silver, and Gold ranks in the unified Olympic system.
              </Typography>
            </Box>
            <Box>
              <Button 
                variant="contained" 
                startIcon={<MigrationIcon />}
                onClick={() => setMigrationDialogOpen(true)}
                disabled={!isReady}
              >
                Migration Tools
              </Button>
            </Box>
          </Box>

          {!isReady && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              Olympic system not ready. Please check your configuration.
            </Alert>
          )}

          {isOlympicSystemAvailable && (
            <Alert severity="success" sx={{ mb: 2 }}>
              Olympic system active: {totalQueries} total queries across all ranks.
            </Alert>
          )}

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
              <Tab label="Gold Queries" />
              <Tab label="Disqualified" />
              <Tab label="Statistics" />
            </Tabs>
          </Box>

          <TabPanel value={tabValue} index={0}>
            <Card>
              <CardContent>
                <Grid container spacing={2} alignItems="center" sx={{ mb: 2 }}>
                  <Grid item>
                    <Typography variant="h6">Bronze Queries</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Raw queries captured from user interactions
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

                {loading || operationStatus === 'loading' ? (
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

                {loading || operationStatus === 'loading' ? (
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
                    <Typography variant="h6">Gold Queries</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Curated training data for LLM prompts
                    </Typography>
                  </Grid>
                  <Grid item xs />
                  <Grid item>
                    <Button 
                      variant="outlined" 
                      onClick={() => loadQueries('gold')}
                      disabled={loading}
                    >
                      Refresh
                    </Button>
                  </Grid>
                </Grid>

                {loading || operationStatus === 'loading' ? (
                  <Box display="flex" justifyContent="center" p={4}>
                    <CircularProgress />
                  </Box>
                ) : (
                  renderQueryTable(queries)
                )}
              </CardContent>
            </Card>
          </TabPanel>

          <TabPanel value={tabValue} index={3}>
            <Card>
              <CardContent>
                <Grid container spacing={2} alignItems="center" sx={{ mb: 2 }}>
                  <Grid item>
                    <Typography variant="h6">Disqualified Queries</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Queries marked as negative feedback or problematic
                    </Typography>
                  </Grid>
                  <Grid item xs />
                  <Grid item>
                    <Button 
                      variant="outlined" 
                      onClick={() => loadQueries('disqualified')}
                      disabled={loading}
                    >
                      Refresh
                    </Button>
                  </Grid>
                </Grid>

                {loading || operationStatus === 'loading' ? (
                  <Box display="flex" justifyContent="center" p={4}>
                    <CircularProgress />
                  </Box>
                ) : (
                  renderQueryTable(queries)
                )}
              </CardContent>
            </Card>
          </TabPanel>

          <TabPanel value={tabValue} index={4}>
            <Card>
              <CardContent>
                <Grid container spacing={2} alignItems="center" sx={{ mb: 2 }}>
                  <Grid item>
                    <Typography variant="h6">Query Statistics</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Overview of the Olympic query system
                    </Typography>
                  </Grid>
                </Grid>

                {loading || operationStatus === 'loading' ? (
                  <Box display="flex" justifyContent="center" p={4}>
                    <CircularProgress />
                  </Box>
                ) : (
                  <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 4 }}>
                    Statistics have been temporarily removed for simplification.
                  </Typography>
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

        {/* Migration Dialog */}
        <Dialog open={migrationDialogOpen} onClose={() => setMigrationDialogOpen(false)} maxWidth="md" fullWidth>
          <DialogTitle>Olympic Migration Tools</DialogTitle>
          <DialogContent>
            <Typography variant="body2" color="text.secondary" paragraph>
              The Olympic system uses a unified table structure for managing queries across Bronze, Silver, and Gold ranks.
            </Typography>

            {!migrationStatus && (
              <Alert severity="info" sx={{ mb: 2 }}>
                Click "Check Migration Status" to analyze your current system and see if migration is needed.
              </Alert>
            )}
            
            {migrationStatus && (
              <Box mb={2}>
                <Typography variant="h6" gutterBottom>Migration Analysis</Typography>
                
                {migrationNeeded ? (
                  <Alert severity={canMigrateSafely ? "warning" : "error"} sx={{ mb: 2 }}>
                    {canMigrateSafely 
                      ? "🔄 Migration recommended - Legacy tables detected"
                      : "⚠️ Migration needed but issues found - Review recommendations below"
                    }
                  </Alert>
                ) : (
                  <Alert severity="success" sx={{ mb: 2 }}>
                    ✅ System is up to date - No migration needed
                  </Alert>
                )}

                <List dense>
                  <ListItem>
                    <ListItemText 
                      primary="Migration Needed" 
                      secondary={migrationNeeded ? '🔄 Yes' : '✅ No'}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Can Migrate Safely" 
                      secondary={canMigrateSafely ? '✅ Yes' : '⚠️ No'}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Legacy Tables Found" 
                      secondary={migrationStatus.legacy_tables_exist?.length || 0}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText 
                      primary="Estimated Records to Migrate" 
                      secondary={migrationStatus.estimated_record_count || 0}
                    />
                  </ListItem>
                </List>
                
                {migrationStatus.recommendations && migrationStatus.recommendations.length > 0 && (
                  <Box mt={2}>
                    <Typography variant="subtitle2" gutterBottom>🔍 Recommendations:</Typography>
                    {migrationStatus.recommendations.map((rec, index) => (
                      <Typography key={index} variant="body2" color="text.secondary" paragraph>
                        • {rec}
                      </Typography>
                    ))}
                  </Box>
                )}

                {migrationStatus.schema_issues && migrationStatus.schema_issues.length > 0 && (
                  <Box mt={2}>
                    <Typography variant="subtitle2" color="warning.main" gutterBottom>⚠️ Issues Found:</Typography>
                    {migrationStatus.schema_issues.map((issue, index) => (
                      <Typography key={index} variant="body2" color="warning.main" paragraph>
                        • {issue.table}: {issue.issue}
                      </Typography>
                    ))}
                  </Box>
                )}
              </Box>
            )}

            {migrationResult && (
              <Box mb={2}>
                <Typography variant="h6" gutterBottom>Migration Result</Typography>
                <Alert severity={migrationResult.success ? 'success' : 'error'} sx={{ mb: 1 }}>
                  Migration {migrationResult.success ? 'completed successfully' : 'failed'}
                </Alert>
                {migrationResult.success && (
                  <List dense>
                    <ListItem>
                      <ListItemText 
                        primary="Records Migrated" 
                        secondary={migrationResult.records_migrated}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText 
                        primary="Steps Completed" 
                        secondary={migrationResult.steps_completed?.length || 0}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText 
                        primary="Tables Archived" 
                        secondary={migrationResult.archived_tables?.length || 0}
                      />
                    </ListItem>
                  </List>
                )}
                {!migrationResult.success && migrationResult.errors && (
                  <Box mt={1}>
                    <Typography variant="subtitle2" color="error" gutterBottom>Errors:</Typography>
                    {migrationResult.errors.map((error, index) => (
                      <Typography key={index} variant="body2" color="error" paragraph>
                        • {error}
                      </Typography>
                    ))}
                  </Box>
                )}
              </Box>
            )}

            {operationStatus === 'loading' && (
              <Box mb={2}>
                <LinearProgress />
                <Typography variant="body2" color="text.secondary" mt={1}>
                  Processing operation...
                </Typography>
              </Box>
            )}

            {lastOperationResult && (
              <Alert severity={lastOperationResult.success ? 'success' : 'error'} sx={{ mb: 2 }}>
                {lastOperationResult.success 
                  ? `Operation successful using ${lastOperationResult.system} system`
                  : `Operation failed: ${lastOperationResult.errors?.join(', ')}`
                }
              </Alert>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setMigrationDialogOpen(false)}>Close</Button>
            {!migrationStatus ? (
              <Button 
                variant="contained" 
                color="primary"
                onClick={() => checkMigrationStatus()}
                disabled={operationStatus === 'loading'}
              >
                Check Migration Status
              </Button>
            ) : migrationNeeded && canMigrateSafely ? (
              <Button 
                variant="contained" 
                color="primary"
                onClick={() => performMigration(true, true)}
                disabled={operationStatus === 'loading'}
              >
                Perform Migration
              </Button>
            ) : migrationNeeded && !canMigrateSafely ? (
              <Button 
                variant="outlined" 
                color="warning"
                onClick={() => checkMigrationStatus()}
                disabled={operationStatus === 'loading'}
              >
                Recheck Migration (Issues Found)
              </Button>
            ) : (
              <Button 
                variant="outlined" 
                color="success"
                onClick={() => checkMigrationStatus()}
                disabled={operationStatus === 'loading'}
              >
                Recheck Migration (Up to Date)
              </Button>
            )}
          </DialogActions>
        </Dialog>
      </div>
    </div>
  )
}

export default QueryPromotionPage
