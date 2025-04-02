import React, { useContext, useEffect, useState } from 'react'
import { Modal, Box, Typography, Switch, IconButton, Button } from '@mui/material'
import { useSelector, useDispatch } from 'react-redux'
import { RootState } from '../../store'
import {
  setSetting,
  AssistantState,
  resetExploreAssistant,
} from '../../slices/assistantSlice'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { useBigQueryExamples } from '../../hooks/useBigQueryExamples'
import useSendVertexMessage from '../../hooks/useSendVertexMessage'
import styles from '../../styles.module.css'
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
  
  // Load user attribute values
  const loadUserAttributeValues = async () => {
    try {
      // Get user attribute values
      const myUserId = await core40SDK.ok(core40SDK.me());
      console.log('myUserId:', myUserId)
      const userAttributeValues = await core40SDK.ok(
        core40SDK.user_attribute_user_values({
          user_id: myUserId.id || '',
          fields: "name, value, user_attribute_id",
          all_values: true
        })
      );
      
      console.log('userAttributeValues:', userAttributeValues);

      // Map user attribute values to their corresponding settings
      userAttributeValues.forEach((attr: any) => {
        if (attr.name && attr.name.toLowerCase().startsWith(`${model_application}_`)) {
          // Use case-insensitive matching for attribute names
          const settingKey = attr.name.toLowerCase().replace(`${model_application}_`, '');
          const value = attr.value;
          
          // Only persist specific settings
          if (
            (settingKey === 'vertex_project' || 
             settingKey === 'vertex_location' || 
             settingKey === 'vertex_model' ||
             settingKey === 'google_oauth_client_id' ||
             settingKey === 'bigquery_example_looker_model_name') && 
            value && 
            settings[settingKey]
          ) {
            dispatch(setSetting({ id: settingKey, value }));
            console.log(`Loaded setting from user attributes: ${settingKey}`);
          }
        }
      });
      setUserAttributes(userAttributeValues.map((attr: any) => ({ 
        id: attr.user_attribute_id, 
        name: attr.name.toLowerCase(), // Ensure name is stored lowercase
        value: attr.value 
      }))) 
    } catch (error) {
      console.error('Error loading user attribute values:', error);
    }
  };

  // Use our hook but don't trigger auto-authentication here
  const { isAuthenticating } = useAutoOAuth()

  // OAuth authentication - Now as a function that can be called on demand
  const doOAuth = async () => {
    try {
      // Check if we have a client ID
      if (!settings['google_oauth_client_id']?.value) {
        console.error('OAuth client ID is required but not provided');
        return false;
      }
      
      // Skip if already authenticating
      if (isAuthenticating) {
        console.log('OAuth flow already in progress, skipping duplicate request');
        return false;
      }
      
      const clientId = settings['google_oauth_client_id']?.value as string;
      console.log('Starting OAuth flow with client ID:', clientId);
      
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
      return false;
    } catch (error) {
      console.error('OAuth2 authentication failed:', error);
      return false;
    }
  }

  // No longer automatically running OAuth on component mount

  // Load user attributes and their values when the modal opens
  useEffect(() => {
    const fetchUserAttributes = async () => {
      try {
        loadUserAttributeValues();
      } catch (error) {
        console.error('Error fetching user attributes:', error)
      }
    }
    fetchUserAttributes()
  }, [core40SDK, open]);

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
        const response = await core40SDK.ok(core40SDK.me('group_ids'))
        if (response?.group_ids?.includes('1')) {
          setIsAdmin(true)
        }
      } catch (error) {
        console.error('Error checking admin status:', error)
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
      className={styles.modalContainer}
    >
      <Box className={styles.modalBox}>
        <span className="bg-clip-text text-transparent bg-gradient-to-r from-pink-500 to-violet-500">
          Settings
        </span>
        <ul className={styles.modalContent}>
          {relevantSettings.map(([id, setting]) => (
            <li key={id} className={styles.settingItem}>
              <div>
                <IconButton
                  onClick={() => handleExpandClick(id)}
                  aria-expanded={expandedSetting === id}
                  aria-label="show more"
                >
                  {setting.name} <div className='infoIcon'><InfoIcon /></div>
                </IconButton>
                {id === 'google_oauth_client_id' ? (
                  <div className={styles.clientIdContainer}>
                    <input
                      type="text"
                      value={String(setting.value)}
                      onChange={(e) => handleSaveSetting(id, e.target.value)}
                      className={styles.inputField}
                    />
                    <Button 
                      onClick={doOAuth} 
                      variant="contained" 
                      size="small"
                      disabled={!setting.value}
                      className={styles.authButton}
                    >
                      Authenticate
                    </Button>
                  </div>
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
                    className={styles.inputField}
                  />
                )}
              </div>
              <div className={`${styles.collapsibleContent} ${expandedSetting === id ? styles.show : ''}`}>
                <Typography variant="body2">
                  {setting.description}
                </Typography>
              </div>
            </li>
          ))}
        </ul>
        <div className={styles.modalContent}>
          <Typography variant="body2">
            OAuth Status: {settings['oauth2_token']?.value ? <span className={styles.passed}>Authenticated</span> : <span className={styles.failed}>Not Authenticated</span>}
          </Typography>
          <Typography variant="body2">
            BigQuery Examples Test: {bigQueryTestResult === null ? 'Testing...' : bigQueryTestResult ? <span className={styles.passed}>Passed</span> : <span className={styles.failed}>Failed</span>}
          </Typography>
          <Typography variant="body2">
            Vertex AI Test: {vertexTestResult === null ? 'Testing...' : vertexTestResult ? <span className={styles.passed}>Passed</span> : <span className={styles.failed}>Failed</span>}
          </Typography>
        </div>
        <button onClick={handleTestAndSave} className={styles.button}>Test</button>
        <button onClick={handleReset} className={`${styles.button} ${styles.resetButton}`}>Reset All Settings</button>
      </Box>
    </Modal>
  )
}
export default SettingsModal
