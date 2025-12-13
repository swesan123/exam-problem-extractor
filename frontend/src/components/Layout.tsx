import { ReactNode } from 'react'

interface LayoutProps {
  children: ReactNode
}

const Layout = ({ children }: LayoutProps) => {
  return (
    <div className="h-screen bg-white overflow-hidden">
      <main className="w-full h-full">
        {children}
      </main>
    </div>
  )
}

export default Layout

