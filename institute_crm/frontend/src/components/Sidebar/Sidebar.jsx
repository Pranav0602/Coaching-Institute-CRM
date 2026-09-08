import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import './Sidebar.css'

function Sidebar({ isCollapsed, onToggle }) {
  const { logout } = useAuth()
  const [searchQuery, setSearchQuery] = useState('')
  const [notifications] = useState([
    { id: 1, text: 'New student enrolled', time: '5m ago', unread: true },
    { id: 2, text: 'Payment received from John', time: '1h ago', unread: true },
    { id: 3, text: 'Course completion: React 101', time: '3h ago', unread: false },
  ])

  const unreadCount = notifications.filter((n) => n.unread).length

  return (
    <aside className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="brand-logo">
            <svg width="24" height="24" viewBox="0 0 40 40" fill="none">
              <rect width="40" height="40" rx="10" fill="currentColor" opacity="0.15"/>
              <path d="M12 28V16L20 12L28 16V28L20 24L12 28Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
              <path d="M20 12V24" stroke="currentColor" strokeWidth="2"/>
            </svg>
          </div>
          {!isCollapsed && <span className="brand-text">CRM Portal</span>}
        </div>
        <button className="sidebar-toggle" onClick={onToggle} aria-label="Toggle sidebar">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d={isCollapsed ? "M7 4L12 9L7 14" : "M11 4L6 9L11 14"} stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>

      <div className="sidebar-search">
        <div className="search-input-wrapper">
          <svg className="search-icon" width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5"/>
            <path d="M11 11L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          {!isCollapsed && (
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          )}
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section">
          {!isCollapsed && <span className="nav-section-title">Main</span>}
          <a href="#" className="nav-item active" title="Dashboard">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <rect x="2" y="2" width="5.5" height="5.5" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
              <rect x="10.5" y="2" width="5.5" height="5.5" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
              <rect x="2" y="10.5" width="5.5" height="5.5" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
              <rect x="10.5" y="10.5" width="5.5" height="5.5" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
            </svg>
            {!isCollapsed && <span>Dashboard</span>}
          </a>
          <a href="#" className="nav-item" title="Students">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <circle cx="9" cy="6" r="3" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M3 16C3 12.69 5.69 10 9 10C12.31 10 15 12.69 15 16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            {!isCollapsed && <span>Students</span>}
          </a>
          <a href="#" className="nav-item" title="Courses">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M2 4L9 1L16 4V14L9 17L2 14V4Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
              <path d="M9 1V17" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M2 4L9 7L16 4" stroke="currentColor" strokeWidth="1.5"/>
            </svg>
            {!isCollapsed && <span>Courses</span>}
          </a>
          <a href="#" className="nav-item" title="Revenue">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M9 2V16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              <path d="M5 5C5 5 6.5 3 9 3C11.5 3 13 5 13 5C13 5 13 7 9 7C5 7 5 9 5 9C5 9 6.5 11 9 11C11.5 11 13 9 13 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            {!isCollapsed && <span>Revenue</span>}
          </a>
        </div>

        <div className="nav-section">
          {!isCollapsed && <span className="nav-section-title">Management</span>}
          <a href="#" className="nav-item" title="Instructors">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <circle cx="7" cy="7" r="3" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M1 16C1 12.69 3.69 10 7 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              <circle cx="13" cy="7" r="2.5" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M11 16C11 13.24 11.78 11 13 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            {!isCollapsed && <span>Instructors</span>}
          </a>
          <a href="#" className="nav-item" title="Reports">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <rect x="3" y="2" width="12" height="14" rx="2" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M6 6H12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              <path d="M6 9H12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              <path d="M6 12H9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            {!isCollapsed && <span>Reports</span>}
          </a>
          <a href="#" className="nav-item" title="Settings">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <circle cx="9" cy="9" r="2.5" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M9 1.5V3M9 15V16.5M1.5 9H3M15 9H16.5M3.4 3.4L4.5 4.5M13.5 13.5L14.6 14.6M14.6 3.4L13.5 4.5M4.5 13.5L3.4 14.6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            {!isCollapsed && <span>Settings</span>}
          </a>
        </div>
      </nav>

      <div className="sidebar-footer">
        <button className="sidebar-logout" title="Logout" onClick={logout}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M7 14L2 9M2 9L7 4M2 9H12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M10 14.5H14C14.83 14.5 15.5 13.83 15.5 13V5C15.5 4.17 14.83 3.5 14 3.5H10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          {!isCollapsed && <span>Logout</span>}
        </button>

        <div className="notification-bell" title={`${unreadCount} notifications`}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M7 14C7.55 14.95 8.22 15.5 9 15.5C9.78 15.5 10.45 14.95 11 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            <path d="M13.5 6.5C13.5 4.01 11.49 2 9 2C6.51 2 4.5 4.01 4.5 6.5C4.5 11 2 12.5 2 12.5H16C16 12.5 13.5 11 13.5 6.5Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
          </svg>
          {unreadCount > 0 && <span className="notification-badge">{unreadCount}</span>}
        </div>

        <div className="user-profile">
          <div className="user-avatar">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <circle cx="9" cy="6" r="3" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M3 16C3 12.69 5.69 10 9 10C12.31 10 15 12.69 15 16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </div>
          {!isCollapsed && (
            <div className="user-info">
              <span className="user-name">Admin User</span>
              <span className="user-role">Administrator</span>
            </div>
          )}
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
