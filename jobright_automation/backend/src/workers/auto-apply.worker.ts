import { applicationQueue } from '../config/queues';
import { prisma } from '../config/database';
import { logger } from '../config/logger';
import { chromium, Page } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import axios from 'axios';

interface ApplicationData {
  resume: any;
  coverLetter?: string;
  user?: any;
}

interface PlatformHandler {
  detect: (url: string) => boolean;
  apply: (page: Page, data: ApplicationData) => Promise<boolean>;
}

// Platform-specific handlers
const platformHandlers: PlatformHandler[] = [
  {
    detect: (url: string) => url.includes('linkedin.com'),
    apply: handleLinkedInEasyApply,
  },
  {
    detect: (url: string) => url.includes('indeed.com'),
    apply: handleIndeedApplication,
  },
  {
    detect: (url: string) => url.includes('glassdoor.com'),
    apply: handleGlassdoorApplication,
  },
];

// Process auto-application tasks with retry logic
applicationQueue.process('auto-apply', 3, async (job) => {
  const { applicationId, userId, jobId, resumeId, coverLetter } = job.data;

  logger.info('Starting auto-application', { applicationId, jobId, attempt: job.attemptsMade + 1 });

  let browser;
  try {
    // Get job, resume, and user data
    const [jobData, resume, user] = await Promise.all([
      prisma.job.findUnique({ where: { id: jobId } }),
      prisma.resume.findUnique({ where: { id: resumeId } }),
      prisma.user.findUnique({
        where: { id: userId },
        include: { profile: true, preferences: true }
      }),
    ]);

    if (!jobData || !resume || !user) {
      throw new Error('Job, resume, or user not found');
    }

    // Launch browser for automation
    browser = await chromium.launch({
      headless: process.env.NODE_ENV === 'production',
      args: ['--disable-blink-features=AutomationControlled']
    });

    const context = await browser.newContext({
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
      viewport: { width: 1920, height: 1080 },
    });

    const page = await context.newPage();

    try {
      // Navigate to application page with retry
      await page.goto(jobData.sourceUrl!, { waitUntil: 'domcontentloaded', timeout: 30000 });

      // Wait for page to be ready
      await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {
        logger.warn('Network idle timeout - proceeding anyway');
      });

      // Check for CAPTCHA
      const hasCaptcha = await detectCaptcha(page);
      if (hasCaptcha) {
        logger.warn('CAPTCHA detected', { applicationId });
        await solveCaptcha(page, applicationId);
      }

      // Try platform-specific handler first
      const handler = platformHandlers.find(h => h.detect(jobData.sourceUrl!));
      let success = false;

      if (handler) {
        logger.info('Using platform-specific handler', { platform: jobData.source });
        success = await handler.apply(page, {
          resume: resume.content,
          coverLetter,
          user: { ...user, profile: user.profile }
        });
      } else {
        // Fall back to generic form filling
        logger.info('Using generic form filler');
        success = await fillGenericApplicationForm(page, {
          resume: resume.content,
          coverLetter,
          user: { ...user, profile: user.profile }
        });
      }

      if (success) {
        // Take screenshot of confirmation
        const screenshotPath = path.join(os.tmpdir(), `application-${applicationId}.png`);
        await page.screenshot({ path: screenshotPath, fullPage: true });

        // Update application status
        await prisma.application.update({
          where: { id: applicationId },
          data: {
            status: 'SUBMITTED',
            applicationUrl: page.url(),
            submittedAt: new Date(),
          },
        });

        logger.info('Auto-application successful', { applicationId, url: page.url() });

        return { success: true, applicationId, url: page.url() };
      } else {
        throw new Error('Failed to fill and submit application form');
      }
    } finally {
      await page.close();
      await context.close();
    }
  } catch (error: any) {
    logger.error('Auto-application failed', {
      error: error.message,
      applicationId,
      attempt: job.attemptsMade + 1
    });

    // Update application with error
    await prisma.application.update({
      where: { id: applicationId },
      data: {
        status: job.attemptsMade >= 2 ? 'FAILED' : 'PENDING',
        notes: `Auto-application failed (attempt ${job.attemptsMade + 1}): ${error.message}`,
      },
    });

    throw error;
  } finally {
    if (browser) {
      await browser.close();
    }
  }
});

// LinkedIn Easy Apply handler
async function handleLinkedInEasyApply(page: Page, data: ApplicationData): Promise<boolean> {
  try {
    // Click Easy Apply button
    const easyApplyButton = await page.$('button:has-text("Easy Apply"), button[aria-label*="Easy Apply"]');
    if (!easyApplyButton) {
      logger.warn('Easy Apply button not found');
      return false;
    }

    await easyApplyButton.click();
    await page.waitForTimeout(2000);

    // Multi-step form navigation
    let currentStep = 1;
    const maxSteps = 10;

    while (currentStep <= maxSteps) {
      logger.info(`LinkedIn Easy Apply - Step ${currentStep}`);

      // Fill current page
      await fillGenericApplicationForm(page, data);

      // Check for submit vs next
      const submitButton = await page.$('button[aria-label="Submit application"], button:has-text("Submit application")');
      if (submitButton) {
        await submitButton.click();
        logger.info('Application submitted via LinkedIn Easy Apply');
        await page.waitForTimeout(3000);
        return true;
      }

      // Click next
      const nextButton = await page.$('button[aria-label="Continue to next step"], button:has-text("Next"), button:has-text("Review")');
      if (nextButton) {
        await nextButton.click();
        await page.waitForTimeout(2000);
        currentStep++;
      } else {
        logger.warn('Could not find next or submit button');
        return false;
      }
    }

    return false;
  } catch (error: any) {
    logger.error('LinkedIn Easy Apply error', { error: error.message });
    return false;
  }
}

// Indeed application handler
async function handleIndeedApplication(page: Page, data: ApplicationData): Promise<boolean> {
  try {
    // Click apply button
    const applyButton = await page.$('button[id*="apply"], a:has-text("Apply now"), button:has-text("Apply")');
    if (applyButton) {
      await applyButton.click();
      await page.waitForTimeout(2000);
    }

    // Fill form
    await fillGenericApplicationForm(page, data);

    // Submit
    const submitButton = await page.$('button[type="submit"]:has-text("Submit"), button[id*="submit"], input[type="submit"]');
    if (submitButton) {
      await submitButton.click();
      await page.waitForTimeout(3000);
      return true;
    }

    return false;
  } catch (error: any) {
    logger.error('Indeed application error', { error: error.message });
    return false;
  }
}

// Glassdoor application handler
async function handleGlassdoorApplication(page: Page, data: ApplicationData): Promise<boolean> {
  try {
    // Click apply button
    const applyButton = await page.$('button:has-text("Apply Now"), a:has-text("Apply"), button[data-test="apply-button"]');
    if (applyButton) {
      await applyButton.click();
      await page.waitForTimeout(2000);
    }

    // Fill form
    await fillGenericApplicationForm(page, data);

    // Submit
    const submitButton = await page.$('button:has-text("Submit Application"), button[type="submit"]');
    if (submitButton) {
      await submitButton.click();
      await page.waitForTimeout(3000);
      return true;
    }

    return false;
  } catch (error: any) {
    logger.error('Glassdoor application error', { error: error.message });
    return false;
  }
}

// Generic form filling with comprehensive field detection
async function fillGenericApplicationForm(page: Page, data: ApplicationData): Promise<boolean> {
  try {
    const { resume, coverLetter, user } = data;
    const personalInfo = resume.personalInfo || {};
    const profile = user?.profile || {};

    // Get all form elements
    const inputs = await page.$$('input, textarea, select');

    for (const input of inputs) {
      const type = await input.getAttribute('type');
      const name = (await input.getAttribute('name'))?.toLowerCase() || '';
      const id = (await input.getAttribute('id'))?.toLowerCase() || '';
      const placeholder = (await input.getAttribute('placeholder'))?.toLowerCase() || '';
      const label = await input.evaluate(el => {
        const labelEl = el.labels?.[0] || document.querySelector(`label[for="${el.id}"]`);
        return labelEl?.textContent?.toLowerCase() || '';
      });

      const fieldIdentifier = `${name} ${id} ${placeholder} ${label}`;

      try {
        // Skip hidden and disabled fields
        const isVisible = await input.isVisible();
        const isEnabled = await input.isEnabled();
        if (!isVisible || !isEnabled) continue;

        // File upload
        if (type === 'file') {
          const resumePath = await generateResumeFile(resume);
          await input.setInputFiles(resumePath);
          logger.info('Uploaded resume file');
          continue;
        }

        // Checkbox/radio
        if (type === 'checkbox' || type === 'radio') {
          // Handle common checkbox fields
          if (fieldIdentifier.includes('authorize') || fieldIdentifier.includes('eligible')) {
            await input.check();
          } else if (fieldIdentifier.includes('veteran') || fieldIdentifier.includes('disability')) {
            // Skip optional demographic fields
            continue;
          }
          continue;
        }

        // Select dropdown
        if (await input.evaluate(el => el.tagName === 'SELECT')) {
          await fillSelectField(input, fieldIdentifier, data);
          continue;
        }

        // Text fields
        let value = '';

        // Name fields
        if (fieldIdentifier.match(/first.*name|firstname/)) {
          value = personalInfo.firstName || '';
        } else if (fieldIdentifier.match(/last.*name|lastname|surname/)) {
          value = personalInfo.lastName || '';
        } else if (fieldIdentifier.match(/full.*name|^name$/) && !fieldIdentifier.includes('company')) {
          value = `${personalInfo.firstName || ''} ${personalInfo.lastName || ''}`.trim();
        }
        // Contact fields
        else if (fieldIdentifier.includes('email')) {
          value = personalInfo.email || user?.email || '';
        } else if (fieldIdentifier.match(/phone|mobile|telephone/)) {
          value = personalInfo.phone || '';
        }
        // Address fields
        else if (fieldIdentifier.includes('address') && !fieldIdentifier.includes('email')) {
          value = personalInfo.address || '';
        } else if (fieldIdentifier.includes('city')) {
          value = personalInfo.city || '';
        } else if (fieldIdentifier.match(/state|province/)) {
          value = personalInfo.state || '';
        } else if (fieldIdentifier.match(/zip|postal/)) {
          value = personalInfo.zipCode || '';
        } else if (fieldIdentifier.includes('country')) {
          value = personalInfo.country || '';
        }
        // Professional fields
        else if (fieldIdentifier.match(/linkedin|profile.*url/)) {
          value = profile.linkedinUrl || '';
        } else if (fieldIdentifier.match(/portfolio|website|github/)) {
          value = profile.portfolioUrl || profile.githubUrl || '';
        } else if (fieldIdentifier.match(/cover.*letter|motivation/)) {
          value = coverLetter || '';
        } else if (fieldIdentifier.match(/salary|compensation/)) {
          value = ''; // Skip salary fields
        } else if (fieldIdentifier.match(/start.*date|available/)) {
          value = 'Immediately';
        }
        // Work authorization
        else if (fieldIdentifier.match(/sponsor|visa/)) {
          value = profile.requiresSponsorship ? 'Yes' : 'No';
        } else if (fieldIdentifier.match(/authorize|eligible.*work/)) {
          value = 'Yes';
        }

        if (value) {
          await input.fill(value);
          logger.debug('Filled field', { field: fieldIdentifier.substring(0, 50), value: value.substring(0, 50) });
        }
      } catch (error: any) {
        logger.debug('Error filling field', { field: fieldIdentifier.substring(0, 50), error: error.message });
      }
    }

    return true;
  } catch (error: any) {
    logger.error('Generic form filling error', { error: error.message });
    return false;
  }
}

// Fill select/dropdown fields
async function fillSelectField(select: any, fieldIdentifier: string, data: ApplicationData): Promise<void> {
  const options = await select.$$eval('option', (opts: any[]) =>
    opts.map(o => ({ value: o.value, text: o.textContent?.toLowerCase() || '' }))
  );

  let selectedValue = '';

  // Education level
  if (fieldIdentifier.match(/education|degree/)) {
    const education = data.resume.education?.[0];
    if (education?.degree) {
      const matchingOption = options.find(o =>
        o.text.includes(education.degree.toLowerCase())
      );
      selectedValue = matchingOption?.value || '';
    }
  }
  // Years of experience
  else if (fieldIdentifier.match(/experience|years/)) {
    const experience = data.resume.experience || [];
    const totalYears = experience.reduce((sum: number, exp: any) => {
      const start = new Date(exp.startDate);
      const end = exp.current ? new Date() : new Date(exp.endDate);
      return sum + (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24 * 365);
    }, 0);

    const matchingOption = options.find(o => {
      const match = o.text.match(/(\d+)/);
      if (match) {
        const years = parseInt(match[1]);
        return Math.abs(years - totalYears) < 2;
      }
      return false;
    });
    selectedValue = matchingOption?.value || options[0]?.value || '';
  }
  // Gender/ethnicity - skip
  else if (fieldIdentifier.match(/gender|race|ethnicity/)) {
    selectedValue = options.find(o => o.text.includes('decline') || o.text.includes('prefer not'))?.value || '';
  }

  if (selectedValue) {
    await select.selectOption(selectedValue);
  }
}

// Generate resume PDF file from content
async function generateResumeFile(resumeContent: any): Promise<string> {
  const resumePath = path.join(os.tmpdir(), `resume-${Date.now()}.pdf`);

  // In production, this would use a proper PDF generator
  // For now, create a simple text file as placeholder
  const resumeText = JSON.stringify(resumeContent, null, 2);
  fs.writeFileSync(resumePath, resumeText);

  return resumePath;
}

// Detect CAPTCHA on page
async function detectCaptcha(page: Page): Promise<boolean> {
  const captchaSelectors = [
    'iframe[src*="recaptcha"]',
    'iframe[src*="hcaptcha"]',
    '.g-recaptcha',
    '#captcha',
    '[class*="captcha"]',
  ];

  for (const selector of captchaSelectors) {
    const element = await page.$(selector);
    if (element) {
      return true;
    }
  }

  return false;
}

// Solve CAPTCHA (integration with 2Captcha/Anti-Captcha)
async function solveCaptcha(page: Page, applicationId: string): Promise<void> {
  const captchaApiKey = process.env.CAPTCHA_API_KEY;

  if (!captchaApiKey) {
    logger.warn('CAPTCHA detected but no API key configured', { applicationId });
    throw new Error('CAPTCHA present - manual intervention required');
  }

  try {
    // Check for reCAPTCHA
    const recaptchaSiteKey = await page.$eval(
      '.g-recaptcha',
      (el: any) => el.getAttribute('data-sitekey')
    ).catch(() => null);

    if (recaptchaSiteKey) {
      logger.info('Solving reCAPTCHA', { applicationId });

      // Call 2Captcha API
      const response = await axios.post('https://2captcha.com/in.php', null, {
        params: {
          key: captchaApiKey,
          method: 'userrecaptcha',
          googlekey: recaptchaSiteKey,
          pageurl: page.url(),
          json: 1,
        },
      });

      if (response.data.status === 1) {
        const captchaId = response.data.request;

        // Poll for solution
        for (let i = 0; i < 30; i++) {
          await new Promise(resolve => setTimeout(resolve, 5000));

          const result = await axios.get('https://2captcha.com/res.php', {
            params: {
              key: captchaApiKey,
              action: 'get',
              id: captchaId,
              json: 1,
            },
          });

          if (result.data.status === 1) {
            // Inject solution
            await page.evaluate((token: string) => {
              (window as any).grecaptcha.getResponse = () => token;
              const textarea = document.getElementById('g-recaptcha-response');
              if (textarea) {
                (textarea as any).innerHTML = token;
              }
            }, result.data.request);

            logger.info('CAPTCHA solved successfully', { applicationId });
            return;
          }
        }
      }
    }

    throw new Error('Failed to solve CAPTCHA');
  } catch (error: any) {
    logger.error('CAPTCHA solving failed', { error: error.message, applicationId });
    throw new Error('CAPTCHA solving failed - manual intervention required');
  }
}

logger.info('Auto-apply worker initialized');
