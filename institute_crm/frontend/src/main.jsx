import { Component, StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Unhandled application error:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false });
    try {
      window.localStorage.clear();
    } catch { }
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          style={{
            minHeight: "100vh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "12px",
            padding: "24px",
            fontFamily: "system-ui, sans-serif",
            textAlign: "center",
          }}
        >
          <p style={{ margin: 0 }}>
            Session expired or something went wrong —{" "}
            <button
              type="button"
              onClick={this.handleReset}
              style={{
                background: "none",
                border: "none",
                padding: 0,
                color: "#1976d2",
                textDecoration: "underline",
                cursor: "pointer",
                font: "inherit",
              }}
            >
              Click here to reset
            </button>
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>
);
