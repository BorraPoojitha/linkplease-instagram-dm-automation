import React, { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import DashboardPage from "./pages/DashboardPage";
import RulesPage from "./pages/RulesPage";
import JobsPage from "./pages/JobsPage";
import EventsPage from "./pages/EventsPage";
import StatsPage from "./pages/StatsPage";
import { fetchStats, fetchHealth, fetchRules, fetchJobs, fetchEvents } from "./services/api";

export default function App() {
  const [currentPage, setCurrentPage] = useState("dashboard");
  const [stats, setStats] = useState(null);
  const [healthStatus, setHealthStatus] = useState(null);
  const [rules, setRules] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [events, setEvents] = useState([]);

  const [toast, setToast] = useState(null);

  const showToast = (message, type = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const loadData = async () => {
    try {
      const [hRes, sRes, rRes, jRes, eRes] = await Promise.allSettled([
        fetchHealth(),
        fetchStats(),
        fetchRules(),
        fetchJobs(),
        fetchEvents(),
      ]);

      if (hRes.status === "fulfilled") setHealthStatus(hRes.value);
      if (sRes.status === "fulfilled") setStats(sRes.value);
      if (rRes.status === "fulfilled") setRules(rRes.value);
      if (jRes.status === "fulfilled") setJobs(jRes.value);
      if (eRes.status === "fulfilled") setEvents(eRes.value);
    } catch (err) {
      console.error("Error loading application data:", err);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 3000); // 3-second live refresh
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-container">
      <Sidebar
        currentPage={currentPage}
        setCurrentPage={setCurrentPage}
        healthStatus={healthStatus}
      />

      <div className="main-content">
        <Header healthStatus={healthStatus} />

        <div className="page-body">
          {currentPage === "dashboard" && (
            <DashboardPage
              stats={stats}
              healthStatus={healthStatus}
              rules={rules}
              jobs={jobs}
            />
          )}

          {currentPage === "rules" && (
            <RulesPage
              rules={rules}
              refreshRules={loadData}
              showToast={showToast}
            />
          )}

          {currentPage === "jobs" && <JobsPage jobs={jobs} />}

          {currentPage === "events" && <EventsPage events={events} />}

          {currentPage === "stats" && <StatsPage stats={stats} />}
        </div>
      </div>

      {toast && (
        <div className={`toast toast-${toast.type}`}>
          <span>{toast.message}</span>
        </div>
      )}
    </div>
  );
}
