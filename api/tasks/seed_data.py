"""Sample users and tasks. Shared by `seed` and `gitea_bootstrap` so both stay in step.

The password is not here: it comes from the `blt_password` secret (settings.SEED_PASSWORD).
"""

# username -> (first name, last name)
USERS = {
    "fernando": ("Fernando", "Campana"),
    "ballast": ("Ballast", "Team"),
    "lane": ("Lane", "Team"),
}

# (title, description, status, due offset in days, created by, assigned to or None)
TASKS = (
    (
        "Review the customer contract",
        "Read the amendment and flag risks.",
        "in_progress",
        2,
        "fernando",
        "fernando",
    ),
    ("Close the monthly report", "Consolidate October numbers.", "todo", 5, "fernando", "fernando"),
    ("Ship the checkout fix", "Hotfix validated in staging.", "done", -1, "fernando", "fernando"),
    ("Plan sprint 24", "Refinement with the team on Thursday.", "todo", 9, "fernando", "fernando"),
    (
        "Update the API documentation",
        "Schema and error examples.",
        "in_progress",
        -2,
        "fernando",
        "fernando",
    ),
    (
        "Review the authentication PR",
        "Focus on token expiration.",
        "todo",
        1,
        "fernando",
        "fernando",
    ),
    ("Prepare the customer presentation", "Ten-minute script.", "todo", 3, "fernando", "fernando"),
    ("Fix the date filter", "Timezone in the due date filter.", "done", -4, "fernando", "fernando"),
    (
        "Move the email job to Celery",
        "Remove the manual thread.",
        "in_progress",
        6,
        "fernando",
        "fernando",
    ),
    (
        "Write permission tests",
        "Cover creator, assignee and stranger.",
        "todo",
        None,
        "fernando",
        None,
    ),
    # Ballast
    (
        "Design the onboarding checklist",
        "Steps a new teammate follows in the first week.",
        "todo",
        4,
        "ballast",
        "ballast",
    ),
    (
        "Review the pull request template",
        "Keep it to five checks.",
        "in_progress",
        2,
        "ballast",
        "ballast",
    ),
    (
        "Publish the release notes",
        "Summarize what shipped this sprint.",
        "done",
        -2,
        "ballast",
        "ballast",
    ),
    (
        "Validate the new spec flow",
        "Generate a spec from an issue and turn it into tasks.",
        "in_progress",
        1,
        "fernando",
        "ballast",
    ),
    # Lane
    (
        "Set up the staging database backup",
        "Nightly dump with a seven-day retention.",
        "todo",
        7,
        "lane",
        "lane",
    ),
    (
        "Audit the API rate limits",
        "Check the login and spec scopes under load.",
        "in_progress",
        3,
        "lane",
        "lane",
    ),
    (
        "Document the Celery retry policy",
        "What retries, how often, and when it gives up.",
        "todo",
        10,
        "lane",
        "lane",
    ),
    (
        "Pair on the date filter tests",
        "Cover timezone edges and empty ranges.",
        "todo",
        5,
        "fernando",
        "lane",
    ),
    # Created by a teammate for the owner
    (
        "Share the sprint 24 plan",
        "Send the agreed scope to everyone.",
        "todo",
        6,
        "lane",
        "fernando",
    ),
)

# Tasks for these people also exist as Gitea issues with the same title and assignee.
GITEA_USERS = ("ballast", "lane")
