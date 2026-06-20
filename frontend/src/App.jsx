import React, { useState, useEffect } from 'react';
import JobsFinder from './components/JobsFinder';
import Tracker from './components/Tracker';
import ProfileSettings from './components/ProfileSettings';
import ApplyAssistant from './components/ApplyAssistant';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('jobs');
  const [db, setDb] = useState({
    jobs: [],
    profile: { name: '', email: '', phone: '' },
    settings: { categories: [] }
  });
  const [isScraping, setIsScraping] = useState(false);
  const [toast, setToast] = useState({ show: false, message: '', type: 'success' });
  const [activeJobForDrawer, setActiveJobForDrawer] = useState(null);

  const fetchDb = async () => {
    try {
      const res = await fetch('/api/db');
      if (res.ok) {
        const data = await res.json();
        setDb(data);
      }
    } catch (err) {
      console.error('Failed to load database state:', err);
      showToast('Error loading server data. Is server running?', 'error');
    }
  };

  useEffect(() => {
    fetchDb();
  }, []);

  const showToast = (message, type = 'success') => {
    setToast({ show: true, message, type });
    setTimeout(() => {
      setToast(prev => ({ ...prev, show: false }));
    }, 3500);
  };

  const handleUpdateJobStatus = async (jobId, updatesOrStatus) => {
    // If we only passed a status string, construct the payload object
    const payload = typeof updatesOrStatus === 'string' 
      ? { status: updatesOrStatus } 
      : updatesOrStatus;

    try {
      const res = await fetch(`/api/jobs/${jobId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      
      if (res.ok) {
        // Update local state without full reload
        setDb(prev => ({
          ...prev,
          jobs: prev.jobs.map(j => j.id === jobId ? { ...j, ...payload } : j)
        }));

        // If the drawer is open for this job, sync it
        if (activeJobForDrawer && activeJobForDrawer.id === jobId) {
          setActiveJobForDrawer(prev => ({ ...prev, ...payload }));
        }

        // Notify user of certain transitions
        if (payload.status) {
          showToast(`Job status updated to ${payload.status}!`, 'success');
        }
      } else {
        showToast(data.error || 'Failed to update job status', 'error');
      }
    } catch (err) {
      console.error(err);
      showToast('Connection error updating job state', 'error');
    }
  };

  const handleTriggerScrape = async () => {
    setIsScraping(true);
    showToast('Starting remote job scrape. Please wait...', 'success');
    
    try {
      const res = await fetch('/api/scrape', {
        method: 'POST'
      });
      const data = await res.json();
      
      if (res.ok) {
        setDb(prev => ({ ...prev, jobs: data.jobs }));
        showToast(`Scrape completed! Found ${data.newCount} new jobs.`, 'success');
      } else {
        showToast(data.error || 'Failed to scrape jobs', 'error');
      }
    } catch (err) {
      console.error(err);
      showToast('Scraping connection error', 'error');
    } finally {
      setIsScraping(false);
    }
  };

  // Sync active job description in drawer when db changes
  useEffect(() => {
    if (activeJobForDrawer) {
      const updatedJob = db.jobs.find(j => j.id === activeJobForDrawer.id);
      if (updatedJob) {
        setActiveJobForDrawer(updatedJob);
      }
    }
  }, [db.jobs]);

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="logo-container">
          <span className="logo-icon">📡</span>
          <span className="logo-text">Remote Hunter</span>
        </div>

        <nav className="nav-menu">
          <li className="nav-item">
            <button 
              onClick={() => setActiveTab('jobs')}
              className={`nav-link ${activeTab === 'jobs' ? 'active' : ''}`}
            >
              <span className="nav-icon">🔍</span>
              Find Jobs
            </button>
          </li>
          <li className="nav-item">
            <button 
              onClick={() => setActiveTab('tracker')}
              className={`nav-link ${activeTab === 'tracker' ? 'active' : ''}`}
            >
              <span className="nav-icon">📋</span>
              App Tracker
            </button>
          </li>
          <li className="nav-item">
            <button 
              onClick={() => setActiveTab('settings')}
              className={`nav-link ${activeTab === 'settings' ? 'active' : ''}`}
            >
              <span className="nav-icon">⚙️</span>
              Profile & Keys
            </button>
          </li>
        </nav>

        <div className="sidebar-footer">
          <div className="user-badge">
            <div className="avatar">
              {db.profile.name ? db.profile.name.substring(0, 2).toUpperCase() : 'ME'}
            </div>
            <div className="user-info">
              <span className="user-name">{db.profile.name || 'Job Seeker'}</span>
              <span className="user-role">Remote Candidate</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <main className="main-content">
        <header className="content-header">
          <h1 className="page-title">
            {activeTab === 'jobs' && 'Remote Jobs Board'}
            {activeTab === 'tracker' && 'Application Pipeline'}
            {activeTab === 'settings' && 'Profile & Configurations'}
          </h1>
          <div className="header-actions">
            {activeTab === 'jobs' && (
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {db.jobs.length} jobs available
              </span>
            )}
          </div>
        </header>

        <div className="page-body">
          {activeTab === 'jobs' && (
            <JobsFinder 
              jobs={db.jobs}
              categories={db.settings.categories}
              onOpenApply={setActiveJobForDrawer}
              onUpdateJobStatus={handleUpdateJobStatus}
              isScraping={isScraping}
              onTriggerScrape={handleTriggerScrape}
            />
          )}

          {activeTab === 'tracker' && (
            <Tracker 
              jobs={db.jobs}
              onOpenApply={setActiveJobForDrawer}
              onUpdateJobStatus={handleUpdateJobStatus}
            />
          )}

          {activeTab === 'settings' && (
            <ProfileSettings 
              db={db}
              onSave={fetchDb}
              showToast={showToast}
            />
          )}
        </div>
      </main>

      {/* Slide-out Drawer: Apply Assistant */}
      <ApplyAssistant 
        isOpen={!!activeJobForDrawer}
        job={activeJobForDrawer}
        profile={db.profile}
        dbSettings={db.settings}
        onClose={() => setActiveJobForDrawer(null)}
        onUpdateJobStatus={handleUpdateJobStatus}
        showToast={showToast}
      />

      {/* Global Toast Notification */}
      <div className={`toast ${toast.show ? 'show' : ''} ${toast.type}`}>
        <span>{toast.type === 'success' ? '✅' : '❌'}</span>
        <span>{toast.message}</span>
      </div>
    </div>
  );
}
