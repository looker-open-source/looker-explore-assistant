import { Card, CardContent, Paragraph, Section } from '@looker/components'
import React from 'react'

import styles from './style.module.scss'
import MarkdownText from './MarkdownText'

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
  <Card border={'none'} width={'100%'}>
    <CardContent  p={0}>
      <Paragraph fontSize="xsmall" color="text1" mb="u2">
        {actor == 'system' && 'Gemini'}
      </Paragraph>

      <Section
        fontSize={'small'}
        className={styles.chatBubble + ' ' + styles[actor]}
      >
        <div className={styles.chatBubbleContent}>
          {message && (<MarkdownText text={message} />)}
          {children && <div>{children}</div>}
        </div>
      </Section>
    </CardContent>
  </Card>
)

export default Message
