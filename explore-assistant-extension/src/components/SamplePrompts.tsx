import { Box, Card, Heading, Paragraph } from '@looker/components'
import React from 'react'

interface SamplePromptsProps {
  handleSubmit: (prompt: string) => void,
  exploreId: string
}
const SamplePrompts = ({ handleSubmit,exploreId }: SamplePromptsProps) => {
  const categorizedPrompts = {
    "thelook/order_items": [
      {category: 'Cohorting',prompt: 'Count of Users by first purchase date',color: 'blue'},
      {category: 'Audience Building',prompt:'Users who have purchased more than 100 dollars worth of Calvin Klein products and have purchased in the last 30 days',color: 'green'},
      {category: 'Period Comparison',prompt:'Total revenue by category this year compared to last year in a line chart with year pivoted',color: 'red'}
    ],
    "healthcare_operations/ortho_procedures": [
      {category: 'Patient Groupings',prompt: 'count of patients by facility',color: 'blue'},
      {category: 'Quality of Encounters',prompt:'encounters with an average wait time > 30 minutes because the staff was too busy',color: 'green'},
      {category: 'Period Comparison',prompt:'Total procedural charges by payer July 2020 compared to August 2020 in a line chart with month pivoted',color: 'red'}
    ],
    "gcp_billing_demo/gcp_billing_export": [
      {category: 'Billing Aggregate',prompt: 'Top billed services in the past 2 years.',color: 'blue'},
      {category: 'Time Series',prompt: 'Totaled Billed by month last year',color: 'green'}
    ]
  }
  return (
    <div>
      {categorizedPrompts[exploreId].map((item, index: number) => (
        <Box
          cursor="pointer"
          key={index}
          onClick={() => {
            handleSubmit(item.prompt)
          }}
        >
          <Card border={'ui1'} fontSize={'small'} m="u1" px="u2" py="u4" style={{height:'auto'}}>
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