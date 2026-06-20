import { GoogleGenerativeAI } from '@google/generative-ai';

export async function generateCoverLetter({ apiKey, resumeText, jobTitle, company, jobDescription, profile }) {
  if (!apiKey) {
    throw new Error('Gemini API key is required to generate a cover letter.');
  }

  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({ model: 'gemini-1.5-flash' });

  const prompt = `
You are a career assistant helping a professional write a highly customized, compelling, and punchy cover letter for a remote job application.

Here is the applicant's profile details:
- Name: ${profile.name || 'Not provided'}
- Email: ${profile.email || 'Not provided'}
- Phone: ${profile.phone || 'Not provided'}
- Portfolio: ${profile.portfolio || 'Not provided'}
- LinkedIn: ${profile.linkedin || 'Not provided'}
- GitHub: ${profile.github || 'Not provided'}

Applicant's Resume Context:
"""
${resumeText || 'No resume text uploaded. Please use the profile information.'}
"""

Target Job Details:
- Job Title: ${jobTitle}
- Company: ${company}
- Job Description:
"""
${jobDescription || 'Not provided'}
"""

INSTRUCTIONS:
1. Write a professional cover letter tailored specifically to the job description and company.
2. Link the applicant's relevant experience (from the Resume/Profile) to the key responsibilities of the role.
3. Keep it brief, punchy, and engaging (maximum 3-4 paragraphs, around 250-350 words). Long cover letters are ignored.
4. Highlight that this is for a REMOTE position, showcasing the applicant's ability to work autonomously, communicate asynchronously, and manage time effectively.
5. Do NOT use generic placeholders like "[Date]" or "[Hiring Manager's Name]". Start directly with a friendly and professional greeting, like "Dear Hiring Team at ${company}," or similar.
6. End with a strong call to action and sign off with the applicant's name: ${profile.name || '[Your Name]'}.
7. Return only the final cover letter text. Do not include introductory notes or markdown fences.
`;

  try {
    const result = await model.generateContent(prompt);
    const response = await result.response;
    return response.text();
  } catch (error) {
    console.error('Gemini Cover Letter Generation Error:', error);
    throw new Error(`AI Generation failed: ${error.message}`);
  }
}
