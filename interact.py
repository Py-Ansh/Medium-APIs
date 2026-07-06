#!/usr/bin/env python3
"""
Medium Python API Stealth Interaction Client
============================================
Implements full-spectrum article interaction including content retrieval, threaded
comment reading/writing, clap distribution, view/read emulation, browser event simulation,
and social connections (follow/unfollow).

Inherits general authentication and transport facilities from /init.py base layer.

Author: Ansh Raj
Date: June 2026
"""

import os
import re
import json
import time
import uuid
import random
from typing import List, Dict, Any, Union, Optional

from init import MediumClient as MediumBaseClient

from QUERY import PUBLISH_RESPONSE_QUERY


class MediumInteractionClient(MediumBaseClient):
    """
    Medium Client matching official browser behavior for interacting with other users' posts
    and accounts.
    """

    def _post_graphql(self, operation_name: str, query: str, variables: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Overrides base GraphQL caller to automatically inject Medium's mandatory
        routing, client name, version, and app routing headers.
        """
        target_id = variables.get("inResponseToPostId") or variables.get("targetPostId") or variables.get("targetUserId") or ""
        
        req_headers = {
            "graphql-operation": operation_name,
            "medium-frontend-path": f"/p/{target_id}" if target_id else "/",
            "medium-frontend-route": "post" if target_id else "homepage",
            "apollographql-client-version": "main-20260622-195358-6c4762890c",
            "apollographql-client-name": "lite",
            "medium-frontend-app": "lite/main-20260622-195358-6c4762890c"
        }
        
        if headers:
            req_headers.update(headers)

        self._get_xsrf_token()

        # Wrap in batch array as strictly expected by the Lite frontend gateway
        payload = [{
            "operationName": operation_name,
            "variables": variables,
            "query": query
        }]

        res = self.session.post(
            self.GRAPHQL_URL,
            json=payload,
            headers=req_headers
        )
        res.raise_for_status()
        
        res_json = res.json()
        if isinstance(res_json, list) and len(res_json) > 0:
            return res_json[0]
        return res_json

    

    def human_delay(self, min_s: float = 1.2, max_s: float = 3.5):
        """Staggers subsequent requests with randomized real-user processing intervals."""
        delay = random.uniform(min_s, max_s)
        time.sleep(delay)

    # =========================================================================
    # 1) Article Retrieval and Reading
    # =========================================================================

    def get_article_content(self, post_id: str) -> Dict[str, Any]:
        """
        Fetches the primary details, title, slug, and paragraph contents of an article.
        """
        query = """
        query PostPageQuery($postId: ID!) {
          postResult(id: $postId) {
            __typename
            ... on Post {
              id
              title
              mediumUrl
              uniqueSlug
              visibility
              isLocked
              creator {
                id
                name
                username
              }
              content {
                bodyModel {
                  paragraphs {
                    text
                    type
                  }
                }
              }
            }
          }
        }
        """
        variables = {"postId": post_id}
        return self._post_graphql("PostPageQuery", query, variables)

    def get_article_responses(self, post_id: str, limit: int = 10, next_page_paging: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Retrieves the comment/response threads linked to a target article.
        """
        query = """
        query PostResponsesQuery($postId: ID!, $paging: PagingOptions, $sortType: ResponseSortType) {
          postResult(id: $postId) {
            ... on Post {
              id
              threadedPostResponses(paging: $paging, sortType: $sortType) {
                posts {
                  id
                  mediumUrl
                  creator {
                    id
                    name
                    username
                  }
                  content {
                    bodyModel {
                      paragraphs {
                        text
                        type
                      }
                    }
                  }
                }
                pagingInfo {
                  next {
                    limit
                    to
                  }
                }
              }
            }
          }
        }
        """
        variables = {
            "postId": post_id,
            "sortType": "TOP",
            "paging": next_page_paging or {"limit": limit}
        }
        return self._post_graphql("PostResponsesQuery", query, variables)

    


    # =========================================================================
    # 2) Interactive Writing and Feedback (Production-Mined Operations)
    # =========================================================================

    

    def comment_on_article(self, post_id: str, text: str) -> Dict[str, Any]:
        """
        Submits a top-level comment (response) to an article using the exact 
        production-conforming delta structures mapped from browser capture files.
        Avoids layout fragments to run on any network condition cleanly.
        """
        sec_name = "".join(random.choices("abcdef0123456789", k=4))
        p1_name = "".join(random.choices("abcdef0123456789", k=4))
        p2_name = "".join(random.choices("abcdef0123456789", k=4))

        variables = {
            "inResponseToPostId": post_id,
            "deltas": [
                {
                    "type": 8,  # Section break initialization
                    "index": 0,
                    "section": {
                        "name": sec_name,
                        "startIndex": 0
                    }
                },
                {
                    "type": 1,  # Header paragraph spacer
                    "index": 0,
                    "paragraph": {
                        "name": p1_name,
                        "type": 3,
                        "text": "",
                        "markups": []
                    }
                },
                {
                    "type": 1,  # Text content container
                    "index": 1,
                    "paragraph": {
                        "name": p2_name,
                        "type": 1,
                        "text": text,
                        "markups": []
                    },
                    "verifySameName": False
                }
            ],
            "inResponseToQuoteId": None,
            "responseDistribution": "NOT_DISTRIBUTED",
            "sortType": "TOP"
        }
        return self._post_graphql("PublishPostThreadedResponse", PUBLISH_RESPONSE_QUERY, variables)

    def reply_to_comment(self, comment_id: str, text: str) -> Dict[str, Any]:
        """
        Submits a nested response/reply to an existing comment.
        """
        return self.comment_on_article(post_id=comment_id, text=text)

    def clap_on_article(self, post_id: str, claps: int = 1) -> Dict[str, Any]:
        """
        Awards claps to a Medium post. Matches production variables mapping perfectly.
        """
        if claps < 1 or claps > 50:
            raise ValueError("Medium clapping conventions mandate values between 1 and 50.")

        # Extract current user ID from synchronizing session cookies to complete variables mapping
        user_id = self.session.cookies.get("uid")
        if not user_id:
            # Fallback inline query if cookie representation is not accessible
            me_res = self._post_graphql("MeQuery", "query MeQuery { viewer { id } }", {})
            user_id = me_res.get("data", {}).get("viewer", {}).get("id", "")

        query = """
        mutation ClapMutation($targetPostId: ID!, $userId: ID!, $numClaps: Int!) {
          clap(targetPostId: $targetPostId, userId: $userId, numClaps: $numClaps) {
            viewerEdge {
              id
              clapCount
              __typename
            }
            id
            clapCount
            __typename
          }
        }
        """
        variables = {
            "targetPostId": post_id,
            "userId": user_id,
            "numClaps": claps
        }
        return self._post_graphql("ClapMutation", query, variables)


    # =========================================================================
    # 4) Behavioral Telemetry Simulation
    # =========================================================================

    def generate_view(self, post_id: str) -> Dict[str, Any]:
        """
        Simulates registering a pageview event for an article in browser telemetry logs.
        """
        tracking_id = uuid.uuid4().hex
        events = [
            {
                "event_type": "post.view",
                "timestamp": int(time.time() * 1000),
                "params": {
                    "postId": post_id,
                    "trackingId": tracking_id,
                    "source": "homepage_feed",
                    "referrer": "https://medium.com/"
                }
            }
        ]
        return self.log_client_events(events)

    def generate_read(self, post_id: str, dwell_time: float) -> Dict[str, Any]:
        """
        Simulates visual tracking metrics matching active article reading behavior.
        """
        tracking_id = uuid.uuid4().hex
        start_ms = int(time.time() * 1000)
        end_ms = start_ms + int(dwell_time * 1000)

        events = [
            {
                "event_type": "post.read_start",
                "timestamp": start_ms,
                "params": {
                    "postId": post_id,
                    "trackingId": tracking_id
                }
            },
            {
                "event_type": "post.dwell",
                "timestamp": end_ms,
                "params": {
                    "postId": post_id,
                    "trackingId": tracking_id,
                    "durationMs": int(dwell_time * 1000),
                    "scrolledPercent": random.randint(85, 100)
                }
            }
        ]
        return self.log_client_events(events)

    def simulated_idle_browse(self) -> Dict[str, Any]:
        """
        Simulates standard desktop browse context event streams.
        """
        events = [
            {
                "event_type": "client.idle",
                "timestamp": int(time.time() * 1000),
                "params": {
                    "viewportWidth": random.choice([1440, 1920, 1280]),
                    "viewportHeight": random.choice([900, 1080, 800])
                }
            }
        ]
        return self.log_client_events(events)


def print_json(data: Any):
    """Auxiliary printer tool formatting logs to terminal standard output stream."""
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Medium Stealth API CLI Interaction Manager")
    parser.add_argument(
        "--action", 
        choices=[
            "read_article", 
            "get_responses", 
            "comment", 
            "reply", 
            "clap", 
            "follow",
            "unfollow",
            "simulate_view", 
            "simulate_read", 
            "idle_browse"
        ],
        required=True,
        help="Interaction operation to execute"
    )
    parser.add_argument("--post-id", type=str, help="Target post ID or parent comment ID")
    parser.add_argument("--user-id", type=str, help="Target User ID for follow/unfollow actions")
    parser.add_argument("--text", type=str, help="Message body text for comment or reply thread")
    parser.add_argument("--claps", type=int, default=1, help="Number of claps (1 to 50)")
    parser.add_argument("--dwell-time", type=float, default=35.0, help="Simulated article reading time (seconds)")
    parser.add_argument(
        "--email-notifications", 
        type=str, 
        default="true", 
        choices=["true", "false"], 
        help="Enable/disable email notification when following user (default: true)"
    )
    parser.add_argument("--cookie", type=str, help="Direct raw cookies to load session")
    parser.add_argument("--env-cookie-var", type=str, default="MEDIUM_COOKIE", help="Env var containing cookie")

    args = parser.parse_args()

    # Read cookies from parameters or environment variables
    cookie_str = args.cookie if args.cookie else os.environ.get(args.env_cookie_var, "")

    client = MediumInteractionClient(cookies=cookie_str if cookie_str else None)

    try:
        if args.action == "read_article":
            if not args.post_id:
                print_json({"success": False, "msg": "Missing --post-id parameter"})
            else:
                print_json(client.get_article_content(args.post_id))

        elif args.action == "get_responses":
            if not args.post_id:
                print_json({"success": False, "msg": "Missing --post-id parameter"})
            else:
                print_json(client.get_article_responses(args.post_id))

        elif args.action == "comment":
            if not args.post_id or not args.text:
                print_json({"success": False, "msg": "Missing --post-id or --text parameter"})
            else:
                print_json(client.comment_on_article(args.post_id, args.text))

        elif args.action == "reply":
            if not args.post_id or not args.text:
                print_json({"success": False, "msg": "Missing --post-id (comment_id) or --text parameter"})
            else:
                print_json(client.reply_to_comment(args.post_id, args.text))

        elif args.action == "clap":
            if not args.post_id:
                print_json({"success": False, "msg": "Missing --post-id parameter"})
            else:
                print_json(client.clap_on_article(args.post_id, args.claps))

        elif args.action == "follow":
            if not args.user_id:
                print_json({"success": False, "msg": "Missing --user-id parameter"})
            else:
                enable_email = args.email_notifications.lower() == "true"
                print_json(client.follow_user(args.user_id, enable_email_notifications=enable_email))

        elif args.action == "unfollow":
            if not args.user_id:
                print_json({"success": False, "msg": "Missing --user-id parameter"})
            else:
                print_json(client.unfollow_user(args.user_id))

        elif args.action == "simulate_view":
            if not args.post_id:
                print_json({"success": False, "msg": "Missing --post-id parameter"})
            else:
                print_json(client.generate_view(args.post_id))

        elif args.action == "simulate_read":
            if not args.post_id:
                print_json({"success": False, "msg": "Missing --post-id parameter"})
            else:
                print_json(client.generate_read(args.post_id, args.dwell_time))

        elif args.action == "idle_browse":
            print_json(client.simulated_idle_browse())

        else:
            print_json({"success": False, "msg": f"Unknown action: {args.action}"})

    except Exception as e:
        import traceback
        print_json({
            "success": False,
            "msg": str(e),
            "traceback": traceback.format_exc()
        })