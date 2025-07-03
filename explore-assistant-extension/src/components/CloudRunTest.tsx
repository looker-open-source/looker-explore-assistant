// Test the serverProxy solution for CORS
// Add this to your Looker extension component to test the Cloud Run connection

import React, { useState } from 'react'
import { Button, Space, MessageBar } from '@looker/components'
import useSendCloudRunMessage from '../hooks/useSendCloudRunMessage'

export const CloudRunTest: React.FC = () => {
  const [testResult, setTestResult] = useState<string>('')
  const [isLoading, setIsLoading] = useState(false)
  const { testCloudRunSettings, processPrompt } = useSendCloudRunMessage()

  const handleConnectionTest = async () => {
    setIsLoading(true)
    setTestResult('')
    
    try {
      console.log('Starting Cloud Run connection test...')
      const result = await testCloudRunSettings()
      
      if (result) {
        setTestResult('✅ Cloud Run connection successful via Looker proxy')
      } else {
        setTestResult('❌ Cloud Run connection failed')
      }
    } catch (error) {
      console.error('Connection test error:', error)
      setTestResult(`❌ Connection test error: ${error}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleProcessTest = async () => {
    setIsLoading(true)
    setTestResult('')
    
    try {
      console.log('Starting Cloud Run process test...')
      const result = await processPrompt(
        'Test prompt for Cloud Run processing',
        'test-conversation-id',
        ['Test prompt for Cloud Run processing']
      )
      
      if (result) {
        setTestResult(`✅ Cloud Run processing successful: ${JSON.stringify(result, null, 2)}`)
      } else {
        setTestResult('❌ Cloud Run processing failed')
      }
    } catch (error) {
      console.error('Process test error:', error)
      setTestResult(`❌ Process test error: ${error}`)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Space>
      <Button 
        onClick={handleConnectionTest}
        disabled={isLoading}
      >
        Test Cloud Run Connection
      </Button>
      
      <Button 
        onClick={handleProcessTest}
        disabled={isLoading}
      >
        Test Cloud Run Processing
      </Button>
      
      {testResult && (
        <MessageBar intent={testResult.includes('✅') ? 'positive' : 'critical'}>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: '12px' }}>
            {testResult}
          </pre>
        </MessageBar>
      )}
    </Space>
  )
}
