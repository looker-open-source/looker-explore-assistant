import {
  Layout,
  Spinner,
  Space,
  SpaceVertical
} from '@looker/components'
import React, { useEffect } from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../../store'

const ExploreBasePage = ({ children }: { children: React.ReactNode }) => {
  const [loading, setLoading] = React.useState<boolean>(true)
  const { examples } =
    useSelector((state: RootState) => state.assistant)


  useEffect(() => {
    if (
      examples.exploreGenerationExamples.length > 0 &&
      examples.exploreRefinementExamples.length > 0
    ) {
      setLoading(false)
    }
  }, [examples])

  return (
    <Layout height={'100%'} hasAside={true}>
      {loading ? (
        <Space><SpaceVertical align={'center'} ><Spinner color="key" /></SpaceVertical></Space>
      ) : (children)}
    </Layout>
  )
}

export default ExploreBasePage
