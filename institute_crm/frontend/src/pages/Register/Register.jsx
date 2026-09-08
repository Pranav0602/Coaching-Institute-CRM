import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../../services/api'
import './Register.css'

export default function Register() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    address: '',
    course: '',
    mode: 'online',
  })
  const [errors, setErrors] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [apiError, setApiError] = useState('')
  const [success, setSuccess] = useState(false)

  const validate = () => {
    const newErrors = {}
    if (!form.full_name.trim()) newErrors.full_name = 'Full name is required'
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!form.email.trim()) newErrors.email = 'Email is required'
    else if (!emailRegex.test(form.email)) newErrors.email = 'Invalid email address'
    if (!form.phone.trim()) newErrors.phone = 'Phone is required'
    if (!form.course.trim()) newErrors.course = 'Course is required'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }))
  }

  const handleBlur = (e) => {
    const { name, value } = e.target
    if (!value.trim()) {
      setErrors((prev) => ({ ...prev, [name]: `${name.replace('_', ' ')} is required` }))
    } else {
      setErrors((prev) => ({ ...prev, [name]: '' }))
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return

    setIsSubmitting(true)
    setApiError('')

    try {
      await api.post('/crm/public-enquiry/', {
        name: form.full_name,
        email: form.email,
        phone: form.phone,
        target_course: form.course,
        notes: `Address: ${form.address || 'N/A'} | Mode: ${form.mode}`,
      })
      setSuccess(true)
    } catch (err) {
      const data = err.response?.data
      if (typeof data === 'object' && data !== null) {
        const firstKey = Object.keys(data)[0]
        const msg = data[firstKey]
        setApiError(Array.isArray(msg) ? msg[0] : msg)
      } else {
        setApiError('Submission failed. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  if (success) {
    return (
      <div className="register-page">
        <div className="register-container">
          <div className="register-left">
            <div className="register-brand">
              <div className="brand-icon">
                <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
                  <rect width="40" height="40" rx="10" fill="currentColor" opacity="0.15"/>
                  <rect x="10" y="10" width="8" height="8" rx="2" fill="currentColor"/>
                  <rect x="22" y="10" width="8" height="8" rx="2" fill="currentColor"/>
                  <rect x="10" y="22" width="8" height="8" rx="2" fill="currentColor"/>
                  <rect x="22" y="22" width="8" height="8" rx="2" fill="currentColor"/>
                </svg>
              </div>
              <h1>CRM Portal</h1>
              <p>Your registration has been submitted successfully.</p>
            </div>
            <div className="register-features">
              <div className="feature-item">
                <div className="feature-icon">
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M10 2L12.09 7.26L18 8.27L14 12.14L14.82 18.02L10 15.27L5.18 18.02L6 12.14L2 8.27L7.91 7.26L10 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                  </svg>
                </div>
                <span>Track student progress</span>
              </div>
              <div className="feature-item">
                <div className="feature-icon">
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M2 10C2 5.58 5.58 2 10 2C14.42 2 18 5.58 18 10C18 14.42 14.42 18 10 18" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                    <path d="M10 6V10L13 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                </div>
                <span>Real-time analytics</span>
              </div>
            </div>
          </div>
          <div className="register-right">
            <div className="success-message">
              <div className="success-icon">
                <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
                  <circle cx="32" cy="32" r="32" fill="#22c55e" opacity="0.1"/>
                  <path d="M20 33L28 41L44 25" stroke="#22c55e" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <h2>Registration Submitted!</h2>
              <p>Thank you for registering. The admin will review your details and send login credentials to your email.</p>
              <button className="register-btn" onClick={() => navigate('/login')}>
                Go to Login
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="register-page">
      <div className="register-container">
        <div className="register-left">
          <div className="register-brand">
            <div className="brand-icon">
              <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
                <rect width="40" height="40" rx="10" fill="currentColor" opacity="0.15"/>
                <rect x="10" y="10" width="8" height="8" rx="2" fill="currentColor"/>
                <rect x="22" y="10" width="8" height="8" rx="2" fill="currentColor"/>
                <rect x="10" y="22" width="8" height="8" rx="2" fill="currentColor"/>
                <rect x="22" y="22" width="8" height="8" rx="2" fill="currentColor"/>
              </svg>
            </div>
            <h1>CRM Portal</h1>
            <p>Register to join our institute and start your learning journey.</p>
          </div>
          <div className="register-features">
            <div className="feature-item">
              <div className="feature-icon">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M10 2L12.09 7.26L18 8.27L14 12.14L14.82 18.02L10 15.27L5.18 18.02L6 12.14L2 8.27L7.91 7.26L10 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                </svg>
              </div>
              <span>Expert instructors</span>
            </div>
            <div className="feature-item">
              <div className="feature-icon">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M2 10C2 5.58 5.58 2 10 2C14.42 2 18 5.58 18 10C18 14.42 14.42 18 10 18" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  <path d="M10 6V10L13 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              </div>
              <span>Flexible schedules</span>
            </div>
            <div className="feature-item">
              <div className="feature-icon">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M3 10C3 6.13 6.13 3 10 3C13.87 3 17 6.13 17 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  <path d="M10 3V17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  <path d="M3 10H17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              </div>
              <span>Online & offline modes</span>
            </div>
          </div>
        </div>

        <div className="register-right">
          <form className="register-form" onSubmit={handleSubmit} noValidate>
            <div className="form-header">
              <h2>Create Account</h2>
              <p>Fill in your details to register</p>
            </div>

            {apiError && <div className="error-message api-error">{apiError}</div>}

            <div className="form-group">
              <label htmlFor="full_name">Full Name</label>
              <div className={`input-wrapper ${errors.full_name ? 'input-error' : ''}`}>
                <svg className="input-icon" width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <circle cx="9" cy="5" r="3" stroke="currentColor" strokeWidth="1.5"/>
                  <path d="M3 16C3 13.5 6 12 9 12C12 12 15 13.5 15 16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
                <input type="text" id="full_name" name="full_name" placeholder="John Doe" value={form.full_name} onChange={handleChange} onBlur={handleBlur} autoComplete="name" />
              </div>
              {errors.full_name && <span className="error-message">{errors.full_name}</span>}
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="email">Email</label>
                <div className={`input-wrapper ${errors.email ? 'input-error' : ''}`}>
                  <svg className="input-icon" width="18" height="18" viewBox="0 0 18 18" fill="none">
                    <path d="M3 5.25L9 9.75L15 5.25" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    <rect x="2" y="3.5" width="14" height="11" rx="2" stroke="currentColor" strokeWidth="1.5"/>
                  </svg>
                  <input type="email" id="email" name="email" placeholder="you@example.com" value={form.email} onChange={handleChange} onBlur={handleBlur} autoComplete="email" />
                </div>
                {errors.email && <span className="error-message">{errors.email}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="phone">Phone</label>
                <div className={`input-wrapper ${errors.phone ? 'input-error' : ''}`}>
                  <svg className="input-icon" width="18" height="18" viewBox="0 0 18 18" fill="none">
                    <path d="M4 2H14C14.55 2 15 2.45 15 3V15C15 15.55 14.55 16 14 16H4C3.45 16 3 15.55 3 15V3C3 2.45 3.45 2 4 2Z" stroke="currentColor" strokeWidth="1.5"/>
                    <path d="M7 13H11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                  <input type="tel" id="phone" name="phone" placeholder="+1 234 567 890" value={form.phone} onChange={handleChange} onBlur={handleBlur} autoComplete="tel" />
                </div>
                {errors.phone && <span className="error-message">{errors.phone}</span>}
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="address">Address</label>
              <div className="input-wrapper">
                <svg className="input-icon" width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <path d="M9 2C6.24 2 4 4.24 4 7C4 10.75 9 16 9 16C9 16 14 10.75 14 7C14 4.24 11.76 2 9 2Z" stroke="currentColor" strokeWidth="1.5"/>
                  <circle cx="9" cy="7" r="2" stroke="currentColor" strokeWidth="1.5"/>
                </svg>
                <input type="text" id="address" name="address" placeholder="123 Main St, City" value={form.address} onChange={handleChange} autoComplete="street-address" />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="course">Course</label>
                <div className={`input-wrapper ${errors.course ? 'input-error' : ''}`}>
                  <svg className="input-icon" width="18" height="18" viewBox="0 0 18 18" fill="none">
                    <path d="M2 4L9 8L16 4L9 0L2 4Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                    <path d="M2 8L9 12L16 8" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                    <path d="M2 12L9 16L16 12" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                  </svg>
                  <input type="text" id="course" name="course" placeholder="e.g. Web Development" value={form.course} onChange={handleChange} onBlur={handleBlur} />
                </div>
                {errors.course && <span className="error-message">{errors.course}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="mode">Mode</label>
                <div className="select-wrapper">
                  <svg className="input-icon" width="18" height="18" viewBox="0 0 18 18" fill="none">
                    <rect x="2" y="3" width="14" height="12" rx="2" stroke="currentColor" strokeWidth="1.5"/>
                    <path d="M6 7L9 10L12 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  <select id="mode" name="mode" value={form.mode} onChange={handleChange}>
                    <option value="online">Online</option>
                    <option value="offline">Offline</option>
                  </select>
                </div>
              </div>
            </div>

            <button type="submit" className="register-btn" disabled={isSubmitting}>
              {isSubmitting ? (
                <span className="btn-loading">
                  <span className="spinner"></span>
                  Submitting...
                </span>
              ) : (
                'Submit Registration'
              )}
            </button>

            <div className="form-footer">
              <p>Already have an account? <Link to="/login">Login</Link></p>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}