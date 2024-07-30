import React, { useEffect } from 'react'
import { IconButton, Tooltip } from '@mui/material'
import MenuIcon from '@mui/icons-material/Menu'
import SettingsIcon from '@mui/icons-material/Settings'
import AddIcon from '@mui/icons-material/Add'
import ChatBubbleOutline from '@mui/icons-material/ChatBubbleOutline'

interface SidebarProps {
  expanded: boolean
  toggleDrawer: () => void
}

const Sidebar = ({ expanded, toggleDrawer }: SidebarProps) => {
  const [isExpanded, setIsExpanded] = React.useState(expanded)

  const sidebarItems = [
    { text: 'New chat' },
    { text: 'Ready to Assist' },
    { text: 'Which Extensions?' },
    { text: 'Embedding Videos' },
    { text: 'Corrected Dagster' },
    { text: 'Camel in the Desert' },
  ]

  useEffect(() => {
    console.log('expanded', expanded)
  }, [expanded])

  const handleClick = () => {
    if (expanded) {
      // closing
      console.log('closing')

      setIsExpanded(false)
      setTimeout(() => toggleDrawer(), 100)
    } else {
      // opening
      console.log('opening')
      toggleDrawer()
      setTimeout(() => setIsExpanded(true), 100)
    }
  }

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
              mr-2 flex flex-row text-gray-600 items-center cursor-pointer bg-gray-200
              
              rounded-full p-2
              
              transition-all duration-300 ease-in-out
            
            `}
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
            <div className="mb-4 font-semibold">Recent</div>
            <div className="flex flex-col space-y-4">
              {sidebarItems.map((item, index) => (
                <Tooltip
                  key={index}
                  title={expanded ? '' : item.text}
                  placement="right"
                  arrow
                >
                  <div
                    className={`flex items-center hover:bg-gray-100 cursor-pointer`}
                  >
                    <ChatBubbleOutline
                      fontSize="small"
                      className="mr-2 text-gray-600"
                    />
                    {expanded && <span className="ml-3">{item.text}</span>}
                  </div>
                </Tooltip>
              ))}
            </div>

            {sidebarItems.length === 0 && (
              <div className="text-gray-400">No recent chats</div>
            )}
          </div>
        )}
      </nav>
      <div className="mt-auto p-4 border-t">
        <Tooltip title={expanded ? '' : 'Settings'} placement="top" arrow>
          <div
            className={`mr-2 flex flex-row text-gray-400 items-center cursor-pointer p-2 transition-all duration-300 ease-in-out`}
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
    </div>
  )
}

export default Sidebar
