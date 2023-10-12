/*

 Copyright 2023 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

 */

const fs = require('fs')
const path = require('path')
const webpack = require('webpack')
const dotenv = require('dotenv')

const BundleAnalyzerPlugin =
  require('webpack-bundle-analyzer').BundleAnalyzerPlugin

// Create .env file if it does not exist
if (!fs.existsSync('.env')) {
  fs.copyFileSync('.env_example', '.env')
}
dotenv.config()
if (!process.env.POSTS_SERVER_URL) {
  // webpack 5 is stricter about environment variables. The POSTS_SERVER_URL
  // environment variable was not mentioned in the README so default it for
  // those developers who may have created a .env file without the variable.
  process.env.POSTS_SERVER_URL = 'http://127.0.0.1:3000'
}

const PATHS = {
  app: path.join(__dirname, 'src/index.tsx'),
}

module.exports = {
  entry: {
    app: PATHS.app,
  },
  output: {
    path: __dirname + '/dist',
    filename: 'bundle.js',
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx|ts|tsx)$/,
        loader: 'babel-loader',
        exclude: /node_modules/,
        include: /src/,
        sideEffects: false,
      },
      {
        test: /\.css$/i,
        use: ["style-loader", "css-loader"],
      },
      {
        test: /\.(png|jpe?g|gif)$/i,
        use: [
          {
            loader: 'file-loader',
          },
        ],
      },
    ],
  },
  resolve: {
    extensions: ['.tsx', '.ts', '.js'],
    fallback: { buffer: false },
  },
  devtool: 'source-map',
  plugins: [
    new BundleAnalyzerPlugin({
      analyzerMode: process.env.ANALYZE_MODE || 'disabled',
    }),
    new webpack.EnvironmentPlugin(['VERTEX_AI_ENDPOINT','LOOKER_EXPLORE_ID','LOOKER_MODEL','LOOKER_EXPLORE']),
  ],
}
