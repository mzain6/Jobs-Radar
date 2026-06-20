import React, { useState, useEffect } from 'react';

export default function ProfileSettings({ db, onSave, showToast }) {
  const [profile, setProfile] = useState({
    name: '',
    email: '',
    phone: '',
    portfolio: '',
    linkedin: '',
    github: '',
    resumeText: ''
  });

  const [settings, setSettings] = useState({
    geminiApiKey: '',
    categories: []
  });

  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (db) {
      if (db.profile) setProfile(db.profile);
      if (db.settings) setSettings(db.settings);
    }
  }, [db]);

  const handleProfileChange = (e) => {
    const { name, value } = e.target;
    setProfile(prev => ({ ...prev, [name]: value }));
  };

  const handleSettingsChange = (e) => {
    const { name, value } = e.target;
    setSettings(prev => ({ ...prev, [name]: value }));
  };

  const handleCategoryToggle = (catId) => {
    setSettings(prev => ({
      ...prev,
      categories: prev.categories.map(cat => 
        cat.id === catId ? { ...cat, enabled: !cat.enabled } : cat
      )
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      // Save Profile
      const profileRes = await fetch('/api/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile)
      });
      const profileData = await profileRes.json();

      // Save Settings
      const settingsRes = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      const settingsData = await settingsRes.json();

      if (profileRes.ok && settingsRes.ok) {
        showToast('Settings & Profile saved successfully!', 'success');
        onSave(); // Refresh root DB state
      } else {
        showToast(profileData.error || settingsData.error || 'Failed to save settings', 'error');
      }
    } catch (err) {
      console.error(err);
      showToast('Connection error. Is backend server running?', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div style={{ animation: 'fadeIn 0.5s ease' }}>
      <form onSubmit={handleSubmit} className="settings-form">
        <div style={{ borderBottom: '1px solid var(--border-light)', paddingBottom: '1rem', marginBottom: '1rem' }}>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontWeight: '700', fontSize: '1.25rem' }}>Personal Profile Info</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            These details are used to auto-fill job applications and write AI-powered cover letters.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input
              type="text"
              name="name"
              value={profile.name}
              onChange={handleProfileChange}
              placeholder="Zain Muhammad"
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input
              type="email"
              name="email"
              value={profile.email}
              onChange={handleProfileChange}
              placeholder="zain@example.com"
              className="form-input"
            />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div className="form-group">
            <label className="form-label">Phone Number</label>
            <input
              type="text"
              name="phone"
              value={profile.phone}
              onChange={handleProfileChange}
              placeholder="+92 300 1234567"
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Portfolio Website</label>
            <input
              type="url"
              name="portfolio"
              value={profile.portfolio}
              onChange={handleProfileChange}
              placeholder="https://myportfolio.dev"
              className="form-input"
            />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div className="form-group">
            <label className="form-label">LinkedIn Profile URL</label>
            <input
              type="url"
              name="linkedin"
              value={profile.linkedin}
              onChange={handleProfileChange}
              placeholder="https://linkedin.com/in/zain"
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label className="form-label">GitHub Profile URL</label>
            <input
              type="url"
              name="github"
              value={profile.github}
              onChange={handleProfileChange}
              placeholder="https://github.com/zain"
              className="form-input"
            />
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Resume Text</label>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-dark)', marginTop: '-0.3rem', marginBottom: '0.2rem' }}>
            Paste the raw text content of your resume (experience, education, skills) to feed the AI generator.
          </p>
          <textarea
            name="resumeText"
            value={profile.resumeText}
            onChange={handleProfileChange}
            placeholder="Work Experience: Senior Developer at TechCorp... Skills: React, Node, Python, AWS..."
            className="form-input form-textarea"
          />
        </div>

        <div style={{ borderBottom: '1px solid var(--border-light)', paddingBottom: '1rem', marginTop: '1.5rem', marginBottom: '1rem' }}>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontWeight: '700', fontSize: '1.25rem' }}>Preferences & Job Search Categories</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Toggle which remote job categories you want to search. Only active categories will be fetched during scraping.
          </p>
        </div>

        <div className="form-group">
          <label className="form-label">Active Search Categories</label>
          <div className="checkbox-grid">
            {settings.categories.map(cat => (
              <label key={cat.id} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={cat.enabled}
                  onChange={() => handleCategoryToggle(cat.id)}
                  className="checkbox-input"
                />
                {cat.name}
              </label>
            ))}
          </div>
        </div>

        <div style={{ borderBottom: '1px solid var(--border-light)', paddingBottom: '1rem', marginTop: '1.5rem', marginBottom: '1rem' }}>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontWeight: '700', fontSize: '1.25rem' }}>AI Assistant Configurations</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Provide your Gemini API key to customize applications with real-time AI cover letters.
          </p>
        </div>

        <div className="form-group">
          <label className="form-label">Gemini API Key</label>
          <input
            type="password"
            name="geminiApiKey"
            value={settings.geminiApiKey}
            onChange={handleSettingsChange}
            placeholder="AIzaSy..."
            className="form-input"
          />
          <p style={{ fontSize: '0.7rem', color: 'var(--text-dark)' }}>
            Your API Key is saved locally on your machine in the db.json file and never uploaded elsewhere.
          </p>
        </div>

        <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
          <button type="submit" disabled={isSaving} className="btn btn-primary">
            {isSaving ? 'Saving Settings...' : 'Save All Settings'}
          </button>
        </div>
      </form>
    </div>
  );
}
