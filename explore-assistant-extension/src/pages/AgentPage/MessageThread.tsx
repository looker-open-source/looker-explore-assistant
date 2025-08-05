import React, { useCallback, useEffect, useRef } from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../../store'
import Message from '../../components/Chat/Message'
import ExploreMessage from '../../components/Chat/ExploreMessage'
import SummaryMessage from '../../components/Chat/SummaryMessage'
import { CircularProgress } from '@material-ui/core'
import { AssistantState, ChatMessage } from '../../slices/assistantSlice'

interface MessageThreadProps {
  endOfMessageRef: React.RefObject<HTMLDivElement>
}

const MessageThread = ({ endOfMessageRef }: MessageThreadProps) => {
  const { currentExploreThread, isQuerying } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )

  const autoOpenTriggered = useRef(false); // Ref to track if autoOpen has been triggered

  const scrollIntoView = useCallback(() => {
    endOfMessageRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [endOfMessageRef])

  const handleSummaryComplete = () => {
    scrollIntoView()
  }

  useEffect(() => {
    scrollIntoView()
  }, [currentExploreThread])

  if(currentExploreThread === null) {
    return <></>
  }

  const messages = currentExploreThread.messages as ChatMessage[]

  return (
    <div className="">
      {messages.map((message, i) => {
        if (message.type === 'explore') {
          
          const shouldAutoOpen = !autoOpenTriggered.current && i === 1 && messages.length === 2;
          if (shouldAutoOpen) {
            autoOpenTriggered.current = true; // Set the ref to true after triggering autoOpen
          }

          return (
            <ExploreMessage
              key={message.uuid}
              exploreParams={message.exploreParams}
              modelName={currentExploreThread.modelName}
              exploreId={currentExploreThread.exploreId}
              prompt={message.summarizedPrompt}
              autoOpen={shouldAutoOpen}
              summary={message.summary}
            />
          )
        } else if (message.type === 'summarize') {
          return <SummaryMessage key={message.uuid} message={message} onSummaryComplete={handleSummaryComplete} />
        } else {
          return (
            <Message
              key={message.uuid}
              message={message.message}
              actor={message.actor}
              createdAt={message.createdAt}
            />
          )
        }
      })}
      {isQuerying && (
        <div className="flex flex-col text-gray-300 size-8">
          <CircularProgress color={'inherit'} size={'inherit'} />
        </div>
      )}
      <div ref={endOfMessageRef} />
    </div>
  )
}

export default MessageThread
