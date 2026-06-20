import React, { useState, useEffect } from 'react';

export default function ApplyAssistant({ isOpen, job, profile, dbSettings, onClose, onUpdateJobStatus, showToast }) {
  const [copiedField, setCopiedField] = useState('');
  const [coverLetter, setCoverLetter] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [notes, setNotes] = useState('');

  useEffect(() => {
    if (job) {
      setCoverLetter(job.coverLetter || '');
      setNotes(job.notes || '');
    }
  }, [job]);

  if (!job) return null;

  const handleCopy = (fieldName, textToCopy) => {
    if (!textToCopy) {
      showToast(`${fieldName} is empty. Add it in Settings first!`, 'error');
      return;
    }
    navigator.clipboard.writeText(textToCopy);
    setCopiedField(fieldName);
    showToast(`Copied ${fieldName}!`, 'success');
    setTimeout(() => setCopiedField(''), 1500);
  };

  const handleStatusChange = (e) => {
    onUpdateJobStatus(job.id, e.target.value);
  };

  const handleGenerateCoverLetter = async () => {
    if (!profile.name || !profile.resumeText) {
      showToast('Please add your Name and Resume in Settings first!', 'error');
      return;
    }
    
    setIsGenerating(true);
    try {
      const response = await fetch(`/api/jobs/${job.id}/cover-letter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ apiKey: dbSettings?.geminiApiKey })
      });
      const data = await response.json();
      
      if (response.ok) {
        setCoverLetter(data.coverLetter);
        // Refresh job details in parent state
        onUpdateJobStatus(job.id, { coverLetter: data.coverLetter });
        showToast('AI Cover Letter generated successfully!', 'success');
      } else {
        showToast(data.error || 'Failed to generate cover letter', 'error');
      }
    } catch (err) {
      console.error(err);
      showToast('Error connecting to backend server', 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSaveEdits = async () => {
    try {
      await onUpdateJobStatus(job.id, { coverLetter, notes });
      showToast('Changes saved successfully!', 'success');
    } catch (err) {
      showToast('Failed to save changes', 'error');
    }
  };

  return (
    <>
      <div className={`drawer-backdrop ${isOpen ? 'open' : ''}`} onClick={onClose}></div>
      
      <div className={`drawer ${isOpen ? 'open' : ''}`}>
        <div className="drawer-header">
          <div className="drawer-title-container">
            <h3 className="drawer-title">{job.title}</h3>
            <span className="drawer-subtitle">{job.company}</span>
          </div>
          <button className="btn-close" onClick={onClose}>&times;</button>
        </div>

        <div className="drawer-body">
          {/* Quick Actions Panel */}
          <div className="drawer-section">
            <div className="drawer-section-title">Application Status</div>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', justifyContent: 'space-between' }}>
              <select 
                value={job.status || 'not-applied'} 
                onChange={handleStatusChange} 
                className="form-input"
                style={{ flex: 1, padding: '0.5rem' }}
              >
                <option value="not-applied">Not Applied</option>
                <option value="saved">Saved / Bookmarked</option>
                <option value="applied">Applied</option>
                <option value="interviewing">Interviewing</option>
                <option value="offered">Offered 🎉</option>
                <option value="rejected">Rejected / Closed</option>
              </select>
              
              <a 
                href={job.url} 
                target="_blank" 
                rel="noopener noreferrer" 
                className="btn btn-primary"
                onClick={() => {
                  if (job.status === 'not-applied' || job.status === 'saved') {
                    onUpdateJobStatus(job.id, 'applied');
                  }
                }}
                style={{ textDecoration: 'none', padding: '0.5rem 1rem' }}
              >
                Open Apply Link ↗
              </a>
            </div>
          </div>

          {/* Copy-Paste Helper Profile Drawer */}
          <div className="drawer-section">
            <div className="drawer-section-title">Copy-Paste Autofill Helper</div>
            <div className="copy-grid">
              <div className="copy-field">
                <div className="copy-field-info">
                  <span className="copy-field-label">Full Name</span>
                  <span className="copy-field-value">{profile.name || '(Empty in Settings)'}</span>
                </div>
                <button 
                  onClick={() => handleCopy('Name', profile.name)} 
                  className={`btn-copy ${copiedField === 'Name' ? 'copied' : ''}`}
                >
                  {copiedField === 'Name' ? 'Copied!' : 'Copy'}
                </button>
              </div>

              <div className="copy-field">
                <div className="copy-field-info">
                  <span className="copy-field-label">Email</span>
                  <span className="copy-field-value">{profile.email || '(Empty in Settings)'}</span>
                </div>
                <button 
                  onClick={() => handleCopy('Email', profile.email)} 
                  className={`btn-copy ${copiedField === 'Email' ? 'copied' : ''}`}
                >
                  {copiedField === 'Email' ? 'Copied!' : 'Copy'}
                </button>
              </div>

              <div className="copy-field">
                <div className="copy-field-info">
                  <span className="copy-field-label">Phone</span>
                  <span className="copy-field-value">{profile.phone || '(Empty in Settings)'}</span>
                </div>
                <button 
                  onClick={() => handleCopy('Phone', profile.phone)} 
                  className={`btn-copy ${copiedField === 'Phone' ? 'copied' : ''}`}
                >
                  {copiedField === 'Phone' ? 'Copied!' : 'Copy'}
                </button>
              </div>

              <div className="copy-field">
                <div className="copy-field-info">
                  <span className="copy-field-label">Portfolio URL</span>
                  <span className="copy-field-value">{profile.portfolio || '(Empty in Settings)'}</span>
                </div>
                <button 
                  onClick={() => handleCopy('Portfolio', profile.portfolio)} 
                  className={`btn-copy ${copiedField === 'Portfolio' ? 'copied' : ''}`}
                >
                  {copiedField === 'Portfolio' ? 'Copied!' : 'Copy'}
                </button>
              </div>

              <div className="copy-field">
                <div className="copy-field-info">
                  <span className="copy-field-label">LinkedIn URL</span>
                  <span className="copy-field-value">{profile.linkedin || '(Empty in Settings)'}</span>
                </div>
                <button 
                  onClick={() => handleCopy('LinkedIn', profile.linkedin)} 
                  className={`btn-copy ${copiedField === 'LinkedIn' ? 'copied' : ''}`}
                >
                  {copiedField === 'LinkedIn' ? 'Copied!' : 'Copy'}
                </button>
              </div>

              <div className="copy-field">
                <div className="copy-field-info">
                  <span className="copy-field-label">GitHub URL</span>
                  <span className="copy-field-value">{profile.github || '(Empty in Settings)'}</span>
                </div>
                <button 
                  onClick={() => handleCopy('GitHub', profile.github)} 
                  className={`btn-copy ${copiedField === 'GitHub' ? 'copied' : ''}`}
                >
                  {copiedField === 'GitHub' ? 'Copied!' : 'Copy'}
                </button>
              </div>
            </div>
          </div>

          {/* AI Cover Letter Section */}
          <div className="drawer-section">
            <div className="drawer-section-title">AI Cover Letter Generator</div>
            <div className="cover-letter-area">
              {coverLetter ? (
                <>
                  <textarea
                    value={coverLetter}
                    onChange={(e) => setCoverLetter(e.target.value)}
                    className="cover-letter-text"
                  />
                  <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                    <button 
                      onClick={() => handleCopy('Cover Letter', coverLetter)}
                      className="btn btn-secondary"
                      style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                    >
                      📋 Copy Letter
                    </button>
                    
                    <button 
                      onClick={handleGenerateCoverLetter} 
                      disabled={isGenerating}
                      className="btn btn-secondary"
                      style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                    >
                      🔄 Regenerate
                    </button>
                    
                    <button 
                      onClick={handleSaveEdits}
                      className="btn btn-primary"
                      style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                    >
                      💾 Save Changes
                    </button>
                  </div>
                </>
              ) : (
                <div style={{ textAlign: 'center', padding: '1rem' }}>
                  <button 
                    onClick={handleGenerateCoverLetter}
                    disabled={isGenerating}
                    className="btn btn-primary"
                    style={{ width: '100%' }}
                  >
                    {isGenerating ? 'Generating customized cover letter...' : '⚡ Generate AI Cover Letter'}
                  </button>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-dark)', marginTop: '0.5rem' }}>
                    Writes a custom letter matching this job posting with your resume.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Application Notes */}
          <div className="drawer-section">
            <div className="drawer-section-title">Job Application Notes</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add contacts, follow-up dates, salary expectations, or interview questions here..."
                className="form-input"
                style={{ height: '80px', resize: 'vertical', fontSize: '0.85rem' }}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button 
                  onClick={handleSaveEdits}
                  className="btn btn-primary"
                  style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
                >
                  💾 Save Notes
                </button>
              </div>
            </div>
          </div>

          {/* Job Description details */}
          <div className="drawer-section">
            <div className="drawer-section-title">Job Description Details</div>
            <div 
              className="job-description-content"
              dangerouslySetInnerHTML={{ __html: job.description || 'No description summary available.' }}
            />
          </div>
        </div>
      </div>
    </>
  );
}
