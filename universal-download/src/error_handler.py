"""
Comprehensive error handler and diagnostic analyzer for Universal Downloader.
Categorizes download exceptions into human-readable explanations and actionable solutions.
"""

def analyze_error(exception: Exception, context: str = "") -> dict:
    """
    Parses an exception and returns a structured dictionary:
    {
        "title": Short error heading,
        "message": Clear description of what happened,
        "hint": Actionable advice for the user
    }
    """
    err_str = str(exception)
    err_lower = err_str.lower()
    
    # 1. Private / Login Required Content
    if any(k in err_lower for k in ["private video", "sign in", "login required", "authentication required", "members-only"]):
        if "instagram" in err_lower:
            return {
                "title": "Private Instagram Content",
                "message": "This Instagram post, reel, or story is from a private account or requires authentication.",
                "hint": "Ensure the post is from a public profile, or open it in a browser to check accessibility."
            }
        elif "facebook" in err_lower:
            return {
                "title": "Private Facebook Content",
                "message": "This Facebook video is hosted in a private group or restricted to friends.",
                "hint": "Check that the Facebook video's privacy is set to Public."
            }
        return {
            "title": "Authentication / Private Video",
            "message": "The creator has set this content to private or restricted it to channel members.",
            "hint": "Verify the media is publicly accessible without requiring a sign-in."
        }

    # 2. Age Gate
    if "age" in err_lower and ("restricted" in err_lower or "confirm" in err_lower):
        return {
            "title": "Age-Restricted Content",
            "message": "This video requires age confirmation on the host platform.",
            "hint": "The platform requires age verification which cannot be bypassed without signed-in cookies."
        }

    # 3. HTTP 429 / Bot detection / Rate Limiting
    if "429" in err_lower or "too many requests" in err_lower or "bot" in err_lower or "sign in to confirm you’re not a bot" in err_lower:
        return {
            "title": "Rate Limit / Bot Protection",
            "message": "The platform is temporarily throttling requests or detected automated traffic.",
            "hint": "Wait 2-3 minutes before trying again, or try downloading individual links."
        }

    # 4. Network / Connection Errors
    if any(k in err_lower for k in ["timed out", "connection reset", "name resolution", "getaddrinfo failed", "urlopen error", "network is unreachable"]):
        return {
            "title": "Network Connection Failure",
            "message": "Failed to connect to the media server. The connection dropped or timed out.",
            "hint": "Check your internet connection, VPN, or proxy settings, then retry."
        }

    # 5. Unsupported or Invalid URL
    if "unsupported url" in err_lower or "is not a valid url" in err_lower or "no suitable extractor" in err_lower:
        return {
            "title": "Unsupported or Invalid URL",
            "message": "The provided address is not a supported media link or the link format is invalid.",
            "hint": "Ensure you copied a direct link to a video, reel, post, or playlist."
        }

    # 6. Video Deleted / Not Found (404)
    if "404" in err_lower or "not found" in err_lower or "video unavailable" in err_lower or "deleted" in err_lower:
        return {
            "title": "Content Unavailable",
            "message": "This video or playlist no longer exists, was deleted, or removed by the uploader.",
            "hint": "Verify that the video still plays in your web browser."
        }

    # 7. Geo-restriction
    if "geo" in err_lower or "not available in your country" in err_lower or "blocked in your country" in err_lower:
        return {
            "title": "Geo-Restricted Content",
            "message": "This media is blocked in your geographical region by the rights holder.",
            "hint": "You may need a VPN or proxy configured to a region where this media is available."
        }

    # 8. Playlist Range / Indexing
    if "playlist" in err_lower and ("index" in err_lower or "range" in err_lower):
        return {
            "title": "Playlist Range Error",
            "message": "The requested video count or range exceeds the available playlist items.",
            "hint": "Enter a number within the playlist count shown in brackets."
        }

    # 9. Disk Space or File Permissions
    if any(k in err_lower for k in ["no space left", "disk full", "permission denied", "access is denied"]):
        return {
            "title": "Disk / Permission Error",
            "message": "Cannot write to the target folder. Disk may be full or write permissions are restricted.",
            "hint": "Check free disk space on drive C: and ensure the Videos folder is writable."
        }

    # Fallback generic message
    clean_msg = err_str.split("\n")[0] if err_str else "An unknown error occurred during download."
    if len(clean_msg) > 150:
        clean_msg = clean_msg[:147] + "..."
    return {
        "title": "Download Error",
        "message": clean_msg,
        "hint": "Check the activity log below for technical details."
    }
