import { prisma } from '../config/database';
import { logger } from '../config/logger';
import { AppError } from '../middleware/error.middleware';
import { aiService } from './ai.service';
import { PDFDocument, rgb } from 'pdf-lib';

interface ResumeContent {
  personalInfo: {
    name: string;
    email: string;
    phone?: string;
    location?: string;
    linkedin?: string;
    website?: string;
  };
  summary?: string;
  experience: Array<{
    title: string;
    company: string;
    location?: string;
    startDate: string;
    endDate?: string;
    current?: boolean;
    description: string;
    achievements?: string[];
  }>;
  education: Array<{
    degree: string;
    institution: string;
    location?: string;
    graduationDate: string;
    gpa?: string;
  }>;
  skills: Array<{
    category: string;
    items: string[];
  }>;
  certifications?: Array<{
    name: string;
    issuer: string;
    date: string;
  }>;
}

export class ResumeService {
  async createResume(userId: string, name: string, content: ResumeContent, template: string = 'modern') {
    try {
      const resume = await prisma.resume.create({
        data: {
          userId,
          name,
          content: content as any,
          template,
          status: 'DRAFT',
        },
      });

      logger.info('Resume created', { userId, resumeId: resume.id });

      return resume;
    } catch (error) {
      logger.error('Create resume error', { error, userId });
      throw error;
    }
  }

  async getUserResumes(userId: string) {
    try {
      const resumes = await prisma.resume.findMany({
        where: { userId },
        orderBy: { updatedAt: 'desc' },
      });

      return resumes;
    } catch (error) {
      logger.error('Get user resumes error', { error, userId });
      throw error;
    }
  }

  async getResumeById(resumeId: string, userId: string) {
    try {
      const resume = await prisma.resume.findFirst({
        where: {
          id: resumeId,
          userId,
        },
      });

      if (!resume) {
        throw new AppError('Resume not found', 404);
      }

      return resume;
    } catch (error) {
      logger.error('Get resume error', { error, resumeId });
      throw error;
    }
  }

  async updateResume(resumeId: string, userId: string, updates: any) {
    try {
      const resume = await prisma.resume.updateMany({
        where: {
          id: resumeId,
          userId,
        },
        data: updates,
      });

      if (resume.count === 0) {
        throw new AppError('Resume not found', 404);
      }

      logger.info('Resume updated', { userId, resumeId });

      return resume;
    } catch (error) {
      logger.error('Update resume error', { error, resumeId });
      throw error;
    }
  }

  async deleteResume(resumeId: string, userId: string) {
    try {
      await prisma.resume.deleteMany({
        where: {
          id: resumeId,
          userId,
        },
      });

      logger.info('Resume deleted', { userId, resumeId });

      return { message: 'Resume deleted successfully' };
    } catch (error) {
      logger.error('Delete resume error', { error, resumeId });
      throw error;
    }
  }

  async generateResumeWithAI(userId: string, userProfile: any, jobDescription?: string) {
    try {
      const systemPrompt = `You are an expert resume writer. Create a professional, ATS-optimized resume based on the user's profile${jobDescription ? ' and job description' : ''}. Return the resume as a JSON object with the structure: {personalInfo, summary, experience, education, skills, certifications}.`;

      const messages = [
        {
          role: 'user' as const,
          content: `User Profile: ${JSON.stringify(userProfile, null, 2)}${jobDescription ? `\n\nJob Description: ${jobDescription}` : ''}\n\nGenerate a professional resume.`,
        },
      ];

      const response = await aiService.generateCompletion(messages, {
        systemPrompt,
        temperature: 0.7,
        maxTokens: 3000,
        useCache: false,
      });

      let content: ResumeContent;
      try {
        content = JSON.parse(response);
      } catch {
        throw new AppError('Failed to parse AI-generated resume', 500);
      }

      const resume = await this.createResume(
        userId,
        jobDescription ? 'AI Generated Resume (Job Specific)' : 'AI Generated Resume',
        content,
        'modern'
      );

      // Calculate ATS score
      const atsScore = await this.calculateATSScore(resume.id, jobDescription);

      await prisma.resume.update({
        where: { id: resume.id },
        data: { atsScore },
      });

      logger.info('AI resume generated', { userId, resumeId: resume.id });

      return resume;
    } catch (error) {
      logger.error('Generate AI resume error', { error, userId });
      throw error;
    }
  }

  async optimizeResumeForJob(resumeId: string, userId: string, jobDescription: string) {
    try {
      const resume = await this.getResumeById(resumeId, userId);

      const recommendations = await aiService.optimizeResume(resume.content, jobDescription);

      // Create a new version with optimizations
      const optimizedContent = resume.content; // In reality, would apply AI recommendations

      const newResume = await prisma.resume.create({
        data: {
          userId,
          name: `${resume.name} (Optimized)`,
          content: optimizedContent,
          template: resume.template,
          customizedForJobId: jobDescription, // Would be job ID in practice
          version: resume.version + 1,
          status: 'ACTIVE',
        },
      });

      // Calculate new ATS score
      const atsScore = await this.calculateATSScore(newResume.id, jobDescription);

      await prisma.resume.update({
        where: { id: newResume.id },
        data: { atsScore },
      });

      logger.info('Resume optimized', { userId, originalResumeId: resumeId, newResumeId: newResume.id });

      return {
        resume: newResume,
        recommendations,
      };
    } catch (error) {
      logger.error('Optimize resume error', { error, resumeId });
      throw error;
    }
  }

  async calculateATSScore(resumeId: string, jobDescription?: string): Promise<number> {
    try {
      const resume = await prisma.resume.findUnique({
        where: { id: resumeId },
      });

      if (!resume) {
        throw new AppError('Resume not found', 404);
      }

      let score = 50; // Base score

      const content = resume.content as any;

      // Check for essential sections (30 points)
      if (content.personalInfo?.email) score += 5;
      if (content.personalInfo?.phone) score += 5;
      if (content.summary) score += 5;
      if (content.experience?.length > 0) score += 10;
      if (content.education?.length > 0) score += 5;

      // Check formatting (20 points)
      if (content.experience?.every((exp: any) => exp.title && exp.company)) score += 10;
      if (content.skills?.length > 0) score += 10;

      // Job description keyword matching (30 points)
      if (jobDescription) {
        const keywords = this.extractKeywords(jobDescription);
        const resumeText = JSON.stringify(content).toLowerCase();
        const matchedKeywords = keywords.filter((keyword) =>
          resumeText.includes(keyword.toLowerCase())
        );
        score += (matchedKeywords.length / keywords.length) * 30;
      }

      return Math.min(Math.round(score), 100);
    } catch (error) {
      logger.error('Calculate ATS score error', { error, resumeId });
      return 50; // Default score on error
    }
  }

  async generatePDF(resumeId: string, userId: string): Promise<Buffer> {
    try {
      const resume = await this.getResumeById(resumeId, userId);

      // Create PDF document
      const pdfDoc = await PDFDocument.create();
      const page = pdfDoc.addPage([612, 792]); // Letter size

      const { height } = page.getSize();
      const fontSize = 12;

      const content = resume.content as any;

      // Simple PDF generation (in reality, would use proper templating)
      let yPosition = height - 50;

      page.drawText(content.personalInfo?.name || 'Resume', {
        x: 50,
        y: yPosition,
        size: 20,
        color: rgb(0, 0, 0),
      });

      const pdfBytes = await pdfDoc.save();

      logger.info('PDF generated', { userId, resumeId });

      return Buffer.from(pdfBytes);
    } catch (error) {
      logger.error('Generate PDF error', { error, resumeId });
      throw new AppError('Failed to generate PDF', 500);
    }
  }

  private extractKeywords(text: string): string[] {
    // Simple keyword extraction (in reality, would use NLP)
    const words = text.toLowerCase().match(/\b\w+\b/g) || [];
    const commonWords = new Set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for']);
    return [...new Set(words.filter((word) => word.length > 3 && !commonWords.has(word)))].slice(0, 20);
  }
}

export const resumeService = new ResumeService();
