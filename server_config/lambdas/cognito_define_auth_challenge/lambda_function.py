MAX_ATTEMPTS = 3


def lambda_handler(event, context):
    session = event.get("request", {}).get("session", [])

    if len(session) == 0:
        event["response"]["issueTokens"] = False
        event["response"]["failAuthentication"] = False
        event["response"]["challengeName"] = "CUSTOM_CHALLENGE"
        return event

    last = session[-1]
    if last.get("challengeName") == "CUSTOM_CHALLENGE" and last.get("challengeResult") is True:
        event["response"]["issueTokens"] = True
        event["response"]["failAuthentication"] = False
        return event

    if len(session) >= MAX_ATTEMPTS:
        event["response"]["issueTokens"] = False
        event["response"]["failAuthentication"] = True
        return event

    event["response"]["issueTokens"] = False
    event["response"]["failAuthentication"] = False
    event["response"]["challengeName"] = "CUSTOM_CHALLENGE"
    return event
