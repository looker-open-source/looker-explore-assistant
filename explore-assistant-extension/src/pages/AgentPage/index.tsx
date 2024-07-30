import React, { useState } from 'react'
import PromptInput from './PromptInput'
import Sidebar from './Sidebar'

import './style.css'
import SamplePrompts from '../../components/SamplePrompts'
import Chat from '../../components/Chat'
import { ExploreEmbed } from '../../components/ExploreEmbed'
import { RootState } from '../../store'
import { useSelector } from 'react-redux'

const AgentPage = () => {
  const [expanded, setExpanded] = useState(false)

  const { isQuerying } = useSelector((state: RootState) => state.assistant)

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
          {isQuerying ? (
            <div className="">
            <ExploreEmbed />
            <Chat />
          </div>
          ) : (
            <>
            <div className="flex flex-col space-y-4 mx-auto max-w-2xl p-4">
              <h1 className="text-5xl font-bold">
                <span className="bg-clip-text text-transparent  bg-gradient-to-r from-pink-500 to-violet-500">
                  Hello.
                </span>
              </h1>
              <h1 className="text-5xl text-gray-400">
                How can I help you today?
              </h1>
            </div>

            <div className="flex justify-center items-center mt-16">
              <SamplePrompts />
            </div>
          </>
           
          )}
        </div>
        <div className="fixed bottom-0 left-1/2 transform -translate-x-1/2 w-4/5">
          <PromptInput />
        </div>
      </main>
    </div>
  )
}

export default AgentPage
