"""Constants and configuration values for the GCSE Question Generator."""

# Valid GCSE topics
VALID_TOPICS = [
    "Number",
    "Algebra", 
    "Geometry",
    "Statistics",
    "Probability",
    "Ratio"
]

# Valid difficulty tiers
VALID_TIERS = ["Foundation", "Higher"]

# Topic mapping for S3 content retrieval (deterministic mapping)
TOPIC_MAPPING = {
    "fractions": {"domain": "number", "file": "fractions.json"},
    "decimals": {"domain": "number", "file": "decimals.json"},
    "percentages": {"domain": "number", "file": "percentages.json"},
    "integers": {"domain": "number", "file": "integers.json"},
    "algebra": {"domain": "algebra", "file": "linear-equations.json"},
    "equations": {"domain": "algebra", "file": "linear-equations.json"},
    "expressions": {"domain": "algebra", "file": "expressions.json"},
    "sequences": {"domain": "algebra", "file": "sequences.json"},
    "geometry": {"domain": "geometry", "file": "angles.json"},
    "angles": {"domain": "geometry", "file": "angles.json"},
    "shapes": {"domain": "geometry", "file": "shapes.json"},
    "area": {"domain": "geometry", "file": "area-perimeter.json"},
    "perimeter": {"domain": "geometry", "file": "area-perimeter.json"},
    "statistics": {"domain": "statistics", "file": "data-analysis.json"},
    "data": {"domain": "statistics", "file": "data-analysis.json"},
    "graphs": {"domain": "statistics", "file": "graphs.json"},
    "probability": {"domain": "probability", "file": "probability.json"},
    "ratio": {"domain": "ratio", "file": "ratio-proportion.json"},
    "proportion": {"domain": "ratio", "file": "ratio-proportion.json"}
}

# Query validation constants
MAX_QUERY_LENGTH = 500
MIN_QUESTION_COUNT = 1
MAX_QUESTION_COUNT = 100

# SQL injection patterns to detect and block
SQL_INJECTION_PATTERNS = [
    r"(?i)\b(union\s+select|select\s+\*|select\s+.+\s+from|insert\s+into|update\s+set|delete\s+from|drop\s+table|create\s+table|alter\s+table)\b",  # SQL command patterns
    r"(?i)\b(exec|execute|sp_|xp_)\b",  # Stored procedure patterns
    r"(?i)\b(or\s+1\s*=\s*1|and\s+1\s*=\s*1)\b",  # Common injection patterns
    r"(?i)\b(having\s+|group\s+by\s+|order\s+by\s+)\b",  # SQL clause patterns
    r"(?i)(script|javascript|vbscript)",
    r"['\";]",
    r"--",
    r"/\*",
    r"\*/",
    r"(?i)\b(waitfor\s+delay|benchmark|sleep)\b",  # Time-based injection
    r"(?i)\b(information_schema|sys\.tables|sys\.columns)\b",  # Schema enumeration
    r"(?i)\b(load_file|into\s+outfile|into\s+dumpfile)\b"  # File operations
]

# XSS patterns to detect and block
XSS_PATTERNS = [
    r"<script[^>]*>",
    r"</script>",
    r"javascript:",
    r"vbscript:",
    r"data:text/html",
    r"onload\s*=",
    r"onerror\s*=",
    r"onclick\s*=",
    r"onmouseover\s*=",
    r"onfocus\s*=",
    r"onblur\s*=",
    r"onchange\s*=",
    r"onsubmit\s*=",
    r"<iframe[^>]*>",
    r"<object[^>]*>",
    r"<embed[^>]*>",
    r"<link[^>]*>",
    r"<meta[^>]*>",
    r"expression\s*\(",
    r"url\s*\(",
    r"@import",
    r"<svg[^>]*onload"
]

# Malicious content patterns
MALICIOUS_CONTENT_PATTERNS = [
    r"(?i)\b(eval|exec|system|shell_exec|passthru|proc_open)\b",  # Code execution
    r"(?i)\b(file_get_contents|fopen|fread|include|require)\b",  # File operations
    r"(?i)\b(base64_decode|hex2bin|gzinflate)\b",  # Encoding/obfuscation
    r"(?i)\b(curl|wget|http_get|fsockopen)\b",  # Network operations
    r"(?i)\b(phpinfo|var_dump|print_r)\b",  # Information disclosure
    r"\$\{[^}]*\}",  # Template injection patterns
    r"<%[^%]*%>",  # Server-side template patterns
    r"{{[^}]*}}",  # Template engine patterns
]

# Rate limiting constants
RATE_LIMIT_REQUESTS_PER_HOUR = 100
RATE_LIMIT_WINDOW_SECONDS = 3600

# Authentication constants
API_KEY_HEADER = "X-API-Key"
API_KEY_MIN_LENGTH = 32