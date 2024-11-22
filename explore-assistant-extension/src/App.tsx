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
import { setHasTestedSettings } from './slices/assistantSlice'

const ExploreApp = () => {
  const dispatch = useDispatch()
  const { settings, hasTestedSettings } = useSelector((state: RootState) => state.assistant)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)

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
      const bigQueryResult = await testBigQuerySettings()
      const vertexResult = await testVertexSettings()
      if (!bigQueryResult || !vertexResult) {
        setIsSettingsOpen(true)
      }
      dispatch(setHasTestedSettings(true))
    }
    if (!hasTestedSettings) {
      runTests()
    }
  }, [testBigQuerySettings, testVertexSettings, hasTestedSettings, dispatch])

  return (
    <>
      <SettingsModal
        open={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
      {!isSettingsOpen && (
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
