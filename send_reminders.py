import json
import sys
import os
from datetime import datetime
import pytz
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import get_reminder_posts, mark_reminder_sent, get_all_users

IST = pytz.timezone("Asia/Kolkata")

def main():
    due_posts = get_reminder_posts()
    if not due_posts:
        print("No due reminders.")
        return

    users = {email: True for email, _, _ in get_all_users()}
    recipients = []
    email_bodies = []

    with open(".github/emails/reminder_body.md", "r") as f:
        template = f.read()

    for user_email, platform, content, schedule_time, reminder_minutes, post_id in due_posts:
        if user_email not in users:
            print(f"Skipping invalid user: {user_email}", file=sys.stderr)
            continue

        # Format schedule_time for display in IST
        try:
            sched_time = datetime.fromisoformat(schedule_time).astimezone(IST).strftime("%Y-%m-%d %H:%M:%S %Z")
        except ValueError:
            sched_time = schedule_time

        # Generate personalized email body
        body = template.replace("{{platform}}", platform) \
                      .replace("{{reminder_minutes}}", str(reminder_minutes)) \
                      .replace("{{schedule_time}}", sched_time) \
                      .replace("{{content}}", content)
        
        recipients.append(user_email)
        email_bodies.append(body)

        mark_reminder_sent(post_id)
        print(f"Prepared reminder for {user_email}: Post on {platform} at {schedule_time}")

    # Write email bodies to a file for the Action
    with open("email_bodies.txt", "w") as f:
        for email, body in zip(recipients, email_bodies):
            f.write(f"{email}:{body}\n")

    with open(os.environ.get('GITHUB_OUTPUT', 'output.txt'), 'a') as f:
        f.write(f"recipients={','.join(recipients)}\n")
        f.write(f"email_bodies=email_bodies.txt\n")
        f.write(f"post_count={len(due_posts)}\n")

if __name__ == "__main__":
    main()