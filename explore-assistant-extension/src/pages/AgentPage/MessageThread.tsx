import React from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../../store'
import Message from '../../components/Chat/Message'
import ExploreMessage from '../../components/Chat/ExploreMessage'
import SummaryMessage from '../../components/Chat/SummaryMessage'
import { CircularProgress } from '@material-ui/core'
import { AssistantState, ChatMessage } from '../../slices/assistantSlice'

const MessageThread = () => {
  const { currentExploreThread, isQuerying } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )

  if(currentExploreThread === null) {
    return <></>
  }

  const messages = currentExploreThread.messages as ChatMessage[]
  return (
    <div className="">
      {messages.map((message) => {
        if (message.type === 'explore') {
          return (
            <ExploreMessage
              key={message.uuid}
              queryArgs={message.exploreUrl}
              prompt={message.summarizedPrompt}
            />
          )
        } else if (message.type === 'summarize') {
          return <SummaryMessage key={message.uuid} message={message} />
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
    </div>
  )
}

export default MessageThread
