import Anthropic from '@anthropic-ai/sdk';
import OpenAI from 'openai';
import { logger } from '../config/logger';
import { AppError } from '../middleware/error.middleware';
import { cache } from '../config/redis';

type AIProvider = 'anthropic' | 'openai';

interface AIMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface AIRequestOptions {
  provider?: AIProvider;
  model?: string;
  temperature?: number;
  maxTokens?: number;
  systemPrompt?: string;
  useCache?: boolean;
}

export class AIService {
  private anthropic: Anthropic | null = null;
  private openai: OpenAI | null = null;

  constructor() {
    // Initialize AI clients if API keys are available
    if (process.env.ANTHROPIC_API_KEY) {
      this.anthropic = new Anthropic({
        apiKey: process.env.ANTHROPIC_API_KEY,
      });
    }

    if (process.env.OPENAI_API_KEY) {
      this.openai = new OpenAI({
        apiKey: process.env.OPENAI_API_KEY,
      });
    }
  }

  async generateCompletion(
    messages: AIMessage[],
    options: AIRequestOptions = {}
  ): Promise<string> {
    const {
      provider = 'anthropic',
      model,
      temperature = 0.7,
      maxTokens = 2000,
      systemPrompt,
      useCache = true,
    } = options;

    // Check cache
    if (useCache) {
      const cacheKey = this.getCacheKey(messages, options);
      const cached = await cache.get<string>(cacheKey);
      if (cached) {
        logger.debug('AI response served from cache');
        return cached;
      }
    }

    try {
      let response: string;

      if (provider === 'anthropic' && this.anthropic) {
        response = await this.generateAnthropicCompletion(
          messages,
          model || 'claude-3-5-sonnet-20241022',
          temperature,
          maxTokens,
          systemPrompt
        );
      } else if (provider === 'openai' && this.openai) {
        response = await this.generateOpenAICompletion(
          messages,
          model || 'gpt-4-turbo-preview',
          temperature,
          maxTokens,
          systemPrompt
        );
      } else {
        throw new AppError('AI provider not configured', 500);
      }

      // Cache response
      if (useCache) {
        const cacheKey = this.getCacheKey(messages, options);
        await cache.set(cacheKey, response, 3600); // 1 hour TTL
      }

      return response;
    } catch (error) {
      logger.error('AI completion error', { error, provider });
      throw new AppError('Failed to generate AI completion', 500);
    }
  }

  private async generateAnthropicCompletion(
    messages: AIMessage[],
    model: string,
    temperature: number,
    maxTokens: number,
    systemPrompt?: string
  ): Promise<string> {
    if (!this.anthropic) {
      throw new AppError('Anthropic client not initialized', 500);
    }

    const response = await this.anthropic.messages.create({
      model,
      max_tokens: maxTokens,
      temperature,
      system: systemPrompt,
      messages: messages.map((msg) => ({
        role: msg.role,
        content: msg.content,
      })),
    });

    const content = response.content[0];
    if (content.type === 'text') {
      return content.text;
    }

    throw new AppError('Unexpected response format from Anthropic', 500);
  }

  private async generateOpenAICompletion(
    messages: AIMessage[],
    model: string,
    temperature: number,
    maxTokens: number,
    systemPrompt?: string
  ): Promise<string> {
    if (!this.openai) {
      throw new AppError('OpenAI client not initialized', 500);
    }

    const openaiMessages: any[] = [];

    if (systemPrompt) {
      openaiMessages.push({ role: 'system', content: systemPrompt });
    }

    openaiMessages.push(...messages);

    const response = await this.openai.chat.completions.create({
      model,
      messages: openaiMessages,
      temperature,
      max_tokens: maxTokens,
    });

    return response.choices[0].message.content || '';
  }

  async generateCareerAdvice(userProfile: any, question: string): Promise<string> {
    const systemPrompt = `You are Orion, a professional AI career advisor. You help job seekers with career guidance, job search strategies, resume improvement, interview preparation, and salary negotiation. Be helpful, encouraging, and provide actionable advice.`;

    const messages: AIMessage[] = [
      {
        role: 'user',
        content: `User Profile: ${JSON.stringify(userProfile, null, 2)}\n\nQuestion: ${question}`,
      },
    ];

    return this.generateCompletion(messages, {
      systemPrompt,
      temperature: 0.8,
      maxTokens: 1500,
    });
  }

  async optimizeResume(resumeContent: any, jobDescription: string): Promise<string> {
    const systemPrompt = `You are an expert resume writer and ATS optimization specialist. Analyze the resume and job description, then provide specific recommendations to improve the resume's match with the job requirements and ATS compatibility.`;

    const messages: AIMessage[] = [
      {
        role: 'user',
        content: `Resume: ${JSON.stringify(resumeContent, null, 2)}\n\nJob Description: ${jobDescription}\n\nProvide specific recommendations for optimizing this resume.`,
      },
    ];

    return this.generateCompletion(messages, {
      systemPrompt,
      temperature: 0.7,
    });
  }

  async generateCoverLetter(
    userProfile: any,
    jobDescription: string,
    companyInfo?: string
  ): Promise<string> {
    const systemPrompt = `You are an expert cover letter writer. Create compelling, personalized cover letters that highlight the candidate's relevant experience and enthusiasm for the role.`;

    const messages: AIMessage[] = [
      {
        role: 'user',
        content: `User Profile: ${JSON.stringify(userProfile, null, 2)}\n\nJob Description: ${jobDescription}\n\nCompany Info: ${companyInfo || 'Not provided'}\n\nWrite a professional cover letter (250-400 words) for this job application.`,
      },
    ];

    return this.generateCompletion(messages, {
      systemPrompt,
      temperature: 0.8,
      maxTokens: 1000,
    });
  }

  async generateInterviewQuestions(jobDescription: string, role: string): Promise<string[]> {
    const systemPrompt = `You are an interview preparation expert. Generate relevant interview questions based on the job description and role.`;

    const messages: AIMessage[] = [
      {
        role: 'user',
        content: `Job Description: ${jobDescription}\n\nRole: ${role}\n\nGenerate 10 likely interview questions for this position. Return as a JSON array of strings.`,
      },
    ];

    const response = await this.generateCompletion(messages, {
      systemPrompt,
      temperature: 0.7,
    });

    try {
      return JSON.parse(response);
    } catch {
      // Fallback if not valid JSON
      return response.split('\n').filter((q) => q.trim());
    }
  }

  async provideInterviewFeedback(question: string, answer: string): Promise<string> {
    const systemPrompt = `You are an interview coach. Provide constructive feedback on interview answers using the STAR method (Situation, Task, Action, Result) framework.`;

    const messages: AIMessage[] = [
      {
        role: 'user',
        content: `Question: ${question}\n\nCandidate's Answer: ${answer}\n\nProvide detailed feedback on this answer and suggestions for improvement.`,
      },
    ];

    return this.generateCompletion(messages, {
      systemPrompt,
      temperature: 0.7,
    });
  }

  async analyzeSalary(
    jobTitle: string,
    location: string,
    yearsOfExperience: number,
    offerAmount?: number
  ): Promise<string> {
    const systemPrompt = `You are a salary negotiation expert. Provide market salary insights and negotiation strategies based on the job details.`;

    const messages: AIMessage[] = [
      {
        role: 'user',
        content: `Job Title: ${jobTitle}\nLocation: ${location}\nYears of Experience: ${yearsOfExperience}\n${offerAmount ? `Current Offer: $${offerAmount}` : ''}\n\nProvide salary analysis and negotiation advice.`,
      },
    ];

    return this.generateCompletion(messages, {
      systemPrompt,
      temperature: 0.7,
    });
  }

  private getCacheKey(messages: AIMessage[], options: AIRequestOptions): string {
    const key = JSON.stringify({ messages, options });
    return `ai:completion:${Buffer.from(key).toString('base64').substring(0, 64)}`;
  }
}

export const aiService = new AIService();
