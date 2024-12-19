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

// For CSS modules
declare module '*.module.css' {
  const classes: Record<string, string>
  export default classes
}

// For SCSS modules - assuming you are using SCSS syntax for these files
declare module '*.module.scss' {
  const classes: Record<string, string>
  export default classes
}

// For regular CSS files, if you are importing them directly and want type support
declare module '*.css' {
  const css: Record<string, string>
  export default css
}

// For regular SCSS files, similar to CSS but for SCSS
declare module '*.scss' {
  const scss: Record<string, string>
  export default scss
}

declare module '*.md' {
  const content: string;
  export default content;
}
