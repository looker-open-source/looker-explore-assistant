import React from 'react'
import { IconButton, Tooltip } from '@mui/material'
import MenuIcon from '@mui/icons-material/Menu'
import SettingsIcon from '@mui/icons-material/Settings'
import AddIcon from '@mui/icons-material/Add'
import ChatBubbleOutline from '@mui/icons-material/ChatBubbleOutline'
import { useDispatch, useSelector } from 'react-redux'
import {
  clearHistory,
  ExploreThread,
  openSidePanel,
  resetChat,
  setCurrentThread,
  setIsChatMode,
  setSidePanelExploreParams,
  AssistantState,
} from '../../slices/assistantSlice'
import { RootState } from '../../store'
import SettingsModal from './Settings'

interface SidebarProps {
  expanded: boolean
  toggleDrawer: () => void
}

const Sidebar = ({ expanded, toggleDrawer }: SidebarProps) => {
  const dispatch = useDispatch()
  const [isExpanded, setIsExpanded] = React.useState(expanded)
  const [isSettingsOpen, setIsSettingsOpen] = React.useState(false)
  const { isChatMode, isQuerying, history } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )

  const handleClick = () => {
    if (expanded) {
      // closing
      setIsExpanded(false)
      setTimeout(() => toggleDrawer(), 100)
    } else {
      // opening
      toggleDrawer()
      setTimeout(() => setIsExpanded(true), 100)
    }
  }

  const canReset = isChatMode && !isQuerying

  const handleNewChat = () => {
    if (canReset) {
      dispatch(resetChat())
    }
  }

  const handleHistoryClick = (thread: ExploreThread) => {
    dispatch(resetChat())
    dispatch(setCurrentThread(thread))
    dispatch(setIsChatMode(true))
    dispatch(setSidePanelExploreParams(thread.exploreParams))
    dispatch(openSidePanel())
  }

  const handleClearHistory = () => {
    dispatch(clearHistory())
  }

  const reverseHistory = [...history].reverse() as ExploreThread[]

  return (
    <div
      className={`fixed inset-y-0 left-0 bg-[#f0f4f9] transition-all duration-300 ease-in-out flex flex-col ${
        expanded ? 'w-80' : 'w-16'
      } shadow-md`}
    >
      <div className="p-4 flex items-center">
        <Tooltip
          title={expanded ? 'Collapse Menu' : 'Expand Menu'}
          placement="bottom"
          arrow={false}
        >
          <IconButton onClick={handleClick} className="mr-2">
            <MenuIcon />
          </IconButton>
        </Tooltip>
      </div>
      <div className="p-4 flex items-center">
        <Tooltip title={'New Chat'} placement="bottom" arrow={false}>
          <div
            className={`
              mr-2 flex flex-row items-center

              ${
                canReset
                  ? 'cursor-pointer bg-gray-300 text-gray-600 hover:text-gray-700'
                  : 'bg-gray-200 text-gray-400'
              }
              
              rounded-full p-2
              
              transition-all duration-300 ease-in-out
            
            `}
            onClick={handleNewChat}
          >
            <AddIcon />

            <div
              className={`
                  
                   whitespace-nowrap transition-all duration-300 ease-in-out
                  ${isExpanded ? 'mx-3 opacity-100' : 'opacity-0'}
                  
                  `}
            >
              {isExpanded && 'New Chat'}
            </div>
          </div>
        </Tooltip>
      </div>
      <nav className="flex-grow overflow-y-auto mt-4 ml-6 text-sm">
        {isExpanded && (
          <div>
            <div className="mb-4 flex flex-row">
              <div className="flex-grow font-semibold">Recent</div>
              {history.length > 0 && (
                <div
                  className="px-4 text-xs text-gray-400 hover:underline cursor-pointer"
                  onClick={handleClearHistory}
                >
                  clear
                </div>
              )}
            </div>
            <div className="flex flex-col space-y-4">
              {history.length == 0 && (
                <div className="text-gray-400">No recent chats</div>
              )}
              {reverseHistory.map((item) => (
                <div key={'history-' + item.uuid}>
                  <Tooltip
                    title={item.summarizedPrompt}
                    placement="right"
                    arrow
                  >
                    <div
                      className={`flex items-center cursor-pointer hover:underline`}
                      onClick={() => handleHistoryClick(item)}
                    >
                      <div className="">
                        <ChatBubbleOutline
                          fontSize="small"
                          className="mr-2 text-gray-600"
                        />
                      </div>
                      <div className="line-clamp-1">
                        <span className="ml-3">{item.summarizedPrompt}</span>
                      </div>
                    </div>
                  </Tooltip>
                </div>
              ))}
            </div>
          </div>
        )}
      </nav>
      <div className="mt-auto p-4 border-t">
        <Tooltip title={expanded ? '' : 'Settings'} placement="top" arrow>
          <div
            className={`mr-2 flex flex-row text-gray-400 items-center cursor-pointer p-2 transition-all duration-300 ease-in-out`}
            onClick={() => setIsSettingsOpen(true)}
          >
            <SettingsIcon />
            <div
              className={`
                   whitespace-nowrap transition-all duration-300 ease-in-out
                  ${isExpanded ? 'mx-3 opacity-100' : 'opacity-0'}
                  
                  `}
            >
              {isExpanded && 'Settings'}
            </div>
          </div>
        </Tooltip>
      </div>
      <SettingsModal
        open={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
  )
}

export default Sidebar
