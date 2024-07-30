import React, { useState } from 'react'
import PromptInput from './PromptInput'
import Sidebar from './Sidebar'

import './style.css'
import PromptExamples from './PromptExamples'

const AgentPage = () => {
  const [expanded, setExpanded] = useState(false)

  const toggleDrawer = () => {
    setExpanded(!expanded)
  }
  return (
    <div className="page-container flex h-screen">
      <Sidebar expanded={expanded} toggleDrawer={toggleDrawer} />

      <main
        className={`flex-grow flex flex-col transition-all duration-300 ${
          expanded ? 'ml-80' : 'ml-16'
        } p-4 h-screen`}
      >
        <div className="flex-grow p-4">
          <div className="flex flex-col space-y-4 mx-auto max-w-2xl p-4">
            <h1 className="text-5xl font-bold">
              <span
                style={{
                  color: 'transparent',
                  backgroundSize: '400% 100%',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  background:
                    'linear-gradient(74deg, #4285f4 0%, #9b72cb 9%, #d96570 20%, #d96570 24%, #9b72cb 35%, #4285f4 44%, #9b72cb 50%, #d96570 56%, #e9eef6 75%, #e9eef6 100%)',
                }}
              >
                Hello.
              </span>
            </h1>
            <h1 className="text-5xl text-gray-400">
              How can I help you today?
            </h1>
          </div>

          <div className="flex justify-center items-center mt-16">
            <PromptExamples />
          </div>

        </div>
        <div className="mt-4">
          <PromptInput />
        </div>
      </main>
    </div>
  )
}

export default AgentPage
