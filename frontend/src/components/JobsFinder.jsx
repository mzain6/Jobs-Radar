import React, { useState } from 'react';

export default function JobsFinder({ jobs, categories, onOpenApply, onUpdateJobStatus, isScraping, onTriggerScrape }) {
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState('all');

  const activeCategories = categories.filter(c => c.enabled);

  // Filter jobs based on search query and category filters
  const filteredJobs = jobs.filter(job => {
    const matchesSearch = 
      job.title.toLowerCase().includes(search.toLowerCase()) ||
      job.company.toLowerCase().includes(search.toLowerCase()) ||
      (job.tags && Array.isArray(job.tags) && job.tags.some(t => typeof t === 'string' && t.toLowerCase().includes(search.toLowerCase())));

    const matchesCategory = 
      activeFilter === 'all' || 
      job.category === activeFilter;

    return matchesSearch && matchesCategory;
  });

  const formatDate = (dateStr) => {
    try {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return dateStr;
      
      const diffMs = new Date() - date;
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      
      if (diffDays === 0) return 'Today';
      if (diffDays === 1) return 'Yesterday';
      if (diffDays < 30) return `${diffDays} days ago`;
      return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    } catch (e) {
      return dateStr;
    }
  };

  return (
    <div style={{ animation: 'fadeIn 0.5s ease' }}>
      <div className="filter-bar">
        <div style={{ display: 'flex', gap: '1rem', width: '100%', alignItems: 'center' }}>
          <div className="search-input-wrapper">
            <span className="search-icon-placeholder">🔍</span>
            <input
              type="text"
              placeholder="Search remote jobs by title, company, or skills..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="search-input"
            />
          </div>
          
          <button 
            onClick={onTriggerScrape} 
            disabled={isScraping || activeCategories.length === 0} 
            className="btn btn-primary"
            style={{ whiteSpace: 'nowrap' }}
          >
            {isScraping ? (
              <>
                <span className="spinner" style={{ marginRight: '0.5rem' }}>⏳</span>
                Scraping...
              </>
            ) : 'Scrape Fresh Jobs'}
          </button>
        </div>

        <div className="category-pills">
          <button
            onClick={() => setActiveFilter('all')}
            className={`category-pill ${activeFilter === 'all' ? 'active' : ''}`}
          >
            All Jobs ({jobs.length})
          </button>
          
          {activeCategories.map(cat => {
            const count = jobs.filter(j => j.category === cat.id).length;
            return (
              <button
                key={cat.id}
                onClick={() => setActiveFilter(cat.id)}
                className={`category-pill ${activeFilter === cat.id ? 'active' : ''}`}
              >
                {cat.name} ({count})
              </button>
            );
          })}
        </div>
      </div>

      {isScraping && jobs.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">🛰️</div>
          <div className="empty-state-title">Scraping Remote Job Boards</div>
          <div className="empty-state-desc">
            We are aggregating fresh remote jobs from WeWorkRemotely and Remote.co matching your active categories. This will take a moment...
          </div>
        </div>
      )}

      {!isScraping && filteredJobs.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          <div className="empty-state-title">No Remote Jobs Found</div>
          <div className="empty-state-desc">
            {jobs.length === 0 
              ? 'Start by clicking "Scrape Fresh Jobs" above to fetch remote job postings.' 
              : 'Try adjusting your search query or switching categories.'}
          </div>
        </div>
      )}

      <div className="jobs-grid">
        {filteredJobs.map(job => (
          <div key={job.id} className="job-card">
            <div className="job-card-header">
              {job.logo ? (
                <img src={job.logo} alt={job.company} className="company-logo" onError={(e) => { e.target.style.display = 'none'; }} />
              ) : (
                <div className="company-logo-placeholder">
                  {job.company.substring(0, 1).toUpperCase()}
                </div>
              )}
              <span className={`source-badge ${job.source === 'Remote.co' ? 'rco' : 'wwr'}`}>
                {job.source}
              </span>
            </div>

            <h3 className="job-details-title">{job.title}</h3>
            <div className="job-company-name">{job.company}</div>

            {job.tags && job.tags.length > 0 && (
              <div className="job-tags">
                {job.tags.slice(0, 5).map((tag, idx) => (
                  <span key={idx} className="job-tag">{tag}</span>
                ))}
              </div>
            )}

            <div className="job-footer">
              <div className="job-date-salary">
                <span className="job-date">Posted {formatDate(job.date)}</span>
                {job.salary && <span className="job-salary">{job.salary}</span>}
              </div>

              <div style={{ display: 'flex', gap: '0.5rem' }}>
                {job.status === 'not-applied' ? (
                  <button 
                    onClick={() => onUpdateJobStatus(job.id, 'saved')}
                    className="btn btn-secondary" 
                    style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                    title="Bookmark Job"
                  >
                    💾 Save
                  </button>
                ) : (
                  <span style={{ fontSize: '0.8rem', color: 'var(--color-accent)', padding: '0.4rem 0.5rem', fontWeight: 'bold' }}>
                    {job.status.toUpperCase()}
                  </span>
                )}
                
                <button 
                  onClick={() => onOpenApply(job)}
                  className="btn btn-primary"
                  style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                >
                  Apply ⚡
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
