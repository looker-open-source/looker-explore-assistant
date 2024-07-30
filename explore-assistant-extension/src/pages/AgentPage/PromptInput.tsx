import { Send } from '@material-ui/icons'
import React, { useState, useRef } from 'react'

const PromptInput = () => {
  const [inputText, setInputText] = useState('')
  const [isAnimating, setIsAnimating] = useState(false)
  const inputRef = useRef(null)

  const handleInputChange = (e: any) => {
    setInputText(e.target.value)
  }

  const handleSubmit = () => {
    if (inputText.trim()) {
      setIsAnimating(true)
      // Simulate processing time
      setTimeout(() => {
        setIsAnimating(false)
        setInputText('')
      }, 2000)
    }
  }

  const handleKeyPress = (e: any) => {
    if (e.key === 'Enter') {
      handleSubmit()
    }
  }
  return (
    <div className="max-w-3xl mx-auto mt-4">
      <div className="relative flex items-center bg-[rgb(240,244,249)] rounded-full p-2">
        <input
          ref={inputRef}
          type="text"
          value={inputText}
          onChange={handleInputChange}
          onKeyDown={handleKeyPress}
          placeholder="Enter a prompt here"
          className="flex-grow bg-transparent text-black-300 placeholder-gray-400 outline-none pl-4"
        />
        <div className="flex items-center space-x-2">
          {inputText ? (
            <button
              onClick={handleSubmit}
              className={`p-2 text-white bg-blue-500 rounded-full transition-all duration-300 ease-in-out ${
                isAnimating ? 'animate-spin' : ''
              }`}
            >
              {isAnimating ? (
                <div className="w-5 h-5 border-t-2 border-white rounded-full animate-spin"></div>
              ) : (
                <Send />
              )}
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              className={`p-2 text-gray-600 hover:bg-gray-200 hover:text-gray-800 rounded-full transition-all duration-300 ease-in-out ${
                isAnimating ? 'animate-spin' : ''
              }`}
            >
              <Send />
            </button>
          )}
        </div>
      </div>
      <p className="text-xs text-gray-500 mt-2 text-center">
        Gemini may display inaccurate info, including about people, so double-check its responses.
      </p>
    </div>
  )
}

export default PromptInput
