import React from 'react'
import { Container, Typography, Box } from '@material-ui/core'
import FeedbackButton from '../components/Feedback/FeedbackButton'

const FeedbackTestPage: React.FC = () => {
  const sampleExploreParams = {
    model: "ecommerce",
    view: "order_items",
    fields: ["products.brand", "order_items.total_sale_price"],
    filters: { "order_items.created_date": "2023 Q2" },
    sorts: ["order_items.total_sale_price desc"],
    limit: 100
  }

  return (
    <Container maxWidth="md">
      <Box p={4}>
        <Typography variant="h4" gutterBottom>
          Feedback System Test
        </Typography>
        
        <Typography variant="body1" paragraph>
          This page tests the new explicit feedback mechanism for Looker query responses.
        </Typography>

        <Box mt={4} p={3} border={1} borderColor="grey.300" borderRadius={2}>
          <Typography variant="h6" gutterBottom>
            Sample Query Response
          </Typography>
          <Typography variant="body2" color="textSecondary" gutterBottom>
            Query: "Show me sales by brand for Q2 2023"
          </Typography>
          <pre style={{ fontSize: '12px', background: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
            {JSON.stringify(sampleExploreParams, null, 2)}
          </pre>
          
          <Box mt={2}>
            <Typography variant="subtitle2" gutterBottom>
              Provide Feedback:
            </Typography>
            <FeedbackButton
              exploreId="ecommerce:order_items"
              originalPrompt="Show me sales by brand for Q2 2023"
              generatedParams={sampleExploreParams}
              shareUrl="https://example.looker.com/explore/ecommerce/order_items"
              size="medium"
              onFeedbackSubmitted={(feedbackType, success) => {
                console.log(`Feedback submitted: ${feedbackType}, Success: ${success}`)
                alert(`Feedback "${feedbackType}" ${success ? 'submitted successfully!' : 'failed to submit.'}`)
              }}
            />
          </Box>
        </Box>

        <Box mt={3}>
          <Typography variant="body2" color="textSecondary">
            Use the feedback buttons above to test the new explicit feedback system.
            Check the console and network tabs for debugging information.
          </Typography>
        </Box>
      </Box>
    </Container>
  )
}

export default FeedbackTestPage
