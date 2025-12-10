import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Classes from './pages/Classes'
import ClassDetails from './pages/ClassDetails'
import ClassQuestions from './pages/ClassQuestions'
import Generate from './pages/Generate'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/classes" element={<Classes />} />
        <Route path="/classes/:id" element={<ClassDetails />} />
        <Route path="/classes/:id/questions" element={<ClassQuestions />} />
        <Route path="/generate" element={<Generate />} />
      </Routes>
    </Layout>
  )
}

export default App

