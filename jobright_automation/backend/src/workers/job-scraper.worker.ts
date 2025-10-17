import { scraperQueue } from '../config/queues';
import { prisma } from '../config/database';
import { logger } from '../config/logger';
import { chromium } from 'playwright';

// Process job scraping tasks
scraperQueue.process('scrape-jobs', async (job) => {
  const { platform, searchQuery, location } = job.data;

  logger.info('Starting job scraping', { platform, searchQuery, location });

  try {
    let jobs: any[] = [];

    switch (platform) {
      case 'linkedin':
        jobs = await scrapeLinkedIn(searchQuery, location);
        break;
      case 'indeed':
        jobs = await scrapeIndeed(searchQuery, location);
        break;
      case 'glassdoor':
        jobs = await scrapeGlassdoor(searchQuery, location);
        break;
      default:
        throw new Error(`Unsupported platform: ${platform}`);
    }

    // Store jobs in database
    for (const jobData of jobs) {
      await prisma.job.upsert({
        where: { sourceId: jobData.sourceId },
        update: jobData,
        create: jobData,
      });
    }

    logger.info('Job scraping completed', {
      platform,
      jobsFound: jobs.length,
    });

    return { success: true, jobsFound: jobs.length };
  } catch (error) {
    logger.error('Job scraping failed', { error, platform });
    throw error;
  }
});

async function scrapeLinkedIn(query: string, location: string): Promise<any[]> {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    const url = `https://www.linkedin.com/jobs/search/?keywords=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}`;
    await page.goto(url);

    // Wait for job cards to load
    await page.waitForSelector('.job-card-container', { timeout: 10000 });

    // Extract job data
    const jobs = await page.$$eval('.job-card-container', (cards) => {
      return cards.map((card) => {
        const titleEl = card.querySelector('.job-card-list__title');
        const companyEl = card.querySelector('.job-card-container__company-name');
        const locationEl = card.querySelector('.job-card-container__metadata-item');
        const linkEl = card.querySelector('a');

        return {
          title: titleEl?.textContent?.trim() || '',
          company: companyEl?.textContent?.trim() || '',
          location: locationEl?.textContent?.trim() || '',
          sourceUrl: linkEl?.href || '',
          source: 'linkedin',
          sourceId: linkEl?.href || '',
          status: 'ACTIVE',
          postedAt: new Date(),
        };
      });
    });

    return jobs;
  } catch (error) {
    logger.error('LinkedIn scraping error', { error });
    return [];
  } finally {
    await browser.close();
  }
}

async function scrapeIndeed(query: string, location: string): Promise<any[]> {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    const url = `https://www.indeed.com/jobs?q=${encodeURIComponent(query)}&l=${encodeURIComponent(location)}`;
    await page.goto(url, { waitUntil: 'domcontentloaded' });

    // Wait for job cards to load
    await page.waitForSelector('.job_seen_beacon, .jobCard', { timeout: 10000 }).catch(() => {
      logger.warn('Indeed job cards timeout - page may have changed structure');
    });

    // Extract job data
    const jobs = await page.$$eval('.job_seen_beacon, .jobCard', (cards) => {
      return cards.map((card) => {
        const titleEl = card.querySelector('h2.jobTitle a, .jobTitle span');
        const companyEl = card.querySelector('[data-testid="company-name"], .companyName');
        const locationEl = card.querySelector('[data-testid="text-location"], .companyLocation');
        const salaryEl = card.querySelector('.salary-snippet, .metadata.salary-snippet-container');
        const linkEl = card.querySelector('h2.jobTitle a, a.jcs-JobTitle');
        const descriptionEl = card.querySelector('.job-snippet, .jobCardShelfContainer li');

        const jobId = linkEl?.getAttribute('data-jk') || linkEl?.getAttribute('id') || '';
        const href = linkEl?.getAttribute('href') || '';
        const fullUrl = href.startsWith('http') ? href : `https://www.indeed.com${href}`;

        return {
          title: titleEl?.textContent?.trim() || '',
          company: companyEl?.textContent?.trim() || '',
          location: locationEl?.textContent?.trim() || '',
          sourceUrl: fullUrl,
          source: 'indeed',
          sourceId: `indeed-${jobId}`,
          status: 'ACTIVE',
          salary: salaryEl?.textContent?.trim() || null,
          description: descriptionEl?.textContent?.trim() || '',
          postedAt: new Date(),
        };
      }).filter(job => job.title && job.company);
    });

    logger.info('Indeed scraping successful', { jobsFound: jobs.length });
    return jobs;
  } catch (error: any) {
    logger.error('Indeed scraping error', { error: error.message });
    return [];
  } finally {
    await browser.close();
  }
}

async function scrapeGlassdoor(query: string, location: string): Promise<any[]> {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    const url = `https://www.glassdoor.com/Job/jobs.htm?sc.keyword=${encodeURIComponent(query)}&locT=C&locId=&locKeyword=${encodeURIComponent(location)}`;
    await page.goto(url, { waitUntil: 'domcontentloaded' });

    // Wait for job cards to load
    await page.waitForSelector('[data-test="job-listing"], .react-job-listing', { timeout: 10000 }).catch(() => {
      logger.warn('Glassdoor job cards timeout - page may have changed structure');
    });

    // Extract job data
    const jobs = await page.$$eval('[data-test="job-listing"], .react-job-listing, li[data-id]', (cards) => {
      return cards.map((card) => {
        const titleEl = card.querySelector('[data-test="job-title"], .jobTitle, a.jobLink');
        const companyEl = card.querySelector('[data-test="employer-name"], .employerName');
        const locationEl = card.querySelector('[data-test="emp-location"], .location');
        const salaryEl = card.querySelector('[data-test="detailSalary"], .salaryEstimate');
        const linkEl = card.querySelector('a[data-test="job-link"], a.jobLink');
        const ratingEl = card.querySelector('.rating, [data-test="rating"]');

        const jobId = card.getAttribute('data-id') || card.getAttribute('data-job-id') || '';
        const href = linkEl?.getAttribute('href') || '';
        const fullUrl = href.startsWith('http') ? href : `https://www.glassdoor.com${href}`;

        return {
          title: titleEl?.textContent?.trim() || '',
          company: companyEl?.textContent?.trim() || '',
          location: locationEl?.textContent?.trim() || '',
          sourceUrl: fullUrl,
          source: 'glassdoor',
          sourceId: `glassdoor-${jobId}`,
          status: 'ACTIVE',
          salary: salaryEl?.textContent?.trim() || null,
          companyRating: ratingEl?.textContent?.trim() || null,
          postedAt: new Date(),
        };
      }).filter(job => job.title && job.company);
    });

    logger.info('Glassdoor scraping successful', { jobsFound: jobs.length });
    return jobs;
  } catch (error: any) {
    logger.error('Glassdoor scraping error', { error: error.message });
    return [];
  } finally {
    await browser.close();
  }
}

logger.info('Job scraper worker initialized');
