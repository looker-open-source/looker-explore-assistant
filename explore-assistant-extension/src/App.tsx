import React from 'react'
import { hot } from 'react-hot-loader/root'
import {
  BrowserRouter as Router,
  Route,
  Switch,
  Redirect,
} from 'react-router-dom'

import LandingPage from './pages/LandingPage'
import ExploreAssistantPage from './pages/ExploreAssistantPage'

const ExploreApp = () => {
  return (
    <Router>
      <Switch>
        <Route path="/" exact>
          <LandingPage />
        </Route>
        <Route path="/assistant">
          <ExploreAssistantPage />
        </Route>
        <Route>
          <Redirect to="/" />
        </Route>
      </Switch>
    </Router>
  )
}

export const App = hot(ExploreApp)
