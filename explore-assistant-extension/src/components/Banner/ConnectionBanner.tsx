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
    // Optional: save the dismissal to localStorage to persist across sessions
    localStorage.setItem('connectionBannerDismissed', 'true')
  }
  
  return (
    <Box 
      width="100%" 
      bgcolor="#EEF7FF" 
      p={1} 
      display="flex" 
      alignItems="center" 
      justifyContent="space-between"
      borderBottom="1px solid #DDECF9"
    >
      <Typography variant="body2" style={{ marginLeft: '16px' }}>
        Error retrieving data? Open the Profile icon and select Accounts to log in to your data connections
      </Typography>
      <Box display="flex" alignItems="center">
        <Box 
          display="flex" 
          alignItems="center" 
          mr={1} 
          color="#1A73E8"
        >
          {/* Arrow pointing to upper right corner */}
          <div style={{ 
            borderRight: '2px solid currentColor', 
            borderTop: '2px solid currentColor', 
            width: '10px', 
            height: '10px', 
            transform: 'rotate(45deg)',
            marginRight: '5px'
          }}></div>
          <Typography variant="caption" color="primary">
            Upper right
          </Typography>
        </Box>
        <IconButton size="small" onClick={handleDismiss}>
          <Close fontSize="small" />
        </IconButton>
      </Box>
    </Box>
  )
}

export default ConnectionBanner