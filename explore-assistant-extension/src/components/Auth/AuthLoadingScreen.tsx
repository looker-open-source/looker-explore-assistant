import React from 'react'
import { LinearProgress } from '@mui/material'

const AuthLoadingScreen = ({ onAuthClick }: { onAuthClick: () => void }) => {
  return (
    <div className="flex justify-center items-center h-screen">
      <div className="flex flex-col space-y-4 mx-auto max-w-2xl p-4">
        <h1 className="text-5xl font-bold">
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-pink-500 to-violet-500">
            Welcome to Explore Assistant
          </span>
        </h1>
        <h1 className="text-3xl text-gray-400">
          Please authenticate to continue
        </h1>
        <button 
          onClick={onAuthClick}
          className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        >
          Sign in with Google
        </button>
        <div className="max-w-2xl text-blue-300">
          <LinearProgress color="inherit" />
        </div>
      </div>
    </div>
  )
}

export default AuthLoadingScreen