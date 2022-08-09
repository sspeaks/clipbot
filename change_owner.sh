#!/bin/sh

git filter-branch --env-filter '

OLD_EMAIL="sspeaks@microsoft.com"
CORRECT_NAME="Seth Speaks"
CORRECT_EMAIL="sspeaks610@gmail.com"

if [ "$GIT_COMMITTER_NAME" = "sspeaks610" ]
then
    export GIT_COMMITTER_NAME="$CORRECT_NAME"
    export GIT_COMMITTER_EMAIL="$CORRECT_EMAIL"
fi
if [ "$GIT_AUTHOR_NAME" = "sspeaks610" ]
then
    export GIT_AUTHOR_NAME="$CORRECT_NAME"
    export GIT_AUTHOR_EMAIL="$CORRECT_EMAIL"
fi
' --tag-name-filter cat -- --branches --tags
