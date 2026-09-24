import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import type { CSSProperties } from 'react'
import { askAgent, getCourses } from './api'
import type { Course } from './api'
import './App.css'

type Message = { role: 'user' | 'assistant'; text: string; tools?: string[] }

const suggestions = ['Who teaches MGT 409?', 'How many core courses are there?', 'What are some good AI courses?']

function field(course: Course, ...keys: string[]) {
  for (const key of keys) if (course[key]) return course[key]
  return ''
}

function CourseCard({ course, index }: { course: Course; index: number }) {
  const number = field(course, 'number', 'Course Number') || 'COURSE'
  const title = field(course, 'title', 'Course Title') || 'Untitled course'
  const faculty = field(course, 'faculty', 'Faculty 1') || 'Faculty TBA'
  const schedule = field(course, 'day_time', 'Daytimes') || 'Schedule TBA'
  const category = field(course, 'category', 'Course Category') || 'Elective'
  const description = field(course, 'description', 'Course Description')
  return (
    <article className="course-card" style={{ '--card-index': index } as CSSProperties}>
      <div className="card-topline"><span className="course-number">{number}</span><span className="category-pill">{category}</span></div>
      <h3>{title}</h3>
      <p className="faculty"><span className="faculty-dot" />{faculty}</p>
      <div className="schedule"><span>◷</span>{schedule}</div>
      {description && <p className="description">{description.replace(/\s+/g, ' ').trim()}</p>}
      <div className="card-footer"><span>{field(course, 'Units', 'units') || '—'} units</span><span className="arrow">↗</span></div>
    </article>
  )
}

function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([{ role: 'assistant', text: 'Ask me anything about the Yale SOM course catalog. I can search course details or look beyond the catalog when needed.' }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  async function send(message = input) {
    const trimmed = message.trim()
    if (!trimmed || loading) return
    setInput('')
    setMessages((current) => [...current, { role: 'user', text: trimmed }])
    setLoading(true)
    try {
      const result = await askAgent(trimmed)
      setMessages((current) => [...current, { role: 'assistant', text: result.reply, tools: result.tools_used }])
    } catch (error) {
      setMessages((current) => [...current, { role: 'assistant', text: error instanceof Error ? error.message : 'Something went wrong.' }])
    } finally { setLoading(false) }
  }

  function submit(event: FormEvent) { event.preventDefault(); void send() }

  return (
    <aside className="chat-panel">
      <div className="chat-heading"><div className="agent-mark">✦</div><div><p className="eyebrow">Yale SOM intelligence</p><h2>Ask the catalog</h2></div><span className="online-dot" title="Assistant ready" /></div>
      <div className="chat-messages">
        {messages.map((message, index) => <div className={`message ${message.role}`} key={`${message.role}-${index}`}><div className="message-bubble">{message.text}</div>{message.role === 'assistant' && message.tools && message.tools.length > 0 && <div className="tool-trace"><span>TOOLS USED</span>{message.tools.map((tool) => <code key={tool}>{tool}</code>)}</div>}</div>)}
        {loading && <div className="message assistant"><div className="message-bubble thinking"><span /><span /><span /> Searching the catalog…</div></div>}
      </div>
      <div className="suggestions">{suggestions.map((suggestion) => <button key={suggestion} onClick={() => void send(suggestion)}>{suggestion}</button>)}</div>
      <form className="chat-input" onSubmit={submit}><input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask a course question…" aria-label="Ask the course assistant" /><button type="submit" aria-label="Send message" disabled={!input.trim() || loading}>↑</button></form>
      <p className="chat-footnote">Answers are grounded in course data and cited tool activity.</p>
    </aside>
  )
}

function App() {
  const [courses, setCourses] = useState<Course[]>([])
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('All courses')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    getCourses(query).then((result) => { if (!cancelled) setCourses(result.courses) }).catch((reason) => { if (!cancelled) setError(reason.message) }).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [query])

  const categories = useMemo(() => ['All courses', ...Array.from(new Set(courses.map((course) => field(course, 'category', 'Course Category')).filter(Boolean))).sort()], [courses])
  const visibleCourses = category === 'All courses' ? courses : courses.filter((course) => field(course, 'category', 'Course Category') === category)

  return (
    <div className="app-shell">
      <header className="site-header"><div className="brand"><div className="brand-seal">Y</div><div><strong>Yale School of Management</strong><span>Course explorer · 2026–27</span></div></div><div className="header-meta"><span className="status-dot" />Catalog live <span className="header-divider" /> Lecture 07</div></header>
      <main>
        <section className="hero-section"><div className="hero-copy"><p className="eyebrow">THE SOM COURSE CATALOG</p><h1>Find your next<br /><em>great class.</em></h1><p className="hero-subtitle">Explore 234 courses across the Yale School of Management — from core foundations to the ideas shaping what comes next.</p></div><div className="hero-orbit"><div className="orbit-ring ring-one" /><div className="orbit-ring ring-two" /><div className="orbit-core">SOM<span>YALE</span></div><span className="orbit-label label-one">LEARN</span><span className="orbit-label label-two">LEAD</span></div></section>
        <section className="catalog-bar"><div className="search-wrap"><span>⌕</span><input value={query} onChange={(event) => { setLoading(true); setError(''); setQuery(event.target.value) }} placeholder="Search courses, faculty, topics…" /></div><div className="filter-wrap"><label htmlFor="category">Browse by</label><select id="category" value={category} onChange={(event) => setCategory(event.target.value)}>{categories.map((item) => <option key={item}>{item}</option>)}</select></div></section>
        <section className="catalog-heading"><div><p className="eyebrow">DISCOVER</p><h2>{category === 'All courses' ? 'All courses' : category}</h2></div><span className="result-count">{loading ? 'Loading…' : `${visibleCourses.length} courses`}</span></section>
        {error ? <div className="error-state">{error} Make sure the FastAPI server is running on port 8000.</div> : <section className="course-grid">{visibleCourses.map((course, index) => <CourseCard key={`${field(course, 'Course ID', 'number')}-${index}`} course={course} index={index} />)}</section>}
        {!loading && !error && visibleCourses.length === 0 && <div className="empty-state">No courses match that search. Try a faculty name, course number, or topic.</div>}
      </main>
      <ChatPanel />
    </div>
  )
}

export default App
