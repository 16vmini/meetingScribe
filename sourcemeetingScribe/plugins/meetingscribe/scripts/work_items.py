"""
MeetingScribe v3 - Work Items Generator
Creates separate markdown documents for each topic/bug/feature discussed
"""
import json
import re
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Set
import requests

from utils import get_openai_api_key, format_timestamp, parse_timestamp

class WorkItemsGenerator:
    """Analyzes transcript and creates individual work item documents"""
    
    def __init__(self, session_path: Path):
        self.session_path = session_path
        self.work_items_dir = session_path / "work-items"
        self.screenshots_dir = session_path / "screenshots"
        
        # Ensure directories exist
        self.work_items_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Work items state
        self.work_items: List[Dict] = []
        self.item_counter = 1
        
        # API configuration
        self.api_key = get_openai_api_key()
        
    def generate_work_items(self, transcript_file: str = None) -> List[Dict]:
        """Generate work items from transcript"""
        if transcript_file is None:
            transcript_file = str(self.session_path / "transcript.md")
        
        if not Path(transcript_file).exists():
            self.logger.error(f"Transcript file not found: {transcript_file}")
            return []
        
        try:
            # Read transcript
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript_content = f.read()
            
            # Extract work items using AI
            work_items = self._extract_work_items_from_transcript(transcript_content)
            
            # Link screenshots to work items
            self._link_screenshots_to_work_items(work_items)
            
            # Generate markdown files for each work item
            for item in work_items:
                self._create_work_item_file(item)
            
            self.work_items = work_items
            self.logger.info(f"Generated {len(work_items)} work item documents")
            
            return work_items
            
        except Exception as e:
            self.logger.error(f"Error generating work items: {e}")
            return []
    
    def _extract_work_items_from_transcript(self, transcript_content: str) -> List[Dict]:
        """Use AI to extract distinct topics/issues from transcript"""
        try:
            prompt = f"""
Analyze this meeting transcript and extract distinct work items (bugs, features, topics, issues) that were discussed.

For each work item, provide:
1. A short name (for filename)
2. A title
3. Type (Bug, Feature, Discussion, Decision, etc.)
4. Priority if mentioned (High, Medium, Low)
5. Who raised it
6. Time range when discussed (start - end timestamps)
7. Description of the item
8. Key points from the discussion
9. Any action items or decisions made

Transcript:
{transcript_content}

Respond with a JSON array of work items in this format:
[
  {{
    "short_name": "grid-view-bug",
    "title": "Grid View Bug",
    "type": "Bug",
    "priority": "High",
    "raised_by": "James",
    "time_start": "00h14m23s",
    "time_end": "00h16m45s",
    "description": "Column widths reset when filtering is applied",
    "discussion_points": [
      "Users have to manually resize columns after every filter",
      "Affects all grid views in the system"
    ],
    "action_items": [
      "Fix grid column persistence - store widths in local storage",
      "Test with all grid views"
    ],
    "decisions": [
      "Will use local storage approach"
    ]
  }}
]

Important:
- Only include substantive topics that were actually discussed
- Don't create items for brief mentions or side comments
- Use the exact timestamp format from the transcript
- If multiple people discussed an item, list the primary person who raised it
- Action items should be specific and actionable
"""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-4",  # Use GPT-4 for better analysis
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 3000,
                "temperature": 0.1
            }
            
            self.logger.info("Extracting work items using AI...")
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                
                # Try to parse JSON from the response
                try:
                    # Sometimes the response includes markdown formatting
                    if content.startswith('```json'):
                        content = content.replace('```json', '').replace('```', '').strip()
                    elif content.startswith('```'):
                        content = content.replace('```', '').strip()
                    
                    work_items = json.loads(content)
                    self.logger.info(f"Extracted {len(work_items)} work items")
                    return work_items
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse AI response as JSON: {e}")
                    self.logger.debug(f"AI response content: {content}")
                    return []
            else:
                self.logger.error(f"AI API request failed: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error in AI work item extraction: {e}")
            return []
    
    def _link_screenshots_to_work_items(self, work_items: List[Dict]):
        """Link relevant screenshots to each work item based on timing"""
        if not self.screenshots_dir.exists():
            return
        
        # Get list of screenshots with their timestamps
        screenshots = []
        for screenshot_file in self.screenshots_dir.glob("*.jpg"):
            # Extract timestamp from filename (e.g., "screenshot_00h14m23s.jpg")
            match = re.search(r'(\d{2}h\d{2}m\d{2}s)', screenshot_file.name)
            if match:
                timestamp_str = match.group(1)
                timestamp_seconds = parse_timestamp(timestamp_str)
                screenshots.append({
                    'filename': screenshot_file.name,
                    'timestamp': timestamp_seconds,
                    'timestamp_str': timestamp_str,
                    'path': screenshot_file
                })
        
        # Sort screenshots by timestamp
        screenshots.sort(key=lambda x: x['timestamp'])
        
        # Link screenshots to work items
        for item in work_items:
            start_time = parse_timestamp(item.get('time_start', ''))
            end_time = parse_timestamp(item.get('time_end', ''))
            
            linked_screenshots = []
            
            # Find screenshots within the time range
            for screenshot in screenshots:
                if start_time <= screenshot['timestamp'] <= end_time:
                    linked_screenshots.append(screenshot)
            
            # Also include screenshots shortly before/after (within 30 seconds)
            buffer_seconds = 30
            for screenshot in screenshots:
                if (start_time - buffer_seconds <= screenshot['timestamp'] <= start_time or
                    end_time <= screenshot['timestamp'] <= end_time + buffer_seconds):
                    if screenshot not in linked_screenshots:
                        linked_screenshots.append(screenshot)
            
            item['linked_screenshots'] = linked_screenshots
            
            if linked_screenshots:
                self.logger.info(f"Linked {len(linked_screenshots)} screenshots to '{item['title']}'")
    
    def _create_work_item_file(self, item: Dict):
        """Create a markdown file for a work item"""
        try:
            # Generate filename
            short_name = item.get('short_name', f'item_{self.item_counter}')
            # Clean short name for filename
            short_name = re.sub(r'[^\w\-_]', '', short_name.replace(' ', '-').lower())
            filename = f"{self.item_counter:03d}_{short_name}.md"
            
            filepath = self.work_items_dir / filename
            
            # Build markdown content
            content = self._build_work_item_markdown(item)
            
            # Write file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"Created work item: {filename}")
            self.item_counter += 1
            
        except Exception as e:
            self.logger.error(f"Error creating work item file: {e}")
    
    def _build_work_item_markdown(self, item: Dict) -> str:
        """Build markdown content for a work item"""
        content = []
        
        # Title
        title = item.get('title', 'Untitled Work Item')
        content.append(f"# {title}\n")
        
        # Metadata
        item_type = item.get('type', 'Discussion')
        priority = item.get('priority', '')
        raised_by = item.get('raised_by', '')
        time_start = item.get('time_start', '')
        time_end = item.get('time_end', '')
        
        content.append(f"**Type:** {item_type}")
        if priority:
            content.append(f"**Priority:** {priority}")
        if time_start and time_end:
            content.append(f"**Discussed at:** {time_start} - {time_end}")
        elif time_start:
            content.append(f"**Discussed at:** {time_start}")
        if raised_by:
            content.append(f"**Raised by:** {raised_by}")
        
        # Primary screenshot if available
        linked_screenshots = item.get('linked_screenshots', [])
        if linked_screenshots:
            primary_screenshot = linked_screenshots[0]
            content.append(f"**Screenshot:** [{primary_screenshot['filename']}](../screenshots/{primary_screenshot['filename']})")
        
        content.append("")  # Empty line
        
        # Description
        description = item.get('description', '')
        if description:
            content.append("## Description")
            content.append(description)
            content.append("")
        
        # Discussion context
        discussion_points = item.get('discussion_points', [])
        if discussion_points:
            content.append("## Context from Discussion")
            for point in discussion_points:
                content.append(f"- {point}")
            content.append("")
        
        # Action items
        action_items = item.get('action_items', [])
        if action_items:
            content.append("## Action Items")
            for action in action_items:
                content.append(f"- [ ] {action}")
            content.append("")
        
        # Decisions
        decisions = item.get('decisions', [])
        if decisions:
            content.append("## Decisions Made")
            for decision in decisions:
                content.append(f"- {decision}")
            content.append("")
        
        # Related screenshots
        if len(linked_screenshots) > 1:
            content.append("## Related Screenshots")
            for screenshot in linked_screenshots:
                content.append(f"- ![{screenshot['filename']}](../screenshots/{screenshot['filename']}) - {screenshot['timestamp_str']}")
            content.append("")
        
        return "\n".join(content)
    
    def process_live_transcript_chunk(self, transcript_chunk: str, chunk_timestamp: float) -> Optional[Dict]:
        """Process a live transcript chunk and update/create work items"""
        try:
            # Use AI to analyze if this chunk introduces new work items or updates existing ones
            prompt = f"""
Analyze this transcript chunk from an ongoing meeting. Determine if it:
1. Introduces a NEW work item (bug, feature, topic, issue)
2. Continues discussion of an EXISTING work item
3. Just general conversation (no specific work item)

Current chunk timestamp: {format_timestamp(chunk_timestamp)}

Transcript chunk:
"{transcript_chunk}"

If this is a NEW work item, respond with JSON:
{{
  "action": "create",
  "work_item": {{
    "short_name": "brief-name",
    "title": "Title",
    "type": "Bug|Feature|Discussion|Decision",
    "priority": "High|Medium|Low" (if detectable),
    "raised_by": "Speaker name" (if clear),
    "time_start": "{format_timestamp(chunk_timestamp)}",
    "description": "Brief description",
    "discussion_points": ["key points from this chunk"],
    "preliminary": true
  }}
}}

If this continues an EXISTING item, respond with JSON:
{{
  "action": "update",
  "update_type": "add_discussion|add_action|add_decision",
  "content": "What to add",
  "keywords": ["keywords to match existing items"]
}}

If no specific work item, respond with:
{{
  "action": "none"
}}
"""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.1
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                
                # Parse response
                try:
                    if content.startswith('```json'):
                        content = content.replace('```json', '').replace('```', '').strip()
                    
                    analysis = json.loads(content)
                    
                    if analysis.get('action') == 'create':
                        # Create new work item
                        new_item = analysis.get('work_item', {})
                        new_item['created_live'] = True
                        new_item['live_updates'] = []
                        
                        self.work_items.append(new_item)
                        self._create_work_item_file(new_item)
                        
                        self.logger.info(f"Created new live work item: {new_item.get('title', 'Untitled')}")
                        return new_item
                        
                    elif analysis.get('action') == 'update':
                        # Update existing work item
                        self._update_existing_work_item(analysis, chunk_timestamp)
                        
                    return analysis
                    
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Could not parse live analysis response: {e}")
                    return None
            else:
                self.logger.error(f"Live analysis API request failed: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error in live transcript processing: {e}")
            return None
    
    def _update_existing_work_item(self, update_info: Dict, timestamp: float):
        """Update an existing work item with new information"""
        keywords = update_info.get('keywords', [])
        content = update_info.get('content', '')
        update_type = update_info.get('update_type', '')
        
        # Find matching work item
        matching_item = None
        for item in self.work_items:
            item_text = f"{item.get('title', '')} {item.get('description', '')} {' '.join(item.get('discussion_points', []))}"
            item_text_lower = item_text.lower()
            
            # Check if any keywords match
            for keyword in keywords:
                if keyword.lower() in item_text_lower:
                    matching_item = item
                    break
            
            if matching_item:
                break
        
        if matching_item:
            # Update the item
            if 'live_updates' not in matching_item:
                matching_item['live_updates'] = []
            
            update_record = {
                'timestamp': timestamp,
                'type': update_type,
                'content': content
            }
            matching_item['live_updates'].append(update_record)
            
            # Apply the update to the item
            if update_type == 'add_discussion':
                if 'discussion_points' not in matching_item:
                    matching_item['discussion_points'] = []
                matching_item['discussion_points'].append(content)
                
            elif update_type == 'add_action':
                if 'action_items' not in matching_item:
                    matching_item['action_items'] = []
                matching_item['action_items'].append(content)
                
            elif update_type == 'add_decision':
                if 'decisions' not in matching_item:
                    matching_item['decisions'] = []
                matching_item['decisions'].append(content)
            
            # Update the end time
            matching_item['time_end'] = format_timestamp(timestamp)
            
            # Re-create the file with updated content
            self._create_work_item_file(matching_item)
            
            self.logger.info(f"Updated work item '{matching_item.get('title', 'Untitled')}' with {update_type}")
    
    def get_work_items_summary(self) -> Dict:
        """Get summary of all work items"""
        if not self.work_items:
            return {"total": 0, "items": []}
        
        summary = {
            "total": len(self.work_items),
            "by_type": {},
            "by_priority": {},
            "items": []
        }
        
        for item in self.work_items:
            item_type = item.get('type', 'Unknown')
            priority = item.get('priority', 'Unknown')
            
            # Count by type
            summary["by_type"][item_type] = summary["by_type"].get(item_type, 0) + 1
            
            # Count by priority
            summary["by_priority"][priority] = summary["by_priority"].get(priority, 0) + 1
            
            # Add to items list
            summary["items"].append({
                "title": item.get('title', 'Untitled'),
                "type": item_type,
                "priority": priority,
                "raised_by": item.get('raised_by', ''),
                "time_range": f"{item.get('time_start', '')} - {item.get('time_end', '')}",
                "action_items_count": len(item.get('action_items', []))
            })
        
        return summary

# Example usage and testing
if __name__ == "__main__":
    from utils import MeetingSession
    
    # Create test session
    session = MeetingSession("work_items_test")
    session.create_directories()
    
    # Create test transcript
    test_transcript = """# Meeting Transcript

**00h05m12s - 00h05m30s**
Welcome everyone to today's standup. Let's go through the items.

**00h10m15s - 00h12m45s**
James: I found a bug in the grid view. When you apply filters, all the column widths reset to default. Users have to manually resize them again.

**00h12m46s - 00h15m20s**
Matthew: That's annoying. Can we store the column widths in local storage? James: Good idea. I'll look into that approach.

**00h16m00s - 00h18m30s**
Sarah: I've been working on the new dispatch feature. We need to decide on the workflow for assigning drivers.

**00h18m31s - 00h20m00s**
Matthew: Let's discuss that in detail next week. For now, focus on the basic assignment logic.
"""
    
    # Save test transcript
    transcript_path = session.session_path / "transcript.md"
    with open(transcript_path, 'w', encoding='utf-8') as f:
        f.write(test_transcript)
    
    print("Test transcript created")
    
    # Test work items generation
    generator = WorkItemsGenerator(session.session_path)
    
    # This would normally use the API - for testing, we'll just show the setup
    print("Work items generator created")
    print(f"Work items directory: {generator.work_items_dir}")
    
    # Show summary (will be empty without API call)
    summary = generator.get_work_items_summary()
    print(f"Current work items summary: {summary}")
    