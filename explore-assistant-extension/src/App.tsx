import React, { useEffect } from 'react'
import { hot } from 'react-hot-loader/root'
import { Route, Switch, Redirect } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import ExploreAssistantPage from './pages/ExploreAssistantPage'
import ExploreChatPage from './pages/ExploreChatPage'
import { useDispatch } from 'react-redux'
import {
  setExploreId,
  setExploreName,
  setModelName,
} from './slices/assistantSlice'
import { useLookerFields } from './hooks/useLookerFields'
import { useBigQueryExamples } from './hooks/useBigQueryExamples'

const ExploreApp = () => {
  const dispatch = useDispatch()
  const LOOKER_EXPLORE_ID =
    `${process.env.LOOKER_MODEL}/${process.env.LOOKER_EXPLORE}` || ''
  useEffect(() => {
    dispatch(setExploreId(LOOKER_EXPLORE_ID))
    dispatch(setModelName(process.env.LOOKER_MODEL || ''))
    dispatch(setExploreName(process.env.LOOKER_EXPLORE || ''))
  }, [])


  // load dimensions and measures into the state
  useLookerFields()
  useBigQueryExamples()

  return (
    <>
        <Switch>
          <Route path="/index" exact>
              <LandingPage />
          </Route>
          <Route path="/assistant">
              <ExploreAssistantPage />
          </Route>
          <Route path="/chat">
              <ExploreChatPage />
          </Route>
          <Route>
            <Redirect to="/index" />
          </Route>
        </Switch>
    </>
  )
}

export const App = hot(ExploreApp)
