"""
MeetingScribe v3 - Command Line Interface
"""
import argparse
import sys
import os
import subprocess
from pathlib import Path
from utils import MeetingSession, list_meetings

class MeetingScribeCLI:
    """Command line interface for MeetingScribe"""
    
    def __init__(self):
        self.current_session = None
        
    def record(self, monitor=0, name=None):
        """Start live recording"""
        try:
            from live_session import LiveSession
            
            session = MeetingSession(name=name)
            session.create_directories()
            
            print(f"Starting live recording session: {session.name}")
            print(f"Session folder: {session.session_folder}")
            
            live_session = LiveSession(session, monitor=monitor)
            live_session.start()
            
            # Save session info for stop command
            self.current_session = session
            self._save_current_session_info(session)
            
        except ImportError as e:
            print(f"Error: Required module not found: {e}")
            print("Make sure all dependencies are installed.")
            return False
        except Exception as e:
            print(f"Error starting recording: {e}")
            return False
            
        return True
    
    def stop(self):
        """Stop current recording and process"""
        session = self._load_current_session_info()
        if not session:
            print("No active recording session found")
            return False
            
        try:
            from live_session import LiveSession
            
            # This would normally connect to running session and stop it
            # For now, we'll implement a basic stop mechanism
            print(f"Stopping recording session: {session.name}")
            
            # Run post-processing
            self._run_post_processing(session)
            
            # Clear current session
            self._clear_current_session_info()
            
        except Exception as e:
            print(f"Error stopping recording: {e}")
            return False
            
        return True
    
    def process(self, mp4_file, name=None):
        """Process existing MP4 file"""
        if not Path(mp4_file).exists():
            print(f"Error: File {mp4_file} not found")
            return False
            
        try:
            from video_processor import VideoProcessor
            
            session = MeetingSession(name=name)
            session.create_directories()
            
            print(f"Processing MP4 file: {mp4_file}")
            print(f"Session folder: {session.session_folder}")
            
            processor = VideoProcessor(session)
            processor.process_mp4(mp4_file)
            
            self._run_post_processing(session)
            
        except ImportError as e:
            print(f"Error: Required module not found: {e}")
            return False
        except Exception as e:
            print(f"Error processing MP4: {e}")
            return False
            
        return True
    
    def list_sessions(self):
        """List all past meetings"""
        meetings = list_meetings()
        
        if not meetings:
            print("No meetings found")
            return
            
        print("Past meetings:")
        print("-" * 60)
        
        for meeting in meetings:
            start_time = meeting.get('start_time', 'Unknown')
            name = meeting.get('session_name', 'Unnamed')
            folder = meeting.get('session_folder', 'Unknown')
            
            print(f"Name: {name}")
            print(f"Time: {start_time}")
            print(f"Folder: {folder}")
            print("-" * 60)
    
    def view(self, session_name):
        """Open meeting output folder"""
        meetings = list_meetings()
        
        # Find session by name or folder name
        target_session = None
        for meeting in meetings:
            if (session_name in meeting.get('session_name', '') or 
                session_name in meeting.get('session_folder', '')):
                target_session = meeting
                break
                
        if not target_session:
            print(f"Session '{session_name}' not found")
            return False
            
        session_path = target_session.get('session_path')
        if session_path and Path(session_path).exists():
            # Open folder in explorer
            os.startfile(session_path)
            print(f"Opened session folder: {session_path}")
            return True
        else:
            print(f"Session folder not found: {session_path}")
            return False
    
    def _save_current_session_info(self, session):
        """Save current session info for stop command"""
        session_info = {
            'name': session.name,
            'session_folder': str(session.session_folder),
            'session_path': str(session.session_path)
        }
        
        info_file = Path(__file__).parent.parent / '.current_session.json'
        import json
        with open(info_file, 'w') as f:
            json.dump(session_info, f, indent=2)
    
    def _load_current_session_info(self):
        """Load current session info"""
        info_file = Path(__file__).parent.parent / '.current_session.json'
        if not info_file.exists():
            return None
            
        try:
            import json
            with open(info_file, 'r') as f:
                session_info = json.load(f)
                
            # Recreate session object
            session = MeetingSession(name=session_info['name'])
            session.session_folder = session_info['session_folder']
            session.session_path = Path(session_info['session_path'])
            
            return session
        except Exception as e:
            print(f"Warning: Could not load current session info: {e}")
            return None
    
    def _clear_current_session_info(self):
        """Clear current session info"""
        info_file = Path(__file__).parent.parent / '.current_session.json'
        if info_file.exists():
            info_file.unlink()
    
    def _run_post_processing(self, session):
        """Run post-processing scripts"""
        print("Running post-processing...")
        
        try:
            # Generate work items
            from work_items import WorkItemsGenerator
            work_items_gen = WorkItemsGenerator(session)
            work_items_gen.generate_work_items()
            
            # Generate summary and minutes
            from summarizer import MeetingSummarizer
            summarizer = MeetingSummarizer(session)
            summarizer.generate_minutes()
            summarizer.generate_html_report()
            
            print(f"Processing complete! Session saved to: {session.session_path}")
            
        except ImportError as e:
            print(f"Warning: Could not run post-processing: {e}")
        except Exception as e:
            print(f"Error in post-processing: {e}")

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='MeetingScribe v3 - AI-powered meeting recording and analysis')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Record command
    record_parser = subparsers.add_parser('record', help='Start live recording')
    record_parser.add_argument('--monitor', type=int, default=0, help='Monitor number to record (default: 0)')
    record_parser.add_argument('--name', type=str, help='Meeting name')
    
    # Stop command
    subparsers.add_parser('stop', help='Stop recording and process')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process existing MP4 file')
    process_parser.add_argument('file', help='MP4 file path')
    process_parser.add_argument('--name', type=str, help='Meeting name')
    
    # List command
    subparsers.add_parser('list', help='List past meetings')
    
    # View command
    view_parser = subparsers.add_parser('view', help='Open meeting output')
    view_parser.add_argument('session', help='Session name or folder name')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = MeetingScribeCLI()
    
    try:
        if args.command == 'record':
            success = cli.record(monitor=args.monitor, name=args.name)
        elif args.command == 'stop':
            success = cli.stop()
        elif args.command == 'process':
            success = cli.process(args.file, name=args.name)
        elif args.command == 'list':
            cli.list_sessions()
            success = True
        elif args.command == 'view':
            success = cli.view(args.session)
        else:
            parser.print_help()
            return
            
        if not success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()