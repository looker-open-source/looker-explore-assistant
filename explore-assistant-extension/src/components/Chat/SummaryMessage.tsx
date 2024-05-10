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
      setSummary(response)
      setLoading(false)
    }
    fetchSummary()
  }, [])

  return (
    <Message actor="system" createdAt={Date.now()}>
      <Section my={'u2'}>
        <Chip disabled>Summary</Chip>
        {loading ? (
          <Spinner size={20} my={'u2'} />
        ) : (
          <>
            <Section maxHeight={150} scrolling={'auto'} my={'u2'}>
              <MarkdownText text={summary} />
            </Section>
          </>
        )}
      </Section>
    </Message>
  )
}

export default SummaryMessage
