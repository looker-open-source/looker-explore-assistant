import React, { useEffect, useState } from 'react'
import { hot } from 'react-hot-loader/root'
import { HashRouter as Router, Route, Switch, Redirect } from 'react-router-dom'

import LandingPage from './pages/LandingPage'
import ExploreAssistantPage from './pages/ExploreAssistantPage'
import ExploreChatPage from './pages/ExploreChatPage'
import { ExtensionProvider } from '@looker/extension-sdk-react'
import { ComponentsProvider, Spinner } from '@looker/components'
import { useDispatch } from 'react-redux'
import {
  setExploreId,
  setExploreName,
  setModelName,
} from './slices/assistantSlice'

const ExploreApp = () => {
  const dispatch = useDispatch()
  const LOOKER_EXPLORE_ID =
    `${process.env.LOOKER_MODEL}/${process.env.LOOKER_EXPLORE}` || ''
  useEffect(() => {
    dispatch(setExploreId(LOOKER_EXPLORE_ID))
    dispatch(setModelName(process.env.LOOKER_MODEL || ''))
    dispatch(setExploreName(process.env.LOOKER_EXPLORE || ''))
  }, [])
  return (
    <ExtensionProvider
      loadingComponent={<Spinner />}
      requiredLookerVersion=">=21.0"
    >
      <ComponentsProvider
        themeCustomizations={{
          colors: { key: '#1A73E8' },
          defaults: { externalLabel: false },
        }}
      >
        <Router>
          <Switch>
            <Route path="/" exact>
              <LandingPage />
            </Route>
            <Route path="/assistant">
              <ExploreAssistantPage />
            </Route>
            <Route path="/chat">
              <ExploreChatPage />
            </Route>
            <Route>
              <Redirect to="/" />
            </Route>
          </Switch>
        </Router>
      </ComponentsProvider>
    </ExtensionProvider>
  )
}

export const App = hot(ExploreApp)
