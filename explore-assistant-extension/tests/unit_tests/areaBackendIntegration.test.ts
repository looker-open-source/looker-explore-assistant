// Tests for area selector backend integration

describe('Area Selector Backend Integration', () => {
  describe('restrictedExploreKeys logic', () => {
    it('should prioritize selectedExplores over area-wide restrictions', () => {
      const getRestrictedExploreKeys = (
        selectedArea: string | null,
        selectedExplores: string[],
        availableAreas: any[]
      ) => {
        // If specific explores are selected, use those
        if (selectedExplores && selectedExplores.length > 0) {
          return selectedExplores
        }
        
        // If an area is selected but no specific explores, use all explores from that area
        if (selectedArea) {
          const area = availableAreas.find(a => a.area === selectedArea)
          return area ? area.explore_keys : []
        }
        
        // No restrictions
        return []
      }

      const mockAreas = [
        {
          area: 'Sales',
          explore_keys: ['ecommerce:order_items', 'ecommerce:orders', 'ecommerce:customers'],
          explore_details: {}
        }
      ]

      // Test specific explores selected
      const result1 = getRestrictedExploreKeys('Sales', ['ecommerce:order_items'], mockAreas)
      expect(result1).toEqual(['ecommerce:order_items'])

      // Test area selected but no specific explores
      const result2 = getRestrictedExploreKeys('Sales', [], mockAreas)
      expect(result2).toEqual(['ecommerce:order_items', 'ecommerce:orders', 'ecommerce:customers'])

      // Test no area selected
      const result3 = getRestrictedExploreKeys(null, [], mockAreas)
      expect(result3).toEqual([])

      // Test multiple specific explores
      const result4 = getRestrictedExploreKeys('Sales', ['ecommerce:order_items', 'ecommerce:orders'], mockAreas)
      expect(result4).toEqual(['ecommerce:order_items', 'ecommerce:orders'])
    })

    it('should handle missing area data gracefully', () => {
      const getRestrictedExploreKeys = (
        selectedArea: string | null,
        selectedExplores: string[],
        availableAreas: any[]
      ) => {
        if (selectedExplores && selectedExplores.length > 0) {
          return selectedExplores
        }
        
        if (selectedArea) {
          const area = availableAreas.find(a => a.area === selectedArea)
          return area ? area.explore_keys : []
        }
        
        return []
      }

      const result = getRestrictedExploreKeys('NonExistentArea', [], [])
      expect(result).toEqual([])
    })
  })

  describe('payload construction for backend', () => {
    it('should construct correct payload with area restrictions', () => {
      const constructPayload = (
        prompt: string,
        conversationId: string,
        promptList: string[],
        restrictedExploreKeys: string[]
      ) => {
        const payload: any = {
          prompt,
          conversation_id: conversationId,
          prompt_list: promptList
        }

        if (restrictedExploreKeys && restrictedExploreKeys.length > 0) {
          payload.restricted_explore_keys = restrictedExploreKeys
        }

        return payload
      }

      const payload1 = constructPayload(
        'Show me sales data',
        'conv123',
        ['Show me sales data'],
        ['ecommerce:orders']
      )

      expect(payload1).toEqual({
        prompt: 'Show me sales data',
        conversation_id: 'conv123',
        prompt_list: ['Show me sales data'],
        restricted_explore_keys: ['ecommerce:orders']
      })

      const payload2 = constructPayload(
        'Show me data',
        'conv456',
        ['Show me data'],
        []
      )

      expect(payload2).toEqual({
        prompt: 'Show me data',
        conversation_id: 'conv456',
        prompt_list: ['Show me data']
      })
      expect(payload2.restricted_explore_keys).toBeUndefined()
    })
  })

  describe('backend response handling', () => {
    it('should handle explore determination with restrictions', () => {
      const mockResponse = {
        explore_key: 'ecommerce:orders',
        explore_params: { limit: 100 },
        summarized_prompt: 'Show order data',
        message_type: 'explore'
      }

      const handleBackendResponse = (response: typeof mockResponse, restrictedKeys: string[]) => {
        // Validate that the returned explore is within restrictions
        if (restrictedKeys.length > 0 && !restrictedKeys.includes(response.explore_key)) {
          console.warn(`Backend returned explore ${response.explore_key} which is not in restricted keys:`, restrictedKeys)
        }

        return {
          exploreKey: response.explore_key,
          exploreParams: response.explore_params,
          summarizedPrompt: response.summarized_prompt,
          messageType: response.message_type
        }
      }

      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation()

      // Valid case
      const result1 = handleBackendResponse(mockResponse, ['ecommerce:orders', 'ecommerce:order_items'])
      expect(result1.exploreKey).toBe('ecommerce:orders')
      expect(consoleSpy).not.toHaveBeenCalled()

      // Invalid case
      const result2 = handleBackendResponse(mockResponse, ['marketing:campaigns'])
      expect(result2.exploreKey).toBe('ecommerce:orders')
      expect(consoleSpy).toHaveBeenCalledWith(
        'Backend returned explore ecommerce:orders which is not in restricted keys:',
        ['marketing:campaigns']
      )

      // No restrictions
      const result3 = handleBackendResponse(mockResponse, [])
      expect(result3.exploreKey).toBe('ecommerce:orders')

      consoleSpy.mockRestore()
    })
  })

  describe('conversation context with areas', () => {
    it('should include area context in conversation messages', () => {
      const createAreaContextMessage = (area: string | null, selectedExplores: string[]) => {
        if (!area) return null

        if (selectedExplores.length > 0) {
          const exploreNames = selectedExplores
            .map(key => key.split(':')[1]?.replace(/_/g, ' '))
            .join(', ')
          return `Now focusing on: ${exploreNames} for this conversation.`
        }

        return `Now focusing on the "${area}" area for this conversation.`
      }

      expect(createAreaContextMessage('Sales', [])).toBe('Now focusing on the "Sales" area for this conversation.')
      
      expect(createAreaContextMessage('Sales', ['ecommerce:order_items', 'ecommerce:orders']))
        .toBe('Now focusing on: order items, orders for this conversation.')

      expect(createAreaContextMessage(null, [])).toBe(null)
    })

    it('should format explore names correctly for messages', () => {
      const formatExploreNamesForMessage = (exploreKeys: string[]) => {
        return exploreKeys
          .map(key => key.split(':')[1]?.replace(/_/g, ' '))
          .filter(name => name) // Remove any undefined names
          .join(', ')
      }

      expect(formatExploreNamesForMessage(['ecommerce:order_items', 'ecommerce:orders']))
        .toBe('order items, orders')

      expect(formatExploreNamesForMessage(['marketing:user_events']))
        .toBe('user events')

      expect(formatExploreNamesForMessage(['malformed']))
        .toBe('')

      expect(formatExploreNamesForMessage([])).toBe('')
    })
  })
})
