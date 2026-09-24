export type Course = Record<string, string> & {
  title?: string
  number?: string
  faculty?: string
  day_time?: string
  category?: string
  description?: string
  faculty_bio?: string
  room?: string
  units?: string
}

export type CoursesResponse = { count: number; courses: Course[] }
export type ChatResponse = { reply: string; tools_used: string[] }

const API_BASE = `${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/api`

export async function getCourses(query = ''): Promise<CoursesResponse> {
  const url = new URL(`${API_BASE}/courses`)
  if (query.trim()) url.searchParams.set('q', query.trim())
  const response = await fetch(url)
  if (!response.ok) throw new Error('Could not load the course catalog.')
  return response.json()
}

export async function askAgent(message: string): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  if (!response.ok) throw new Error('The course assistant is unavailable.')
  return response.json()
}
