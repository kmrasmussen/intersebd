# Add this function near the top of your file, after the imports
import hashlib
import json
def hash_json_content(content):
    """
    Create a consistent string hash from a JSON-serializable object.
    
    Args:
        content: Any JSON-serializable object (dict, list, string, etc.)
        
    Returns:
        str: A hexadecimal MD5 hash string
    """
    json_str = json.dumps(content, sort_keys=True)
    return hashlib.md5(json_str.encode('utf-8')).hexdigest()