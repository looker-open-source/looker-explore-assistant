import React from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../../store'
import Message from '../../components/Chat/Message'
import ExploreMessage from '../../components/Chat/ExploreMessage'
import SummaryMessage from '../../components/Chat/SummaryMessage'
import { CircularProgress } from '@material-ui/core'

const MessageThread = () => {
  const { currentExploreThread, isQuerying } = useSelector(
    (state: RootState) => state.assistant,
  )

  const messages = currentExploreThread.messages
  return (
    <div className="">
      {messages.map((message, index) => {
        if (message.type === 'explore') {
          return (
            <ExploreMessage
              key={index}
              queryArgs={message.exploreUrl}
              prompt={message.summarizedPrompt}
            />
          )
        } else if (message.type === 'summarize') {
          return <SummaryMessage key={index} queryArgs={message.exploreUrl} />
        } else {
          return (
            <Message
              key={index}
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
    </div>
  )
}

export default MessageThread
