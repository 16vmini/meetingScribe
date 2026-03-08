# MeetingScribe - Future Ideas

## Live Claude Q&A (HIGH PRIORITY - do after core recording works)

Have Claude listen to the live transcript and proactively ask clarifying questions
during the meeting — displayed in the Live Dictation window.

### How it could work
- After each transcript chunk arrives, send recent transcript context to Claude API
- Claude detects ambiguity, action items without owners, or unanswered questions
- Surfaces a prompt in the Live Dictation window: e.g. "Who is owning the API migration?"
- User can dismiss, answer verbally (gets picked up next chunk), or type a response
- Claude's questions + answers get saved into the meeting notes

### Variations to consider
- "Coach mode" — Claude nudges the meeting toward better outcomes (e.g. "No decision was made on X")
- "Scribe mode" — Claude asks to clarify spellings of names, project codes, acronyms
- "Follow-up mode" — Claude flags items that need a deadline or owner assigned
- Configurable: user can toggle on/off per session

### Technical sketch
- Trigger: on each new transcript chunk callback in `live_session.py`
- Call Claude API (claude-sonnet-4-6) with rolling ~5-minute transcript window
- Prompt: "You are a meeting assistant. Based on the transcript so far, is there
  a question that would help clarify an important point? If yes, output it briefly.
  If no, output nothing."
- Display question in a yellow banner in `LiveDictationWindow`
- Rate-limit to at most one question per 2 minutes to avoid being annoying
