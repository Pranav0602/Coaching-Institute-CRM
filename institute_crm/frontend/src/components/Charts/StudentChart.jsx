import { Doughnut } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(ArcElement, Tooltip, Legend)

const data = {
  labels: ['Active', 'Completed', 'Dropped', 'Pending'],
  datasets: [
    {
      data: [450, 320, 85, 145],
      backgroundColor: ['#4f46e5', '#10b981', '#ef4444', '#f59e0b'],
      borderColor: ['#4f46e5', '#10b981', '#ef4444', '#f59e0b'],
      borderWidth: 0,
      hoverOffset: 6,
      spacing: 3,
      borderRadius: 4,
    },
  ],
}

const options = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '68%',
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      backgroundColor: '#1e293b',
      titleColor: '#f8fafc',
      bodyColor: '#cbd5e1',
      borderColor: '#334155',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 8,
      titleFont: { size: 13, weight: '600', family: "'Inter', sans-serif" },
      bodyFont: { size: 12, family: "'Inter', sans-serif" },
      callbacks: {
        label: (context) => {
          const total = context.dataset.data.reduce((a, b) => a + b, 0)
          const pct = ((context.parsed / total) * 100).toFixed(1)
          return `${context.label}: ${context.parsed} (${pct}%)`
        },
      },
    },
  },
}

const legendItems = [
  { label: 'Active', count: 450, color: '#4f46e5', pct: '45%' },
  { label: 'Completed', count: 320, color: '#10b981', pct: '32%' },
  { label: 'Dropped', count: 85, color: '#ef4444', pct: '8.5%' },
  { label: 'Pending', count: 145, color: '#f59e0b', pct: '14.5%' },
]

function StudentChart() {
  const total = 1000

  return (
    <div className="chart-container">
      <div className="chart-header">
        <div>
          <h3>Student Enrollment</h3>
          <p className="chart-subtitle">Total: {total.toLocaleString()} students</p>
        </div>
      </div>
      <div className="chart-body doughnut-wrapper">
        <div className="doughnut-chart">
          <Doughnut data={data} options={options} />
          <div className="doughnut-center">
            <span className="doughnut-number">{total.toLocaleString()}</span>
            <span className="doughnut-label">Students</span>
          </div>
        </div>
        <div className="doughnut-legend">
          {legendItems.map((item) => (
            <div key={item.label} className="legend-row">
              <div className="legend-left">
                <span className="legend-color" style={{ background: item.color }}></span>
                <span className="legend-label">{item.label}</span>
              </div>
              <div className="legend-right">
                <span className="legend-count">{item.count}</span>
                <span className="legend-pct">{item.pct}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default StudentChart
