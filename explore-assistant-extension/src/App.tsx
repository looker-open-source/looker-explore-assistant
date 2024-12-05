import React, { useEffect, useState } from 'react'
import { hot } from 'react-hot-loader/root'
import { Route, Switch, Redirect } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import { RootState } from './store'
import { useLookerFields } from './hooks/useLookerFields'
import { useBigQueryExamples } from './hooks/useBigQueryExamples'
import useSendVertexMessage from './hooks/useSendVertexMessage'
import AgentPage from './pages/AgentPage'
import SettingsModal from './pages/AgentPage/Settings'

const ExploreApp = () => {
  const dispatch = useDispatch()
  const { settings, bigQueryTestSuccessful, vertexTestSuccessful } = useSelector((state: RootState) => state.assistant)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isFetching, setIsFetching] = useState(false)

  useLookerFields()
  const { testBigQuerySettings } = useBigQueryExamples()
  const { testVertexSettings } = useSendVertexMessage()

  useEffect(() => {
    const missingSettings = Object.values(settings).some(setting => !setting.value)
    if (missingSettings) {
      setIsSettingsOpen(true)
    } 
  }, [settings])

  useEffect(() => {
    const runTests = async () => {
      testBigQuerySettings()
      testVertexSettings()
    }
    if (!bigQueryTestSuccessful || !vertexTestSuccessful) {
      runTests()
    }
  }, [testBigQuerySettings, testVertexSettings, bigQueryTestSuccessful, vertexTestSuccessful, dispatch, settings.useCloudFunction.value, settings])

  // useEffect(() => {
  //   if (bigQueryTestSuccessful && vertexTestSuccessful && !isFetching) {
  //     setIsFetching(true)
  //     // Fetch BigQuery examples only if settings are tested and valid
  //     getExamplesAndSamples().then(()=>setIsFetching(false)).catch((error) => {
  //       console.error('Error fetching BigQuery examples:', error)
  //       setIsSettingsOpen(true)
       
  //     })
  //   }
  // }, [bigQueryTestSuccessful, vertexTestSuccessful, dispatch])

  return (
    <>
      <SettingsModal
        open={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
      {!isSettingsOpen && bigQueryTestSuccessful && vertexTestSuccessful && (
        <Switch>
          <Route path="/index" exact>
            <AgentPage />
          </Route>
          <Route>
            <Redirect to="/index" />
          </Route>
        </Switch>
      )}
    </>
  )
}

export const App = hot(ExploreApp)
