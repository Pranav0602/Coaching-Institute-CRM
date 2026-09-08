import './QuickActions.css'

const kpis = [
  {
    id: 1,
    title: 'Total Students',
    value: '1,284',
    change: '+12.5%',
    changeType: 'positive',
    icon: 'students',
    color: 'blue',
  },
  {
    id: 2,
    title: 'Monthly Revenue',
    value: '$48,295',
    change: '+8.2%',
    changeType: 'positive',
    icon: 'revenue',
    color: 'green',
  },
  {
    id: 3,
    title: 'Active Courses',
    value: '24',
    change: '+3',
    changeType: 'positive',
    icon: 'courses',
    color: 'purple',
  },
  {
    id: 4,
    title: 'Completion Rate',
    value: '78.4%',
    change: '-2.1%',
    changeType: 'negative',
    icon: 'completion',
    color: 'orange',
  },
]

const quickActions = [
  { id: 1, label: 'Add Student', icon: 'add-student' },
  { id: 2, label: 'Create Course', icon: 'add-course' },
  { id: 3, label: 'Send Invoice', icon: 'invoice' },
  { id: 4, label: 'Generate Report', icon: 'report' },
]

function QuickActions() {
  return (
    <div className="quick-actions-section">
      <div className="kpi-grid">
        {kpis.map((kpi) => (
          <div key={kpi.id} className={`kpi-card ${kpi.color}`}>
            <div className="kpi-top">
              <div className={`kpi-icon ${kpi.color}`}>
                {kpi.icon === 'students' && (
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <circle cx="10" cy="7" r="3" stroke="currentColor" strokeWidth="1.5"/>
                    <path d="M4 18C4 14.69 6.69 12 10 12C13.31 12 16 14.69 16 18" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                )}
                {kpi.icon === 'revenue' && (
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M10 3V17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                    <path d="M6 7C6 7 7.5 5 10 5C12.5 5 14 7 14 7C14 7 14 9 10 9C6 9 6 11 6 11C6 11 7.5 13 10 13C12.5 13 14 11 14 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                )}
                {kpi.icon === 'courses' && (
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M3 5L10 2L17 5V15L10 18L3 15V5Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                    <path d="M10 2V18" stroke="currentColor" strokeWidth="1.5"/>
                    <path d="M3 5L10 8L17 5" stroke="currentColor" strokeWidth="1.5"/>
                  </svg>
                )}
                {kpi.icon === 'completion' && (
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <circle cx="10" cy="10" r="7.5" stroke="currentColor" strokeWidth="1.5"/>
                    <path d="M6.5 10L9 12.5L13.5 7.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                )}
              </div>
              <span className={`kpi-change ${kpi.changeType}`}>
                {kpi.changeType === 'positive' ? '+' : ''}{kpi.change}
              </span>
            </div>
            <div className="kpi-value">{kpi.value}</div>
            <div className="kpi-title">{kpi.title}</div>
          </div>
        ))}
      </div>

      <div className="actions-card">
        <div className="card-header">
          <h3>Quick Actions</h3>
        </div>
        <div className="actions-grid">
          {quickActions.map((action) => (
            <button key={action.id} className="action-btn" onClick={(e) => e.preventDefault()}>
              <div className="action-icon">
                {action.icon === 'add-student' && (
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <circle cx="8" cy="6" r="3" stroke="currentColor" strokeWidth="1.5"/>
                    <path d="M2 18C2 14.69 4.69 12 8 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                    <path d="M14 11V17M11 14H17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                )}
                {action.icon === 'add-course' && (
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M3 5L10 2L17 5V15L10 18L3 15V5Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                    <path d="M10 9V15M7 12H13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                )}
                {action.icon === 'invoice' && (
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <rect x="3" y="2" width="14" height="16" rx="2" stroke="currentColor" strokeWidth="1.5"/>
                    <path d="M7 6H13M7 9H13M7 12H10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                )}
                {action.icon === 'report' && (
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <rect x="2" y="10" width="3" height="6" rx="1" stroke="currentColor" strokeWidth="1.5"/>
                    <rect x="7" y="7" width="3" height="9" rx="1" stroke="currentColor" strokeWidth="1.5"/>
                    <rect x="12" y="4" width="3" height="12" rx="1" stroke="currentColor" strokeWidth="1.5"/>
                  </svg>
                )}
              </div>
              <span className="action-label">{action.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export default QuickActions
