import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { getDb, saveDb, updateProfile, updateSettings, saveJobs, updateJob } from './services/db.js';
import { scrapeAllJobs } from './services/scrapers.js';
import { generateCoverLetter } from './services/aiService.js';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json({ limit: '10mb' })); // Support larger payloads for resumes

// Route: Get entire state
app.get('/api/db', async (req, res) => {
  try {
    const db = await getDb();
    res.json(db);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Route: Update Profile
app.post('/api/profile', async (req, res) => {
  try {
    const updated = await updateProfile(req.body);
    res.json({ message: 'Profile updated successfully', profile: updated });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Route: Update Settings
app.post('/api/settings', async (req, res) => {
  try {
    const updated = await updateSettings(req.body);
    res.json({ message: 'Settings updated successfully', settings: updated });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Route: Trigger manual scrape
app.post('/api/scrape', async (req, res) => {
  try {
    const db = await getDb();
    // Get enabled category ids
    const activeCategories = db.settings.categories
      .filter(cat => cat.enabled)
      .map(cat => cat.id);

    if (activeCategories.length === 0) {
      return res.status(400).json({ error: 'No active categories selected. Please enable at least one category in Settings.' });
    }

    const scrapedJobs = await scrapeAllJobs(activeCategories);
    const { jobs, newCount } = await saveJobs(scrapedJobs);

    res.json({
      message: `Scrape completed successfully.`,
      newCount,
      totalCount: jobs.length,
      jobs
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Route: Update single job details (status, notes, cover letter, etc.)
app.put('/api/jobs/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const updatedJob = await updateJob(id, req.body);
    if (!updatedJob) {
      return res.status(404).json({ error: 'Job not found' });
    }
    res.json({ message: 'Job updated successfully', job: updatedJob });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Route: Generate Cover Letter for a job
app.post('/api/jobs/:id/cover-letter', async (req, res) => {
  try {
    const { id } = req.params;
    const db = await getDb();
    
    const job = db.jobs.find(j => j.id === id);
    if (!job) {
      return res.status(404).json({ error: 'Job not found' });
    }

    // Get API Key: check request body, then settings, then env
    const apiKey = req.body.apiKey || db.settings.geminiApiKey || process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return res.status(400).json({ error: 'Gemini API Key is missing. Please add your key in Settings.' });
    }

    const coverLetter = await generateCoverLetter({
      apiKey,
      resumeText: db.profile.resumeText,
      jobTitle: job.title,
      company: job.company,
      jobDescription: job.description,
      profile: db.profile
    });

    // Save generated cover letter to the database
    const updatedJob = await updateJob(id, { coverLetter });

    res.json({
      message: 'Cover letter generated successfully',
      coverLetter,
      job: updatedJob
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Start Server
app.listen(PORT, () => {
  console.log(`Remote Job Scraper backend running at http://localhost:${PORT}`);
});
