"""
Copy shown to renters for key handover (API ``move_in_guidance`` on reservations).

Wording is product guidance, not legal advice. Adjust per market / counsel.
"""

MOVE_IN_GUIDANCE = {
    "title": "Before your stay starts — keys & handover",
    "intro": (
        "Coordinate directly with the landlord or broker who published this listing. "
        "Yallastay does not hold keys; use Messages on the property thread so both sides "
        "have a written record."
    ),
    "steps": [
        "Open Messages and find the conversation for this listing (same property as your booking).",
        "Agree a handover time, meeting place, and who will meet you — usually the lister or their agent.",
        "Confirm ID or deposit steps if the lister asked for them before releasing keys.",
        "After you physically receive keys, check the box below so your lister knows handover is done.",
    ],
    "platform_feedback_prompt": (
        "Optional: tell us how the platform worked for you (bugs, confusion, or what went well). "
        "This is for Yallastay product improvement — not sent as a public review."
    ),
    "messages_link_path": "/messages",
}
