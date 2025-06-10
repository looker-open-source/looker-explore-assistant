import { Chip, Section, Spinner } from '@looker/components'
import React, { useEffect } from 'react'
import Message from './Message'
import useSendCloudRunMessage from '../../hooks/useSendCloudRunMessage'
import MarkdownText from './MarkdownText'
import { ExploreParams, SummarizeMesage, updateLastHistoryEntry, updateSummaryMessage } from '../../slices/assistantSlice'
import { useDispatch } from 'react-redux'

interface SummaryMessageProps {
  message: SummarizeMesage
  onSummaryComplete: () => void
}

const SummaryMessage = ({ message, onSummaryComplete }: SummaryMessageProps) => {
  const dispatch = useDispatch()
  const [loading, setLoading] = React.useState<boolean>(true)
  const [summary, setSummary] = React.useState<string>('')

  const { summarizeData } = useSendCloudRunMessage()

  useEffect(() => {
    let isMounted = true

    if (message.summary) {
      setSummary(message.summary)
      setLoading(false)
      return
    }

    const fetchSummary = async () => {
      const conversationId = `summary_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      const response = await summarizeData(message.exploreParams, conversationId)
      if (!response) {
        setSummary('There was an error summarizing the data')
      } else {
        setSummary(response)

        // save to the store
        dispatch(
          updateSummaryMessage({ uuid: message.uuid, summary: response }),
        )

        // update the history with the current contents of the thread
        dispatch(updateLastHistoryEntry())
      }

      // call the parent component to scroll to the bottom
      onSummaryComplete()

      if (isMounted) {
        setLoading(false)
      }
    }

    fetchSummary()

    return () => {
      isMounted = false
    }
  }, [message])

  return (
    <Message actor="system" createdAt={Date.now()}>
      <Section my={'u2'}>
        <Chip disabled>Summary</Chip>
        {loading ? (
          <Spinner size={20} my={'u2'} />
        ) : (
          <>
            <div className="text-sm mt-6">
              <MarkdownText text={summary} />
            </div>
          </>
        )}
      </Section>
    </Message>
  )
}

export default SummaryMessage
