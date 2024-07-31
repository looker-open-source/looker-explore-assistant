import { Chip, Section, Spinner } from '@looker/components'
import React, { useEffect } from 'react'
import Message from './Message'
import useSendVertexMessage from '../../hooks/useSendVertexMessage'
import MarkdownText from './MarkdownText'

interface SummaryMessageProps {
  queryArgs: string
}

const SummaryMessage = ({ queryArgs }: SummaryMessageProps) => {
  const [loading, setLoading] = React.useState<boolean>(true)
  const [summary, setSummary] = React.useState<string>('')

  const { summarizeExplore } = useSendVertexMessage()

  useEffect(() => {
    const fetchSummary = async () => {
      const response = await summarizeExplore(queryArgs)
      if (!response) {
        setSummary('There was an error summarizing the data')
      } else {
        setSummary(response)
      }
      setLoading(false)
    }
    fetchSummary()
  }, [])
  console.log(summary)
  return (
    <Message actor="system" createdAt={Date.now()}>
      <Section my={'u2'}>
        <Chip disabled>Summary</Chip>
        {loading ? (
          <Spinner size={20} my={'u2'} />
        ) : (
          <>
            <div className="">
              <MarkdownText text={summary} />
          </div>
          </>
        )}
      </Section>
    </Message>
  )
}

export default SummaryMessage
