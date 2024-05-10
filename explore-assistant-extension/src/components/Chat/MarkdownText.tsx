import React from 'react'
import { Marked } from 'marked'
import { markedHighlight } from 'marked-highlight'
import hljs from 'highlight.js'
// @ts-ignore
import hlsjLookML from 'highlightjs-lookml'
import 'highlight.js/styles/github.css'

const marked = new Marked(
  markedHighlight({
    langPrefix: 'hljs border rounded shadow syntax-highlighter language-',
    highlight(code, lang) {
      const language = hljs.getLanguage(lang) ? lang : 'plaintext'
      return hljs.highlight(code, { language }).value
    },
  }),
)

const processText = (text: string) => {
  if (!text) {
    return text
  }
  const modifiedText = marked.parse(text, {
    gfm: true,
    breaks: true,
  })
  return modifiedText
}

const MarkdownText = ({ text }: { text: string }) => {

  return (
    <div
      dangerouslySetInnerHTML={{
        __html: processText(text),
      }}
    />
  )
}

export default MarkdownText