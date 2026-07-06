PUBLISH_RESPONSE_QUERY = """mutation PublishPostThreadedResponse($inResponseToPostId: ID!, $deltas: [Delta!]!, $inResponseToQuoteId: ID, $responseDistribution: ResponseDistributionType, $sortType: ResponseSortType) {
  publishPostThreadedResponse(
    inResponseToPostId: $inResponseToPostId
    deltas: $deltas
    inResponseToQuoteId: $inResponseToQuoteId
    responseDistribution: $responseDistribution
  ) {
    ...PublishPostThreadedResponse_post
    __typename
  }
}

fragment StoryResponse_paragraph on Paragraph {
  text
  type
  __typename
  id
}

fragment DropCap_image on ImageMetadata {
  id
  originalHeight
  originalWidth
  __typename
}

fragment MarkupNode_data_dropCapImage on ImageMetadata {
  ...DropCap_image
  __typename
  id
}

fragment Markups_markup on Markup {
  type
  start
  end
  href
  anchorType
  userId
  linkMetadata {
    httpStatus
    __typename
  }
  __typename
}

fragment Markups_paragraph on Paragraph {
  name
  text
  hasDropCap
  dropCapImage {
    ...MarkupNode_data_dropCapImage
    __typename
    id
  }
  markups {
    ...Markups_markup
    __typename
  }
  __typename
  id
}

fragment ParagraphRefsMapContext_paragraph on Paragraph {
  id
  name
  text
  __typename
}

fragment TextParagraph_paragraph on Paragraph {
  type
  hasDropCap
  codeBlockMetadata {
    mode
    lang
    __typename
  }
  ...Markups_paragraph
  ...ParagraphRefsMapContext_paragraph
  __typename
  id
}

fragment buildQuotePreviewParagraph_quote on Quote {
  paragraphs {
    id
    text
    type
    markups {
      end
      start
      type
      __typename
    }
    __typename
  }
  startOffset
  endOffset
  __typename
  id
}

fragment ResponseQuote_quote on Quote {
  __typename
  quoteId
  startOffset
  endOffset
  paragraphs {
    ...TextParagraph_paragraph
    __typename
  }
  ...buildQuotePreviewParagraph_quote
  id
}

fragment ResponseQuote_mediaResource on MediaResource {
  href
  mediumQuote {
    ...ResponseQuote_quote
    __typename
    id
  }
  __typename
  id
}

fragment PostPresentationTracker_post on Post {
  id
  visibility
  collection {
    id
    slug
    __typename
  }
  __typename
}

fragment UserAvatar_user on User {
  id
  imageId
  name
  username
  __typename
}

fragment UserAvatarWithBadge_user on User {
  membership {
    tier
    __typename
    id
  }
  ...UserAvatar_user
  __typename
  id
}

fragment userUrl_user on User {
  __typename
  id
  customDomainState {
    live {
      domain
      __typename
    }
    __typename
  }
  hasSubdomain
  username
}

fragment UserAvatarLinkContainer_user on User {
  ...userUrl_user
  __typename
  id
}

fragment UserAvatarWithBadgeAndLink_user on User {
  ...UserAvatarWithBadge_user
  ...UserAvatarLinkContainer_user
  __typename
  id
}

fragment isUserVerifiedBookAuthor_user on User {
  verifications {
    isBookAuthor
    __typename
  }
  __typename
  id
}

fragment UserLink_user on User {
  ...userUrl_user
  __typename
  id
}

fragment UserPronouns_user on User {
  pronouns
  __typename
  id
}

fragment SusiModal_post on Post {
  id
  creator {
    id
    __typename
  }
  __typename
}

fragment SusiClickable_post on Post {
  id
  mediumUrl
  ...SusiModal_post
  __typename
}

fragment ReportUserMenuItem_post on Post {
  __typename
  id
  creator {
    id
    __typename
  }
  ...SusiClickable_post
}

fragment useHideResponseParent_post on Post {
  __typename
  id
  creator {
    id
    __typename
  }
  collection {
    id
    viewerEdge {
      id
      isEditor
      __typename
    }
    __typename
  }
}

fragment HideResponseMenuItemParent_post on Post {
  id
  ...useHideResponseParent_post
  __typename
}

fragment BlockUserMenuItem_post on Post {
  __typename
  id
  creator {
    id
    __typename
  }
}

fragment UndoClapsMenuItem_post on Post {
  id
  clapCount
  __typename
}

fragment DeleteResponseMenuItem_post on Post {
  creator {
    id
    __typename
  }
  __typename
  id
}

fragment useReportStory_post on Post {
  id
  creator {
    id
    __typename
  }
  __typename
}

fragment ReportResponseDialog_post on Post {
  __typename
  id
  creator {
    id
    __typename
  }
  ...useHideResponseParent_post
  ...useReportStory_post
}

fragment ResponsePopoverMenu_post on Post {
  id
  responseDistribution
  ...ReportUserMenuItem_post
  ...HideResponseMenuItemParent_post
  ...BlockUserMenuItem_post
  ...UndoClapsMenuItem_post
  ...DeleteResponseMenuItem_post
  ...ReportResponseDialog_post
  __typename
}

fragment ResponseHeader_post on Post {
  __typename
  id
  createdAt
  firstPublishedAt
  latestPublishedAt
  creator {
    id
    name
    ...UserAvatarWithBadgeAndLink_user
    ...isUserVerifiedBookAuthor_user
    ...UserLink_user
    ...UserPronouns_user
    __typename
  }
  ...ResponsePopoverMenu_post
}

fragment StoryResponse_post on Post {
  id
  mediumUrl
  clapCount
  responsesCount
  creator {
    id
    __typename
  }
  previewContent {
    bodyModel {
      paragraphs {
        ...StoryResponse_paragraph
        __typename
      }
      __typename
    }
    __typename
  }
  inResponseToMediaResource {
    ...ResponseQuote_mediaResource
    __typename
    id
  }
  ...PostPresentationTracker_post
  ...ResponseHeader_post
  __typename
}

fragment SimpleResponseBodyModel_paragraph on Paragraph {
  id
  name
  text
  type
  markups {
    type
    start
    end
    href
    anchorType
    userId
    linkMetadata {
      httpStatus
      __typename
    }
    __typename
  }
  __typename
}

fragment SimpleResponseBodyModel_richText on RichText {
  paragraphs {
    ...SimpleResponseBodyModel_paragraph
    __typename
  }
  __typename
}

fragment PostScrollTracker_post on Post {
  id
  collection {
    id
    __typename
  }
  sequence {
    sequenceId
    __typename
  }
  __typename
}

fragment ResponseQuote_post on Post {
  inResponseToMediaResource {
    ...ResponseQuote_mediaResource
    __typename
    id
  }
  __typename
  id
}

fragment SimpleResponse_threadedSimpleResponse_post on Post {
  id
  createdAt
  firstPublishedAt
  latestPublishedAt
  title
  creator {
    id
    name
    username
    imageId
    mediumMemberAt
    viewerEdge {
      id
      isBlocking
      __typename
    }
    ...userUrl_user
    ...isUserVerifiedBookAuthor_user
    __typename
  }
  clapCount
  viewerEdge {
    id
    clapCount
    __typename
  }
  isPublished
  voterCount
  responsesCount
  postResponses {
    count
    __typename
  }
  allowResponses
  latestRev
  recommenders {
    id\n    name
    __typename
  }
  mediumUrl
  content {
    bodyModel {
      ...SimpleResponseBodyModel_richText
      __typename
    }
    __typename
  }
  collection {
    id
    slug
    __typename
  }
  isLimitedState
  inResponseToType
  responseDistribution
  ...PostPresentationTracker_post
  ...PostScrollTracker_post
  ...ResponseQuote_post
  ...ResponseHeader_post
  __typename
}

fragment SimpleResponse_threadedSimpleResponse_defaultPostResponses on Post {
  responsesCount
  postResponses {
    count
    __typename
  }
  threadedPostResponses(paging: {limit: 10}, sortType: $sortType) {
    __typename
    autoExpandedPostIds
    pagingInfo {
      next {
        limit
        to
        __typename
      }
      __typename
    }
    posts {
      ... on Post {
        ...StoryResponse_post
        ...SimpleResponse_threadedSimpleResponse_post
        __typename
        id
      }
      __typename
    }
  }
  __typename
  id
}

fragment PublishPostThreadedResponse_post on Post {
  id
  ...StoryResponse_post
  ...SimpleResponse_threadedSimpleResponse_post
  ...SimpleResponse_threadedSimpleResponse_defaultPostResponses
  __typename
}"""

