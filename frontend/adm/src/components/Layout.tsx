import { Outlet } from 'react-router-dom'
import Header from '@/components/Header'

export default function Layout() {
  return (
    <div className="flex flex-col h-screen bg-[#FAF6F2]">
      <Header />
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
