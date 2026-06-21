from typing import Dict
import os


def file_read_tool(file_path: str) -> Dict:
    """
    Read a file and return its content.

    Args:
        file_path: Path to the file to read

    Returns:
        dict with status, content, error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return {
            "status": "completed",
            "content": content,
            "bytes_read": len(content.encode('utf-8'))
        }
    except FileNotFoundError:
        return {
            "status": "failed",
            "content": "",
            "error": f"File not found: {file_path}"
        }
    except Exception as e:
        return {
            "status": "failed",
            "content": "",
            "error": str(e)
        }


def file_write_tool(file_path: str, content: str) -> Dict:
    """
    Write content to a file.

    Args:
        file_path: Path to the file to write
        content: Content to write

    Returns:
        dict with status, bytes_written, error
    """
    try:
        # Create parent directory if it doesn't exist
        parent_dir = os.path.dirname(file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        bytes_written = len(content.encode('utf-8'))

        return {
            "status": "completed",
            "bytes_written": bytes_written,
            "file_path": file_path
        }
    except Exception as e:
        return {
            "status": "failed",
            "bytes_written": 0,
            "error": str(e)
        }
