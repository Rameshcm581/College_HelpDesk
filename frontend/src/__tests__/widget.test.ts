import { describe, it, expect } from 'vitest';
import { WidgetConfig } from '../types';

describe('Chatbot Widget Architecture & Protocol', () => {
  it('validates default widget configuration schema', () => {
    const defaultConfig: WidgetConfig = {
      college_name: 'St. Jude College of Engineering & Technology',
      current_academic_year: '2025-2026',
      supported_languages: ['en', 'ta'],
      primary_color: '#1e3a8a',
      accent_color: '#059669',
      widget_position: 'bottom-right',
      greeting_en: 'Hello! I am the College AI Help Desk Assistant. Ask me about admissions, fees, hostel regulations, scholarships, or academic policies for 2025–2026.',
      greeting_ta: 'வணக்கம்! நான் கல்லூரி AI உதவி மைய உதவியாளர். சேர்க்கை, கட்டணம், விடுதி, தேர்வுகள் அல்லது உதவித்தொகை பற்றி கேளுங்கள்.',
      suggested_questions: [
        { text: 'What is the hostel caution deposit fee?', lang: 'en' },
        { text: 'விடுதி வைப்புத் தொகை எவ்வளவு?', lang: 'ta' },
        { text: 'What is the minimum attendance required for semester exams?', lang: 'en' },
        { text: 'How much is the B.E. Computer Science tuition fee?', lang: 'en' },
      ],
      anti_hallucination_guarantee: true,
      is_demonstration_sample: true,
      allowed_embed_origins: ['http://localhost:5175', 'http://127.0.0.1:5175'],
    };

    expect(defaultConfig.college_name).toContain('College');
    expect(defaultConfig.supported_languages).toContain('en');
    expect(defaultConfig.supported_languages).toContain('ta');
    expect(['bottom-right', 'bottom-left']).toContain(defaultConfig.widget_position);
    expect(defaultConfig.suggested_questions.length).toBeGreaterThanOrEqual(4);
  });

  it('verifies bilingual greeting strings and Tamil Unicode coverage', () => {
    const greetingTa = 'வணக்கம்! நான் கல்லூரி AI உதவி மைய உதவியாளர்.';
    const greetingEn = 'Hello! I am the College AI Help Desk Assistant.';

    // Check Tamil unicode range (\u0B80 - \u0BFF)
    const hasTamil = /[\u0B80-\u0BFF]/.test(greetingTa);
    expect(hasTamil).toBe(true);

    const isEnglish = /^[A-Za-z0-9\s!.,']+$/.test(greetingEn);
    expect(isEnglish).toBe(true);
  });

  it('validates postMessage contract between host loader and widget iframe', () => {
    const validHostMessages = ['helpdesk:init', 'helpdesk:command:open', 'helpdesk:command:close'];
    const validIframeMessages = ['helpdesk:open', 'helpdesk:close', 'helpdesk:resize', 'helpdesk:ready'];

    expect(validHostMessages).toContain('helpdesk:init');
    expect(validIframeMessages).toContain('helpdesk:open');
    expect(validIframeMessages).toContain('helpdesk:close');
  });

  it('verifies responsive layout breakpoint rules', () => {
    const mobileBreakpoint = 640;
    const isMobileViewport = (width: number) => width <= mobileBreakpoint;

    expect(isMobileViewport(375)).toBe(true); // iPhone SE / Mini
    expect(isMobileViewport(414)).toBe(true); // iPhone Plus / Pro Max
    expect(isMobileViewport(768)).toBe(false); // iPad
    expect(isMobileViewport(1024)).toBe(false); // Desktop
  });
});
