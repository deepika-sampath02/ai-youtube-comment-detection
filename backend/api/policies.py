"""Policy engine: turns an AI result into an action for the host application."""

RESTRICT_AFTER = 3   # flagged comments before we recommend restricting the user


def decide(result: dict, prior_strikes: int) -> dict:
    cats, sev = result["categories"], result["severity"]
    escalate = report_required = False

    if "Sexual / 18+" in cats:
        action, escalate, report_required = "REMOVE", True, True
    elif "Threat" in cats:
        action, escalate = "REMOVE", True
    elif sev in ("HIGH", "CRITICAL"):
        action = "REMOVE"
    elif sev in ("LOW", "MEDIUM"):
        action = "WARN"
    else:
        action = "ALLOW"

    flagged = action != "ALLOW"
    strikes = prior_strikes + (1 if flagged else 0)
    return {
        "action": action,
        "escalate": escalate,
        "report_required": report_required,   # possible cybercrime -> human review first
        "restrict_user": flagged and strikes >= RESTRICT_AFTER,
        "strikes": strikes,
    }
