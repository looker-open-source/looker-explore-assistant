import { Chip, Section, Spinner } from '@looker/components'
import React, { useEffect } from 'react'
import Message from './Message'
import useSendVertexMessage from '../../hooks/useSendVertexMessage'
import MarkdownText from './MarkdownText'
import { ExploreParams } from '../../slices/assistantSlice'

interface SummaryMessageProps {
  exploreParams: ExploreParams | null
}

const SummaryMessage = ({ exploreParams }: SummaryMessageProps) => {
  const [loading, setLoading] = React.useState<boolean>(true)
  const [summary, setSummary] = React.useState<string>('')

  const { summarizeExplore } = useSendVertexMessage()

  useEffect(() => {
    const fetchSummary = async () => {
      if (!exploreParams) return
      const response = await summarizeExplore(exploreParams)
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
