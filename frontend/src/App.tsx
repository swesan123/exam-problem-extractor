import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Classes from './pages/Classes'
import ClassDetails from './pages/ClassDetails'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/classes" element={<Classes />} />
        <Route path="/classes/:id" element={<ClassDetails />} />
      </Routes>
    </Layout>
  )
}

export default App

