import React from 'react'
import ReactDOM from 'react-dom'
import { ExtensionProvider } from '@looker/extension-sdk-react'
import { ComponentsProvider, Spinner, Flex } from '@looker/components'
import { App } from './App'

const getRoot = () => {
  const id = 'extension-root'
  const existingRoot = document.getElementById(id)
  if (existingRoot) return existingRoot
  const root = document.createElement('div')
  root.setAttribute('id', id)
  root.style.height = '100vh'
  root.style.display = 'flex'
  document.body.style.margin = '0'
  document.body.appendChild(root)
  return root
}

const render = (Component: typeof App) => {
  const root = getRoot()
  const loading = (
    <Flex width="100%" height="90%" alignItems="center" justifyContent="center">
      <Spinner color="black" />
    </Flex>
  )

  ReactDOM.render(
    <ComponentsProvider
      themeCustomizations={{
        colors: { key: '#1A73E8' },
        defaults: { externalLabel: false },
      }}
    >
      <ExtensionProvider
        loadingComponent={loading}
        requiredLookerVersion=">=21.0"
      >
        <Component />
      </ExtensionProvider>
    </ComponentsProvider>,
    root
  )
}

window.addEventListener('DOMContentLoaded', async () => {
  render(App)
})

// Allow hot module reload
if (module.hot) {
  module.hot.accept('./App.tsx', () => {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const NextApp = require('./App.tsx').default
    render(NextApp)
  })
}
