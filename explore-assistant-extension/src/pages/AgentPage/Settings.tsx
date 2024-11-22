import React, { useContext, useEffect, useState } from 'react'
import { Modal, Box, Typography, Switch } from '@mui/material'
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
  const model_application = extensionId?.replace(/::/g, '_').replace(/-/g, '_')

  const [userAttributes, setUserAttributes] = useState<{ id: string | undefined, name: string }[]>([])

  const VERTEX_CF_AUTH_TOKEN = 'vertex_cf_auth_token'
  
  const [bigQueryTestResult, setBigQueryTestResult] = useState<boolean | null>(null)
  const [vertexTestResult, setVertexTestResult] = useState<boolean | null>(null)
  const { testBigQuerySettings } = useBigQueryExamples()
  const { testVertexSettings } = useSendVertexMessage()

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
          })
        )
        setUserAttributes([...userAttributes, { id: newUserAttribute.id, name: prefixedId }])
      }
    } catch (error) {
      console.error('Error saving user attribute:', error)
    }
  }

  const handleReset = () => {
    dispatch(resetExploreAssistant())
    setInterval(() => {
      window.location.reload()
    }, 100)
  }

  if (!settings) return null

  return (
    <Modal
      open={open}
      onClose={onClose}
      aria-labelledby="settings-modal-title"
      className={styles.modalContainer}
    >
      <Box className={styles.modalBox}>
        <Typography
          id="settings-modal-title"
          variant="h6"
          component="h2"
          className={styles.modalTitle}
        >
          Settings
        </Typography>
        <ul className={styles.modalContent}>
          {Object.entries(settings).map(([id, setting]) => (
            <li key={id} className={styles.settingItem}>
              <div>
                {setting.name}: 
                {typeof setting.value === 'boolean' ? (
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
                    className="outline-2 outline-black p-1 rounded-md"
                  />
                )}
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
        <div
          onClick={handleReset}
          className="flex justify-start text-xs text-blue-500 hover:text-blue-600 cursor-pointer hover:underline mt-4"
        >
          reset explore assistant
        </div>
      </Box>
    </Modal>
  )
}

export default SettingsModal
