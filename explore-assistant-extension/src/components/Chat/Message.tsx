import React, { useState } from 'react'

import MarkdownText from './MarkdownText'
import clsx from 'clsx'
import { ThumbUp, ThumbDown } from '@material-ui/icons'
import './Message.css'

export const getRelativeTimeString = (dateStr: string | Date) => {
  const date = new Date(dateStr)
  const now = new Date()

  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)
  const diffInMinutes = Math.floor(diffInSeconds / 60)
  const diffInHours = Math.floor(diffInMinutes / 60)
  const diffInDays = Math.floor(diffInHours / 24)

  // Function to format the date as "Oct 25, 2023"
  const formatDate = (date: Date) => {
    const options: Intl.DateTimeFormatOptions = {
      month: 'short', // allowed values: 'numeric', '2-digit', 'long', 'short', 'narrow'
      day: 'numeric', // allowed values: 'numeric', '2-digit'
      year: 'numeric', // allowed values: 'numeric', '2-digit'
    }
    return date.toLocaleDateString('en-US', options)
  }

  let relativeTime

  if (diffInSeconds < 1) {
    relativeTime = 'just now'
  } else if (diffInSeconds < 60) {
    relativeTime =
      diffInSeconds === 1 ? '1 second ago' : `${diffInSeconds} seconds ago`
  } else if (diffInMinutes < 60) {
    relativeTime =
      diffInMinutes === 1 ? '1 minute ago' : `${diffInMinutes} minutes ago`
  } else if (diffInHours < 24) {
    relativeTime = diffInHours === 1 ? '1 hour ago' : `${diffInHours} hours ago`
  } else if (diffInDays <= 2) {
    relativeTime = diffInDays === 1 ? '1 day ago' : `${diffInDays} days ago`
  } else {
    relativeTime = formatDate(date)
  }

  return relativeTime
}

export const getDateCategory = (date: Date) => {
  const now = new Date()
  const threadDate = new Date(date)

  const diffTime = Math.abs(now.getTime() - threadDate.getTime())
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) // difference in days

  if (diffDays === 1) {
    return 'Today'
  }
  if (diffDays === 2) {
    return 'Yesterday'
  }
  if (diffDays <= 7) {
    return 'Last 7 days'
  }
  if (diffDays <= 30) {
    return 'Last 30 days'
  }
  return 'More than 30 days ago'
}

interface MessageProps {
  actor: string
  children?: React.ReactNode
  createdAt?: number
  message?: string
}

const Message = ({ message, actor, children }: MessageProps) => {
  const [isThumbUpClicked, setIsThumbUpClicked] = useState(false)
  const [isThumbDownClicked, setIsThumbDownClicked] = useState(false)
  const [showButtons, setShowButtons] = useState(false)
  const [feedbackVisible, setFeedbackVisible] = useState(false)
  const [feedbackText, setFeedbackText] = useState('')


  const handleThumbUpClick = () => {

    setIsThumbUpClicked(!isThumbUpClicked)
    setIsThumbDownClicked(false)
    setFeedbackVisible(!isThumbUpClicked) // Show feedback form
    // You can also implement logic to track thumb up votes here, e.g., update state or send a feedback event
  }

  const handleThumbDownClick = () => {
    setIsThumbDownClicked(!isThumbDownClicked)
    setIsThumbUpClicked(false)
    setFeedbackVisible(!isThumbDownClicked) // Show feedback form
    // You can also implement logic to track thumb down votes here
  }

  const handleMouseEnter = () => {
    setShowButtons(true)
  }

  const handleMouseLeave = () => {
    setTimeout(() => {
      setShowButtons(false)
    }, 100) // Adjust the delay as needed
  }

  const handleSubmitFeedback = () => {
    setFeedbackVisible(false) // Hide feedback form
    // Optionally handle the feedback submission logic here
  }

  const handleCancelFeedback = () => {
    setFeedbackVisible(false) // Hide feedback form
    setFeedbackText('')
    setIsThumbUpClicked(false)
    setIsThumbDownClicked(false)
  }

  return (
    <div
      className={`flex ${
        actor === 'user' ? 'justify-end' : 'justify-start'
      } mb-4`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
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