const webpack = require('webpack')
const config = require('./webpack.develop.js')

// Create a minimal webpack compiler
const compiler = webpack(config)

// Start the server with minimal memory usage
const server = require('webpack-dev-server')
const devServer = new server({
  ...config.devServer,
  client: {
    overlay: false,
    logging: 'none'
  },
  devMiddleware: {
    stats: 'errors-only'
  }
}, compiler)

console.log('Starting minimal webpack dev server...')
server.listen(8080, 'localhost', (err) => {
  if (err) {
    console.error('Failed to start server:', err)
    process.exit(1)
  }
  console.log('✅ Server started at https://localhost:8080')
})

// Handle memory pressure
process.on('warning', (warning) => {
  if (warning.name === 'MaxListenersExceededWarning') {
    console.log('Warning: Too many listeners, this might indicate memory issues')
  }
})
