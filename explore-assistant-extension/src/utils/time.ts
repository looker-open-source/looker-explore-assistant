export const getHumanReadableDuration = (startDateTime: string, endDateTime: string): string => {
    const start = new Date(startDateTime)
    const end = new Date(endDateTime)
  
    if (isNaN(start.getTime()) || isNaN(end.getTime())) {
      throw new Error('Invalid date-time string')
    }
  
    const durationMilliseconds = end.getTime() - start.getTime()
    let durationSeconds = Math.floor(durationMilliseconds / 1000)
    const durationMinutes = Math.floor(durationSeconds / 60)
    const durationHours = Math.floor(durationMinutes / 60)
  
    durationSeconds %= 60
    const remainingMinutes = durationMinutes % 60
  
    const parts: string[] = []
    if (durationHours > 0) {
      parts.push(`${durationHours} ${durationHours === 1 ? 'hour' : 'hours'}`)
    }
    if (remainingMinutes > 0) {
      parts.push(`${remainingMinutes} ${remainingMinutes === 1 ? 'minute' : 'minutes'}`)
    }
    if (durationSeconds > 0 || parts.length === 0) {
      parts.push(`${durationSeconds} ${durationSeconds === 1 ? 'second' : 'seconds'}`)
    }
  
    return parts.join(' ')
  }
  
  export const getRelativeTimeString = (dateStr: string | Date) => {
    const date = new Date(dateStr)
    const now = new Date()
  
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)
    const diffInMinutes = Math.floor(diffInSeconds / 60)
    const diffInHours = Math.floor(diffInMinutes / 60)
    const diffInDays = Math.floor(diffInHours / 24)
  
    // Function to format the date as "Oct 25, 2023"
    const formatDate = (date: Date) => {
      const options: Intl.DateTimeFormatOptions = {
        month: 'short', // allowed values: 'numeric', '2-digit', 'long', 'short', 'narrow'
        day: 'numeric', // allowed values: 'numeric', '2-digit'
        year: 'numeric', // allowed values: 'numeric', '2-digit'
      }
      return date.toLocaleDateString('en-US', options)
    }
  
    let relativeTime
  
    if (diffInSeconds < 1) {
      relativeTime = 'just now'
    } else if (diffInSeconds < 60) {
      relativeTime = diffInSeconds === 1 ? '1 second ago' : `${diffInSeconds} seconds ago`
    } else if (diffInMinutes < 60) {
      relativeTime = diffInMinutes === 1 ? '1 minute ago' : `${diffInMinutes} minutes ago`
    } else if (diffInHours < 24) {
      relativeTime = diffInHours === 1 ? '1 hour ago' : `${diffInHours} hours ago`
    } else if (diffInDays <= 2) {
      relativeTime = diffInDays === 1 ? '1 day ago' : `${diffInDays} days ago`
    } else {
      relativeTime = formatDate(date)
    }
  
    return relativeTime
  }