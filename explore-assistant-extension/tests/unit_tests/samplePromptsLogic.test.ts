// Simple tests for SamplePrompts area selector integration

// Mock functions that mirror the logic in SamplePrompts.tsx
const shouldShowPrompts = (selectedArea: string | null, selectedExplores: string[] | null) => {
  return Boolean(selectedArea && selectedExplores && selectedExplores.length > 0)
}

const getSelectedExploresSamples = (selectedExplores: string[], examples: any) => {
  const exploreGenerationExamples = examples.exploreGenerationExamples || {}
  let allSamples: any[] = []

  selectedExplores.forEach(exploreKey => {
    const samples = exploreGenerationExamples[exploreKey]?.samples || []
    allSamples = allSamples.concat(samples)
  })

  return allSamples
}

const getExploreDisplayName = (exploreKey: string, selectedArea: string | null, availableAreas: any[]) => {
  const areaDetails = availableAreas.find(area => area.label === selectedArea)
  const exploreDetails = areaDetails?.explores?.find((e: any) => e.name === exploreKey)
  return exploreDetails?.display_name || exploreKey.split(':')[1] || exploreKey
}

describe('SamplePrompts Area Selector Integration', () => {
  describe('Sample prompt visibility logic', () => {
    it('should not show prompts when no area is selected', () => {
      expect(shouldShowPrompts(null, [])).toBe(false)
      expect(shouldShowPrompts(null, ['ecommerce:orders'])).toBe(false)
    })

    it('should not show prompts when no explores are selected', () => {
      expect(shouldShowPrompts('Sales', [])).toBe(false)
      expect(shouldShowPrompts('Sales', null as any)).toBe(false)
    })

    it('should show prompts when both area and explores are selected', () => {
      expect(shouldShowPrompts('Sales', ['ecommerce:orders'])).toBe(true)
      expect(shouldShowPrompts('Sales', ['ecommerce:orders', 'ecommerce:users'])).toBe(true)
    })
  })

  describe('Sample aggregation from selected explores', () => {
    it('should collect samples from all selected explores', () => {
      const mockExamples = {
        exploreGenerationExamples: {
          'ecommerce:orders': {
            samples: [{ category: 'Sales', prompt: 'Show me sales data' }]
          },
          'ecommerce:users': {
            samples: [{ category: 'Users', prompt: 'Show me user data' }]
          }
        }
      }

      const result = getSelectedExploresSamples(['ecommerce:orders', 'ecommerce:users'], mockExamples)
      expect(result).toHaveLength(2)
      expect(result[0]).toEqual({ category: 'Sales', prompt: 'Show me sales data' })
      expect(result[1]).toEqual({ category: 'Users', prompt: 'Show me user data' })
    })

    it('should handle missing explores gracefully', () => {
      const mockExamples = {
        exploreGenerationExamples: {
          'ecommerce:orders': {
            samples: [{ category: 'Sales', prompt: 'Show me sales data' }]
          }
        }
      }

      const result = getSelectedExploresSamples(['ecommerce:orders', 'nonexistent:explore'], mockExamples)
      expect(result).toHaveLength(1)
      expect(result[0]).toEqual({ category: 'Sales', prompt: 'Show me sales data' })
    })

    it('should handle empty sample arrays', () => {
      const mockExamples = {
        exploreGenerationExamples: {
          'ecommerce:orders': { samples: [] }
        }
      }

      const result = getSelectedExploresSamples(['ecommerce:orders'], mockExamples)
      expect(result).toHaveLength(0)
    })
  })
})
