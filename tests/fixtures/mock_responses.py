"""Realistic mock responses for testing."""

CLAUDE_ANALYSIS_SUCCESS = {
    "similar_patterns": [
        {"pattern": "json.loads without validation", "location": "app.py:42"},
        {"pattern": "missing error handling", "location": "utils.py:15"}
    ],
    "root_cause_hypothesis": "The application attempts to parse JSON without validating the input string first",
    "affected_files": ["app.py", "utils.py", "handlers/api.py"],
    "dependency_chain": ["main", "handle_request", "process_data", "json.loads"],
    "code_snippets": [
        {
            "file": "app.py",
            "code": "data = json.loads(request_body)  # No validation"
        }
    ],
    "confidence_score": 0.85
}

GEMINI_VISUAL_ANALYSIS = {
    "detected_error": "JSONDecodeError: Expecting value",
    "error_location": "app.py:42",
    "ui_context": "VSCode editor showing Python traceback",
    "suggested_focus_areas": ["app.py", "Input validation layer"],
    "confidence_score": 0.92
}

OPENAI_WEB_RESEARCH = {
    "swarm_analysis": "Similar issues found on Stack Overflow suggest adding input validation before JSON parsing",
    "agent_trace": [
        "TriageAgent: Analyzing error pattern",
        "WebAgent: Searching Stack Overflow",
        "WebAgent: Found 3 similar issues",
        "SynthesisAgent: Compiling solutions"
    ],
    "status": "success"
}

SYNTHESIS_RESULT = '''
{
    "root_cause": "The application receives non-JSON data but attempts to parse it without validation, causing JSONDecodeError",
    "solutions": [
        {
            "title": "Add Input Validation",
            "description": "Validate that the input is valid JSON before parsing",
            "probability": 0.92
        },
        {
            "title": "Use json.loads with error handling",
            "description": "Wrap json.loads in try-except block",
            "probability": 0.85
        },
        {
            "title": "Use json.JSONDecoder with strict=False",
            "description": "Use lenient JSON parsing mode",
            "probability": 0.65
        }
    ],
    "fix_instructions": "1. Add validation: if not data or not data.strip(): return error\\n2. Wrap parsing: try: result = json.loads(data) except JSONDecodeError: handle_error()\\n3. Test with empty and malformed inputs",
    "confidence_score": 0.88
}
'''
