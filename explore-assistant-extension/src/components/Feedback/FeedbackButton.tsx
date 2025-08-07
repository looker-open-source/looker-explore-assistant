import React, { useState } from 'react'
import {
  IconButton,
  Tooltip,
  Dialog,
  DialogContent,
  DialogTitle,
  Button,
  Box,
  Typography,
  TextField,
  FormControlLabel,
  Radio,
  RadioGroup,
  Snackbar,
  Chip
} from '@material-ui/core'
import {
  ThumbUp,
  ThumbDown,
  Feedback as FeedbackIcon,
  Close,
  Add as AddIcon,
  CheckCircle,
  Error
} from '@material-ui/icons'
import { useSelector } from 'react-redux'
import { RootState } from '../../store'
import { useFeedback } from '../../hooks/useFeedback'
import { v4 as uuidv4 } from 'uuid'

export type FeedbackType = 'positive' | 'negative' | 'refinement' | 'alternative'

// Simple Alert component replacement
const CustomAlert: React.FC<{ severity: 'success' | 'error', onClose?: () => void, children: React.ReactNode }> = ({
  severity,
  onClose,
  children
}) => (
  <Box
    display="flex"
    alignItems="center"
    p={2}
    bgcolor={severity === 'success' ? '#e8f5e8' : '#ffebee'}
    border={1}
    borderColor={severity === 'success' ? '#4caf50' : '#f44336'}
    borderRadius={1}
    color={severity === 'success' ? '#2e7d32' : '#c62828'}
  >
    {severity === 'success' ? <CheckCircle style={{ marginRight: 8 }} /> : <Error style={{ marginRight: 8 }} />}
    <Typography variant="body2" style={{ flex: 1 }}>
      {children}
    </Typography>
    {onClose && (
      <IconButton size="small" onClick={onClose} style={{ color: 'inherit' }}>
        <Close fontSize="small" />
      </IconButton>
    )}
  </Box>
)

interface FeedbackButtonProps {
  queryId?: string
  exploreId: string
  originalPrompt: string
  generatedParams: any
  shareUrl: string
  size?: 'small' | 'medium'
  onFeedbackSubmitted?: (feedbackType: FeedbackType, success: boolean) => void
}

interface FeedbackDialogProps {
  open: boolean
  onClose: () => void
  exploreId: string
  originalPrompt: string
  generatedParams: any
  shareUrl: string
  initialFeedbackType?: FeedbackType
  onFeedbackSubmitted?: (feedbackType: FeedbackType, success: boolean) => void
}

const FeedbackDialog: React.FC<FeedbackDialogProps> = ({
  open,
  onClose,
  exploreId,
  originalPrompt,
  generatedParams,
  shareUrl,
  initialFeedbackType = 'positive',
  onFeedbackSubmitted
}) => {
  const [feedbackType, setFeedbackType] = useState<FeedbackType>(initialFeedbackType)
  const [userComment, setUserComment] = useState('')
  const [suggestedImprovements, setSuggestedImprovements] = useState('')
  const [issues, setIssues] = useState<string[]>([])
  const [newIssue, setNewIssue] = useState('')
  const [submitSuccess, setSubmitSuccess] = useState<boolean | null>(null)

  const { settings } = useSelector((state: RootState) => state.assistant)
  // Use a system identifier since userEmail is not available in OAuth state
  const userId = 'system_user'
  
  const { 
    submitFeedback,
    submitPositiveFeedback,
    submitNegativeFeedback,
    requestResponseImprovement,
    isSubmitting
  } = useFeedback()

  const addIssue = () => {
    if (newIssue.trim() && !issues.includes(newIssue.trim())) {
      setIssues([...issues, newIssue.trim()])
      setNewIssue('')
    }
  }

  const removeIssue = (issueToRemove: string) => {
    setIssues(issues.filter(issue => issue !== issueToRemove))
  }

  const handleSubmit = async () => {
    try {
      const queryId = uuidv4() // Generate unique ID for this feedback session
      let success = false

      if (feedbackType === 'positive') {
        success = await submitPositiveFeedback({
          queryId,
          userInput: originalPrompt,
          response: JSON.stringify(generatedParams),
          feedbackNotes: userComment.trim() || undefined
        })
      } else if (feedbackType === 'negative') {
        if (issues.length === 0) {
          // Fallback to generic issue if none specified
          setIssues(['Response did not match expectations'])
        }
        
        success = await submitNegativeFeedback({
          queryId,
          userInput: originalPrompt,
          response: JSON.stringify(generatedParams),
          issues: issues.length > 0 ? issues : ['Response did not match expectations'],
          improvementSuggestions: suggestedImprovements.trim() || undefined,
          feedbackNotes: userComment.trim() || undefined
        })
      } else if (feedbackType === 'refinement') {
        const improvementRequest = suggestedImprovements.trim() || 'Please refine this query to better match my needs'
        
        success = await requestResponseImprovement({
          queryId,
          originalInput: originalPrompt,
          originalResponse: JSON.stringify(generatedParams),
          improvementRequest,
          context: userComment.trim() || undefined
        })
      } else {
        // For alternative feedback, use the original method
        success = await submitFeedback({
          exploreId,
          originalPrompt,
          generatedParams,
          shareUrl,
          feedbackType,
          userId,
          userComment: userComment.trim() || undefined,
          suggestedImprovements: suggestedImprovements.trim() ? { comment: suggestedImprovements.trim() } : undefined
        })
      }
      
      setSubmitSuccess(success)
      onFeedbackSubmitted?.(feedbackType, success)
      
      // Close dialog after a brief delay
      setTimeout(() => {
        onClose()
        setSubmitSuccess(null)
        setUserComment('')
        setSuggestedImprovements('')
        setIssues([])
        setNewIssue('')
      }, 2000)
      
    } catch (error) {
      console.error('Failed to submit feedback:', error)
      setSubmitSuccess(false)
      onFeedbackSubmitted?.(feedbackType, false)
    }
  }

  const getFeedbackTypeDescription = (type: FeedbackType): string => {
    switch (type) {
      case 'positive':
        return 'This query is exactly what I wanted'
      case 'negative':
        return 'This query doesn\'t match my request'
      case 'refinement':
        return 'This is close but needs some improvements'
      case 'alternative':
        return 'I prefer a different approach'
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">Provide Feedback</Typography>
          <IconButton onClick={onClose} size="small">
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Box p={2}>
          <Typography variant="body2" color="textSecondary" gutterBottom>
            Original Query: "{originalPrompt}"
          </Typography>
          
          <Box mt={3}>
            <Typography variant="subtitle1" gutterBottom>
              How would you rate this query result?
            </Typography>
            <RadioGroup
              value={feedbackType}
              onChange={(e) => setFeedbackType(e.target.value as FeedbackType)}
            >
              <FormControlLabel
                value="positive"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body2" style={{ fontWeight: 'bold' }}>
                      👍 Positive
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      {getFeedbackTypeDescription('positive')}
                    </Typography>
                  </Box>
                }
              />
              <FormControlLabel
                value="negative"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body2" style={{ fontWeight: 'bold' }}>
                      👎 Negative
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      {getFeedbackTypeDescription('negative')}
                    </Typography>
                  </Box>
                }
              />
              <FormControlLabel
                value="refinement"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body2" style={{ fontWeight: 'bold' }}>
                      ⚡ Needs Refinement
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      {getFeedbackTypeDescription('refinement')}
                    </Typography>
                  </Box>
                }
              />
              <FormControlLabel
                value="alternative"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body2" style={{ fontWeight: 'bold' }}>
                      🔄 Alternative Approach
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      {getFeedbackTypeDescription('alternative')}
                    </Typography>
                  </Box>
                }
              />
            </RadioGroup>
          </Box>

          <Box mt={3}>
            <TextField
              fullWidth
              label="Additional Comments (Optional)"
              multiline
              rows={3}
              value={userComment}
              onChange={(e) => setUserComment(e.target.value)}
              placeholder="Tell us more about your experience with this query..."
              variant="outlined"
            />
          </Box>

          {feedbackType === 'negative' && (
            <Box mt={3}>
              <Typography variant="subtitle2" gutterBottom>
                What issues did you encounter? *
              </Typography>
              <Box mb={2}>
                {issues.map((issue, index) => (
                  <Chip
                    key={index}
                    label={issue}
                    onDelete={() => removeIssue(issue)}
                    style={{ margin: '4px' }}
                  />
                ))}
              </Box>
              <Box display="flex" style={{ gap: '8px' }}>
                <TextField
                  fullWidth
                  label="Add issue"
                  value={newIssue}
                  onChange={(e) => setNewIssue(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && addIssue()}
                  placeholder="e.g., Wrong fields selected, Incorrect filters"
                  variant="outlined"
                  size="small"
                />
                <Button onClick={addIssue} disabled={!newIssue.trim()}>
                  <AddIcon />
                </Button>
              </Box>
            </Box>
          )}

          {(feedbackType === 'refinement' || feedbackType === 'alternative') && (
            <Box mt={3}>
              <TextField
                fullWidth
                label="Suggested Improvements (Optional)"
                multiline
                rows={4}
                value={suggestedImprovements}
                onChange={(e) => setSuggestedImprovements(e.target.value)}
                placeholder="Describe what changes you would like to see or provide specific parameter suggestions..."
                variant="outlined"
                helperText="You can provide specific field names, filter suggestions, or describe the changes you'd like to see."
              />
            </Box>
          )}

          <Box mt={3} display="flex" style={{ gap: '16px' }} justifyContent="flex-end">
            <Button onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button
              variant="contained"
              color="primary"
              onClick={handleSubmit}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
            </Button>
          </Box>

          {submitSuccess !== null && (
            <Box mt={2}>
              <CustomAlert severity={submitSuccess ? "success" : "error"}>
                {submitSuccess 
                  ? "Thank you for your feedback! This will help improve our query generation."
                  : "Failed to submit feedback. Please try again."
                }
              </CustomAlert>
            </Box>
          )}
        </Box>
      </DialogContent>
    </Dialog>
  )
}

export const FeedbackButton: React.FC<FeedbackButtonProps> = ({
  queryId,
  exploreId,
  originalPrompt,
  generatedParams,
  shareUrl,
  size = 'small',
  onFeedbackSubmitted
}) => {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [initialFeedbackType, setInitialFeedbackType] = useState<FeedbackType>('positive')
  const [snackbarOpen, setSnackbarOpen] = useState(false)
  const [snackbarMessage, setSnackbarMessage] = useState('')
  const [snackbarSeverity, setSnackbarSeverity] = useState<'success' | 'error'>('success')

  const handleQuickFeedback = async (type: FeedbackType) => {
    if (type === 'positive' || type === 'negative') {
      // For simple feedback, submit directly
      try {
        // TODO: Replace with actual MCP call or API call
        console.log('Quick feedback:', { type, exploreId, originalPrompt })
        
        setSnackbarMessage(`Thank you for your ${type} feedback!`)
        setSnackbarSeverity('success')
        setSnackbarOpen(true)
        
        onFeedbackSubmitted?.(type, true)
      } catch (error) {
        setSnackbarMessage('Failed to submit feedback')
        setSnackbarSeverity('error')
        setSnackbarOpen(true)
        
        onFeedbackSubmitted?.(type, false)
      }
    } else {
      // For complex feedback, open dialog
      setInitialFeedbackType(type)
      setDialogOpen(true)
    }
  }

  const handleDialogFeedbackSubmitted = (feedbackType: FeedbackType, success: boolean) => {
    setSnackbarMessage(
      success 
        ? `Thank you for your detailed ${feedbackType} feedback!`
        : 'Failed to submit feedback'
    )
    setSnackbarSeverity(success ? 'success' : 'error')
    setSnackbarOpen(true)
    
    onFeedbackSubmitted?.(feedbackType, success)
  }

  return (
    <>
      <Box display="flex" style={{ gap: '8px' }}>
        <Tooltip title="This query is helpful">
          <IconButton 
            size={size} 
            onClick={() => handleQuickFeedback('positive')}
            color="default"
          >
            <ThumbUp fontSize={size === 'medium' ? 'default' : 'small'} />
          </IconButton>
        </Tooltip>
        
        <Tooltip title="This query is not helpful">
          <IconButton 
            size={size} 
            onClick={() => handleQuickFeedback('negative')}
            color="default"
          >
            <ThumbDown fontSize={size === 'medium' ? 'default' : 'small'} />
          </IconButton>
        </Tooltip>
        
        <Tooltip title="Provide detailed feedback">
          <IconButton 
            size={size} 
            onClick={() => {
              setInitialFeedbackType('refinement')
              setDialogOpen(true)
            }}
            color="default"
          >
            <FeedbackIcon fontSize={size === 'medium' ? 'default' : 'small'} />
          </IconButton>
        </Tooltip>
      </Box>

      <FeedbackDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        exploreId={exploreId}
        originalPrompt={originalPrompt}
        generatedParams={generatedParams}
        shareUrl={shareUrl}
        initialFeedbackType={initialFeedbackType}
        onFeedbackSubmitted={handleDialogFeedbackSubmitted}
      />

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={4000}
        onClose={() => setSnackbarOpen(false)}
      >
        <CustomAlert onClose={() => setSnackbarOpen(false)} severity={snackbarSeverity}>
          {snackbarMessage}
        </CustomAlert>
      </Snackbar>
    </>
  )
}

export default FeedbackButton
