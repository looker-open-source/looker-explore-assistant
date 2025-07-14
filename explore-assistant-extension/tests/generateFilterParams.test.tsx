import React from 'react'
import { renderHook, act } from '@testing-library/react-hooks'
import useSendCloudRunMessage from '../src/hooks/useSendCloudRunMessage'
import dotenv from 'dotenv'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { Provider } from 'react-redux'
import { ErrorBoundary } from 'react-error-boundary'
import { setSemanticModels } from '../src/slices/assistantSlice'
import { store } from '../src/store'

dotenv.config()

const mockCore40SDK = {
  ok: jest.fn(),
  create_sql_query: jest.fn(),
  run_sql_query: jest.fn(),
  create_query: jest.fn(),
  run_query: jest.fn(),
}

const mockExtensionContextValue = {
  core40SDK: mockCore40SDK,
  route: jest.fn(),
  visualizationSDK: jest.fn(),
  tileHostData: jest.fn(),
  tileSDK: jest.fn(),
  extensionSDK: jest.fn(),
}

// Fallback render function for ErrorBoundary
const FallbackRender = ({ error }: { error: Error }) => (
  <div>Error: {error.message}</div>
)

describe('useSendCloudRunMessage', () => {
  let result: ReturnType<typeof useSendCloudRunMessage>

  const dimensions =  [
    {
      name: 'orders.created_date',
      type: 'string',
      description: 'desc1',
      tags: ['tag1'],
    },
  ]

  const measures = [
    {
      name: 'orders.sum_revenue',
      type: 'number',
      description: 'The sum of the revenue',
      tags: ['tag1'],
    },
  ]
  const semanticModels = {
    'ecommerce:orders': {
      exploreKey: 'ecommerce:orders',
      modelName: 'ecommerce',
      exploreId: 'orders',
      dimensions,
      measures,
    }
  }

  beforeEach(async () => {
    // Set initial dimensions and measures
    await act(async () => {
      store.dispatch(setSemanticModels(semanticModels))
    })

    const { result: hookResult } = renderHook(() => useSendCloudRunMessage(), {
      wrapper: ({ children }) => (
        <Provider store={store}>
          {/* @ts-ignore */}
          <ExtensionContext.Provider value={mockExtensionContextValue}>
            <ErrorBoundary fallbackRender={FallbackRender}>
              {children}
            </ErrorBoundary>
          </ExtensionContext.Provider>
        </Provider>
      ),
    })
    result = hookResult.current
  })

  // Note: This test was for the removed useSendVertexMessage hook
  // The Cloud Run hook doesn't have generateFilterParams method
  test.skip('generateFilterParams test disabled - method removed with useSendVertexMessage hook', async () => {
    // Test disabled as generateFilterParams was specific to the removed vertex hook
    expect(true).toBe(true)
  })

  /*
  test('generateFilterParams should return correct filter parameters', async () => {
    const prompt = 'Show me the sales data for this year'

    await act(async () => {
      const filterParams = await result.generateFilterParams(
        prompt,
        dimensions,
        measures,
      )

      expect(
        Object.prototype.hasOwnProperty.call(
          filterParams,
          'orders.created_date',
        ),
      ).toBe(true)
      expect(filterParams['orders.created_date']).toContain('this year')
    })
  })
  */

  // Additional test cases can be added here
})
