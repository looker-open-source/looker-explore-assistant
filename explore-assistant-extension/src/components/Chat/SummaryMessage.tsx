import { Chip, Section, Spinner } from '@looker/components'
import React, { useEffect } from 'react'
import Message from './Message'
import useSendVertexMessage from '../../hooks/useSendVertexMessage'
import MarkdownText from './MarkdownText'
import { useDispatch } from 'react-redux'
import {
  SummarizeMesage,
  updateLastHistoryEntry,
  updateSummaryMessage,
} from '../../slices/assistantSlice'

interface SummaryMessageProps {
  message: SummarizeMesage
}

const SummaryMessage = ({ message }: SummaryMessageProps) => {
  const queryArgs = message.exploreUrl

  const dispatch = useDispatch()
  const [loading, setLoading] = React.useState<boolean>(true)
  const [summary, setSummary] = React.useState<string>('')

  const { summarizeExplore } = useSendVertexMessage()

  useEffect(() => {
    if (message.summary) {
      setSummary(message.summary)
      setLoading(false)
      return
    }

    const fetchSummary = async () => {
      const response = await summarizeExplore(queryArgs)
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

      setLoading(false)
    }

    fetchSummary()
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
