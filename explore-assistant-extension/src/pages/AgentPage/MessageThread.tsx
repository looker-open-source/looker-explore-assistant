import React from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { RootState } from '../../store'
import Message from '../../components/Chat/Message'
import ExploreMessage from '../../components/Chat/ExploreMessage'
import SummaryMessage from '../../components/Chat/SummaryMessage'
import { CircularProgress, Button } from '@material-ui/core'
import { AssistantState, ChatMessage, fetchThreadMessages } from '../../slices/assistantSlice'
import useThreadManagement from '../../hooks/useThreadManagement'

// MessageThread component is responsible for rendering the chat messages
// within the current explore thread. It displays different types of messages
// such as regular chat messages, explore messages, and summary messages.
const MessageThread = () => {
  const dispatch = useDispatch()
  
  // Extract currentExploreThread, isQuerying, and pagination from the Redux store
  const { currentExploreThread, isQuerying, pagination, messageFetchStatus } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )
  const { isThreadMessagesLoading } = useThreadManagement()

  // If there is no current explore thread, return an empty fragment
  if (currentExploreThread === null) {
    return <></>
  }

  // Extract messages from the current explore thread
  const messages = [...currentExploreThread.messages]
  .sort((a, b) => a.createdAt - b.createdAt) as ChatMessage[];
  const isLoading = isThreadMessagesLoading(currentExploreThread.uuid)
  
  // Get pagination info for the current thread
  const threadPagination = pagination?.messages[currentExploreThread.uuid]
  const hasMoreMessages = threadPagination?.hasMore || false
  const isLoadingMore = messageFetchStatus[currentExploreThread.uuid] === 'pending'

  // Handler for loading more messages
  const handleLoadMoreMessages = () => {
    if (threadPagination && hasMoreMessages && !isLoadingMore) {
      dispatch(fetchThreadMessages({
        threadId: currentExploreThread.uuid,
        limit: threadPagination.limit,
        offset: threadPagination.offset
      }))
    }
  }

  return (
    <div className="">
      {messages.length === 0 && isLoading ? (
        <div className="flex justify-center my-8">
          <CircularProgress size={24} className="text-gray-400" />
          <span className="ml-2 text-gray-500">Loading conversation...</span>
        </div>
      ) : (
        <>
          {/* Load More Messages Button - At the top of the list, but not sticky */}
          {hasMoreMessages && messages.length > 0 && (
            <div className="flex justify-center my-4">
              <button
                variant="outlined"
                size="small"
                onClick={handleLoadMoreMessages}
                disabled={isLoadingMore}
                className="text-blue-500 border-blue-500 hover:bg-blue-50"
              >
                {isLoadingMore ? (
                  <>
                    <CircularProgress size={16} className="mr-2 text-blue-500" />
                    Loading older messages...
                  </>
                ) : (
                  'Load Older Messages'
                )}
              </button>
            </div>
          )}
          
          {messages.map((message) => {
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
            } else if (message.type === 'summarize') {
              return <SummaryMessage key={message.uuid} message={message} uuid={message.uuid} />
            } else {
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
        </>
      )}
      {isQuerying && (
        <div className="flex flex-col text-gray-300 size-8">
          <CircularProgress color={'inherit'} size={'inherit'} />
        </div>
      )}
    </div>
  )
}

export default MessageThread
