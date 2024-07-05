import { Box, Select } from '@looker/components'
import React from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../store'
import { ExploreMetadata } from '../slices/assistantSlice'
import process from 'process'

interface ExploreSelectProps {
  handleSelect: (value: string) => void
}

const ExploreSelect = ({ handleSelect }: ExploreSelectProps) => {
  const exploreMetadataById = useSelector(
    (state: RootState) => state.assistant.exploreMetadataById,
  )
  const LOOKER_MODEL = process.env.LOOKER_MODEL || ''
  const LOOKER_EXPLORE = process.env.LOOKER_EXPLORE || ''
  const LOOKER_EXPLORE_LABEL = process.env.LOOKER_EXPLORE_LABEL || ''
  // console.log('exploreMetadataById', exploreMetadataById)

  const options = Object.keys(exploreMetadataById).length
    ? Object.keys(exploreMetadataById).map((exploreId) => {
        const metadata: ExploreMetadata = exploreMetadataById[exploreId]
        return {
          description: metadata.description,
          label: metadata.label,
          value: exploreId,
        }
      })
    : [
        {
          description: '',
          label: LOOKER_EXPLORE_LABEL,
          value: `${LOOKER_MODEL}:${LOOKER_EXPLORE}`,
        },
      ]

  return (
    <Box maxWidth={400}>
      <Select
        options={options}
        defaultValue={options[0]?.value}
        onChange={(value) => handleSelect(value)}
        placeholder="Select data domain"
      />
    </Box>
  )
}

export default ExploreSelect
