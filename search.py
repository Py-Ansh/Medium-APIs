#!/usr/bin/env python3
"""
Medium Python API Stealth Search & Social Client
===============================================
Implements full search engine features (posts, accounts, tags, publications, lists),
retrieval of following/followers circles, social feeds, and profile posts.

Inherits directly from the master core base layer in init.py to maintain 
modular independence.

Author: Ansh Raj
Date: June 2026
"""

import os
import json
import random
import time
from typing import List, Dict, Any, Union, Optional

from init import MediumClient as MediumBaseClient


class MediumSearchClient(MediumBaseClient):
    """
    Subclass of the core MediumBaseClient adding search, discovery, feed extraction, 
    and social connection graphing features. Executes completely independently 
    using static inline GraphQL definitions within each method.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_current_user_id(self) -> str:
        """Fetches current authenticated user ID via GraphQL."""
        query = """
        query MeQuery {
          viewer {
            id
            name
            username
          }
        }
        """
        res = self._post_graphql("MeQuery", query, {})
        viewer = res.get("data", {}).get("viewer")
        if viewer and viewer.get("id"):
            return viewer["id"]
        raise ValueError("Could not fetch authenticated profile ID. Please double-check your cookies.")

    # =========================================================================
    # 1) Search APIs (Posts, Accounts, Tags, Publications, Lists)
    # =========================================================================

    def search_posts(self, keyword: str, limit: int = 10, next_page_paging: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Searches Medium for articles matching a specific keyword.
        """
        query = """
        query SearchPostsQuery($query: String!, $paging: PagingInput, $filter: SearchCatalogFilterInput) {
          search(query: $query) {
            posts(paging: $paging, filter: $filter) {
              items {
                post {
                  id
                  title
                  mediumUrl
                  uniqueSlug
                  previewContent {
                    subtitle
                  }
                  creator {
                    id
                    name
                    username
                  }
                  virtuals {
                    totalClapCount
                    recommends
                    responsesCreatedCount
                  }
                }
              }
              pagingInfo {
                next {
                  limit
                  from
                  to
                }
              }
            }
          }
        }
        """
        variables = {
            "query": keyword,
            "paging": next_page_paging or {"limit": limit, "from": None, "to": None},
            "filter": None
        }
        return self._post_graphql("SearchPostsQuery", query, variables)

    def search_users(self, keyword: str, limit: int = 10, next_page_paging: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Allows you to search for users/accounts on Medium given search keywords.
        """
        query = """
        query SearchUsersQuery($query: String!, $paging: PagingInput) {
          search(query: $query) {
            users(paging: $paging) {
              items {
                id
                name
                username
                bio
                imageId
                mediumUrl
                allowNotes
                isFollowing
                isWriterWithPublishedStories
              }
              pagingInfo {
                next {
                  limit
                  from
                  to
                }
              }
            }
          }
        }
        """
        variables = {
            "query": keyword,
            "paging": next_page_paging or {"limit": limit, "from": None, "to": None}
        }
        return self._post_graphql("SearchUsersQuery", query, variables)

    def search_tags(self, keyword: str, limit: int = 10, next_page_paging: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Searches Medium tags (topics) matching a keyword.
        """
        query = """
        query SearchTagsQuery($query: String!, $paging: PagingInput) {
          search(query: $query) {
            tags(paging: $paging) {
              items {
                id
                name
                displayTitle
                normalizedName
                slug
                postCount
              }
              pagingInfo {
                next {
                  limit
                  from
                  to
                }
              }
            }
          }
        }
        """
        variables = {
            "query": keyword,
            "paging": next_page_paging or {"limit": limit, "from": None, "to": None}
        }
        return self._post_graphql("SearchTagsQuery", query, variables)

    def search_publications(self, keyword: str, limit: int = 10, next_page_paging: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Searches Medium Publications matching a keyword.
        """
        query = """
        query SearchPublicationsQuery($query: String!, $paging: PagingInput) {
          search(query: $query) {
            publications(paging: $paging) {
              items {
                id
                name
                description
                slug
                domain
                avatar {
                  id
                }
              }
              pagingInfo {
                next {
                  limit
                  from
                  to
                }
              }
            }
          }
        }
        """
        variables = {
            "query": keyword,
            "paging": next_page_paging or {"limit": limit, "from": None, "to": None}
        }
        return self._post_graphql("SearchPublicationsQuery", query, variables)

    def search_lists(self, keyword: str, limit: int = 10, next_page_paging: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Searches user-curated Lists/Collections on Medium.
        """
        query = """
        query SearchCatalogListsQuery($query: String!, $paging: PagingInput) {
          search(query: $query) {
            catalogLists(paging: $paging) {
              items {
                id
                name
                description
                count
                creator {
                  id
                  name
                  username
                }
              }
              pagingInfo {
                next {
                  limit
                  from
                  to
                }
              }
            }
          }
        }
        """
        variables = {
            "query": keyword,
            "paging": next_page_paging or {"limit": limit, "from": None, "to": None}
        }
        return self._post_graphql("SearchCatalogListsQuery", query, variables)

    # =========================================================================
    # 2) Feeds & Social Graph Connections
    # =========================================================================

    def get_following_feed(self, limit: int = 25, next_page_paging: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetch latest posts from the people I follow.
        """
        query = """
        query FollowingFeedQuery($paging: PagingInput) {
          viewer {
            id
            followingFeed(paging: $paging) {
              stream {
                id
                title
                mediumUrl
                uniqueSlug
                creator {
                  id
                  name
                  username
                }
                virtuals {
                  totalClapCount
                  recommends
                  responsesCreatedCount
                }
              }
              pagingInfo {
                next {
                  limit
                  from
                  to
                }
              }
            }
          }
        }
        """
        variables = {
            "paging": next_page_paging or {"limit": limit, "from": None, "to": None}
        }
        return self._post_graphql("FollowingFeedQuery", query, variables)

    def get_followers(self, user_id: Optional[str] = None, limit: int = 25, next_page_paging: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetch people who are following me (or a specific user if user_id is provided).
        """
        if not user_id:
            user_id = self.get_current_user_id()

        query = """
        query UserFollowersQuery($userId: ID!, $paging: PagingInput) {
          user(id: $userId) {
            id
            name
            username
            followers(paging: $paging) {
              items {
                id
                name
                username
                bio
                imageId
                mediumUrl
                isFollowing
              }
              pagingInfo {
                next {
                  limit
                  from
                  to
                }
              }
            }
          }
        }
        """
        variables = {
            "userId": user_id,
            "paging": next_page_paging or {"limit": limit, "from": None, "to": None}
        }
        return self._post_graphql("UserFollowersQuery", query, variables)

    def get_following(self, user_id: Optional[str] = None, limit: int = 25, next_page_paging: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetch people whom I follow (or whom a specific user follows if user_id is provided).
        """
        if not user_id:
            user_id = self.get_current_user_id()

        query = """
        query UserFollowingQuery($userId: ID!, $paging: PagingInput) {
          user(id: $userId) {
            id
            name
            username
            following(paging: $paging) {
              items {
                id
                name
                username
                bio
                imageId
                mediumUrl
                isFollowing
              }
              pagingInfo {
                next {
                  limit
                  from
                  to
                }
              }
            }
          }
        }
        """
        variables = {
            "userId": user_id,
            "paging": next_page_paging or {"limit": limit, "from": None, "to": None}
        }
        return self._post_graphql("UserFollowingQuery", query, variables)

    def get_user_posts(self, user_id: str, limit: int = 25, next_page_paging: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetch articles from a particular person given their user_id / account_id.
        """
        query = """
        query UserProfilePostsQuery($userId: ID!, $paging: PagingInput) {
          user(id: $userId) {
            id
            name
            username
            postsConnection(paging: $paging) {
              stream {
                id
                title
                mediumUrl
                uniqueSlug
                previewContent {
                  subtitle
                }
                creator {
                  id
                  name
                  username
                }
                virtuals {
                  totalClapCount
                  recommends
                  responsesCreatedCount
                }
              }
              pagingInfo {
                next {
                  limit
                  from
                  to
                }
              }
            }
          }
        }
        """
        variables = {
            "userId": user_id,
            "paging": next_page_paging or {"limit": limit, "from": None, "to": None}
        }
        return self._post_graphql("UserProfilePostsQuery", query, variables)


def print_json(data: Any):
    """Auxiliary printer tool formatting logs to terminal standard output stream."""
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Medium Stealth API CLI Search & Social Manager")
    parser.add_argument(
        "--action", 
        choices=[
            "search_posts", 
            "search_users", 
            "search_tags", 
            "search_publications", 
            "search_lists", 
            "feed", 
            "followers", 
            "following", 
            "user_posts"
        ],
        required=True,
        help="Search or Social operation to execute"
    )
    parser.add_argument("--query", type=str, help="Search keyword or query string")
    parser.add_argument("--user-id", type=str, help="Medium account_id / user_id")
    parser.add_argument("--limit", type=int, default=10, help="Pagination result limit")
    parser.add_argument("--cookie", type=str, help="Optional direct raw cookies to load session")
    parser.add_argument("--env-cookie-var", type=str, default="MEDIUM_COOKIE", help="Env var containing cookie")

    args = parser.parse_args()

    # Read cookies from parameters or system environment
    cookie_str = args.cookie
    if not cookie_str:
        cookie_str = os.environ.get(args.env_cookie_var, "")

    client = MediumSearchClient(cookies=cookie_str if cookie_str else None)

    try:
        if args.action == "search_posts":
            if not args.query:
                print_json({"success": False, "msg": "Missing --query parameter"})
            else:
                print_json(client.search_posts(args.query, limit=args.limit))

        elif args.action == "search_users":
            if not args.query:
                print_json({"success": False, "msg": "Missing --query parameter"})
            else:
                print_json(client.search_users(args.query, limit=args.limit))

        elif args.action == "search_tags":
            if not args.query:
                print_json({"success": False, "msg": "Missing --query parameter"})
            else:
                print_json(client.search_tags(args.query, limit=args.limit))

        elif args.action == "search_publications":
            if not args.query:
                print_json({"success": False, "msg": "Missing --query parameter"})
            else:
                print_json(client.search_publications(args.query, limit=args.limit))

        elif args.action == "search_lists":
            if not args.query:
                print_json({"success": False, "msg": "Missing --query parameter"})
            else:
                print_json(client.search_lists(args.query, limit=args.limit))

        elif args.action == "feed":
            print_json(client.get_following_feed(limit=args.limit))

        elif args.action == "followers":
            print_json(client.get_followers(user_id=args.user_id, limit=args.limit))

        elif args.action == "following":
            print_json(client.get_following(user_id=args.user_id, limit=args.limit))

        elif args.action == "user_posts":
            if not args.user_id:
                print_json({"success": False, "msg": "Missing --user-id parameter"})
            else:
                print_json(client.get_user_posts(args.user_id, limit=args.limit))

    except Exception as e:
        import traceback
        print_json({
            "success": False,
            "msg": str(e),
            "traceback": traceback.format_exc()
        })