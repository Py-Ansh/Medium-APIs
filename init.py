#!/usr/bin/env python3
"""
Medium Python API Stealth Base Client
=====================================
Pruned, stealth-focused base client containing authentication, XSRF token handling,
low-level GraphQL/REST post channels, and client telemetry/simulation events.
Includes high-fidelity human emulation session bootstrapping.

Author: AI Studio Agent
Date: June 2026
"""

import os
import re
import json
import time
import uuid
import random
from typing import List, Dict, Any, Union, Optional

# Stealth imports: prefer curl_cffi for browser impersonation, fallback to requests
try:
    from curl_cffi import requests, CurlMime
    try:
        from curl_cffi.requests import HttpVersion
    except ImportError:
        HttpVersion = None
    HAS_CURL_CFFI = True
except ImportError:
    import requests
    HAS_CURL_CFFI = False
    HttpVersion = None


class MediumClient:
    """
    Base Medium Client matching official browser behavior for GraphQL APIs and REST requests.
    Supports session persistence, XSRF, connections check, and telemetry logs.
    """

    GRAPHQL_URL = "https://medium.com/_/graphql"
    BATCH_URL = "https://medium.com/_/batch"
    UPLOAD_URL = "https://medium.com/_/upload"
    NEW_STORY_URL = "https://medium.com/new-story"
    SIGNIN_URL = "https://medium.com/m/signin"
    COLLECTIONS_URL = "https://medium.com/_/api/me/collections"
    ACTIVITY_STATUS_URL = "https://medium.com/_/api/activity-status"
    ACTIVITY_URL = "https://medium.com/_/api/activity"

    def __init__(self, cookies: Optional[Union[str, Dict[str, str]]] = None, token: Optional[str] = None):
        if HAS_CURL_CFFI:
            self.session = requests.Session(impersonate="chrome124")
        else:
            self.session = requests.Session()

        self.xsrf_token = ""
        self._init_headers()

        if cookies:
            self.set_cookies(cookies)
        if token:
            self.set_auth_token(token)

    def _init_headers(self):
        """Pre-populates browser headers to prevent basic automation checks."""
        self.session.headers.update({
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "apollographql-client-name": "lite",
            "apollographql-client-version": "main-20260622-181304-d2c679414a",
            "referer": "https://medium.com/",
            "medium-frontend-path": "/",
            "medium-frontend-route": "homepage"
        })

    def set_cookies(self, cookies: Union[str, Dict[str, str]]):
        """Synchronizes raw browser string cookies or mapping dictionaries."""
        if isinstance(cookies, str):
            cookie_dict = {}
            for cookie in cookies.split(";"):
                cookie = cookie.strip()
                if not cookie or "=" not in cookie:
                    continue
                k, v = cookie.split("=", 1)
                cookie_dict[k] = v
            self.session.cookies.update(cookie_dict)
        else:
            self.session.cookies.update(cookies)
        
        # Pull XSRF token from sync cookies if populated
        for k, v in self.session.cookies.items():
            if k == "sid":
                self.xsrf_token = v
                self.session.headers["otter-xsrf-token"] = v

    def set_auth_token(self, token: str):
        """Sets internal XSRF/Session authorization token."""
        self.xsrf_token = token
        self.session.headers["otter-xsrf-token"] = token

    def _strip_anti_hijack_prefix(self, text: str) -> str:
        """Removes security evaluation shields before JSON processing."""
        prefix = "])}while(1);</x>"
        if text.startswith(prefix):
            return text[len(prefix):]
        return text

    def _get_xsrf_token(self) -> str:
        """Loads Medium frontend to seed cookies and resolve security headers."""
        if self.xsrf_token:
            return self.xsrf_token

        res = self.session.get(self.SIGNIN_URL)
        res.raise_for_status()

        # Match structural dynamic XSRF values
        match = re.search(r'"xsrfToken":"([^"]+)"', res.text)
        if match:
            self.xsrf_token = match.group(1)
            self.session.headers["otter-xsrf-token"] = self.xsrf_token
            return self.xsrf_token

        # Fallback to cookie extraction
        for k, v in self.session.cookies.items():
            if k == "sid":
                self.xsrf_token = v
                self.session.headers["otter-xsrf-token"] = v
                return v

        return ""

    def _post_graphql(self, operation_name: str, query: str, variables: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Dispatches structured, single-request GraphQL queries.
        """
        self._get_xsrf_token()

        payload = {
            "operationName": operation_name,
            "variables": variables,
            "query": query
        }

        req_headers = {}
        if headers:
            req_headers.update(headers)

        res = self.session.post(
            self.GRAPHQL_URL,
            json=payload,
            headers=req_headers
        )
        res.raise_for_status()
        return res.json()

    # =========================================================================
    # Telemetry and Testing APIs
    # =========================================================================

    def log_experiment_exposure(self, experiment_id: str, value: str) -> Dict[str, Any]:
        """Declares exposure values for dynamic client A/B testing."""
        query = """
        mutation LogExperimentExposure($experimentId: String!, $value: String!) {
          logExperimentExposure(experimentId: $experimentId, value: $value) {
            experimentId
            value
          }
        }
        """
        variables = {
            "experimentId": experiment_id,
            "value": value
        }
        res = self._post_graphql("LogExperimentExposure", query, variables)
        return res.get("data", {}).get("logExperimentExposure", {})

    def log_client_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Sends raw telemetry event streams to Medium servers."""
        query = """
        mutation LogClientEventsMutation($payload: String!) {
          logClientEvents(input: {payload: $payload}) {
            success
            __typename
          }
        }
        """
        variables = {
            "payload": json.dumps(events)
        }
        res = self._post_graphql("LogClientEventsMutation", query, variables)
        return res.get("data", {}).get("logClientEvents", {})

    # =========================================================================
    # Human Emulation Session Bootstrapping
    # =========================================================================

    def Simulate_Human_session(self) -> Dict[str, Any]:
        """
        Executes a complete high-fidelity browser-session bootstrap:
        1. Performs a GET request to the signin/home page (seeds cookies & grabs XSRF).
        2. Dispatches VisitorQuery to initialize backend tracking contexts.
        3. Fires a LogExperimentExposure mutation to enroll the user in testing groups.
        4. Queries HomepageFeedQuery to load stream details (mimicking default dashboard load).
        """
        # Step 1: Initialize cookies and XSRF token via initial GET
        self.xsrf_token = ""
        self._get_xsrf_token()
        time.sleep(random.uniform(1.8, 3.2))

        # Step 2: Establish visitor tracking session
        visitor_query = """
        query VisitorQuery {
          viewer {
            id
            name
            username
          }
        }
        """
        visitor_res = self._post_graphql("VisitorQuery", visitor_query, {})
        time.sleep(random.uniform(1.2, 2.5))

        # Step 3: Log baseline experiment exposures
        exp_res = self.log_experiment_exposure(
            experiment_id="conversational_writing_v1",
            value="treatment"
        )
        time.sleep(random.uniform(1.0, 2.2))

        # Step 4: Warmup feed retrieval query
        feed_query = """
        query HomepageFeedQuery($paging: PagingInput) {
          viewer {
            id
            followingFeed(paging: $paging) {
              stream {
                id
                title
              }
            }
          }
        }
        """
        feed_res = self._post_graphql("HomepageFeedQuery", feed_query, {"paging": {"limit": 10}})
        
        return {
            "success": True,
            "visitor": visitor_res,
            "experiment": exp_res,
            "feed": feed_res
        }

    # =========================================================================
    # REST Alert Status Handlers
    # =========================================================================

    def get_alert_status(self) -> Dict[str, Any]:
        """Fetches counts of unread dashboard alerts."""
        res = self.session.get(self.ACTIVITY_STATUS_URL)
        res.raise_for_status()
        sanitized_text = self._strip_anti_hijack_prefix(res.text)
        return json.loads(sanitized_text).get("payload", {})

    def get_activities(self) -> List[Dict[str, Any]]:
        """Fetches list of historical activity alerts."""
        res = self.session.get(self.ACTIVITY_URL)
        res.raise_for_status()
        sanitized_text = self._strip_anti_hijack_prefix(res.text)
        return json.loads(sanitized_text).get("payload", {}).get("value", [])


if __name__ == "__main__":
    # Inline functional boot testing
    client = MediumClient()
    print("Cold booting session...")
    try:
        bootstrap_results = client.Simulate_Human_session()
        print("Human session simulation complete! Results:")
        print(json.dumps(bootstrap_results, indent=2))
    except Exception as e:
        print(f"Error simulating human session: {e}")