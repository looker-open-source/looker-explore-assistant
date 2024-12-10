import React, { useContext, useEffect, useState } from 'react'
import { Modal, Box, Typography, Switch, IconButton, Select, MenuItem } from '@mui/material'
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

interface SettingsModalProps {
  open: boolean
  onClose: () => void
}

const SettingsModal: React.FC<SettingsModalProps> = ({ open, onClose }) => {
  const { core40SDK, extensionSDK } = useContext(ExtensionContext)
  const dispatch = useDispatch()
  const { settings, hasTestedSettings } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )
  const extensionId = extensionSDK?.lookerHostData?.extensionId
  const model_application = extensionId?.replace(/::/g, '_').replace(/-/g, '_')

  const [userAttributes, setUserAttributes] = useState<{ id: string | undefined, name: string }[]>([])
  const [expandedSetting, setExpandedSetting] = useState<string | null>(null)

  const VERTEX_CF_AUTH_TOKEN = 'vertex_cf_auth_token'

  const [bigQueryTestResult, setBigQueryTestResult] = useState<boolean | null>(null)
  const [vertexTestResult, setVertexTestResult] = useState<boolean | null>(null)
  const [hasAutoClosedOnce, setHasAutoClosedOnce] = useState(false)
  const { testBigQuerySettings } = useBigQueryExamples()
  const { testVertexSettings } = useSendVertexMessage()

  const [isAdmin, setIsAdmin] = useState(false)

  useEffect(() => {
    const fetchUserAttributes = async () => {
      try {
        const response = await core40SDK.ok(core40SDK.all_user_attributes({ fields: 'id,name' }))
        // @ts-ignore
        setUserAttributes(response)
      } catch (error) {
        console.error('Error fetching user attributes:', error)
      }
    }
    fetchUserAttributes()
  }, [core40SDK])

  useEffect(() => {
    const runTests = async () => {
      const bigQueryResult = await testBigQuerySettings()
      setBigQueryTestResult(bigQueryResult)
      const vertexResult = await testVertexSettings()
      setVertexTestResult(vertexResult)
    }
    runTests()
  }, [settings])

  useEffect(() => {
    if (hasTestedSettings && bigQueryTestResult && vertexTestResult && !hasAutoClosedOnce) {
      onClose()
      setHasAutoClosedOnce(true)
    }
  }, [hasTestedSettings, bigQueryTestResult, vertexTestResult, onClose])

  useEffect(() => {
    const checkAdminStatus = async () => {
      try {
        const response = await core40SDK.ok(core40SDK.me('group_ids'))
        if (response.group_ids.includes('1')) {
          setIsAdmin(true)
        }
      } catch (error) {
        console.error('Error checking admin status:', error)
      }
    }
    checkAdminStatus()
  }, [core40SDK])

  if (!isAdmin) return null

  const handleToggle = (id: string) => {
    dispatch(
      setSetting({
        id,
        value: !settings[id].value,
      }),
    )
  }

  const handleSaveSetting = async (id: string, value: string) => {
    const prefixedId = `${model_application}_${id}`
    dispatch(setSetting({ id, value }))
    try {
      const userAttribute = userAttributes.find((attr) => attr.name === prefixedId)
      if (userAttribute) {
        await core40SDK.ok(
          core40SDK.update_user_attribute(userAttribute.id || '', {
            name: prefixedId,
            label: prefixedId,
            type: 'string',
            default_value: value,
            value_is_hidden: id === VERTEX_CF_AUTH_TOKEN,
            user_can_view: false,
            user_can_edit: false,
          })
        )
      } else {
        const newUserAttribute = await core40SDK.ok(
          core40SDK.create_user_attribute({
            name: prefixedId,
            label: prefixedId,
            type: 'string',
            default_value: value,
            value_is_hidden: id === VERTEX_CF_AUTH_TOKEN,
            user_can_view: false,
            user_can_edit: false,
            // May be unnecessary since we're using an extension framework, the domain is the server itself.
            hidden_value_domain_whitelist: "https://explore-assistant-api-730192175971.us-central1.run.app"
          })
        )
        setUserAttributes([...userAttributes, { id: newUserAttribute.id, name: prefixedId }])
      }
    } catch (error) {
      console.error('Error saving user attribute:', error)
    }
  }

  const handleTestAndSave = async () => {
    testBigQuerySettings()
    testVertexSettings()
  }

  const handleReset = () => {
    dispatch(resetExploreAssistant())
    setInterval(() => {
      window.location.reload()
    }, 100)
  }

  const handleExpandClick = (id: string) => {
    setExpandedSetting(expandedSetting === id ? null : id)
  }

  const handleDropdownChange = (id: string, value: string) => {
    dispatch(
      setSetting({
        id,
        value: value === 'Cloud Function',
      }),
    )
  }

  if (!settings) return null

  const filteredSettings = Object.entries(settings).filter(([id]) => {
    if (id === 'useCloudFunction' || id === 'show_explore_data') return true
    if (id === 'bigquery_example_prompts_connection_name' || id === 'bigquery_example_prompts_dataset_name') return true
    if (settings.useCloudFunction.value) {
      return id === 'vertex_ai_endpoint' || id === 'vertex_cf_auth_token'
    } else {
      return id === 'vertex_bigquery_looker_connection_name' || id === 'vertex_bigquery_model_id'
    }
  })

  return (
    <Modal
      open={open}
      onClose={onClose}
      aria-labelledby="settings-modal-title"
      className={styles.modalContainer}
    >
      <Box className={styles.modalBox}>
        <span className="bg-clip-text text-transparent  bg-gradient-to-r from-pink-500 to-violet-500">
          Settings
        </span>
        <ul className={styles.modalContent}>
          {filteredSettings.map(([id, setting]) => (
            <li key={id} className={styles.settingItem}>
              <div>

                <IconButton
                  onClick={() => handleExpandClick(id)}
                  aria-expanded={expandedSetting === id}
                  aria-label="show more"
                >
                  {setting.name == 'Use Cloud Function' ? 'Backend' : setting.name} <div className='infoIcon'><InfoIcon /></div>
                </IconButton>
                {id === 'useCloudFunction' ? (
                  <Select
                    value={setting.value ? 'Cloud Function' : 'Bigquery'}
                    onChange={(e) => handleDropdownChange(id, e.target.value)}
                    className={styles.inputField}
                  >
                    <MenuItem value="Cloud Function">Cloud Function</MenuItem>
                    <MenuItem value="Bigquery">Bigquery</MenuItem>
                  </Select>
                ) : typeof setting.value === 'boolean' ? (
                  <Switch
                    edge="end"
                    onChange={() => handleToggle(id)}
                    checked={setting.value}
                    inputProps={{ 'aria-labelledby': `switch-${id}` }}
                  />
                ) : (
                  <input
                    type={id === VERTEX_CF_AUTH_TOKEN ? 'password' : 'text'}
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
            BigQuery Settings Test: {bigQueryTestResult === null ? 'Testing...' : bigQueryTestResult ? <span className={styles.passed}>Passed</span> : <span className={styles.failed}>Failed</span>}
          </Typography>
          <Typography variant="body2">
            Vertex Settings Test: {vertexTestResult === null ? 'Testing...' : vertexTestResult ? <span className={styles.passed}>Passed</span> : <span className={styles.failed}>Failed</span>}
          </Typography>
        </div>
        <button onClick={handleTestAndSave} className={styles.button}>Test and Save</button>
        
      </Box>
    </Modal>
  )
}

export default SettingsModal
