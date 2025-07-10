import React, { useEffect, useState, useRef } from 'react'
import { hot } from 'react-hot-loader/root'
import { Route, Switch, Redirect } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import { RootState } from './store'
import { useLookerFields } from './hooks/useLookerFields'
import { useBigQueryExamples } from './hooks/useBigQueryExamples'
import useSendCloudRunMessage from './hooks/useSendCloudRunMessage'
import { useAutoOAuth } from './hooks/useAutoOAuth'
import { useExtensionContext } from './hooks/useExtensionContext'
import {
  setInitialTestsCompleted,
} from './slices/assistantSlice'
import AgentPage from './pages/AgentPage'
import SettingsModal from './pages/AgentPage/Settings'
import { Box, CircularProgress, Typography, Button } from '@material-ui/core'

// Debug flag for OAuth flow
const AUTH_DEBUG = false

const ExploreApp = () => {
  const { settings, bigQueryTestSuccessful, vertexTestSuccessful, oauth, userAttributesLoaded, initialTestsCompleted } = useSelector((state: RootState) => state.assistant) as any
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  
  // Load extension context first (renamed for clarity but keeping same interface)
  const { isLoading: isLoadingExtensionContext, error: extensionContextError } = useExtensionContext()
  
  // Skip auto OAuth if settings modal is open
  const { isAuthenticating, hasValidToken, error: oauthError, validationInProgress } = useAutoOAuth(isSettingsOpen)

  useLookerFields()

  // Add timeout for OAuth process
  const [showFallbackUI, setShowFallbackUI] = useState(false)
  
  useEffect(() => {
    const oauthTimeout = setTimeout(() => {
      if (isAuthenticating) {
        console.warn('OAuth taking too long, showing fallback UI')
        setShowFallbackUI(true)
      }
    }, 15000) // 15 second timeout

    return () => clearTimeout(oauthTimeout)
  }, [isAuthenticating])

  // Show error state if OAuth fails or times out
  if (oauthError || showFallbackUI) {
    return (
      <>
        <SettingsModal
          open={isSettingsOpen}
          onClose={() => {
            AUTH_DEBUG && console.log('Settings modal closed')
            setIsSettingsOpen(false)
            setShowFallbackUI(false)
          }}
        />
        <Box display="flex" flexDirection="column" justifyContent="center" alignItems="center" height="100vh" p={3}>
          <Typography variant="h6" color="error" gutterBottom>
            {oauthError || 'Authentication Error'}
          </Typography>
          <Typography variant="body1" gutterBottom align="center">
            There seems to be an issue with authentication. Please check your settings and try again.
          </Typography>
          <Box mt={2}>
            <Button 
              variant="contained" 
              color="primary"
              onClick={() => {
                setIsSettingsOpen(true)
                setShowFallbackUI(false)
              }}
            >
              Open Settings
            </Button>
          </Box>
        </Box>
      </>
    )
  }

  // Show loading state while extension context is being loaded
  if (isLoadingExtensionContext || !userAttributesLoaded) {
    AUTH_DEBUG && console.log('Showing extension context loading indicator')
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="100vh">
        <CircularProgress />
        <Box ml={2}>Loading configuration...</Box>
      </Box>
    )
  }

  if (isAuthenticating) {
    AUTH_DEBUG && console.log('Showing authentication progress indicator')
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="100vh">
        <CircularProgress />
        <Box ml={2}>Authenticating with Google...</Box>
      </Box>
    )
  }
  AUTH_DEBUG && console.log('Rendering main app view. Settings open:', isSettingsOpen, 'BQ/Vertex tests successful:', bigQueryTestSuccessful, vertexTestSuccessful)

  return (
    <>
      <SettingsModal
        open={isSettingsOpen}
        onClose={() => {
          AUTH_DEBUG && console.log('Settings modal closed')
          setIsSettingsOpen(false)
        }}
      />
      <Switch>
        <Route path="/index" exact>
          <AgentPage />
        </Route>
        <Route>
          <Redirect to="/index" />
        </Route>
      </Switch>
      {/* Test status banner removed as per user request */}
    </>
  )
}

export const App = hot(ExploreApp)
