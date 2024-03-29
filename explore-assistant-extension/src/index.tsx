/*

MIT License

Copyright (c) 2023 Looker Data Sciences, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

*/

import React from 'react'
import ReactDOM from 'react-dom'
import { ComponentsProvider } from '@looker/components'
import { App } from './App'
import { Provider } from 'react-redux'
import { store } from './store'

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
  ReactDOM.render(
    <>
      <Provider store={store}>
        <Component />
      </Provider>
    </>,
    root,
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
