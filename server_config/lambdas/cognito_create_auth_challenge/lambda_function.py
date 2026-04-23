def lambda_handler(event, context):
    event["response"]["publicChallengeParameters"] = {
        "challenge": "ENTER_PASSWORD"
    }
    event["response"]["privateChallengeParameters"] = {
        "challenge": "ENTER_PASSWORD"
    }
    event["response"]["challengeMetadata"] = "PASSWORD_CHALLENGE"
    return event
