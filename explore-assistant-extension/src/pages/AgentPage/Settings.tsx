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
import useSendVertexMessage from '../../hooks/useSendVertexMessage'
import InfoIcon from '@mui/icons-material/Info'
import { useAutoOAuth } from '../../hooks/useAutoOAuth'

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
  // Convert model_application to lowercase for use in attribute names
  const model_application = extensionId?.replace(/::/g, '_').replace(/-/g, '_').toLowerCase()

  const [userAttributes, setUserAttributes] = useState<{ id: string | undefined, name: string, value?: string }[]>([])
  const [expandedSetting, setExpandedSetting] = useState<string | null>(null)
  const [bigQueryTestResult, setBigQueryTestResult] = useState<boolean | null>(null)
  const [vertexTestResult, setVertexTestResult] = useState<boolean | null>(null)

  const { testBigQuerySettings } = useBigQueryExamples()
  const { testVertexSettings } = useSendVertexMessage()
  const [isAdmin, setIsAdmin] = useState(false)

  const GOOGLE_CLIENT_ID = settings['google_oauth_client_id']?.value as string || '';
  const GOOGLE_SCOPES = 'https://www.googleapis.com/auth/cloud-platform'
  
  // Load user attribute metadata (for saving purposes)
  const loadUserAttributeMetadata = async () => {
    try {
      // Get user attribute values (only for metadata like IDs)
      const myUserId = await core40SDK.ok(core40SDK.me());
      console.log('myUserId:', myUserId)

      const userAttributeValues = await core40SDK.ok(
        core40SDK.user_attribute_user_values({
          user_id: myUserId.id || '',
          fields: "name, value, user_attribute_id",
          all_values: true
        })
      );
      
      console.log('userAttributeValues for metadata:', userAttributeValues.length);

      // Only store metadata for saving, don't update settings (they're loaded globally)
      setUserAttributes(userAttributeValues.map((attr: any) => ({ 
        id: attr.user_attribute_id, 
        name: attr.name.toLowerCase(), // Ensure name is stored lowercase
        value: attr.value 
      }))) 
    } catch (error) {
      console.error('Error loading user attribute metadata:', error);
    }
  };

  // Use our hook but don't trigger auto-authentication here
  const { isAuthenticating, hasValidToken, error: oauthHookError } = useAutoOAuth()

  // OAuth authentication - Now as a function that can be called on demand
  const doOAuth = async () => {
    try {
      // Check if we have a client ID
      if (!settings['google_oauth_client_id']?.value) {
        console.error('OAuth client ID is required but not provided');
        return false;
      }

      // Validate existing token if present
      const existingToken = settings['oauth2_token']?.value;
      if (existingToken) {
        const tokenInfo = await fetch('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=' + existingToken);
        if (tokenInfo.ok) {
          console.log('Existing OAuth token is valid');
          return true;
        }
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

      const response = await extensionSDK.oauth2Authenticate(
        'https://accounts.google.com/o/oauth2/v2/auth',
        {
          client_id: clientId,
          scope: GOOGLE_SCOPES,
          response_type: 'token',
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

  // Load user attribute metadata once when component mounts (for saving functionality)
  useEffect(() => {
    const fetchUserAttributeMetadata = async () => {
      try {
        await loadUserAttributeMetadata();
      } catch (error) {
        console.error('Error fetching user attribute metadata:', error)
      }
    }
    
    if (core40SDK && model_application) {
      fetchUserAttributeMetadata()
    }
  }, [core40SDK, model_application]);

  // Run tests when settings are opened
  useEffect(() => {
    if (open) {
      const runTests = async () => {
        const bigQueryResult = await testBigQuerySettings()
        setBigQueryTestResult(bigQueryResult)
        const vertexResult = await testVertexSettings()
        setVertexTestResult(vertexResult)
      }
      runTests()
    }
  }, [open]);

  // Check admin status
  useEffect(() => {
    const checkAdminStatus = async () => {
      try {
        const response: any = await core40SDK.ok(core40SDK.me())
        
        let adminStatus = false
        console.log('debugging admin status check')
        console.log('Current user response:', response)
        
        // First, get the actual admin role ID by searching for roles with name 'admin'
        let adminRoleId: string | null = null
        try {
          const adminRoles = await core40SDK.ok(core40SDK.search_roles({
            name: 'admin'
          }))
          console.log('Admin roles found:', adminRoles)
          
          if (adminRoles && adminRoles.length > 0) {
            adminRoleId = adminRoles[0].id || null
            console.log('Admin role ID found:', adminRoleId)
          }
        } catch (roleError) {
          console.warn('Could not fetch admin role:', roleError)
        }
        
        // Enhanced admin check with multiple fallbacks
        // 1. Check is_iam_admin if it exists and is false, but still continue to role check
        if (typeof response.is_iam_admin === 'boolean') {
          adminStatus = response.is_iam_admin
          console.log('Admin status from is_iam_admin:', adminStatus)
        }
        
        // 2. Always check role_ids for admin role (even if is_iam_admin is false)
        if (Array.isArray(response.role_ids)) {
          console.log('User role_ids:', response.role_ids)
          
          // Check against the dynamically fetched admin role ID
          if (adminRoleId && (response.role_ids.includes(adminRoleId) || response.role_ids.includes(parseInt(adminRoleId)))) {
            adminStatus = true
            console.log('Admin status determined by role_ids containing admin role ID:', adminRoleId)
          }
          // Fallback: check for role ID 2 (traditional admin role)
          else if (response.role_ids.includes('2') || response.role_ids.includes(2)) {
            adminStatus = true
            console.log('Admin status determined by role_ids containing role ID 2:', response.role_ids)
          }
        }
        
        // 3. Final check: if we have an admin role ID but no role_ids array, check permissions differently
        if (!adminStatus && adminRoleId) {
          console.log('Checking admin status via admin role ID without role_ids array')
          // Additional check could be implemented here if needed
        }
        
        if (!adminStatus) {
          console.warn('Unable to determine admin status')
          console.log('Available user properties:', Object.keys(response))
          console.log('is_iam_admin:', response.is_iam_admin)
          console.log('role_ids:', response.role_ids)
          console.log('Admin role ID found:', adminRoleId)
        } else {
          console.log('Final admin status:', adminStatus)
        }
        
        setIsAdmin(adminStatus)
      } catch (error) {
        console.error('Error checking admin status:', error)
        setIsAdmin(false) // Default to false on error
      }
    }
    checkAdminStatus()
  }, [core40SDK]);

  if (!isAdmin) return null;

  // Handle toggle for boolean settings
  const handleToggle = (id: string) => {
    dispatch(
      setSetting({
        id,
        value: !settings[id].value,
      }),
    )
  }

  // Handle saving settings to user attributes
  const handleSaveSetting = async (id: string, value: string) => {
    // Only persist specific settings
    if (!['vertex_project', 'vertex_location', 'vertex_model', 'google_oauth_client_id', 'bigquery_example_looker_model_name'].includes(id)) {
      dispatch(setSetting({ id, value }));
      return;
    }
    
    // Ensure the user attribute name is lowercase
    const prefixedId = `${model_application}_${id}`.toLowerCase()
    dispatch(setSetting({ id, value }))
    try {
      // Case-insensitive lookup for existing attribute
      const userAttribute = userAttributes.find(
        (attr) => attr.name.toLowerCase() === prefixedId
      )
      console.log('userAttribute:', userAttribute, 'for name:', prefixedId)
      if (userAttribute) {
        await core40SDK.ok(
          core40SDK.update_user_attribute(userAttribute.id || '', {
            name: prefixedId.toLowerCase(),
            label: prefixedId,
            type: 'string',
            default_value: value,
            value_is_hidden: false,
            user_can_view: true,
            user_can_edit: false,
          })
        )
      } else {
        const newUserAttribute = await core40SDK.ok(
          core40SDK.create_user_attribute({
            name: prefixedId.toLowerCase(),
            label: prefixedId,
            type: 'string',
            default_value: value,
            value_is_hidden: false,
            user_can_view: true,
            user_can_edit: false,
          })
        )
        setUserAttributes([...userAttributes, { id: newUserAttribute.id, name: prefixedId }])
      }
    } catch (error) {
      console.error('Error saving user attribute:', error)
    }
  }

  // Run tests and save settings
  const handleTestAndSave = async () => {
    // Run OAuth first if we have a client ID but no token
    if (settings['google_oauth_client_id']?.value && !settings['oauth2_token']?.value) {
      await doOAuth();
    }
    
    const bigQueryResult = await testBigQuerySettings()
    setBigQueryTestResult(bigQueryResult)
    const vertexResult = await testVertexSettings()
    setVertexTestResult(vertexResult)
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

  // Only show the "show_explore_data" toggle setting and vertex settings
  const relevantSettings = Object.entries(settings).filter(
    ([id]) => id === 'show_explore_data' || 
    id === 'vertex_project' || 
    id === 'vertex_location' || 
    id === 'vertex_model' ||
    id === 'google_oauth_client_id' ||
    id === 'bigquery_example_looker_model_name'
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
                      onClick={doOAuth} 
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
            Vertex AI Test: {vertexTestResult === null ? 'Testing...' : vertexTestResult ? 
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
