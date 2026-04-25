"""
Email Agent
===========
Sends personalized outreach emails with the demo link embedded.
Uses SendGrid or SMTP. The email itself has a compelling CTA
that opens the demo page.
"""

import anthropic
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


class EmailAgent:
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")
        self.from_name = os.getenv("FROM_NAME", "Rohan from SAGE AI")
        self.demo_base_url = os.getenv("DEMO_BASE_URL", "https://demos.sage-ai.in")

    async def send(self, lead: dict, research: dict, demo_path: Path) -> str:
        """Generate and send personalized outreach email."""

        demo_filename = demo_path.name
        demo_url = f"{self.demo_base_url}/{demo_filename}"

        # Generate personalized email copy with Claude
        email_copy = await self._generate_email(lead, research, demo_url)

        # Send via SMTP
        if self.smtp_user and self.smtp_pass:
            self._send_smtp(
                to_email=research['contact_email'],
                to_name=research.get('contact_name', ''),
                subject=email_copy['subject'],
                html_body=email_copy['html'],
                text_body=email_copy['text']
            )
            return "sent"
        else:
            # Save email to file for review (when SMTP not configured)
            email_path = demo_path.parent / f"email_{demo_path.stem}.html"
            with open(email_path, 'w') as f:
                f.write(f"<h3>TO: {research['contact_email']}</h3>")
                f.write(f"<h3>SUBJECT: {email_copy['subject']}</h3>")
                f.write(email_copy['html'])
            return f"saved_to_file:{email_path}"

    async def _generate_email(self, lead: dict, research: dict, demo_url: str) -> dict:
        """Use Claude to write a personalized outreach email."""

        prompt = f"""Write a short, punchy outreach email for a real estate company.

Context:
- Company: {research['company_name']}
- Contact: {research.get('contact_name', 'the team')}
- City: {research.get('city', 'India')}
- Their pain: {research.get('pain_points', ['losing leads after hours'])[0]}
- Their projects: {', '.join(research.get('projects', ['Premium Properties'])[:2])}
- Demo URL: {demo_url}

Write a personalized email that:
1. References something specific about their company (not generic)
2. Mentions the pain point naturally
3. Has ONE CTA: clicking the demo link
4. Is under 120 words in the body
5. Does NOT sound salesy or like a mass email
6. Subject line must be curiosity-driven and personal

Return ONLY valid JSON:
{{
  "subject": "email subject line here",
  "text": "plain text version",
  "html": "full HTML email body with the demo URL as a big button"
}}"""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        import json, re
        text = message.content[0].text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)

        try:
            return json.loads(text)
        except:
            # Fallback email
            company = research['company_name']
            return {
                "subject": f"Built a voice AI demo specifically for {company}",
                "text": f"""Hi {research.get('contact_name', 'there')},

I built a live voice AI demo specifically for {company} — it knows your projects and handles inquiries in Hindi/English, 24/7.

Takes 30 seconds to try: {demo_url}

If it makes sense, we can have this live for {company} this week.

— Rohan""",
                "html": f"""
<div style="font-family:sans-serif;max-width:520px;margin:0 auto;color:#222;">
    <p>Hi {research.get('contact_name', 'there')},</p>
    <p>I built a <strong>live voice AI agent demo</strong> specifically for <strong>{company}</strong> — it already knows your projects, responds in Hindi/English, and handles property inquiries 24/7.</p>
    <p style="color:#666;font-size:0.9rem;">Your team misses calls after office hours. This solves that.</p>
    <div style="text-align:center;margin:32px 0;">
        <a href="{demo_url}" style="background:#c9a84c;color:white;padding:16px 32px;border-radius:100px;text-decoration:none;font-weight:700;font-size:1rem;">
            🎙️ Try Your AI Agent Demo →
        </a>
    </div>
    <p style="font-size:0.85rem;color:#999;">Takes 30 seconds. No login. Works on mobile.</p>
    <p>— Rohan<br>SAGE Voice AI</p>
</div>"""
            }

    def _send_smtp(self, to_email, to_name, subject, html_body, text_body):
        """Send email via SMTP."""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.from_name} <{self.smtp_user}>"
        msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email

        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.send_message(msg)
