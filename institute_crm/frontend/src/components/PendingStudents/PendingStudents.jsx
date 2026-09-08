import { useState, useEffect } from 'react'
import api from '../../services/api'
import './PendingStudents.css'

function PendingStudents() {
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/crm/leads/', { params: { stage: 'New' } })
      .then(res => {
        setStudents(res.data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="pending-card">
        <div className="card-header">
          <h3>Pending Students</h3>
        </div>
        <div className="pending-loading">Loading...</div>
      </div>
    )
  }

  return (
    <div className="pending-card">
      <div className="card-header">
        <h3>Pending Students</h3>
        <span className="pending-badge">{students.length} waiting</span>
      </div>
      {students.length === 0 ? (
        <div className="pending-empty">No pending students.</div>
      ) : (
        <div className="pending-table-wrapper">
          <table className="pending-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Course</th>
                <th>Mode</th>
                <th>Registered On</th>
              </tr>
            </thead>
            <tbody>
              {students.map((s) => (
                <tr key={s.id}>
                  <td className="pending-name">{s.name}</td>
                  <td>{s.email}</td>
                  <td>{s.phone}</td>
                  <td>{s.course_title || s.target_course}</td>
                  <td>
                    <span className={`mode-badge ${s.stage}`}>{s.stage}</span>
                  </td>
                  <td className="pending-date">
                    {new Date(s.created_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default PendingStudents
