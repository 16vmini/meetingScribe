"""
MeetingScribe - Live AI Meeting Assistant

Watches the transcript stream and uses Claude to provide real-time suggestions,
answer codebase questions, and flag potential issues.
"""
import threading
import time
import logging
import subprocess
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any

logger = logging.getLogger(__name__)

try:
    import anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False


# Tools exposed to Claude for codebase exploration
_TOOLS = [
    {
        "name": "read_file",
        "description": (
            "Read the contents of a file in the project. "
            "Path is relative to the project root."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative file path (e.g. 'src/main.py')",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "search_code",
        "description": (
            "Search the project codebase for a text pattern. "
            "Returns matching lines with file paths."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Text or regex pattern to search for",
                },
                "file_glob": {
                    "type": "string",
                    "description": "Optional glob to filter files (e.g. '*.py')",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "list_files",
        "description": (
            "List files in the project matching a glob pattern."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g. '**/*.py', 'src/*.ts')",
                },
            },
            "required": ["pattern"],
        },
    },
]

_SYSTEM_PROMPT = """\
You are a helpful AI assistant listening to a live meeting about a software project.
Your role is to:
1. When you hear a question about the codebase (e.g. "how does X work?", "where is Y defined?"), \
use your tools to find the answer and provide a concise response.
2. Suggest follow-up questions the user could ask other meeting participants.
3. Flag potential issues or inconsistencies mentioned in the discussion.

Keep responses SHORT (1-3 sentences). You're a subtle helper, not the main speaker.
Only respond when you have something genuinely useful to add.
If the conversation is just general chat, respond with exactly: null

The project root is: {project_root}
"""


class MeetingAssistant:
    """Live AI assistant that watches meeting transcripts and provides insights."""

    def __init__(self, project_root: str, api_key: str, callback: Optional[Callable] = None):
        """
        Args:
            project_root: Path to the codebase root for tool access.
            api_key: Anthropic API key.
            callback: Called as callback(suggestion: str, suggestion_type: str)
                      suggestion_type is one of "question", "answer", "insight".
                      Called from a background thread.
        """
        if not _HAS_ANTHROPIC:
            raise ImportError("anthropic package is not installed")

        self.project_root = Path(project_root)
        self.callback = callback
        self._client = anthropic.Anthropic(api_key=api_key)
        self._system_prompt = _SYSTEM_PROMPT.format(project_root=project_root)

        # Conversation context — last N chunks
        self._context: List[str] = []
        self._max_context = 10

        # Rate limiting
        self._chunk_counter = 0
        self._process_every_n = 3  # process every Nth chunk

        # Thread safety — only one API call at a time
        self._lock = threading.Lock()
        self._active = True

    def process_chunk(self, transcript_text: str, timestamp: float):
        """Called when a new transcript chunk arrives.

        Decides whether to query Claude based on rate limiting,
        then runs the API call on a background thread.
        """
        if not self._active:
            return

        # Always add to context
        self._context.append(transcript_text)
        if len(self._context) > self._max_context:
            self._context = self._context[-self._max_context:]

        self._chunk_counter += 1

        # Decide whether to process this chunk
        text_lower = transcript_text.lower()
        has_question = "?" in transcript_text
        has_claude_trigger = "claude" in text_lower or "check with" in text_lower
        is_nth_chunk = (self._chunk_counter % self._process_every_n) == 0

        if not has_question and not has_claude_trigger and not is_nth_chunk:
            return

        # Snapshot context for the thread
        context_snapshot = list(self._context)

        threading.Thread(
            target=self._process_in_background,
            args=(context_snapshot, timestamp),
            daemon=True,
        ).start()

    def stop(self):
        """Stop the assistant (no more API calls)."""
        self._active = False

    # ── Internal ──────────────────────────────────────────────────────────────

    def _process_in_background(self, context: List[str], timestamp: float):
        """Run Claude API call on a background thread."""
        if not self._lock.acquire(blocking=False):
            # Another call is already in progress — skip
            return
        try:
            result = self._call_claude(context)
            if result and result.strip().lower() != "null" and self.callback:
                suggestion_type = self._classify(result)
                self.callback(result, suggestion_type)
        except Exception:
            logger.exception("MeetingAssistant API call failed")
        finally:
            self._lock.release()

    def _call_claude(self, context: List[str]) -> Optional[str]:
        """Send the conversation context to Claude with tool access."""
        # Build the user message from context chunks
        numbered = "\n".join(
            f"[chunk {i+1}] {chunk}" for i, chunk in enumerate(context)
        )
        user_message = (
            "Here is the recent meeting transcript:\n\n"
            f"{numbered}\n\n"
            "Based on the above, do you have a useful suggestion, answer, or insight? "
            "If not, reply with just: null"
        )

        messages: List[Dict[str, Any]] = [
            {"role": "user", "content": user_message},
        ]

        # Agentic tool-use loop (Claude may call tools, then we feed results back)
        max_rounds = 5
        for _ in range(max_rounds):
            try:
                response = self._client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=512,
                    system=self._system_prompt,
                    tools=_TOOLS,
                    messages=messages,
                )
            except Exception:
                logger.exception("Anthropic API request failed")
                return None

            # Check if Claude wants to use tools
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            if not tool_use_blocks:
                # No tool calls — extract text response
                text_blocks = [b.text for b in response.content if b.type == "text"]
                return " ".join(text_blocks).strip() if text_blocks else None

            # Process tool calls and build tool results
            # First, add Claude's response as an assistant message
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for tool_block in tool_use_blocks:
                result = self._execute_tool(tool_block.name, tool_block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": result,
                })

            messages.append({"role": "user", "content": tool_results})

        # Exhausted rounds — shouldn't normally happen
        return None

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool and return the result as a string."""
        try:
            if tool_name == "read_file":
                return self._tool_read_file(tool_input["path"])
            elif tool_name == "search_code":
                return self._tool_search_code(
                    tool_input["pattern"],
                    tool_input.get("file_glob"),
                )
            elif tool_name == "list_files":
                return self._tool_list_files(tool_input["pattern"])
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            return f"Tool error: {e}"

    def _tool_read_file(self, rel_path: str) -> str:
        """Read a file relative to the project root."""
        full = self.project_root / rel_path
        # Security: ensure it's inside project_root
        try:
            full.resolve().relative_to(self.project_root.resolve())
        except ValueError:
            return "Error: path is outside the project root"

        if not full.is_file():
            return f"File not found: {rel_path}"

        try:
            text = full.read_text(encoding="utf-8", errors="replace")
            # Truncate very large files
            if len(text) > 8000:
                text = text[:8000] + "\n... (truncated)"
            return text
        except Exception as e:
            return f"Error reading file: {e}"

    def _tool_search_code(self, pattern: str, file_glob: Optional[str] = None) -> str:
        """Search the codebase using rg (ripgrep) or findstr as fallback."""
        try:
            # Try ripgrep first
            cmd = ["rg", "--no-heading", "-n", "--max-count", "20", pattern]
            if file_glob:
                cmd.extend(["--glob", file_glob])
            cmd.append(str(self.project_root))
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                output = result.stdout.strip()
                if len(output) > 4000:
                    output = output[:4000] + "\n... (truncated)"
                return output
            elif result.returncode == 1:
                return "No matches found."
        except FileNotFoundError:
            pass  # rg not installed, fall through to findstr
        except subprocess.TimeoutExpired:
            return "Search timed out."
        except Exception:
            pass

        # Fallback: findstr on Windows
        try:
            cmd = ["findstr", "/s", "/n", "/i", pattern]
            if file_glob:
                cmd.append(file_glob)
            else:
                cmd.append("*.*")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10,
                cwd=str(self.project_root),
            )
            output = result.stdout.strip()
            if output:
                if len(output) > 4000:
                    output = output[:4000] + "\n... (truncated)"
                return output
            return "No matches found."
        except Exception as e:
            return f"Search failed: {e}"

    def _tool_list_files(self, pattern: str) -> str:
        """List files matching a glob pattern."""
        try:
            matches = sorted(self.project_root.glob(pattern))
            # Filter to files only, limit results
            files = [str(m.relative_to(self.project_root)) for m in matches if m.is_file()]
            if not files:
                return "No files matched the pattern."
            if len(files) > 50:
                files = files[:50]
                files.append("... (truncated, 50+ matches)")
            return "\n".join(files)
        except Exception as e:
            return f"Error listing files: {e}"

    @staticmethod
    def _classify(text: str) -> str:
        """Classify the suggestion type based on content."""
        lower = text.lower()
        if "?" in text and any(w in lower for w in ("ask", "question", "could you", "might want to ask")):
            return "question"
        if any(w in lower for w in ("defined in", "found in", "located at", "the code", "function", "class", "file")):
            return "answer"
        return "insight"
