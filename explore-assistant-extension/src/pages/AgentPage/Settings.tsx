import React, { useState } from 'react'
import {
  Modal,
  Box,
  Typography,
  Switch,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
} from '@mui/material'
import { useSelector, useDispatch } from 'react-redux'
import { RootState } from '../../store'
import { setSetting } from '../../slices/assistantSlice'

interface SettingsModalProps {
  open: boolean
  onClose: () => void
}

const SettingsModal: React.FC<SettingsModalProps> = ({ open, onClose }) => {
  const dispatch = useDispatch()
  const { settings } = useSelector((state: RootState) => state.assistant)

  const handleToggle = (id: string) => {
    dispatch(
      setSetting({
        id,
        value: !settings.find((setting) => setting.id === id)?.value,
      }),
    )
  }

  if (!settings) return null

  return (
    <Modal
      open={open}
      onClose={onClose}
      aria-labelledby="settings-modal-title"
      className="flex items-center justify-center"
    >
      <Box className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <Typography
          id="settings-modal-title"
          variant="h6"
          component="h2"
          className="mb-4"
        >
          Settings
        </Typography>
        <List>
          {settings.map((setting) => (
            <ListItem key={setting.id} className="py-2">
              <ListItemText
                primary={setting.name}
                secondary={setting.description}
                className="pr-4"
              />
              <ListItemSecondaryAction>
                <Switch
                  edge="end"
                  onChange={() => handleToggle(setting.id)}
                  checked={setting.value}
                  inputProps={{ 'aria-labelledby': `switch-${setting.id}` }}
                />
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      </Box>
    </Modal>
  )
}

export default SettingsModal
