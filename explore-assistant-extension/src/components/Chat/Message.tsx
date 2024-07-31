import React from 'react'

import MarkdownText from './MarkdownText'
import clsx from 'clsx'

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

const Message = ({ message, actor, children }: MessageProps) => (
  <div
    className={`flex ${
      actor === 'user' ? 'justify-end' : 'justify-start'
    } mb-4`}
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
    </div>
  </div>
)

export default Message
