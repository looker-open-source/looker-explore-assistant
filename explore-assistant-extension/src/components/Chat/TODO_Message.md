To update `Message.tsx` so that it can call `cloudrun_endpoint.com/feedback` on feedback submission and include the metadata of the chat, you can follow these steps. This involves modifying the `handleSubmitFeedback` function to construct a payload similar to the one in `useSendVertexMessage.ts`.

### Step-by-Step Implementation

1.  **Pass Necessary Metadata**: Ensure that the necessary metadata is available in the `Message` component. You might need to pass this data as props or use a context provider if it's not already available.

2.  **Modify `handleSubmitFeedback`**: Update the function to include the metadata in the payload and send it to the specified endpoint.


```javascript

// TODO JOON
import React, { useState } from 'react'
import MarkdownText from './MarkdownText'
import clsx from 'clsx'
import { ThumbUp, ThumbDown } from '@material-ui/icons'
import './Message.css'

interface MessageProps {
  actor: string
  children?: React.ReactNode
  createdAt?: number
  message?: string
  currentThreadID: string
  currentExploreKey: string
  rawPrompt: string
  promptType: string
  userId: string
  contents: string
  parameters: Record<string, any>
}

const Message = ({
  message,
  actor,
  children,
  currentThreadID,
  currentExploreKey,
  rawPrompt,
  promptType,
  userId,
  contents,
  parameters,
}: MessageProps) => {
  const [isThumbUpClicked, setIsThumbUpClicked] = useState(false)
  const [isThumbDownClicked, setIsThumbDownClicked] = useState(false)
  const [showButtons, setShowButtons] = useState(false)
  const [feedbackVisible, setFeedbackVisible] = useState(false)
  const [feedbackText, setFeedbackText] = useState('')

  const handleThumbUpClick = () => {
    setIsThumbUpClicked(!isThumbUpClicked)
    setIsThumbDownClicked(false)
    setFeedbackVisible(!isThumbUpClicked)
  }

  const handleThumbDownClick = () => {
    setIsThumbDownClicked(!isThumbDownClicked)
    setIsThumbUpClicked(false)
    setFeedbackVisible(!isThumbDownClicked)
  }

  const handleSubmitFeedback = async () => {
    setFeedbackVisible(false)

    try {
      const feedbackPayload = {
        current_thread_id: currentThreadID,
        current_explore_key: currentExploreKey,
        raw_prompt: rawPrompt,
        prompt_type: promptType,
        user_id: userId,
        contents: contents,
        parameters: parameters,
        feedback_text: feedbackText,
        feedback_type: isThumbUpClicked ? 'thumbs_up' : 'thumbs_down',
      }

      const response = await fetch('https://cloudrun_endpoint.com/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(feedbackPayload),
      })

      if (!response.ok) {
        throw new Error('Failed to send feedback')
      }

      const responseData = await response.json()
      console.log('Feedback submitted successfully:', responseData)

      setFeedbackText('')
    } catch (error) {
      console.error('Error submitting feedback:', error)
    }
  }

  const handleCancelFeedback = () => {
    setFeedbackVisible(false)
    setFeedbackText('')
    setIsThumbUpClicked(false)
    setIsThumbDownClicked(false)
  }

  return (
    <div
      className={`flex ${
        actor === 'user' ? 'justify-end' : 'justify-start'
      } mb-4`}
      onMouseEnter={() => setShowButtons(true)}
      onMouseLeave={() => setTimeout(() => setShowButtons(false), 100)}
    >
      <div className={`max-w-[70%] ${actor === 'user' ? 'order-2' : 'order-1'}`}>
        <div
          className={clsx(
            'rounded-lg p-3 max-w-xl',
            actor === 'user'
              ? 'bg-[rgb(237,243,253)] text-gray-800'
              : 'bg-[rgb(242,242,242)] text-gray-800',
          )}
        >
          {message && <MarkdownText text={message} />}
          {children && <div>{children}</div>}
        </div>
        {actor !== 'user' && (
          <div className={`flex space-x-2 mt-2 ${showButtons || isThumbUpClicked || isThumbDownClicked ? 'visible' : 'hidden'}`}>
            <button onClick={handleThumbUpClick}>
              <ThumbUp color={isThumbUpClicked ? 'primary' : 'default'} />
            </button>
            <button onClick={handleThumbDownClick}>
              <ThumbDown color={isThumbDownClicked ? 'primary' : 'default'} />
            </button>
          </div>
        )}
        {feedbackVisible && (
          <div className="feedback-form">
            <textarea
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              placeholder="Enter your feedback"
              className="feedback-textarea"
            />
            <div className="flex justify-between mt-2">
              <button onClick={handleSubmitFeedback} className="submit-btn">
                Submit
              </button>
              <button onClick={handleCancelFeedback} className="cancel-btn">
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Message

```