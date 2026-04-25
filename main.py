"""
SAGE - Smart Agent Generation Engine
====================================
Master pipeline that:
1. Reads leads from CSV
2. Researches each builder's website
3. Generates a personalized voice-agent demo page
4. Sends targeted outreach email with demo link
"""

import asyncio
import csv
import json
import os
from pathlib import Path
from agents.researcher import ResearchAgent
from agents.demo_builder import DemoBuilderAgent
from agents.emailer import EmailAgent

LEADS_FILE = "leads/leads.csv"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

async def run_pipeline(leads_file: str = LEADS_FILE, dry_run: bool = False):
    print("🏗️  SAGE Pipeline Starting...\n")

    # Load leads
    leads = load_leads(leads_file)
    print(f"📋 Loaded {len(leads)} leads\n")

    researcher = ResearchAgent()
    demo_builder = DemoBuilderAgent()
    emailer = EmailAgent()

    results = []

    for i, lead in enumerate(leads, 1):
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"[{i}/{len(leads)}] Processing: {lead['company_name']}")

        try:
            # Step 1: Research the builder
            print(f"  🔍 Researching {lead['website']}...")
            research = await researcher.research(lead)

            # Step 2: Generate personalized demo page
            print(f"  🎨 Generating personalized demo...")
            demo_path = await demo_builder.build(lead, research)

            # Step 3: Send outreach email
            if not dry_run:
                print(f"  📧 Sending email to {lead['contact_email']}...")
                email_status = await emailer.send(lead, research, demo_path)
            else:
                print(f"  📧 [DRY RUN] Would send to {lead['contact_email']}")
                email_status = "dry_run"

            results.append({
                "company": lead['company_name'],
                "demo": str(demo_path),
                "email": email_status,
                "status": "✅ Success"
            })
            print(f"  ✅ Done!")

        except Exception as e:
            print(f"  ❌ Failed: {e}")
            results.append({
                "company": lead['company_name'],
                "status": f"❌ {str(e)}"
            })

        # Be polite to APIs
        await asyncio.sleep(2)

    # Summary
    print(f"\n{'━'*40}")
    print(f"📊 PIPELINE COMPLETE")
    print(f"{'━'*40}")
    for r in results:
        print(f"  {r['status']} {r['company']}")
        if 'demo' in r:
            print(f"      Demo: {r['demo']}")

    return results


def load_leads(filepath: str) -> list[dict]:
    leads = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            leads.append(row)
    return leads


if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv
    asyncio.run(run_pipeline(dry_run=dry))
