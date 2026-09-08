import './RecentActivities.css'

const activities = [
  {
    id: 1,
    icon: 'student',
    iconBg: 'blue',
    text: 'New student Sarah Johnson enrolled in React Masterclass',
    time: '5 minutes ago',
  },
  {
    id: 2,
    icon: 'payment',
    iconBg: 'green',
    text: 'Payment of $299 received from Michael Chen',
    time: '23 minutes ago',
  },
  {
    id: 3,
    icon: 'course',
    iconBg: 'purple',
    text: 'Course "Advanced JavaScript" completed by 12 students',
    time: '1 hour ago',
  },
  {
    id: 4,
    icon: 'alert',
    iconBg: 'orange',
    text: '3 students at risk of dropping - follow up required',
    time: '2 hours ago',
  },
  {
    id: 5,
    icon: 'review',
    iconBg: 'teal',
    text: 'New 5-star review from Emily Davis on Python Fundamentals',
    time: '3 hours ago',
  },
]

function RecentActivities() {
  return (
    <div className="activities-card">
      <div className="card-header">
        <h3>Recent Activities</h3>
        <a href="#" className="view-all" onClick={(e) => e.preventDefault()}>View all</a>
      </div>
      <div className="activities-list">
        {activities.map((activity) => (
          <div key={activity.id} className="activity-item">
            <div className={`activity-icon ${activity.iconBg}`}>
              {activity.icon === 'student' && (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="5" r="2.5" stroke="currentColor" strokeWidth="1.5"/>
                  <path d="M3 14C3 11.24 5.24 9 8 9C10.76 9 13 11.24 13 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              )}
              {activity.icon === 'payment' && (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <rect x="1" y="3.5" width="14" height="9" rx="2" stroke="currentColor" strokeWidth="1.5"/>
                  <path d="M1 6.5H15" stroke="currentColor" strokeWidth="1.5"/>
                </svg>
              )}
              {activity.icon === 'course' && (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M2 3.5L8 1L14 3.5V12L8 14.5L2 12V3.5Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                  <path d="M8 1V14.5" stroke="currentColor" strokeWidth="1.5"/>
                </svg>
              )}
              {activity.icon === 'alert' && (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M8 2L14.5 13H1.5L8 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                  <path d="M8 7V9.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  <circle cx="8" cy="11.5" r="0.5" fill="currentColor"/>
                </svg>
              )}
              {activity.icon === 'review' && (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M8 1.5L9.63 5.15L13.5 5.6L10.75 8.3L11.45 12.12L8 10.18L4.55 12.12L5.25 8.3L2.5 5.6L6.37 5.15L8 1.5Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                </svg>
              )}
            </div>
            <div className="activity-content">
              <p className="activity-text">{activity.text}</p>
              <span className="activity-time">{activity.time}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default RecentActivities
