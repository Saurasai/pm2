import json
import sys
import os
from datetime import datetime
import pytz

# Debug: Print environment details
print(f"Current working directory: {os.getcwd()}")
project_root = os.path.normpath(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
print(f"Project root: {project_root}")
try:
    print(f"Files in root: {os.listdir(project_root)}")
except FileNotFoundError:
    print(f"Error: Project root {project_root} not found", file=sys.stderr)
    sys.exit(1)

# Add project root to Python path
sys.path.insert(0, project_root)
print(f"Python path: {sys.path}")

try:
    from db import get_reminder_posts, mark_reminder_sent, get_all_users
except ImportError as e:
    print(f"Failed to import db module: {e}", file=sys.stderr)
    sys.exit(1)

IST = pytz.timezone("Asia/Kolkata")

def main():
    try:
        due_posts = get_reminder_posts()
        if not due_posts:
            print("No due reminders.")
            return
    except Exception as e:
        print(f"Error fetching reminder posts: {e}", file=sys.stderr)
        sys.exit(1)

    users = {email: True for email, _, _ in get_all_users()}
    recipients = []
    email_bodies = []

    try:
        with open(os.path.join(".github", "emails", "reminder_body.md"), "r") as f:
            template = f.read()
    except FileNotFoundError:
        print("Error: reminder_body.md not found", file=sys.stderr)
        sys.exit(1)

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