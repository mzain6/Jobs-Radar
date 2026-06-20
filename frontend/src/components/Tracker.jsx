import React from 'react';

const COLUMNS = [
  { id: 'saved', name: 'Saved / Bookmarked', color: 'var(--text-muted)' },
  { id: 'applied', name: 'Applied', color: 'var(--color-primary)' },
  { id: 'interviewing', name: 'Interviewing', color: 'var(--color-warning)' },
  { id: 'offered', name: 'Offered 🎉', color: 'var(--color-success)' },
  { id: 'rejected', name: 'Rejected / Closed', color: 'var(--color-danger)' }
];

export default function Tracker({ jobs, onOpenApply, onUpdateJobStatus }) {
  // Only track jobs that have been saved or moved to another status
  const trackedJobs = jobs.filter(job => job.status && job.status !== 'not-applied');

  const getColumnJobs = (statusId) => {
    return trackedJobs.filter(job => job.status === statusId);
  };

  return (
    <div style={{ animation: 'fadeIn 0.5s ease' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontFamily: 'var(--font-heading)', fontWeight: '700', fontSize: '1.25rem' }}>Application Pipeline</h2>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Track the progress of your active applications. Select a status dropdown on a card to move it between stages.
        </p>
      </div>

      {trackedJobs.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <div className="empty-state-title">No Tracked Jobs Yet</div>
          <div className="empty-state-desc">
            Go to the "Find Jobs" tab, search for remote positions, and click the "Save" or "Apply" buttons to populate your tracker board.
          </div>
        </div>
      ) : (
        <div className="tracker-board">
          {COLUMNS.map(col => {
            const colJobs = getColumnJobs(col.id);
            return (
              <div key={col.id} className="tracker-column">
                <div className="column-header">
                  <span className="column-title" style={{ color: col.color }}>
                    {col.name}
                  </span>
                  <span className="column-badge">{colJobs.length}</span>
                </div>
                
                <div className="column-cards-container">
                  {colJobs.map(job => (
                    <div 
                      key={job.id} 
                      className="tracker-card"
                      onClick={() => onOpenApply(job)}
                    >
                      <h4 className="tracker-card-title">{job.title}</h4>
                      <div className="tracker-card-company">{job.company}</div>
                      
                      <div className="tracker-card-actions" onClick={(e) => e.stopPropagation()}>
                        <span className="tracker-card-date">
                          {job.source}
                        </span>
                        
                        <select
                          value={job.status}
                          onChange={(e) => onUpdateJobStatus(job.id, e.target.value)}
                          className="status-select"
                        >
                          {COLUMNS.map(c => (
                            <option key={c.id} value={c.id}>{c.name.split(' ')[0]}</option>
                          ))}
                          <option value="not-applied">Remove</option>
                        </select>
                      </div>
                    </div>
                  ))}
                  
                  {colJobs.length === 0 && (
                    <div style={{
                      padding: '2rem 1rem',
                      textAlign: 'center',
                      fontSize: '0.8rem',
                      color: 'var(--text-dark)',
                      border: '1px dashed var(--border-light)',
                      borderRadius: '8px'
                    }}>
                      Empty Column
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
