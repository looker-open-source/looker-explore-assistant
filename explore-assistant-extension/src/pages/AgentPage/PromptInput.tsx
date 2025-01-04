import { Send } from '@material-ui/icons'
import React, { useState, useRef, useCallback } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState } from '../../store'
import { setIsChatMode, setQuery } from '../../slices/assistantSlice'
import clsx from 'clsx'

const PromptInput = () => {
  const dispatch = useDispatch()
  const [inputText, setInputText] = useState('')
  const inputRef = useRef(null)

  const { isQuerying } = useSelector((state: RootState) => state.assistant)

  const handleInputChange = (e: any) => {
    setInputText(e.target.value)
  }

  const handleSubmit = useCallback(() => {
    const prompt = inputText.trim()
    if (prompt && !isQuerying) {
      dispatch(setIsChatMode(true))
      dispatch(setQuery(prompt))
    }

    if (!isQuerying) {
      setInputText('')
    }
  }, [isQuerying, inputText])

  const handleKeyPress = (e: any) => {
    if (e.key === 'Enter' && e.keyCode !== 229) {
      handleSubmit()
    }
  }
  return (
    <div className="max-w-3xl mx-auto px-8 pt-4 pb-2 bg-white bg-opacity-80 rounded-md">
      <div className="relative flex items-center bg-[rgb(240,244,249)] rounded-full p-2">
        <input
          ref={inputRef}
          type="text"
          value={inputText}
          onChange={handleInputChange}
          onKeyDown={handleKeyPress}
          disabled={isQuerying}
          placeholder="Enter a prompt here"
          className={`flex-grow bg-transparent placeholder-gray-400 outline-none pl-4 ${
            isQuerying
              ? 'cursor-not-allowed text-gray-500'
              : 'cursor-text text-gray-800'
          }`}
        />
        <div className="flex items-center space-x-2">
          <button
            onClick={handleSubmit}
            disabled={isQuerying}
            className={clsx("p-2 text-white  rounded-full transition-all duration-300 ease-in-out",
              inputText.trim() ? 'bg-blue-500 hover:bg-blue-600' : 'bg-gray-400',
              isQuerying ? 'animate-spin' : ''
            )}
          >
            {isQuerying ? (
              <div className="w-5 h-5 border-t-2 border-white rounded-full animate-spin"></div>
            ) : (
              <Send />
            )}
          </button>
        </div>
      </div>
      <p className="text-xs text-gray-500 my-2 text-center">
        Gemini may display inaccurate info, including about people, so
        double-check its responses.
      </p>
    </div>
  )
}

export default PromptInput
