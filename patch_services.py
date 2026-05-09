import re

with open("app/services.py", "r") as f:
    content = f.read()

# Add import re at the top if not present
if "import re" not in content:
    content = content.replace("import os", "import os\nimport re")

# Replace _call_tutoring_llm signature and return
old_call = """def _call_tutoring_llm(activity: dict, history: list[dict[str, str]]) -> str:
    messages = _build_tutoring_llm_messages(activity, history)

    api_key = os.environ.get("OPENROUTER_API_KEY")
    model = os.environ.get("OPENROUTER_MODEL")

    if not api_key or not model:
        # Fallback for local testing if no API key or model is provided
        return _build_followup_tutoring_response(history)"""

new_call = """def _extract_log_score_meta(apicall: str) -> str | None:
    if not apicall or "logScore" not in apicall:
        return None
    match = re.search(r'meta=\\\\?["\\\'](.*?)\\\\?["\\\']', apicall)
    if match:
        return match.group(1)
    match = re.search(r'meta=([^)\\n]+)', apicall)
    if match:
        return match.group(1).strip()
    return None

def _call_tutoring_llm(activity: dict, history: list[dict[str, str]]) -> tuple[str, str]:
    messages = _build_tutoring_llm_messages(activity, history)

    api_key = os.environ.get("OPENROUTER_API_KEY")
    model = os.environ.get("OPENROUTER_MODEL")

    if not api_key or not model:
        # Fallback for local testing if no API key or model is provided
        return _build_followup_tutoring_response(history), \"\""""

content = content.replace(old_call, new_call)

# Replace the inner part of _call_tutoring_llm
old_return1 = """        # Extract just the response to show to the user
        return parsed_content.get("response", "Could you elaborate on that?")"""
new_return1 = """        # Extract the response and the APICall
        return parsed_content.get("response", "Could you elaborate on that?"), parsed_content.get("APICall", "")"""
content = content.replace(old_return1, new_return1)

old_return2 = """    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
        # Fallback if API fails or returns invalid JSON
        print(f"LLM Error: {e}")
        return "Can you make your reasoning more specific using the important terms from the activity?"""
new_return2 = """    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
        # Fallback if API fails or returns invalid JSON
        print(f"LLM Error: {e}")
        return "Can you make your reasoning more specific using the important terms from the activity?", \"\""""
content = content.replace(old_return2, new_return2)

# Update submitTutoringAnswer
old_submit = """    history.append({"role": "user", "content": str(answer).strip()})
    response_text = _call_tutoring_llm(activity, list(history))
    history.append({"role": "assistant", "content": response_text})"""

new_submit = """    history.append({"role": "user", "content": str(answer).strip()})
    response_text, apicall = _call_tutoring_llm(activity, list(history))
    
    meta = _extract_log_score_meta(apicall)
    if meta:
        existing_score = db.table("scores").select("id").eq("student_id", student["id"]).eq("course_id", course["id"]).eq("activity_no", activity_no).eq("meta", meta).execute()
        if not existing_score.data:
            logScore(email, password, course["course_id"], activity_no, 1.0, meta)
            
    history.append({"role": "assistant", "content": response_text})"""
content = content.replace(old_submit, new_submit)

with open("app/services.py", "w") as f:
    f.write(content)
