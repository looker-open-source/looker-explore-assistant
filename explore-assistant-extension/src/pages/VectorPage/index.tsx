import React, { useState, useEffect } from 'react'
import { useHistory } from 'react-router-dom'
import { Box, Card, CardContent, Typography, Button, CircularProgress, Alert, Grid } from '@mui/material'
import Sidebar from '../AgentPage/Sidebar'
import { useVectorSearchSetup } from '../../hooks/useVectorSearchSetup'

const VectorPage: React.FC = () => {
  const [sidebarExpanded, setSidebarExpanded] = useState(false)
  const history = useHistory()
  const {
    operationStatus,
    systemStatus,
    setupResult,
    getVectorSystemStatus,
    setupVectorSystem
  } = useVectorSearchSetup()

  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    getVectorSystemStatus()
    // eslint-disable-next-line
  }, [])

  useEffect(() => {
    // Handle different system states
    if (systemStatus) {
      if (systemStatus.system_status === 'operational') {
        setSuccess('Vector search system is operational!')
        setError(null)
      } else if (systemStatus.system_status === 'degraded') {
        setError(`System is degraded. Issues: ${systemStatus.recommendations.join('; ')}`)
        setSuccess(null)
      } else if (systemStatus.system_status === 'partial') {
        setError(`System is partially functional. Issues: ${systemStatus.recommendations.join('; ')}`)
        setSuccess(null)
      } else if (systemStatus.system_status === 'needs_setup') {
        setError('Vector search system needs setup. Click "Run Vector Search Setup" to initialize.')
        setSuccess(null)
      } else {
        setError(null)
        setSuccess(null)
      }
    } else if (operationStatus === 'error') {
      setError('Operation failed. See console for details.')
      setSuccess(null)
    } else {
      setError(null)
      setSuccess(null)
    }

    // Handle setup completion
    if (operationStatus === 'success' && setupResult?.success) {
      setSuccess('Vector search setup completed successfully!')
    }
  }, [operationStatus, setupResult, systemStatus])

  const toggleSidebar = () => setSidebarExpanded((prev) => !prev)
  const navigateBack = () => history.push('/index')

  const loading = operationStatus === 'loading'

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar expanded={sidebarExpanded} toggleDrawer={toggleSidebar} />
      <div className={`flex-1 transition-all duration-300 ${sidebarExpanded ? 'ml-80' : 'ml-16'}`}> 
        <Box sx={{ width: '100%', p: 3 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Box>
              <Typography variant="h4" gutterBottom>
                Vector Search Setup
              </Typography>
              <Typography variant="body1" color="text.secondary" gutterBottom>
                Manage and initialize the semantic vector search system for field discovery.
              </Typography>
            </Box>
            <Box>
              <Button variant="contained" onClick={navigateBack}>
                Back to Chat
              </Button>
            </Box>
          </Box>

          {loading && (
            <Box display="flex" alignItems="center" mb={2}>
              <CircularProgress size={24} />
              <Box ml={2}>Processing...</Box>
            </Box>
          )}

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
          )}

          {success && (
            <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>
          )}

          <Card>
            <CardContent>
              <Grid container spacing={2}>
                <Grid item xs={12} md={8}>
                  <Typography variant="h6" gutterBottom>
                    System Status
                  </Typography>
                  {systemStatus ? (
                    <Box>
                      <Typography variant="body2" sx={{ mb: 1 }}>
                        <b>Overall Status:</b> {systemStatus.system_status.toUpperCase()}
                      </Typography>
                      
                      <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>
                        Components
                      </Typography>
                      
                      <Typography variant="body2">
                        <b>BigQuery Connection:</b> {systemStatus.components.bigquery_connection}
                      </Typography>
                      <Typography variant="body2">
                        <b>Embedding Model:</b> {systemStatus.components.embedding_model}
                      </Typography>
                      <Typography variant="body2">
                        <b>Field Values Table:</b> {systemStatus.components.field_values_table}
                      </Typography>
                      <Typography variant="body2">
                        <b>Vector Index:</b> {systemStatus.components.vector_index}
                      </Typography>
                      
                      {systemStatus.statistics && Object.keys(systemStatus.statistics).length > 0 && (
                        <Box mt={2}>
                          <Typography variant="h6" sx={{ mb: 1 }}>
                            Statistics
                          </Typography>
                          <Typography variant="body2">
                            <b>Total Rows:</b> {systemStatus.statistics.total_rows ?? 'N/A'}
                          </Typography>
                          <Typography variant="body2">
                            <b>Unique Fields:</b> {systemStatus.statistics.unique_fields ?? 'N/A'}
                          </Typography>
                          <Typography variant="body2">
                            <b>Unique Explores:</b> {systemStatus.statistics.unique_explores ?? 'N/A'}
                          </Typography>
                        </Box>
                      )}
                      
                      {systemStatus.recommendations && systemStatus.recommendations.length > 0 && (
                        <Box mt={2}>
                          <Typography variant="body2" color="warning.main" sx={{ fontWeight: 'bold' }}>
                            Recommendations:
                          </Typography>
                          <ul style={{ margin: '8px 0', paddingLeft: '20px' }}>
                            {systemStatus.recommendations.map((rec, idx) => (
                              <li key={idx} style={{ fontSize: '0.875rem', marginBottom: '4px' }}>
                                {rec}
                              </li>
                            ))}
                          </ul>
                        </Box>
                      )}
                      
                      <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
                        Last Updated: {new Date(systemStatus.timestamp).toLocaleString()}
                      </Typography>
                    </Box>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      No status available.
                    </Typography>
                  )}
                </Grid>
                <Grid item xs={12} md={4}>
                  <Box display="flex" flexDirection="column" alignItems="flex-end" height="100%" justifyContent="center">
                    <Button
                      variant="contained"
                      color="primary"
                      onClick={() => setupVectorSystem()}
                      disabled={loading}
                      sx={{ mb: 2 }}
                    >
                      Run Vector Search Setup
                    </Button>
                    <Button
                      variant="outlined"
                      color="secondary"
                      onClick={() => getVectorSystemStatus()}
                      disabled={loading}
                    >
                      Refresh Status
                    </Button>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Box>
      </div>
    </div>
  )
}

export default VectorPage
