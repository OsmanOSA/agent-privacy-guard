"""Background service: keeps the name detector loaded between hook calls.

Every hook call is a short-lived process. Loading a detection model there would
cost seconds on every tool call; the service loads it once and stays up while
the agent works, then stops by itself after a period of inactivity.
"""
