import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dbPath = path.join(__dirname, '../data/db.json');

export async function getDb() {
  try {
    const raw = await fs.readFile(dbPath, 'utf-8');
    return JSON.parse(raw);
  } catch (err) {
    // If not found, return a default structure
    return {
      jobs: [],
      profile: { name: '', email: '', phone: '', portfolio: '', linkedin: '', github: '', resumeText: '' },
      settings: {
        geminiApiKey: '',
        categories: [
          { id: 'software-development', name: 'Software Development', enabled: true },
          { id: 'design-ux', name: 'Design & UX', enabled: true },
          { id: 'product-management', name: 'Product Management', enabled: false },
          { id: 'marketing-sales', name: 'Marketing & Sales', enabled: false },
          { id: 'devops-sysadmin', name: 'DevOps & SysAdmin', enabled: false },
          { id: 'customer-support', name: 'Customer Support', enabled: false }
        ]
      }
    };
  }
}

export async function saveDb(data) {
  await fs.mkdir(path.dirname(dbPath), { recursive: true });
  await fs.writeFile(dbPath, JSON.stringify(data, null, 2), 'utf-8');
}

export async function updateProfile(profileUpdates) {
  const db = await getDb();
  db.profile = { ...db.profile, ...profileUpdates };
  await saveDb(db);
  return db.profile;
}

export async function updateSettings(settingsUpdates) {
  const db = await getDb();
  db.settings = { ...db.settings, ...settingsUpdates };
  await saveDb(db);
  return db.settings;
}

export async function saveJobs(scrapedJobs) {
  const db = await getDb();
  const existingJobsMap = new Map(db.jobs.map(j => [j.id, j]));
  
  let newCount = 0;
  
  const mergedJobs = scrapedJobs.map(newJob => {
    if (existingJobsMap.has(newJob.id)) {
      // Preserve existing user edits (status, notes, cover letters, etc.)
      const existing = existingJobsMap.get(newJob.id);
      return {
        ...newJob,
        status: existing.status || 'not-applied',
        coverLetter: existing.coverLetter || '',
        notes: existing.notes || ''
      };
    } else {
      newCount++;
      return {
        ...newJob,
        status: 'not-applied',
        coverLetter: '',
        notes: ''
      };
    }
  });

  // Keep any existing jobs that weren't in the scraped list (in case they are bookmarked or applied)
  const scrapedIds = new Set(scrapedJobs.map(j => j.id));
  const remainingJobs = db.jobs.filter(j => !scrapedIds.has(j.id));
  
  db.jobs = [...mergedJobs, ...remainingJobs];
  
  // Sort jobs by date (newest first)
  db.jobs.sort((a, b) => new Date(b.date || 0) - new Date(a.date || 0));

  await saveDb(db);
  return { jobs: db.jobs, newCount };
}

export async function updateJob(jobId, updates) {
  const db = await getDb();
  db.jobs = db.jobs.map(job => {
    if (job.id === jobId) {
      return { ...job, ...updates };
    }
    return job;
  });
  await saveDb(db);
  return db.jobs.find(job => job.id === jobId);
}
