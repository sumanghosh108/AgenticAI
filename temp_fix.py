import re

path = r"c:\AgenticAI\research_and_analyst\api\routes\api_routes.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace: "message": f"Failed to fetch reports: {str(e)}"
# With: "message": "Failed to fetch reports. Please check server logs."
content = re.sub(r'f"([^"]+):\s*\{str\(e\)\}"', r'"\1. Please check server logs."', content)

# Replace: "message": str(e)
# With: "message": "An internal error occurred. Please check server logs."
content = re.sub(r'(?<=message":\s)str\(e\)', r'"An internal error occurred. Please check server logs."', content)

# Replace any lingering: f"{str(e)}"
content = re.sub(r'(?<=message":\s)f"\{str\(e\)\}"', r'"An internal error occurred. Please check server logs."', content)

# Replace f"Signup failed: {str(e)}" without colon
content = re.sub(r'f"([^"]+)\s*\{str\(e\)\}"', r'"\1. Please check server logs."', content)


with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Replaced all str(e) in api_routes.py successfully.")
