import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

const data = {
  labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
  datasets: [
    {
      label: 'Revenue',
      data: [12400, 18200, 15600, 22800, 19500, 26400, 24100, 28900, 31200, 27800, 34500, 38200],
      borderColor: '#4f46e5',
      backgroundColor: 'rgba(79, 70, 229, 0.08)',
      fill: true,
      tension: 0.4,
      borderWidth: 2,
      pointBackgroundColor: '#4f46e5',
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 6,
    },
    {
      label: 'Expenses',
      data: [8200, 11400, 9800, 13200, 12100, 15800, 14200, 16500, 18100, 15900, 19200, 21400],
      borderColor: '#0ea5e9',
      backgroundColor: 'rgba(14, 165, 233, 0.05)',
      fill: true,
      tension: 0.4,
      borderWidth: 2,
      pointBackgroundColor: '#0ea5e9',
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 6,
      borderDash: [5, 5],
    },
  ],
}

const options = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    intersect: false,
    mode: 'index',
  },
  plugins: {
    legend: {
      display: true,
      position: 'top',
      align: 'end',
      labels: {
        boxWidth: 12,
        boxHeight: 2,
        padding: 16,
        font: { size: 12, family: "'Inter', sans-serif" },
        usePointStyle: false,
      },
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
        label: (context) => `${context.dataset.label}: $${context.parsed.y.toLocaleString()}`,
      },
    },
  },
  scales: {
    x: {
      grid: { display: false },
      border: { display: false },
      ticks: {
        font: { size: 12, family: "'Inter', sans-serif" },
        color: '#94a3b8',
        padding: 8,
      },
    },
    y: {
      grid: {
        color: 'rgba(226, 232, 240, 0.5)',
        drawBorder: false,
      },
      border: { display: false },
      ticks: {
        font: { size: 12, family: "'Inter', sans-serif" },
        color: '#94a3b8',
        padding: 12,
        callback: (value) => `$${(value / 1000).toFixed(0)}k`,
      },
    },
  },
}

function RevenueChart() {
  return (
    <div className="chart-container">
      <div className="chart-header">
        <div>
          <h3>Revenue Overview</h3>
          <p className="chart-subtitle">Monthly revenue vs expenses</p>
        </div>
        <div className="chart-legend-custom">
          <span className="legend-item">
            <span className="legend-dot" style={{ background: '#4f46e5' }}></span>
            Revenue
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ background: '#0ea5e9' }}></span>
            Expenses
          </span>
        </div>
      </div>
      <div className="chart-body">
        <Line data={data} options={options} />
      </div>
    </div>
  )
}

export default RevenueChart
