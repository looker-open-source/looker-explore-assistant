import React from 'react'
import { Modal, Box, Typography, Switch } from '@mui/material'
import { useSelector, useDispatch } from 'react-redux'
import { RootState } from '../../store'
import {
  setSetting,
  AssistantState,
  resetExploreAssistant,
} from '../../slices/assistantSlice'

interface SettingsModalProps {
  open: boolean
  onClose: () => void
}

const SettingsModal: React.FC<SettingsModalProps> = ({ open, onClose }) => {
  const dispatch = useDispatch()
  const { settings } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )

  const handleToggle = (id: string) => {
    dispatch(
      setSetting({
        id,
        value: !settings[id].value,
      }),
    )
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
      className="flex items-center justify-center"
    >
      <Box className="bg-white rounded-lg p-6 max-w-xl w-full mx-4">
        <Typography
          id="settings-modal-title"
          variant="h6"
          component="h2"
          className="mb-4"
        >
          Settings
        </Typography>
        <ul>
          {Object.entries(settings).map(([id, setting]) => (
            <li key={id} className="flex flex-row py-4">
              <div className="flex-grow pr-4">
                <div className="text-sm font-semibold">{setting.name}</div>
                <div className="text-xs text-gray-500">
                  {setting.description}
                </div>
              </div>
              <div className="">
                <Switch
                  edge="end"
                  onChange={() => handleToggle(id)}
                  checked={setting.value}
                  inputProps={{ 'aria-labelledby': `switch-${id}` }}
                />
              </div>
            </li>
          ))}
        </ul>
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
