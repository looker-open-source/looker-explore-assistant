import {
  Box,
  Card,
  Heading,
  Paragraph,
  Space,
  SpaceVertical,
  Spinner,
} from '@looker/components'
import React from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../store'

interface SamplePromptsProps {
  handleSubmit: (prompt: string) => void
}

const SamplePrompts = ({ handleSubmit }: SamplePromptsProps) => {
  const {
    exploreId, // Added exploreId to selector
  } = useSelector((state: RootState) => state.assistant)
  // console.log('exploreId: ', exploreId)
  const samples = useSelector(
    (state: any) => state.assistant.exploreSamplesById[exploreId],
  )

  if (!samples) {
    return (
      <Space>
        <SpaceVertical align={'center'}>
          <Spinner color="key" />
        </SpaceVertical>
      </Space>
    )
  }

  return (
    <div>
      {samples.map((item: any, index: number) => (
        <Box
          cursor="pointer"
          key={index}
          onClick={() => {
            handleSubmit(item.prompt)
          }}
        >
          <Card
            border={'ui1'}
            fontSize={'small'}
            m="u1"
            px="u2"
            py="u4"
            style={{ height: 'auto' }}
          >
            <Heading
              fontSize={'small'}
              fontWeight={'semiBold'}
              style={{ color: `${item.color}` }}
            >
              {item.category}
            </Heading>
            <Paragraph mt="u2">{item.prompt}</Paragraph>
          </Card>
        </Box>
      ))}
    </div>
  )
}

export default SamplePrompts
