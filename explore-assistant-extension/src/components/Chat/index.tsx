import React, { useCallback, useEffect, useRef } from 'react'
import useSendVertexMessage from '../../hooks/useSendVertexMessage'
import { Space, SpaceVertical, Spinner } from '@looker/components'
import { addMessage, setExploreUrl } from '../../slices/assistantSlice'
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
    generateExploreUrl,
    isSummarizationPrompt,
    summarizePrompts,
    isDataQuestionPrompt,
  } = useSendVertexMessage()
  const [textAreaValue, setTextAreaValue] = React.useState<string>('')
  const { messageThread, query, exploreUrl } = useSelector(
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

    const [promptSummary, isSummary, isDataQuestion] =
      await Promise.all([
        summarizePrompts(promptList),
        isSummarizationPrompt(prompt),
        isDataQuestionPrompt(prompt),
      ])
    const newExploreUrl = await generateExploreUrl(promptSummary)
    setIsSendingMessage(false)

    dispatch(
      addMessage({
        message: textAreaValue,
        actor: 'user',
        createdAt: Date.now(),
        intent: isDataQuestion ? 'dataQuestion' : (isSummary ? 'summarize' : 'exploreRefinement'),
        type: 'text',
      }),
    )
    
    if (isSummary) {
      dispatch(
        addMessage({
          exploreUrl: exploreUrl,
          actor: 'system',
          createdAt: Date.now(),
          type: 'summarize',
        }),
      )
    } else {
      dispatch(setExploreUrl(newExploreUrl))

      dispatch(
        addMessage({
          exploreUrl: newExploreUrl,
          summarizedPrompt: promptSummary,
          actor: 'system',
          createdAt: Date.now(),
          type: 'explore',
        }),
      )
    }
  }, [messageThread, textAreaValue, query])

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
            return <ExploreMessage key={index} queryArgs={message.exploreUrl} prompt={message.summarizedPrompt} />
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
            onKeyDown={(e) => e.key === 'Enter' && onSubmitMessage()}
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
