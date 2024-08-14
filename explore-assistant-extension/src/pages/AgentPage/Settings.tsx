import React from 'react'
import {
  Modal,
  Box,
  Typography,
  Switch,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  MenuItem,
  Select,
  SelectChangeEvent
} from '@mui/material'
import { useSelector, useDispatch } from 'react-redux'
import { RootState } from '../../store'
import { setSetting, setExploreName, setExploreId, setModelName, resetChat } from '../../slices/assistantSlice'

interface SettingsModalProps {
  open: boolean
  onClose: () => void
}

const SettingsModal: React.FC<SettingsModalProps> = ({ open, onClose }) => {
  const dispatch = useDispatch()
  const { settings, exploreId, explores } = useSelector(
    (state: RootState) => state.assistant,
  )

  const setSelectedExplore = (e: SelectChangeEvent<any>) => {
    const parsedExploreID = e.target.value.split(":")
    dispatch(setExploreName(parsedExploreID[1]))
    dispatch(setModelName(parsedExploreID[0]))
    dispatch(setExploreId(e.target.value.replace(":","/")))
    dispatch(resetChat())
  }

  const handleToggle = (id: string) => {
    dispatch(
      setSetting({
        id,
        value: !settings[id].value,
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
          {Object.entries(settings).map(([id, setting]) => (
            <ListItem key={id + setting.name} className="py-2">
              <ListItemText
                primary={setting.name}
                secondary={setting.description}
                className="pr-4"
              />
              <ListItemSecondaryAction>
                <Switch
                edge="end"
                onChange={() => handleToggle(id)}
                checked={setting.value}
                inputProps={{ 'aria-labelledby': `switch-${id}` }}
                />
              </ListItemSecondaryAction>
            </ListItem>
          ))}
          <ListItem key={'explore-select'} className="py-2">
            <ListItemText
                primary={"Select your Explore"}
                secondary={"Load a conversation with a different Explore. These explores are configured in the Backend deployment of Explore Assistant and are loaded dynamically from a table."}
                className="pr-4"
              />
              <ListItemSecondaryAction>
                <Select
                  labelId="demo-simple-select-label"
                  id="demo-simple-select"
                  value={exploreId.replace("/",":")}
                  label="Explore Select"
                  onChange={setSelectedExplore}
                >
                  {explores.length > 0 && explores.map((explore, index) => (
                    <MenuItem key={index} value={explore.explore_id}>{explore.explore_id.split(":")[1]}</MenuItem>
                  ))}
                </Select>
              </ListItemSecondaryAction>
          </ListItem>
        </List>
      </Box>
    </Modal>
  )
}

export default SettingsModal
