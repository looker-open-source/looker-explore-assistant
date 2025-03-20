import React from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../../store'
import Message from '../../components/Chat/Message'
import ExploreMessage from '../../components/Chat/ExploreMessage'
import SummaryMessage from '../../components/Chat/SummaryMessage'
import { CircularProgress } from '@material-ui/core'
import { AssistantState, ChatMessage } from '../../slices/assistantSlice'

// MessageThread component is responsible for rendering the chat messages
// within the current explore thread. It displays different types of messages
// such as regular chat messages, explore messages, and summary messages.
const MessageThread = () => {
  // Extract currentExploreThread and isQuerying from the Redux store
  const { currentExploreThread, isQuerying } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )

  // If there is no current explore thread, return an empty fragment
  if (currentExploreThread === null) {
    return <></>
  }

  // Extract messages from the current explore thread
  const messages = currentExploreThread.messages as ChatMessage[]

  return (
    <div className="">
      {messages.map((message) => {
        // Render an ExploreMessage component for messages of type 'explore'
        if (message.type === 'explore') {
          return (
            <ExploreMessage
              key={message.uuid}
              modelName={currentExploreThread.modelName}
              exploreId={currentExploreThread.exploreId}
              queryArgs={message.exploreUrl}
              prompt={message.summarizedPrompt}
              uuid={message.uuid}
            />
          )
        } 
        // Render a SummaryMessage component for messages of type 'summarize'
        else if (message.type === 'summarize') {
          return <SummaryMessage key={message.uuid} message={message} uuid={message.uuid} />
        } 
        // Render a regular Message component for other message types
        else {
          return (
            <Message
              key={message.uuid}
              message={message.message}
              actor={message.actor}
              createdAt={message.createdAt}
              uuid={message.uuid}
            />
          )
        }
      })}
      {/* Display a loading spinner if a query is currently being processed */}
      {isQuerying && (
        <div className="flex flex-col text-gray-300 size-8">
          <CircularProgress color={'inherit'} size={'inherit'} />
        </div>
      )}
    </div>
  )
}

export default MessageThread
