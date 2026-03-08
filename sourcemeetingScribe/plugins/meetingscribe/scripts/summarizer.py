"""
MeetingScribe v3 - Meeting summarizer with formal minutes and HTML reports
"""
import json
import time
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional
import requests

from utils import get_openai_api_key, format_timestamp, parse_timestamp

class MeetingSummarizer:
    """Generates formal meeting minutes and HTML reports"""
    
    def __init__(self, session_path: Path):
        self.session_path = session_path
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # API configuration
        self.api_key = get_openai_api_key()
        
        # File paths
        self.transcript_path = session_path / "transcript.md"
        self.minutes_path = session_path / "minutes.md"
        self.report_path = session_path / "report.html"
        self.work_items_dir = session_path / "work-items"
        self.screenshots_dir = session_path / "screenshots"
        
        # Data
        self.transcript_content = ""
        self.work_items = []
        self.minutes_data = {}
        
    def generate_minutes(self) -> bool:
        """Generate formal meeting minutes"""
        try:
            # Load transcript
            if not self._load_transcript():
                return False
            
            # Load work items
            self._load_work_items()
            
            # Generate minutes using AI
            minutes_data = self._generate_minutes_with_ai()
            
            if not minutes_data:
                self.logger.error("Failed to generate minutes data")
                return False
            
            # Save minutes markdown
            self._save_minutes_markdown(minutes_data)
            
            # Store for HTML report
            self.minutes_data = minutes_data
            
            self.logger.info("Meeting minutes generated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating minutes: {e}")
            return False
    
    def generate_html_report(self) -> bool:
        """Generate HTML report with embedded screenshots and cross-references"""
        try:
            self.logger.info("Generating HTML report...")
            
            # If minutes not yet generated, do it now
            if not self.minutes_data:
                if not self.generate_minutes():
                    return False
            
            # Generate HTML content
            html_content = self._build_html_report()
            
            # Save HTML file
            with open(self.report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"HTML report generated: {self.report_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating HTML report: {e}")
            return False
    
    def _load_transcript(self) -> bool:
        """Load transcript content"""
        if not self.transcript_path.exists():
            self.logger.error(f"Transcript file not found: {self.transcript_path}")
            return False
        
        try:
            with open(self.transcript_path, 'r', encoding='utf-8') as f:
                self.transcript_content = f.read()
            
            self.logger.info("Transcript loaded")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading transcript: {e}")
            return False
    
    def _load_work_items(self):
        """Load work items from markdown files"""
        if not self.work_items_dir.exists():
            self.logger.warning("No work items directory found")
            return
        
        try:
            work_item_files = list(self.work_items_dir.glob("*.md"))
            
            for work_item_file in sorted(work_item_files):
                work_item_data = self._parse_work_item_file(work_item_file)
                if work_item_data:
                    self.work_items.append(work_item_data)
            
            self.logger.info(f"Loaded {len(self.work_items)} work items")
            
        except Exception as e:
            self.logger.error(f"Error loading work items: {e}")
    
    def _parse_work_item_file(self, file_path: Path) -> Optional[Dict]:
        """Parse a work item markdown file to extract metadata"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract title (first # header)
            title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else file_path.stem
            
            # Extract metadata
            work_item = {
                'file_path': file_path,
                'filename': file_path.name,
                'title': title,
                'content': content
            }
            
            # Parse metadata fields
            metadata_patterns = {
                'type': r'\*\*Type:\*\* (.+)',
                'priority': r'\*\*Priority:\*\* (.+)',
                'discussed_at': r'\*\*Discussed at:\*\* (.+)',
                'raised_by': r'\*\*Raised by:\*\* (.+)',
                'screenshot': r'\*\*Screenshot:\*\* \[([^\]]+)\]'
            }
            
            for field, pattern in metadata_patterns.items():
                match = re.search(pattern, content)
                if match:
                    work_item[field] = match.group(1).strip()
            
            # Extract action items
            action_items = []
            action_section = re.search(r'## Action Items\n(.*?)(?=\n##|\n---|\Z)', content, re.DOTALL)
            if action_section:
                action_lines = action_section.group(1).strip().split('\n')
                for line in action_lines:
                    line = line.strip()
                    if line.startswith('- [ ]') or line.startswith('- [x]'):
                        action_text = line[5:].strip()  # Remove checkbox
                        completed = '[x]' in line
                        action_items.append({
                            'text': action_text,
                            'completed': completed
                        })
            
            work_item['action_items'] = action_items
            
            return work_item
            
        except Exception as e:
            self.logger.error(f"Error parsing work item file {file_path}: {e}")
            return None
    
    def _generate_minutes_with_ai(self) -> Optional[Dict]:
        """Generate meeting minutes using AI"""
        try:
            # Prepare context for AI
            context = self._prepare_ai_context()
            
            prompt = f"""
Generate formal meeting minutes from this transcript and work items information.

{context}

Please generate a JSON response with the following structure:
{{
  "meeting_title": "Meeting title (infer from content)",
  "date": "Meeting date (format: YYYY-MM-DD)",
  "start_time": "Start time (HH:MM)",
  "end_time": "End time (HH:MM)",  
  "attendees": ["List of attendees mentioned in transcript"],
  "agenda_items": ["List of main topics discussed"],
  "key_decisions": ["Important decisions made"],
  "action_items": [
    {{
      "action": "Action description",
      "owner": "Person responsible",
      "due_date": "Due date if mentioned",
      "status": "Open"
    }}
  ],
  "next_meeting": "Next meeting details if mentioned",
  "notes": "Additional notes or context"
}}

Focus on extracting concrete information. If information isn't available, use "Not specified" or leave as null.
"""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-4",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2000,
                "temperature": 0.1
            }
            
            self.logger.info("Generating minutes with AI...")
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                
                # Parse JSON response
                try:
                    if content.startswith('```json'):
                        content = content.replace('```json', '').replace('```', '').strip()
                    elif content.startswith('```'):
                        content = content.replace('```', '').strip()
                    
                    minutes_data = json.loads(content)
                    self.logger.info("Minutes generated successfully")
                    return minutes_data
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse AI response as JSON: {e}")
                    self.logger.debug(f"AI response: {content}")
                    return None
            else:
                self.logger.error(f"AI API request failed: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error in AI minutes generation: {e}")
            return None
    
    def _prepare_ai_context(self) -> str:
        """Prepare context for AI processing"""
        context_parts = []
        
        # Add transcript
        context_parts.append("TRANSCRIPT:")
        context_parts.append(self.transcript_content[:5000])  # Limit to avoid token limits
        
        # Add work items summary
        if self.work_items:
            context_parts.append("\nWORK ITEMS DISCUSSED:")
            for item in self.work_items:
                context_parts.append(f"- {item['title']} ({item.get('type', 'Unknown')})")
                if item.get('discussed_at'):
                    context_parts.append(f"  Discussed at: {item['discussed_at']}")
                if item.get('raised_by'):
                    context_parts.append(f"  Raised by: {item['raised_by']}")
                if item.get('action_items'):
                    context_parts.append(f"  Action items: {len(item['action_items'])}")
        
        return '\n'.join(context_parts)
    
    def _save_minutes_markdown(self, minutes_data: Dict):
        """Save minutes as markdown file"""
        try:
            content = []
            
            # Title and basic info
            title = minutes_data.get('meeting_title', 'Meeting Minutes')
            content.append(f"# {title}")
            
            date = minutes_data.get('date', time.strftime('%Y-%m-%d'))
            start_time = minutes_data.get('start_time', 'Not specified')
            end_time = minutes_data.get('end_time', 'Not specified')
            
            content.append(f"**Date:** {date}")
            content.append(f"**Time:** {start_time} - {end_time}")
            
            # Attendees
            attendees = minutes_data.get('attendees', [])
            if attendees:
                content.append(f"**Attendees:** {', '.join(attendees)}")
            
            content.append("")  # Empty line
            
            # Agenda
            agenda_items = minutes_data.get('agenda_items', [])
            if agenda_items:
                content.append("## Agenda")
                for i, item in enumerate(agenda_items, 1):
                    content.append(f"{i}. {item}")
                content.append("")
            
            # Key Decisions
            decisions = minutes_data.get('key_decisions', [])
            if decisions:
                content.append("## Key Decisions")
                for decision in decisions:
                    content.append(f"- {decision}")
                content.append("")
            
            # Action Items
            action_items = minutes_data.get('action_items', [])
            if action_items:
                content.append("## Action Items")
                content.append("| # | Action | Owner | Due Date | Status |")
                content.append("|---|--------|-------|----------|--------|")
                
                for i, action in enumerate(action_items, 1):
                    action_text = action.get('action', '')
                    owner = action.get('owner', 'TBD')
                    due_date = action.get('due_date', 'TBD')
                    status = action.get('status', 'Open')
                    
                    content.append(f"| {i} | {action_text} | {owner} | {due_date} | {status} |")
                
                content.append("")
            
            # Work Items Cross-Reference
            if self.work_items:
                content.append("## Work Items Discussed")
                for item in self.work_items:
                    title = item['title']
                    filename = item['filename']
                    item_type = item.get('type', 'Unknown')
                    priority = item.get('priority', '')
                    
                    content.append(f"### [{title}](work-items/{filename})")
                    content.append(f"**Type:** {item_type}")
                    if priority:
                        content.append(f"**Priority:** {priority}")
                    
                    # Show action items count
                    action_count = len(item.get('action_items', []))
                    if action_count > 0:
                        content.append(f"**Action Items:** {action_count}")
                    
                    content.append("")
            
            # Next Meeting
            next_meeting = minutes_data.get('next_meeting')
            if next_meeting and next_meeting != "Not specified":
                content.append("## Next Meeting")
                content.append(next_meeting)
                content.append("")
            
            # Additional Notes
            notes = minutes_data.get('notes')
            if notes and notes != "Not specified":
                content.append("## Additional Notes")
                content.append(notes)
            
            # Save file
            with open(self.minutes_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            
            self.logger.info(f"Minutes saved to: {self.minutes_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving minutes markdown: {e}")
    
    def _build_html_report(self) -> str:
        """Build comprehensive HTML report"""
        try:
            # Get list of screenshots
            screenshots = []
            if self.screenshots_dir.exists():
                for screenshot_file in sorted(self.screenshots_dir.glob("*.jpg")):
                    # Extract timestamp from filename
                    timestamp_match = re.search(r'(\d{2}h\d{2}m\d{2}s)', screenshot_file.name)
                    timestamp_str = timestamp_match.group(1) if timestamp_match else ""
                    
                    screenshots.append({
                        'filename': screenshot_file.name,
                        'timestamp': timestamp_str,
                        'path': f"screenshots/{screenshot_file.name}"
                    })
            
            # Build HTML
            html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meeting Report - {self.minutes_data.get('meeting_title', 'Meeting')}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        .header {{
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .meeting-info {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .work-item {{
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            background: #fefefe;
        }}
        .work-item h3 {{
            margin-top: 0;
            color: #2c3e50;
        }}
        .screenshot {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin: 10px 0;
        }}
        .screenshot-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .screenshot-item {{
            text-align: center;
            padding: 10px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            background: #fafafa;
        }}
        .action-item {{
            background: #e8f4fd;
            padding: 10px 15px;
            border-left: 4px solid #007bff;
            margin: 10px 0;
        }}
        .decision-item {{
            background: #e8f5e8;
            padding: 10px 15px;
            border-left: 4px solid #28a745;
            margin: 10px 0;
        }}
        .meta-info {{
            color: #666;
            font-size: 0.9em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
            font-weight: 600;
        }}
        .toc {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .toc ul {{
            list-style-type: none;
            padding-left: 0;
        }}
        .toc li {{
            margin: 8px 0;
        }}
        .toc a {{
            text-decoration: none;
            color: #007bff;
        }}
        .toc a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{self.minutes_data.get('meeting_title', 'Meeting Report')}</h1>
        <p class="meta-info">Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="meeting-info">
        <h2>Meeting Information</h2>
        <p><strong>Date:</strong> {self.minutes_data.get('date', 'Not specified')}</p>
        <p><strong>Time:</strong> {self.minutes_data.get('start_time', 'Not specified')} - {self.minutes_data.get('end_time', 'Not specified')}</p>
        <p><strong>Attendees:</strong> {', '.join(self.minutes_data.get('attendees', []))}</p>
    </div>

    <div class="toc">
        <h2>Table of Contents</h2>
        <ul>
            <li><a href="#agenda">Agenda</a></li>
            <li><a href="#decisions">Key Decisions</a></li>
            <li><a href="#actions">Action Items</a></li>
            <li><a href="#work-items">Work Items</a></li>
            <li><a href="#screenshots">Screenshots</a></li>
        </ul>
    </div>
"""
            
            # Agenda Section
            agenda_items = self.minutes_data.get('agenda_items', [])
            if agenda_items:
                html += f"""
    <div class="section" id="agenda">
        <h2>Agenda</h2>
        <ol>
"""
                for item in agenda_items:
                    html += f"            <li>{item}</li>\n"
                
                html += """        </ol>
    </div>
"""
            
            # Key Decisions
            decisions = self.minutes_data.get('key_decisions', [])
            if decisions:
                html += f"""
    <div class="section" id="decisions">
        <h2>Key Decisions</h2>
"""
                for decision in decisions:
                    html += f'        <div class="decision-item">{decision}</div>\n'
                
                html += "    </div>\n"
            
            # Action Items
            action_items = self.minutes_data.get('action_items', [])
            if action_items:
                html += f"""
    <div class="section" id="actions">
        <h2>Action Items</h2>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Action</th>
                    <th>Owner</th>
                    <th>Due Date</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
"""
                for i, action in enumerate(action_items, 1):
                    html += f"""                <tr>
                    <td>{i}</td>
                    <td>{action.get('action', '')}</td>
                    <td>{action.get('owner', 'TBD')}</td>
                    <td>{action.get('due_date', 'TBD')}</td>
                    <td>{action.get('status', 'Open')}</td>
                </tr>
"""
                
                html += """            </tbody>
        </table>
    </div>
"""
            
            # Work Items Section
            if self.work_items:
                html += f"""
    <div class="section" id="work-items">
        <h2>Work Items Discussed</h2>
"""
                
                for item in self.work_items:
                    title = item['title']
                    item_type = item.get('type', 'Unknown')
                    priority = item.get('priority', '')
                    discussed_at = item.get('discussed_at', '')
                    raised_by = item.get('raised_by', '')
                    
                    html += f"""
        <div class="work-item">
            <h3>{title}</h3>
            <div class="meta-info">
                <p><strong>Type:</strong> {item_type}</p>
"""
                    
                    if priority:
                        html += f"                <p><strong>Priority:</strong> {priority}</p>\n"
                    if discussed_at:
                        html += f"                <p><strong>Discussed at:</strong> {discussed_at}</p>\n"
                    if raised_by:
                        html += f"                <p><strong>Raised by:</strong> {raised_by}</p>\n"
                    
                    html += "            </div>\n"
                    
                    # Show action items for this work item
                    work_item_actions = item.get('action_items', [])
                    if work_item_actions:
                        html += "            <h4>Action Items:</h4>\n"
                        for action in work_item_actions:
                            status = "✅" if action.get('completed') else "⏳"
                            html += f'            <div class="action-item">{status} {action.get("text", "")}</div>\n'
                    
                    html += "        </div>\n"
                
                html += "    </div>\n"
            
            # Screenshots Section
            if screenshots:
                html += f"""
    <div class="section" id="screenshots">
        <h2>Screenshots ({len(screenshots)})</h2>
        <div class="screenshot-grid">
"""
                
                for screenshot in screenshots:
                    html += f"""            <div class="screenshot-item">
                <img src="{screenshot['path']}" alt="{screenshot['filename']}" class="screenshot">
                <p><strong>{screenshot['filename']}</strong></p>
                <p class="meta-info">Timestamp: {screenshot['timestamp']}</p>
            </div>
"""
                
                html += """        </div>
    </div>
"""
            
            # Close HTML
            html += """
</body>
</html>"""
            
            return html
            
        except Exception as e:
            self.logger.error(f"Error building HTML report: {e}")
            return f"<html><body><h1>Error generating report</h1><p>{e}</p></body></html>"

# Example usage and testing
if __name__ == "__main__":
    from utils import MeetingSession
    
    # Create test session
    session = MeetingSession("summarizer_test")
    session.create_directories()
    
    # Create test transcript
    test_transcript = """# Meeting Transcript

**00h05m12s - 00h05m30s**
Welcome everyone to today's standup. Attendees are James, Matthew, and Sarah.

**00h10m15s - 00h12m45s**
James: I found a critical bug in the grid view. When you apply filters, all the column widths reset to default.

**00h16m00s - 00h18m30s**
Sarah: I've been working on the new dispatch feature. We decided to implement it in the next sprint.

**00h20m00s - 00h21m00s**
Matthew: Let's meet again next Friday at 9:30 AM to review progress.
"""
    
    # Save test transcript
    transcript_path = session.session_path / "transcript.md"
    with open(transcript_path, 'w', encoding='utf-8') as f:
        f.write(test_transcript)
    
    # Create summarizer
    summarizer = MeetingSummarizer(session.session_path)
    
    print("Test transcript created")
    print(f"Transcript path: {transcript_path}")
    
    # Test minutes generation (would need API key)
    # success = summarizer.generate_minutes()
    # if success:
    #     print("Minutes generated successfully!")
    #     
    #     # Generate HTML report
    #     if summarizer.generate_html_report():
    #         print("HTML report generated successfully!")
    #         print(f"Report saved to: {summarizer.report_path}")
    
    print("Summarizer test setup complete!")