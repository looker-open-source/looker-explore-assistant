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
    if (operationStatus === 'error') {
      setError('Operation failed. See console for details.')
    } else {
      setError(null)
    }
    if (operationStatus === 'success' && setupResult?.success) {
      setSuccess('Vector search setup completed successfully!')
    } else {
      setSuccess(null)
    }
  }, [operationStatus, setupResult])

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
                      <Typography variant="body2">
                        <b>Vector Table Exists:</b> {systemStatus.table_exists ? 'Yes' : 'No'}
                      </Typography>
                      <Typography variant="body2">
                        <b>Embedding Model Exists:</b> {systemStatus.model_exists ? 'Yes' : 'No'}
                      </Typography>
                      <Typography variant="body2">
                        <b>Table Row Count:</b> {systemStatus.table_row_count ?? 'N/A'}
                      </Typography>
                      <Typography variant="body2">
                        <b>Model Training State:</b> {systemStatus.model_training_state ?? 'N/A'}
                      </Typography>
                      <Typography variant="body2">
                        <b>Last Updated:</b> {systemStatus.last_updated ? new Date(systemStatus.last_updated).toLocaleString() : 'N/A'}
                      </Typography>
                      {systemStatus.errors && systemStatus.errors.length > 0 && (
                        <Box mt={2}>
                          <Typography variant="body2" color="error">
                            Errors:
                          </Typography>
                          <ul>
                            {systemStatus.errors.map((err, idx) => (
                              <li key={idx}>{err}</li>
                            ))}
                          </ul>
                        </Box>
                      )}
                      {systemStatus.warnings && systemStatus.warnings.length > 0 && (
                        <Box mt={2}>
                          <Typography variant="body2" color="warning.main">
                            Warnings:
                          </Typography>
                          <ul>
                            {systemStatus.warnings.map((warn, idx) => (
                              <li key={idx}>{warn}</li>
                            ))}
                          </ul>
                        </Box>
                      )}
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
                      onClick={setupVectorSystem}
                      disabled={loading}
                      sx={{ mb: 2 }}
                    >
                      Run Vector Search Setup
                    </Button>
                    <Button
                      variant="outlined"
                      color="secondary"
                      onClick={getVectorSystemStatus}
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
