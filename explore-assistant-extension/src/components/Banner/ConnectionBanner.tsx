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
      alignItems="right" 
      justifyContent="right"
      borderBottom="1px solid #DDECF9"
    >
      <Box display="flex" alignItems="center" style={{ marginLeft: '16px' }}>
        <Typography variant="body2">
          Errors? Open the Profile icon in the upper right corner, select Account and Log In to your connections.
        </Typography>
      </Box>
      <Box 
        display="flex" 
        alignItems="center" 
        mr={1} 
        color="#1A73E8"
      >
        <IconButton size="small" onClick={handleDismiss}>
          <Close fontSize="small" />
        </IconButton>
      </Box>
    </Box>
  )
}

export default ConnectionBanner