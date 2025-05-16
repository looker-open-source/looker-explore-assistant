import React, { useState, useEffect } from 'react'
import { Box, Typography, IconButton } from '@material-ui/core'
import { Close } from '@material-ui/icons'

interface ConnectionBannerProps {
  initialVisible?: boolean;
}

const ConnectionBanner: React.FC<ConnectionBannerProps> = ({ initialVisible = true }) => {
  const [showBanner, setShowBanner] = useState(initialVisible)
  
  if (!showBanner) return null
  
  const handleDismiss = () => {
    setShowBanner(false)
    // No longer using localStorage for compatibility with Looker's environment
  }
  
  return (
    <Box 
      width="100%" 
      bgcolor="#EEF7FF" 
      p={1} 
      display="flex" 
      alignItems="center" 
      justifyContent="space-around"
      borderBottom="1px solid #DDECF9"
    >
      <Box display="flex" alignItems="center" style={{ marginLeft: '16px' }}>
        <Typography variant="body2">
          Error retrieving data? Open the Profile icon <img 
            src="https://gravatar.lookercdn.com/avatar/25600dffca61be7195af08d332e8d22d?s=156&d=blank" 
            alt="Profile Icon" 
            style={{ 
              height: '16px', 
              width: '16px', 
              borderRadius: '50%', 
              display: 'inline-block',
              verticalAlign: 'middle',
              margin: '0 4px'
            }} 
          /> and select Accounts to log in to your data connections.
        </Typography>
      </Box>
 
    </Box>
  )
}

export default ConnectionBanner