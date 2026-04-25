"""
Research Agent
==============
Uses Claude to analyze a builder's website and extract:
- Projects / property names
- Price ranges
- Target customers
- Business hours
- Key differentiators
- Pain points (what a voice agent would solve for them)
"""

import anthropic
import httpx
from bs4 import BeautifulSoup
import json
import re


class ResearchAgent:
    def __init__(self):
        self.client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var

    async def research(self, lead: dict) -> dict:
        """Research a lead and return structured insights."""

        # Try to scrape their website
        website_content = await self._scrape_website(lead.get('website', ''))

        # Use Claude to analyze and extract insights
        insights = await self._analyze_with_claude(lead, website_content)

        return insights

    async def _scrape_website(self, url: str) -> str:
        """Scrape website text content."""
        if not url:
            return ""

        if not url.startswith('http'):
            url = 'https://' + url

        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (compatible; SageBot/1.0)'
                }
                response = await client.get(url, headers=headers)
                soup = BeautifulSoup(response.text, 'html.parser')

                # Remove scripts and styles
                for tag in soup(['script', 'style', 'nav', 'footer']):
                    tag.decompose()

                text = soup.get_text(separator=' ', strip=True)
                # Trim to reasonable length
                return text[:8000]

        except Exception as e:
            print(f"    ⚠️  Could not scrape {url}: {e}")
            return f"Website unavailable. Company: {url}"

    async def _analyze_with_claude(self, lead: dict, website_content: str) -> dict:
        """Use Claude to extract structured insights from the website."""

        prompt = f"""You are researching a real estate / construction company to help us personalize a voice AI agent demo for them.

Company Details:
- Name: {lead.get('company_name', 'Unknown')}
- Website: {lead.get('website', 'N/A')}
- Location: {lead.get('city', 'India')}
- Contact: {lead.get('contact_name', 'N/A')}

Website Content (scraped):
{website_content or 'No website content available'}

Extract and return ONLY a JSON object with these fields:
{{
  "company_name": "official company name",
  "tagline": "their tagline or a good summary in 8 words",
  "projects": ["Project Name 1", "Project Name 2", "Project Name 3"],
  "price_range": "e.g. ₹45L - ₹2.5Cr",
  "property_types": ["Apartments", "Villas", "Plots"],
  "target_customer": "first-time homebuyers / luxury buyers / investors",
  "city": "city they operate in",
  "pain_points": [
    "Misses leads that come after office hours",
    "Sales team overwhelmed during project launches",
    "Can't handle multiple WhatsApp/calls simultaneously"
  ],
  "voice_agent_pitch": "One sentence on how a voice AI agent specifically helps THIS company",
  "primary_language": "English or Hindi or Telugu or Marathi etc based on their city/region",
  "tone": "luxury / affordable / trusted / modern",
  "key_selling_point": "The ONE thing they are proudest of"
}}

Return ONLY valid JSON, no markdown, no explanation."""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        text = message.content[0].text.strip()

        # Clean JSON if wrapped in backticks
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)

        try:
            insights = json.loads(text)
        except json.JSONDecodeError:
            # Fallback with basic info
            insights = {
                "company_name": lead.get('company_name', 'Builder'),
                "tagline": "Building dreams, one home at a time",
                "projects": ["Premium Residences"],
                "price_range": "₹50L - ₹2Cr",
                "property_types": ["Apartments", "Villas"],
                "target_customer": "homebuyers",
                "city": lead.get('city', 'India'),
                "pain_points": [
                    "Loses leads after office hours",
                    "Sales team can't handle all inquiries",
                    "Manual follow-up is slow"
                ],
                "voice_agent_pitch": f"A 24/7 voice AI agent that handles all your property inquiries automatically.",
                "primary_language": "Hindi",
                "tone": "professional",
                "key_selling_point": "Quality construction"
            }

        # Merge with original lead data
        insights['contact_name'] = lead.get('contact_name', '')
        insights['contact_email'] = lead.get('contact_email', '')
        insights['website'] = lead.get('website', '')

        return insights
