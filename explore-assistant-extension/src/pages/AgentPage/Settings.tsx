import React, { useContext, useEffect, useState } from 'react'
import { Modal, Box, Typography, Switch, IconButton, Button } from '@mui/material'
import { useSelector, useDispatch } from 'react-redux'
import { RootState } from '../../store'
import {
  setSetting,
  AssistantState,
  resetExploreAssistant,
  setOAuthError,
  setOAuthAuthenticating,
} from '../../slices/assistantSlice'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { useBigQueryExamples } from '../../hooks/useBigQueryExamples'
import useSendCloudRunMessage from '../../hooks/useSendCloudRunMessage'
import InfoIcon from '@mui/icons-material/Info'
import { useAutoOAuth } from '../../hooks/useAutoOAuth'
import { useExtensionContext } from '../../hooks/useExtensionContext'

interface SettingsModalProps {
  open: boolean
  onClose: () => void
}

const SettingsModal: React.FC<SettingsModalProps> = ({ open, onClose }) => {
  const { core40SDK, extensionSDK } = useContext(ExtensionContext)
  const dispatch = useDispatch()
  const { settings } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )
  const extensionId = extensionSDK?.lookerHostData?.extensionId

  const [expandedSetting, setExpandedSetting] = useState<string | null>(null)
  const [bigQueryTestResult, setBigQueryTestResult] = useState<boolean | null>(null)
  const [cloudRunTestResult, setCloudRunTestResult] = useState<boolean | null>(null)

  const { testBigQuerySettings } = useBigQueryExamples()
  const { testCloudRunSettings } = useSendCloudRunMessage()
  const [isAdmin, setIsAdmin] = useState(false)

  // Use extension context hook
  const { saveExtensionContext } = useExtensionContext()

  const GOOGLE_CLIENT_ID = settings['google_oauth_client_id']?.value as string || '';
  const GOOGLE_SCOPES = 'https://www.googleapis.com/auth/cloud-platform https://www.googleapis.com/auth/bigquery https://www.googleapis.com/auth/userinfo.email';
  
  // Use our hook but don't trigger auto-authentication here
  const { isAuthenticating, hasValidToken, error: oauthHookError } = useAutoOAuth()

  // OAuth authentication - Now as a function that can be called on demand
  const doOAuth = async (forceNew = false) => {
    try {
      // Check if we have a client ID
      if (!settings['google_oauth_client_id']?.value) {
        console.error('OAuth client ID is required but not provided');
        return false;
      }

      // Only validate existing token if NOT forcing new authentication
      if (!forceNew) {
        const existingToken = settings['oauth2_token']?.value;
        if (existingToken) {
          const tokenInfo = await fetch('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=' + existingToken);
          if (tokenInfo.ok) {
            console.log('Existing OAuth token is valid');
            return true;
          }
        }
      } else {
        console.log('Forcing new OAuth flow - bypassing existing token validation');
      }

      // Skip if already authenticating
      if (isAuthenticating) {
        console.log('OAuth flow already in progress, skipping duplicate request');
        return false;
      }

      const clientId = settings['google_oauth_client_id']?.value as string;
      console.log('Starting OAuth flow with client ID:', clientId);

      // Clear any previous error and set authenticating state
      dispatch(setOAuthError(null));
      dispatch(setOAuthAuthenticating(true));

      // Clear existing token before starting new flow (when forcing new)
      if (forceNew && settings['oauth2_token']?.value) {
        console.log('Clearing existing token before new OAuth flow');
        dispatch(setSetting({ id: 'oauth2_token', value: '' }));
      }

      const response = await extensionSDK.oauth2Authenticate(
        'https://accounts.google.com/o/oauth2/v2/auth',
        {
          client_id: clientId,
          scope: GOOGLE_SCOPES,
          response_type: 'token',
          // Force consent screen to ensure fresh token
          prompt: forceNew ? 'consent' : undefined,
        }
      );

      const { access_token } = response;
      if (access_token) {
        dispatch(setSetting({ id: 'oauth2_token', value: access_token }));
        console.log('OAuth token obtained successfully');
        return true;
      }
      console.error('No access token received from OAuth flow');
      dispatch(setOAuthError('Failed to receive access token from OAuth flow'));
      return false;
    } catch (error) {
      console.error('OAuth2 authentication failed:', error);
      dispatch(setOAuthError(`OAuth authentication failed: ${error.message || 'Unknown error'}`));
      return false;
    } finally {
      dispatch(setOAuthAuthenticating(false));
    }
  }

  // No longer automatically running OAuth on component mount

  // Run tests when settings are opened
  useEffect(() => {
    if (open) {
      const runTests = async () => {
        const bigQueryResult = await testBigQuerySettings()
        setBigQueryTestResult(bigQueryResult)
        const cloudRunResult = await testCloudRunSettings()
        setCloudRunTestResult(cloudRunResult)
      }
      runTests()
    }
  }, [open]);

  // Check admin status
  useEffect(() => {
    const checkAdminStatus = async () => {
      try {
        const me = await core40SDK.ok(core40SDK.me())
        const isLookerAdmin = me.roles?.some((role: any) => 
          role.name === 'Admin' || role.permission_set?.permissions?.includes('admin')
        ) || false
        setIsAdmin(isLookerAdmin)
      } catch (error) {
        console.error('Error checking admin status:', error)
        setIsAdmin(false)
      }
    }
    checkAdminStatus()
  }, [core40SDK]);

  // TEMPORARY ADMIN OVERRIDE - TODO: Remove in next commit
  // Allow all users to edit settings temporarily
  if (!true) return null; // Changed from: if (!isAdmin) return null;

  // Handle toggle for boolean settings
  const handleToggle = (id: string) => {
    dispatch(
      setSetting({
        id,
        value: !settings[id].value,
      }),
    )
  }

  // Handle saving settings to extension context
  const handleSaveSetting = async (id: string, value: string) => {
    // Update Redux state immediately
    dispatch(setSetting({ id, value }));
    
    // Only persist specific settings to extension context
    if (['google_oauth_client_id', 'bigquery_example_looker_model_name', 'cloud_run_service_url', 'vertex_project', 'vertex_location', 'vertex_model'].includes(id)) {
      try {
        await saveExtensionContext({ [id]: value })
        console.log(`Successfully saved ${id} to extension context`)
      } catch (error) {
        console.error('Error saving to extension context:', error)
      }
    }
  }

  // Run tests and save settings
  const handleTestAndSave = async () => {
    console.log('=== Test & Save Button Clicked ===');
    
    try {
      // Run OAuth first if we have a client ID but no token (don't force new here)
      if (settings['google_oauth_client_id']?.value && !settings['oauth2_token']?.value) {
        console.log('Running OAuth before tests...');
        await doOAuth();
      }
      
      console.log('Starting BigQuery test...');
      const bigQueryResult = await testBigQuerySettings();
      console.log('BigQuery test result:', bigQueryResult);
      setBigQueryTestResult(bigQueryResult);
      
      console.log('Starting Cloud Run test...');
      console.log('Cloud Run URL:', settings['cloud_run_service_url']?.value);
      console.log('OAuth Token available:', !!settings['oauth2_token']?.value);
      
      const cloudRunResult = await testCloudRunSettings();
      console.log('Cloud Run test result:', cloudRunResult);
      setCloudRunTestResult(cloudRunResult);
      
      console.log('=== Tests Complete ===');
    } catch (error) {
      console.error('Error in handleTestAndSave:', error);
    }
  }

  // Reset all settings
  const handleReset = () => {
    dispatch(resetExploreAssistant())
    setInterval(() => {
      window.location.reload()
    }, 100)
  }

  // Handle expanding settings description
  const handleExpandClick = (id: string) => {
    setExpandedSetting(expandedSetting === id ? null : id)
  }

  // Only show the "show_explore_data" toggle setting and Cloud Run settings
  const relevantSettings = Object.entries(settings).filter(
    ([id]) => id === 'show_explore_data' || 
    id === 'google_oauth_client_id' ||
    id === 'bigquery_example_looker_model_name' ||
    id === 'cloud_run_service_url' ||
    id === 'vertex_project' ||
    id === 'vertex_location' ||
    id === 'vertex_model'
  )

  return (
    <Modal
      open={open}
      onClose={onClose}
      aria-labelledby="settings-modal-title"
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Box
        sx={{
          width: '90%',
          maxWidth: 600,
          maxHeight: '90vh',
          bgcolor: 'background.paper',
          border: '2px solid #000',
          borderRadius: 2,
          boxShadow: 24,
          p: 4,
          overflow: 'auto'
        }}
      >
        <Typography variant="h4" component="h2" gutterBottom sx={{
          background: 'linear-gradient(45deg, #ec4899 30%, #8b5cf6 90%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          textAlign: 'center'
        }}>
          Settings
        </Typography>

        {(oauthHookError) && (
          <Box sx={{ mb: 2, p: 2, bgcolor: '#ffebee', border: '1px solid #f44336', borderRadius: 1 }}>
            <Typography variant="body2" color="error">
              {oauthHookError}
            </Typography>
          </Box>
        )}

        <Box component="ul" sx={{ listStyle: 'none', p: 0, m: 0 }}>
          {relevantSettings.map(([id, setting]) => (
            <Box component="li" key={id} sx={{ mb: 3, p: 2, border: '1px solid #e0e0e0', borderRadius: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <IconButton
                    onClick={() => handleExpandClick(id)}
                    aria-expanded={expandedSetting === id}
                    aria-label="show more"
                    size="small"
                  >
                    <InfoIcon />
                  </IconButton>
                  <Typography variant="subtitle1" sx={{ ml: 1 }}>
                    {setting.name}
                  </Typography>
                </Box>

                {id === 'google_oauth_client_id' ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <input
                      type="text"
                      value={String(setting.value)}
                      onChange={(e) => handleSaveSetting(id, e.target.value)}
                      style={{
                        padding: '8px 12px',
                        border: '1px solid #ccc',
                        borderRadius: '4px',
                        minWidth: '200px'
                      }}
                      placeholder="Enter Google OAuth Client ID"
                    />
                    <Button 
                      onClick={() => doOAuth(true)} // Force new OAuth flow
                      variant="contained" 
                      size="small"
                      disabled={!setting.value || isAuthenticating}
                    >
                      {isAuthenticating ? 'Authenticating...' : 'Authenticate'}
                    </Button>
                  </Box>
                ) : typeof setting.value === 'boolean' ? (
                  <Switch
                    edge="end"
                    onChange={() => handleToggle(id)}
                    checked={setting.value}
                    inputProps={{ 'aria-labelledby': `switch-${id}` }}
                  />
                ) : (
                  <input
                    type="text"
                    value={String(setting.value)}
                    onChange={(e) => handleSaveSetting(id, e.target.value)}
                    style={{
                      padding: '8px 12px',
                      border: '1px solid #ccc',
                      borderRadius: '4px',
                      minWidth: '200px'
                    }}
                  />
                )}
              </Box>

              {expandedSetting === id && (
                <Box sx={{ mt: 2, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
                  <Typography variant="body2">
                    {setting.description}
                  </Typography>
                </Box>
              )}
            </Box>
          ))}
        </Box>

        <Box sx={{ mt: 3, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
          <Typography variant="body2" sx={{ mb: 1 }}>
            OAuth Status: {settings['oauth2_token']?.value ? 
              <Box component="span" sx={{ color: '#4caf50', fontWeight: 'bold' }}>✅ Authenticated</Box> : 
              <Box component="span" sx={{ color: '#f44336', fontWeight: 'bold' }}>❌ Not Authenticated</Box>
            }
          </Typography>
          <Typography variant="body2" sx={{ mb: 1 }}>
            BigQuery Examples Test: {bigQueryTestResult === null ? 'Testing...' : bigQueryTestResult ? 
              <Box component="span" sx={{ color: '#4caf50', fontWeight: 'bold' }}>✅ Passed</Box> : 
              <Box component="span" sx={{ color: '#f44336', fontWeight: 'bold' }}>❌ Failed</Box>
            }
          </Typography>
          <Typography variant="body2">
            Cloud Run Test: {cloudRunTestResult === null ? 'Testing...' : cloudRunTestResult ? 
              <Box component="span" sx={{ color: '#4caf50', fontWeight: 'bold' }}>✅ Passed</Box> : 
              <Box component="span" sx={{ color: '#f44336', fontWeight: 'bold' }}>❌ Failed</Box>
            }
          </Typography>
        </Box>

        <Box sx={{ mt: 3, display: 'flex', gap: 2, justifyContent: 'center' }}>
          <Button 
            onClick={handleTestAndSave} 
            variant="contained" 
            color="primary"
          >
            Test & Save
          </Button>
          <Button 
            onClick={handleReset} 
            variant="outlined" 
            color="secondary"
          >
            Reset All Settings
          </Button>
        </Box>
      </Box>
    </Modal>
  )
}
export default SettingsModal
