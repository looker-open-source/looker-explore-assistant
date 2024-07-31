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
      const language = hljs.getLanguage(lang) ? lang : 'markdown'
      return hljs.highlight(code, { language }).value
    },
  }),
)

// Custom renderer to add Tailwind CSS classes
const renderer = new marked.Renderer()

renderer.heading = (text, level) => {
  const tag = `h${level}`
  let classes = 'font-bold text-gray-800'

  switch (level) {
    case 1:
      classes += ' text-3xl'
      break
    case 2:
      classes += ' text-2xl'
      break
    case 3:
      classes += ' text-xl'
      break
    case 4:
      classes += ' text-lg'
      break
    case 5:
      classes += ' text-base'
      break
    case 6:
      classes += ' text-base'
      break
    default:
      classes += ' text-base'
      break
  }

  return `<${tag} class="${classes}">${text}</${tag}>`
}

renderer.paragraph = (text) => {
  return `<p class="mb-4">${text}</p>`
}

renderer.list = (body, ordered) => {
  const tag = ordered ? 'ol' : 'ul'
  const classes = 'list-disc list-inside mb-4'
  return `<${tag} class="${classes}">${body}</${tag}>`
}

renderer.listitem = (text) => {
  return `<li class="mb-2">${text}</li>`
}

const processText = (text: string) => {
  if (!text) {
    return text
  }
  const modifiedText = marked.parse(text, {
    renderer,
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
