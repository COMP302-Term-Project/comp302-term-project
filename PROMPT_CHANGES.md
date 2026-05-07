# Prompt Changes Log

This document tracks changes made to the baseline student tutoring prompt (`Studen_Prompt_Simulate.txt`) as it was adapted for the backend implementation of the InClass Platform.

## Rationale
The original prompt was designed for a simulation where the LLM directly interacted with the student to gather their email, password, and course details before fetching the activity. In the actual backend implementation, the student is already authenticated via FastAPI routes, and the activity details (text and learning objectives) are retrieved directly from the Supabase database.

To make the LLM stateless, efficient, and aligned with the backend architecture, the prompt has been revised into a robust System Prompt.

## Changes Made

1. **Removed Authentication Gathering:**
   - **Baseline:** "First, obtain email, password, course_id, and topic_no from the student, Call studentApi(action:'getTopic')..."
   - **Revision:** Removed entirely. The backend now injects the `activity_text` and `learning_objectives` directly into the system prompt.

2. **JSON Response Enforcement:**
   - **Baseline:** Specified a two-field JSON `{"APICall":string, "response":string}`.
   - **Revision:** Strengthened the instruction to output *only* valid JSON. The backend parses this JSON, extracts the `"response"` string, and returns only the clean text to the student.

3. **Contextual History:**
   - **Baseline:** Implied a continuous chat session.
   - **Revision:** The backend maintains the `conversation_state` in the database and sends the past history as a list of text messages. The system prompt instructs the LLM to analyze this history to determine which learning objectives have been achieved.

4. **Terminology Alignment:**
   - **Baseline:** Mentioned "topic" and "topic_text".
   - **Revision:** Updated strictly to use "activity" and "activity text" to comply with the hard rules.

5. **Scoring Logic Delegation:**
   - **Baseline:** Instructed to call `studentApi(action:"logScore")` when an objective is achieved.
   - **Revision:** Maintained this instruction. The backend parses the `"APICall"` field; however, full execution of the `logScore` endpoint is deferred to US-K. For US-J, the LLM correctly generates the request, fulfilling the tutoring flow requirement.

## Expected Effect
The LLM will immediately start the tutoring session by asking a relevant question about the injected activity text. It will return predictable, parsable JSON. It will steer the student towards the hidden learning objectives using Socratic questions without revealing them directly, fully satisfying the requirements of US-J.