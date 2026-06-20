import Parser from 'rss-parser';
import axios from 'axios';
import crypto from 'crypto';

const parser = new Parser();

// Mapping our category IDs to WeWorkRemotely RSS feed names
const WWR_FEED_MAPs = {
  'software-development': 'remote-programming-jobs.rss', // Fixed mapping
  'design-ux': 'remote-design-jobs.rss',
  'product-management': 'remote-product-jobs.rss',
  'marketing-sales': 'remote-marketing-jobs.rss',
  'devops-sysadmin': 'remote-devops-sysadmin-jobs.rss',
  'customer-support': 'remote-customer-support-jobs.rss'
};

// Mapping our category IDs to Remote.co RSS feed paths
const REMOTE_CO_FEED_MAP = {
  'software-development': 'developer/feed/',
  'design-ux': 'design/feed/',
  'product-management': 'product-management/feed/',
  'marketing-sales': 'marketing/feed/',
  'devops-sysadmin': 'it/feed/',
  'customer-support': 'customer-service/feed/'
};

// Helper function to fetch and parse XML robustly using custom User-Agent
async function fetchAndParseRss(url) {
  const response = await axios.get(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
      'Accept': 'text/xml, application/xml, application/rss+xml, */*'
    },
    timeout: 10000 // 10s timeout
  });
  return await parser.parseString(response.data);
}

async function scrapeWeWorkRemotely(category) {
  const feedFileName = WWR_FEED_MAPs[category];
  if (!feedFileName) return [];

  const url = `https://weworkremotely.com/categories/${feedFileName}`;
  try {
    const feed = await fetchAndParseRss(url);
    return feed.items.map(item => {
      // WWR RSS titles are usually "Company: Title" or "Title at Company"
      let company = 'Unknown';
      let title = item.title;
      if (item.title.includes(':')) {
        const parts = item.title.split(':');
        company = parts[0].trim();
        title = parts.slice(1).join(':').trim();
      }

      // Generate a deterministic ID based on the URL or title
      const id = crypto.createHash('md5').update(item.link || item.title).digest('hex');

      return {
        id,
        title,
        company,
        logo: '',
        url: item.link,
        category,
        source: 'WeWorkRemotely',
        description: item.content || item.contentSnippet || '',
        tags: item.categories || [],
        date: item.isoDate || item.pubDate || new Date().toISOString(),
        salary: ''
      };
    });
  } catch (error) {
    console.error(`Error scraping WeWorkRemotely category ${category}:`, error.message);
    return [];
  }
}

async function scrapeRemoteCo(category) {
  const feedPath = REMOTE_CO_FEED_MAP[category];
  if (!feedPath) return [];

  const url = `https://remote.co/remote-jobs/${feedPath}`;
  try {
    const feed = await fetchAndParseRss(url);
    return feed.items.map(item => {
      // Remote.co titles are usually formatted as "Job Title – Company Name" or "Job Title at Company Name"
      let company = 'Remote.co Job';
      let title = item.title;
      
      const splitters = [' – ', ' - ', ' at '];
      for (const splitter of splitters) {
        if (item.title.includes(splitter)) {
          const parts = item.title.split(splitter);
          title = parts[0].trim();
          company = parts.slice(1).join(splitter).trim();
          break;
        }
      }

      const id = crypto.createHash('md5').update(item.link || item.title).digest('hex');

      return {
        id,
        title,
        company,
        logo: '',
        url: item.link,
        category,
        source: 'Remote.co',
        description: item.content || item.contentSnippet || '',
        tags: item.categories || [],
        date: item.isoDate || item.pubDate || new Date().toISOString(),
        salary: ''
      };
    });
  } catch (error) {
    console.error(`Error scraping Remote.co category ${category}:`, error.message);
    return [];
  }
}

export async function scrapeAllJobs(categoriesToScrape = []) {
  console.log('Starting remote job scrape...', new Date().toLocaleTimeString());
  
  const jobs = [];

  for (const cat of categoriesToScrape) {
    // Fetch WeWorkRemotely jobs for category
    const wwrJobs = await scrapeWeWorkRemotely(cat);
    jobs.push(...wwrJobs);

    // Fetch Remote.co jobs for category
    const rcoJobs = await scrapeRemoteCo(cat);
    jobs.push(...rcoJobs);
  }

  console.log(`Scrape finished. Found ${jobs.length} total jobs matching selected categories.`);
  return jobs;
}
