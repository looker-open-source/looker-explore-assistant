import React from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../store'
import { Box, Card, Section, SpaceVertical, Span } from '@looker/components'

interface PromptHistoryProps {
  handleSubmit: (prompt: string) => void
}
const PromptHistory = ({ handleSubmit }: PromptHistoryProps) => {
  const { history } = useSelector((state: RootState) => state.assistant)

  return (
    <Section scrollWithin>
      <SpaceVertical gap="u2">
        {Object.values(history).reverse().map((item: any, index: number) => {
          return (
            <Card
              width={'100%'}
              border={'ui1'}
              borderRadius={'large'}
              p="u2"
              key={index}
              onClick={() => handleSubmit(item.message)}
            >
              <Box cursor="pointer">
                <Span fontSize={'small'}>{item.message}</Span>
              </Box>
            </Card>
          )
        })}
      </SpaceVertical>
    </Section>
  )
}

export default PromptHistory
