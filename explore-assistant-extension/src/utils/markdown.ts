// Function to convert the array of hashes to a Markdown table
export const hashesToMarkdownTable = (hashes: Array<Record<string, any>>): string => {
  // Check if the array is empty
  if (hashes.length === 0) {
    return ''
  }

  // Extract headers (keys) from the first hash
  const headers = Object.keys(hashes[0])

  // Create the header row
  const headerRow = `| ${headers.join(' | ')} |`

  // Create the divider row (assuming all fields are strings for simplicity)
  const dividerRow = `| ${headers.map(() => '---').join(' | ')} |`

  // Create the data rows
  const dataRows = hashes.map((hash) => {
    const rowCells = headers.map((header) => hash[header])
    return `| ${rowCells.join(' | ')} |`
  })

  // Combine all parts to form the full table
  return [headerRow, dividerRow, ...dataRows].join('\n')
}
