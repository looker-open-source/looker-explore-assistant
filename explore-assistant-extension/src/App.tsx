import React from 'react'
import { hot } from 'react-hot-loader/root'
import { Route, Switch, Redirect } from 'react-router-dom'
import { useLookerFields } from './hooks/useLookerFields'
import { useBigQueryExamples } from './hooks/useBigQueryExamples'
import AgentPage from './pages/AgentPage'

const ExploreApp = () => {
  // load dimensions, measures and examples into the state
  useLookerFields()
  useBigQueryExamples()

  return (
    <>
        <Switch>
          <Route path="/index" exact>
              <AgentPage />
          </Route>
          <Route>
            <Redirect to="/index" />
          </Route>
        </Switch>
    </>
  )
}

export const App = hot(ExploreApp)
