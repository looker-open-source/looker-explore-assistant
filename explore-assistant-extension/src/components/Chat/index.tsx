import React, { useCallback, useEffect, useRef } from 'react'
import useSendVertexMessage from '../../hooks/useSendVertexMessage'
import { Space, SpaceVertical, Spinner } from '@looker/components'
import { addMessage, setExploreParams } from '../../slices/assistantSlice'
import { useDispatch, useSelector } from 'react-redux'
import { RootState } from '../../store'
import Message from './Message'
import { Send } from '@material-ui/icons'
import styles from './style.module.scss'
import ExploreMessage from './ExploreMessage'
import SummaryMessage from './SummaryMessage'

const Chat = () => {
  const dispatch = useDispatch()
  const {
    generateExploreParams,
    isSummarizationPrompt,
    summarizePrompts,
  } = useSendVertexMessage()
  const [textAreaValue, setTextAreaValue] = React.useState<string>('')
  const { messageThread, query, exploreParams } = useSelector(
    (state: RootState) => state.assistant,
  )
  const [isSendingMessage, setIsSendingMessage] = React.useState<boolean>(false)
  const endOfMessagesRef = useRef<HTMLDivElement>(null) // Ref for the last message

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messageThread]) // Dependency on messageThread so it triggers on update

  const onSubmitMessage = useCallback(async () => {
    const prompt = textAreaValue.trim()

    const promptList = [query]
    messageThread.forEach((message) => {
      if (message.actor === 'user' && message.intent === 'exploreRefinement') {
        promptList.push(message.message)
      }
    })
    promptList.push(prompt)
    setIsSendingMessage(true)
    setTextAreaValue('')

    const [promptSummary, isSummary] =
      await Promise.all([
        summarizePrompts(promptList),
        isSummarizationPrompt(prompt),
      ])
    const newExploreParams = await generateExploreParams(promptSummary)
    setIsSendingMessage(false)

    dispatch(
      addMessage({
        message: textAreaValue,
        actor: 'user',
        createdAt: Date.now(),
        intent: isSummary ? 'summarize' : 'exploreRefinement',
        type: 'text',
      }),
    )
    
    if (isSummary) {
      dispatch(
        addMessage({
          exploreParams: exploreParams,
          actor: 'system',
          createdAt: Date.now(),
          type: 'summarize',
        }),
      )
    } else {
      dispatch(setExploreParams(newExploreParams))

      dispatch(
        addMessage({
          exploreParams: newExploreParams,
          summarizedPrompt: promptSummary,
          actor: 'system',
          createdAt: Date.now(),
          type: 'explore',
        }),
      )
    }
  }, [messageThread, textAreaValue, query, generateExploreParams])

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setTextAreaValue(e.currentTarget.value)
  }

  const userMessage = 'Generate an explore for me: \n\n `' + query + '`'

  return (
    <SpaceVertical width={'100%'}>
      <SpaceVertical gap="u2">
        <Message message={userMessage} actor="user" createdAt={Date.now()} />
        {messageThread.map((message, index) => {
          if (message.type === 'explore') {
            return <ExploreMessage key={index} exploreParams={message.exploreParams} prompt={message.summarizedPrompt} />
          } else if (message.type === 'summarize') {
            return <SummaryMessage key={index} exploreParams={message.exploreParams} />
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
        {isSendingMessage && (
          <Space justify="end">
            <Spinner size={20} color={'key'} />
          </Space>
        )}
        <div ref={endOfMessagesRef} /> {/* Ref for the last message */}
      </SpaceVertical>

      <div className={styles.chatInput}>
        <div className={styles.inputContainer}>
          <textarea
            onKeyDown={(e) => {
              // nativeEvent.code check to determine if enter press is for submission or for accepting japanese kanji character
              if(e.key === 'Enter' && e.keyCode !== 229 ) {
                onSubmitMessage()
              }
            }}
            disabled={isSendingMessage}
            value={textAreaValue}
            onChange={handleChange}
            onInput={(e: any) => {
              e.target.style.height = 'auto'
              e.target.style.height = `${e.target.scrollHeight}px`
            }}
          />
          <button disabled={isSendingMessage} onClick={onSubmitMessage}>
            <Send />
          </button>
        </div>
      </div>
    </SpaceVertical>
  )
}

export default Chat
