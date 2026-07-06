#!/usr/bin/env python3
"""
Medium Python API Stealth Publisher
==================================
A sleek, stealth-focused Python module implementing all Medium GraphQL and REST APIs
required to log in, write, edit, upload images, tag, schedule, and publish articles on Medium.

Stealth features:
- Utilizes `/init.py` base layer for browser impersonation (curl_cffi chrome124).
- Inherits cookie synchronization and Graphql transport engines.

Author: AI Studio Agent
Date: June 2026
"""

import os
import re
import json
import time
import mimetypes
import uuid
from typing import List, Dict, Any, Union, Optional

from init import MediumClient as MediumBaseClient, HAS_CURL_CFFI, HttpVersion

try:
    from curl_cffi import CurlMime
except ImportError:
    CurlMime = None


class MediumClient(MediumBaseClient):
    """
    Medium Client matched for official browser behavior focused on story publishing.
    Inherits general authentication, session transport, connection checks, and activity feeds from init.py.
    """

    # ==========================================
    # Medium Article Management API Workflow
    # ==========================================

    def get_collections(self, relationship: str = "admin") -> List[Dict[str, Any]]:
        """
        Gets a list of publications (collections) where the current user serves a role.

        Args:
            relationship: Role identifier, can be "admin" or "writer".
        """
        params = {"relationship": relationship, "logLockId": "1724"}
        res = self.session.get(self.COLLECTIONS_URL, params=params)
        res.raise_for_status()
        
        sanitized_text = self._strip_anti_hijack_prefix(res.text)
        data = json.loads(sanitized_text)
        return data.get("payload", {}).get("value", [])

    def create_draft(self, coverless: bool = True) -> Dict[str, Any]:
        """
        Prepares a blank article draft container on Medium.

        Returns:
            The raw response containing the newly assigned `id` of the post.
        """
        url = f"{self.NEW_STORY_URL}?logLockId=1724"
        payload = {
            "deltas": [],
            "baseRev": -1,
            "coverless": coverless,
            "visibility": 0
        }
        res = self.session.post(url, json=payload)
        res.raise_for_status()
        
        sanitized_text = self._strip_anti_hijack_prefix(res.text)
        data = json.loads(sanitized_text)
        return data.get("payload", {}).get("value", {})

    def upload_image(self, file_path: str) -> Dict[str, Any]:
        """
        Stealthily uploads an image file to Medium. Under the hood, this converts the upload
        to CurlMime formatting (required by curl_cffi for multipart data blocks) to bypass
        fingerprint and payload layout detection.
        
        The returned dict contains a 'fileId' string (e.g., '1*hZdfq...'), which should be
        passed directly inside blocks for inline image layouts in `save_content()`.

        Args:
            file_path: Absolute or relative path to the image asset.
            
        Returns:
            Dict containing the file ID, width, height, and metadata.
            
        Usage Example:
            >>> client = MediumClient(uid="...", sid="...")
            >>> img_data = client.upload_image("cover.jpg")
            >>> print(img_data["fileId"])
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image not found at path: {file_path}")

        file_name = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "image/jpeg"

        # Temporarily back up and remove Content-Type from session.headers to prevent curl_cffi from sending Content-Type: application/json
        original_content_types = {}
        for k in list(self.session.headers.keys()):
            if k.lower() == "content-type":
                original_content_types[k] = self.session.headers.pop(k)

        # Clone session headers to serve as the upload request base
        upload_headers = self.session.headers.copy()
        
        # Remove any lingering Content-Type headers
        for k in list(upload_headers.keys()):
            if k.lower() == "content-type":
                del upload_headers[k]

        # Inject browser standard upload attributes/headers safely
        upload_headers["Referer"] = "https://medium.com/new-story"
        upload_headers["Origin"] = "https://medium.com"
        
        # Ensure we have a valid x-xsrf-token
        if "x-xsrf-token" not in upload_headers:
            if self.xsrf:
                upload_headers["x-xsrf-token"] = self.xsrf
            else:
                upload_headers["x-xsrf-token"] = "1"

        try:
            if HAS_CURL_CFFI:
                # Prepare CurlMime for curl_cffi to bypass "files is not supported" constraint
                mp = CurlMime()
                mp.addpart(
                    name="file",
                    content_type=mime_type,
                    filename=file_name,
                    local_path=file_path
                )
                try:
                    # Pass http_version=HttpVersion.V1_1 if available to force HTTP/1.1.
                    # Many security gateways reset the peer connection during multipart file streams
                    # if sent inside multiplexed HTTP/2 or HTTP/3 frames.
                    kwargs = {}
                    if HttpVersion is not None:
                        kwargs["http_version"] = HttpVersion.V1_1
                    res = self.session.post(self.UPLOAD_URL, multipart=mp, headers=upload_headers, **kwargs)
                finally:
                    mp.close()
            else:
                # Fallback to requests if curl_cffi is missing
                with open(file_path, "rb") as f:
                    files = {
                        "file": (file_name, f.read(), mime_type)
                    }
                    res = self.session.post(self.UPLOAD_URL, files=files, headers=upload_headers)
        finally:
            # Restore any removed Content-Type headers to keep the session state clean
            for k, v in original_content_types.items():
                self.session.headers[k] = v

        res.raise_for_status()
        
        sanitized_text = self._strip_anti_hijack_prefix(res.text)
        data = json.loads(sanitized_text)
        return data.get("payload", {}).get("value", {})

    def save_content(self, post_id: str, title: str, subtitle: str, paragraphs: List[Union[str, Dict[str, Any]]], images: Optional[List[Dict[str, Any]]] = None, base_rev: int = -1) -> Dict[str, Any]:
        """
        Saves full article content (Deltas formatting) including title, subtitle, and multi-block paragraphs.
        
        Allows fully flexible mixed layouts containing text, custom headers, blockquotes, code blocks,
        and inline uploaded images anywhere in any order.

        Args:
            post_id: Unique Medium post ID string.
            title: Main title string (converts automatically to H3 display).
            subtitle: Main subtitle string (converts automatically to H4 display).
            paragraphs: A list of items representing text blocks. Each item can be:
                - A plain string (default paragraph type).
                - A dictionary containing rich block configuration:
                    {
                        "type": "paragraph" | "heading" | "subheading" | "image" | "code" | "quote",
                        "text": "Your markdown or plain text",
                        "fileId": "1*hZdfq..." (Only required/used if type == "image"),
                        "width": 1200,          (Optional, image width helper)
                        "height": 800,          (Optional, image height helper)
                        "layout": 1             (Optional, 1 = inset center)
                    }
            images: List of uploaded images to append to the end of the post (legacy argument).
            base_rev: Current revision indexing, default -1 to use current version automatically.
            
        Usage Example:
            >>> client = MediumClient(uid="...", sid="...")
            >>> blocks = [
            ...     "This is a standard starting paragraph.",
            ...     {"type": "heading", "text": "Sub-Technical Breakdown"},
            ...     {"type": "code", "text": "print('Hello From Python API!')"},
            ... ]
            >>> client.save_content("post_id_123", "Main Title", "Subtitle here", blocks)
        """
        url = f"https://medium.com/p/{post_id}/deltas?logLockId=1724"
        
        # Build deltas sequentially
        deltas = []
        
        # Section index delta (Initiates section)
        section_name = "sec_" + uuid.uuid4().hex[:4]
        deltas.append({
            "type": 8,
            "index": 0,
            "section": {
                "name": section_name,
                "startIndex": 0
            }
        })

        # Delta paragraph: Title (H3 - type 3)
        title_name = "tit_" + uuid.uuid4().hex[:4]
        deltas.append({
            "type": 1,
            "index": 0,
            "paragraph": {
                "name": title_name,
                "type": 3,
                "text": title,
                "markups": []
            }
        })

        # Delta paragraph: Subtitle (H4 - type 13)
        subtitle_name = "sub_" + uuid.uuid4().hex[:4]
        deltas.append({
            "type": 1,
            "index": 1,
            "paragraph": {
                "name": subtitle_name,
                "type": 13,
                "text": subtitle,
                "markups": []
            }
        })

        current_index = 2

        # Delta paragraphs: Mixed block inputs mapping
        # This allows you to intersperse headings, images, blockquotes, and code snippets anywhere in any order!
        type_mapping = {
            "p": 1, "paragraph": 1, "1": 1, 1: 1,
            "h3": 3, "heading": 3, "3": 3, 3: 3,
            "h4": 13, "subheading": 13, "13": 13, 13: 13,
            "img": 4, "image": 4, "4": 4, 4: 4,
            "code": 8, "pre": 8, "8": 8, 8: 8,
            "quote": 10, "blockquote": 10, "10": 10, 10: 10
        }

        for block in paragraphs:
            if isinstance(block, dict):
                # Structured block dictionary
                raw_type = block.get("type", 1)
                resolved_type = 1
                if isinstance(raw_type, str):
                    resolved_type = type_mapping.get(raw_type.lower(), 1)
                elif isinstance(raw_type, int):
                    resolved_type = type_mapping.get(raw_type, 1)

                p_name = "blk_" + uuid.uuid4().hex[:4]

                if resolved_type == 4:
                    # Image block
                    deltas.append({
                        "type": 1,
                        "index": current_index,
                        "paragraph": {
                            "name": p_name,
                            "type": 4,
                            "text": block.get("text") or block.get("caption") or "",
                            "markups": [],
                            "layout": block.get("layout", 1),
                            "metadata": {
                                "id": block.get("fileId") or block.get("id"),
                                "originalWidth": block.get("width") or block.get("originalWidth", 1200),
                                "originalHeight": block.get("height") or block.get("originalHeight", 800)
                            }
                        }
                    })
                else:
                    # Text/Heading/Quote/Code block
                    deltas.append({
                        "type": 1,
                        "index": current_index,
                        "paragraph": {
                            "name": p_name,
                            "type": resolved_type,
                            "text": block.get("text", ""),
                            "markups": block.get("markups") or []
                        }
                    })
            else:
                # Flat body paragraph string string
                p_name = "p_" + uuid.uuid4().hex[:4]
                deltas.append({
                    "type": 1,
                    "index": current_index,
                    "paragraph": {
                        "name": p_name,
                        "type": 1,
                        "text": str(block),
                        "markups": []
                    }
                })
            current_index += 1

        # Delta paragraphs: Supporting appended trailing images via the legacy 'images' kwarg
        if images:
            for img in images:
                img_name = "img_" + uuid.uuid4().hex[:4]
                deltas.append({
                    "type": 1,
                    "index": current_index,
                    "paragraph": {
                        "name": img_name,
                        "type": 4,
                        "text": img.get("text", ""),
                        "markups": [],
                        "layout": 1,
                        "metadata": {
                            "id": img.get("fileId"),
                            "originalWidth": img.get("width", 1200),
                            "originalHeight": img.get("height", 800)
                        }
                    }
                })
                current_index += 1

        payload = {
            "id": post_id,
            "deltas": deltas,
            "baseRev": base_rev
        }

        res = self.session.post(url, json=payload)
        res.raise_for_status()
        
        sanitized_text = self._strip_anti_hijack_prefix(res.text)
        data = json.loads(sanitized_text)
        return data.get("payload", {}).get("value", {})

    def get_tags_typeahead(self, query_prefix: str) -> List[Dict[str, Any]]:
        """
        Fetches dynamic auto-suggest tags from Medium using tag prefix.
        
        Args:
            query_prefix: Starting characters of the tag.
        """
        query = """
        query TagsMultiSelectFieldQuery($prefix: String!, $includeNormalized: Boolean!) {
          tagsTypeahead(prefix: $prefix, includeNormalized: $includeNormalized) {
            __typename
            id
            displayTitle
            normalizedTagSlug
            followerCount
          }
        }
        """
        variables = {
            "prefix": query_prefix,
            "includeNormalized": False
        }
        res = self._post_graphql("TagsMultiSelectFieldQuery", query, variables)
        return res.get("data", {}).get("tagsTypeahead", [])

    def set_tags(self, post_id: str, tags: List[str]) -> Dict[str, Any]:
        """
        Sets article tag tags to Medium. Max 5 tags permitted.

        Args:
            post_id: Unique Medium post ID.
            tags: List of tag strings (e.g. ['programming', 'ai']).
        """
        query = """
        mutation SetPostTagsMutation($targetPostId: ID!, $tagNames: [String!]!) {
          setPostTags(targetPostId: $targetPostId, tagNames: $tagNames) {
            __typename
            id
            tagsConnection {
              __typename
              edges {
                __typename
                node {
                  __typename
                  id
                  displayTitle
                  normalizedTagSlug
                }
              }
            }
          }
        }
        """
        variables = {
            "targetPostId": post_id,
            "tagNames": tags
        }
        res = self._post_graphql("SetPostTagsMutation", query, variables)
        return res.get("data", {}).get("setPostTags", {})

    def schedule_post(self, post_id: str, publish_at_timestamp_sec: int) -> Dict[str, Any]:
        """
        Schedules a story to be published automatically at a designated time.

        Args:
            post_id: Unique Medium post ID.
            publish_at_timestamp_sec: Time to publish in Unix epoch seconds.
        """
        query = """
        mutation UpdateSubmitSchedulePostMutation($input: UpdatePostPublishScheduleInput!) {
          updatePostPublishSchedule(input: $input) {
            __typename
          }
        }
        """
        # Convert seconds to milliseconds as required by Medium GraphQL api
        variables = {
            "input": {
                "postId": post_id,
                "publishAt": int(publish_at_timestamp_sec * 1000)
            }
        }
        res = self._post_graphql("UpdateSubmitSchedulePostMutation", query, variables)
        return res.get("data", {}).get("updatePostPublishSchedule", {})

    def publish_post(self, post_id: str) -> Dict[str, Any]:
        """
        Publishes an article draft immediately.

        Args:
            post_id: Unique Medium post ID.
        """
        query = """
        mutation SubmitPublishPostMutation($input: SetPostPublishedInput!) {
          setPostPublished(input: $input) {
            __typename
          }
        }
        """
        variables = {
            "input": {
                "postId": post_id
            }
        }
        res = self._post_graphql("SubmitPublishPostMutation", query, variables)
        return res.get("data", {}).get("setPostPublished", {})

    def get_post_metadata(self, post_id: str) -> Dict[str, Any]:
        """
        Queries Medium GraphQL to load draft metadata, publish settings, and preview indicators.

        Args:
            post_id: Medium story ID.
        """
        query = """
        query PostSubmitMainQuery($postId: ID!) {
          postResult(id: $postId) {
            __typename
            ... on Post {
              id
              title
              isPublished
              isLocked
              isPublishToEmail
              visibility
              extendedPreviewContent {
                subtitle
              }
              tagsConnection {
                edges {
                  node {
                    id
                    displayTitle
                    normalizedTagSlug
                  }
                }
              }
            }
          }
        }
        """
        variables = {"postId": post_id}
        res = self._post_graphql("PostSubmitMainQuery", query, variables)
        return res.get("data", {}).get("postResult", {})


# CLI JSON Argument Parser for subprocess execution
if __name__ == "__main__":
    import sys
    import argparse

    # Quick helper to print json output and exit
    def print_json(data: Any):
        print(json.dumps(data, ensure_ascii=False))
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Medium Stealth API Command Line Utility")
    parser.add_argument("--action", type=str, required=True, help="Action to perform")
    parser.add_argument("--uid", type=str, help="Medium User ID")
    parser.add_argument("--sid", type=str, help="Medium Session ID (sid)")
    parser.add_argument("--xsrf", type=str, help="Medium XSRF cookie token")
    
    # Action specific parameters
    parser.add_argument("--email", type=str, help="Email address for susp/login trigger")
    parser.add_argument("--code", type=str, help="6-digit verification code")
    parser.add_argument("--post-id", type=str, help="Medium Post ID")
    parser.add_argument("--title", type=str, default="", help="Story title")
    parser.add_argument("--subtitle", type=str, default="", help="Story subtitle")
    parser.add_argument("--paragraphs", type=str, help="JSON array of story paragraph strings")
    parser.add_argument("--image-path", type=str, help="Local file path for upload image")
    parser.add_argument("--image-base64", type=str, help="Base64 encoded image to upload")
    parser.add_argument("--tags", type=str, help="JSON list of tags")
    parser.add_argument("--publish-at", type=int, help="Publish timestamp in seconds for schedule")
    parser.add_argument("--query", type=str, help="Query search prefix string")

    args = parser.parse_args()

    try:
        # Initialize client with provided tokens
        client = MediumClient(uid=args.uid, sid=args.sid, xsrf=args.xsrf)

        if args.action == "check_conn":
            print_json(client.check_connection())

        elif args.action == "get_collections":
            print_json({"success": True, "collections": client.get_collections()})

        elif args.action == "create_draft":
            print_json({"success": True, "draft": client.create_draft()})

        elif args.action == "save_content":
            if not args.post_id:
                print_json({"success": False, "msg": "Missing --post-id parameter"})
            
            p_list = []
            if args.paragraphs:
                p_list = json.loads(args.paragraphs)

            img_list = []
            if args.image_base64:
                # If a base64 image is passed, write to a temp file and upload it
                import base64
                temp_filename = f"temp_upload_{uuid.uuid4().hex[:6]}.jpg"
                try:
                    img_data = base64.b64decode(args.image_base64.split(",")[-1])
                    with open(temp_filename, "wb") as temp_file:
                        temp_file.write(img_data)
                    
                    # Upload using our client
                    uploaded_info = client.upload_image(temp_filename)
                    if uploaded_info.get("fileId"):
                        img_list.append({
                            "fileId": uploaded_info.get("fileId"),
                            "width": 1200,
                            "height": 800,
                            "text": "Uploaded via Stealth API"
                        })
                finally:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)

            result = client.save_content(
                post_id=args.post_id,
                title=args.title,
                subtitle=args.subtitle,
                paragraphs=p_list,
                images=img_list if img_list else None
            )
            print_json({"success": True, "result": result, "images": img_list})

        elif args.action == "tags_suggest":
            if not args.query:
                print_json({"success": False, "msg": "Missing --query parameter"})
            print_json({"success": True, "tags": client.get_tags_typeahead(args.query)})

        elif args.action == "set_tags":
            if not args.post_id or not args.tags:
                print_json({"success": False, "msg": "Missing --post-id or --tags parameter"})
            t_list = json.loads(args.tags)
            print_json({"success": True, "result": client.set_tags(args.post_id, t_list)})

        elif args.action == "schedule_post":
            if not args.post_id or not args.publish_at:
                print_json({"success": False, "msg": "Missing --post-id or --publish-at parameter"})
            print_json({"success": True, "result": client.schedule_post(args.post_id, args.publish_at)})

        elif args.action == "publish_post":
            if not args.post_id:
                print_json({"success": False, "msg": "Missing --post-id parameter"})
            print_json({"success": True, "result": client.publish_post(args.post_id)})

        elif args.action == "upload_image":
            target_path = args.image_path
            if args.image_base64:
                import base64
                target_path = f"temp_upload_{uuid.uuid4().hex[:6]}.jpg"
                img_data = base64.b64decode(args.image_base64.split(",")[-1])
                with open(target_path, "wb") as temp_file:
                    temp_file.write(img_data)
                
            if not target_path or not os.path.exists(target_path):
                print_json({"success": False, "msg": "No valid image specified or found"})
                
            try:
                res_img = client.upload_image(target_path)
                print_json({"success": True, "result": res_img})
            finally:
                if args.image_base64 and os.path.exists(target_path):
                    os.remove(target_path)

        elif args.action == "get_alerts":
            print_json({
                "success": True,
                "status": client.get_alert_status(),
                "activities": client.get_activities()
            })

        else:
            print_json({"success": False, "msg": f"Unknown action: {args.action}"})

    except Exception as e:
        import traceback
        print_json({
            "success": False,
            "msg": str(e),
            "traceback": traceback.format_exc()
        })

