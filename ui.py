import asyncio
import sqlite3
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime
import pytz
from db import DB_PATH, verify_user, add_user, get_user_role, get_api_calls, increment_api_calls, schedule_post, get_user_scheduled_posts, delete_scheduled_post, get_all_users, get_all_scheduled_posts
from api import generate_platform_drafts
from config import PROMPT_TEMPLATES, TONE_OPTIONS
import logging

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

def login_register():
    logger.info("Rendering login/register UI")
    st.subheader("Login or Register")
    auth_option = st.selectbox("Choose an action", ["Login", "Register"], key="auth_option")
    
    if auth_option == "Login":
        login_email = st.text_input("Email", key="login_email")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            logger.info(f"Login attempt for user: {login_email}")
            try:
                if verify_user(login_email.lower(), login_pass):
                    st.session_state.logged_in_user = login_email.lower()
                    st.success("Logged in successfully!")
                    logger.debug(f"User {login_email} logged in successfully")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
                    logger.warning(f"Invalid login attempt for {login_email}")
            except Exception as e:
                st.error(f"Login error: {e}")
                logger.error(f"Login error for {login_email}: {e}")
    else:
        reg_email = st.text_input("Email", key="reg_email")
        reg_pass = st.text_input("Password", type="password", key="reg_pass")
        reg_pass2 = st.text_input("Confirm Password", type="password", key="reg_pass2")
        if st.button("Register"):
            logger.info(f"Registration attempt for user: {reg_email}")
            try:
                if reg_pass != reg_pass2:
                    st.error("Passwords do not match")
                    logger.warning("Password mismatch during registration")
                elif add_user(reg_email.lower(), reg_pass):
                    st.success("Registration successful! Please login.")
                    logger.debug(f"User {reg_email} registered successfully")
                else:
                    st.error("User already exists or registration failed.")
                    logger.warning(f"Registration failed for {reg_email}")
            except Exception as e:
                st.error(f"Registration error: {e}")
                logger.error(f"Registration error for {reg_email}: {e}")

def update_user(email: str, role: str = None, api_calls: int = None):
    logger.info(f"Updating user: {email}")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        updates = []
        params = []
        if role is not None:
            updates.append("role = ?")
            params.append(role)
        if api_calls is not None:
            updates.append("api_calls = ?")
            params.append(api_calls)
        if updates:
            params.append(email)
            query = f"UPDATE users SET {', '.join(updates)} WHERE email = ?"
            c.execute(query, params)
            conn.commit()
            logger.debug(f"User {email} updated successfully")
        else:
            logger.debug("No updates provided for user")
    except sqlite3.Error as e:
        logger.error(f"Database error updating user: {e}")
        st.error(f"Database error updating user: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            logger.warning("Failed to close database connection")

def delete_user(email: str):
    logger.info(f"Deleting user: {email}")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE email = ?", (email,))
        c.execute("DELETE FROM scheduled_posts WHERE user_email = ?", (email,))
        conn.commit()
        logger.debug(f"User {email} and their scheduled posts deleted successfully")
    except sqlite3.Error as e:
        logger.error(f"Database error deleting user: {e}")
        st.error(f"Database error deleting user: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            logger.warning("Failed to close database connection")

def admin_panel():
    logger.info("Rendering admin panel")
    st.subheader("Admin Panel")

    # Create new user
    st.markdown("### Create New User")
    with st.form(key="create_user_form"):
        new_email = st.text_input("New User Email")
        new_password = st.text_input("New User Password", type="password")
        new_role = st.selectbox("Role", ["user", "admin"], key="new_user_role")
        submit_create = st.form_submit_button("Create User")
        if submit_create:
            if new_email and new_password:
                if add_user(new_email.lower(), new_password, new_role):
                    st.success(f"User {new_email} created successfully")
                    logger.info(f"Admin created user: {new_email}")
                    st.rerun()
                else:
                    st.error("Failed to create user. Email may already exist.")
                    logger.warning(f"Failed to create user: {new_email}")
            else:
                st.error("Email and password are required.")
                logger.warning("Attempt to create user with missing email or password")

    # Display and manage all users
    st.markdown("### Manage Users")
    users = get_all_users()
    if not users:
        st.info("No users found in the database.")
        logger.debug("No users found in database")
    else:
        user_data = [{"Email": email, "Role": role, "API Calls": api_calls} for email, role, api_calls in users]
        st.table(user_data)
        logger.debug(f"Displayed {len(user_data)} users in admin panel")

        # Update or delete user
        st.markdown("#### Update/Delete User")
        selected_email = st.selectbox("Select User", [u[0] for u in users], key="update_user_select")
        with st.form(key="update_user_form"):
            new_role = st.selectbox("New Role", ["user", "admin"], key="update_user_role")
            new_api_calls = st.number_input("New API Calls", min_value=0, step=1, key="update_api_calls")
            col1, col2 = st.columns(2)
            with col1:
                submit_update = st.form_submit_button("Update User")
            with col2:
                submit_delete = st.form_submit_button("Delete User")
            
            if submit_update:
                update_user(selected_email, role=new_role, api_calls=new_api_calls)
                st.success(f"User {selected_email} updated successfully")
                logger.info(f"Admin updated user: {selected_email}")
                st.rerun()
            if submit_delete:
                if selected_email == st.session_state.logged_in_user:
                    st.error("Cannot delete your own admin account!")
                    logger.warning(f"Admin {selected_email} attempted to delete own account")
                else:
                    delete_user(selected_email)
                    st.success(f"User {selected_email} deleted successfully")
                    logger.info(f"Admin deleted user: {selected_email}")
                    st.rerun()

    # Display and manage all scheduled posts
    st.markdown("### All Scheduled Posts")
    posts = get_all_scheduled_posts()
    if not posts:
        st.info("No scheduled posts found.")
        logger.debug("No scheduled posts found")
    else:
        post_data = [
            {
                "Post ID": post_id,
                "User Email": user_email,
                "Platform": platform,
                "Content": content,
                "Scheduled Time (IST)": schedule_time,
                "Reminder (min before)": reminder_minutes
            } for post_id, user_email, platform, content, schedule_time, reminder_minutes in posts
        ]
        st.table(post_data)
        logger.debug(f"Displayed {len(post_data)} scheduled posts in admin panel")
        
        # Delete scheduled post
        st.markdown("#### Delete Scheduled Post")
        post_id_to_delete = st.number_input("Enter Post ID to delete", min_value=1, step=1)
        if st.button("Delete Post"):
            delete_scheduled_post(post_id_to_delete)
            st.success(f"Scheduled post {post_id_to_delete} deleted.")
            logger.info(f"Admin deleted scheduled post {post_id_to_delete}")
            st.rerun()

def render_main_ui():
    logger.info("Rendering main UI")
    st.title("✨ Pose Muse ")
    st.caption("Create and schedule platform-specific posts 🚀")
    st.markdown("---")

    # Session state initialization
    if "logged_in_user" not in st.session_state:
        st.session_state.logged_in_user = None
    if "drafts" not in st.session_state:
        st.session_state.drafts = {}
    if "api_call_count" not in st.session_state:
        st.session_state.api_call_count = 0

    # User status and API limits
    if st.session_state.logged_in_user is None:
        login_register()
        st.info("Use the app as a free user without login (max 5 calls per session).")
        limit = 5
        usage = st.session_state.api_call_count
        st.markdown(f"**API calls used:** {usage} / {limit}")
        logger.debug(f"Free user API usage: {usage}/{limit}")
        if usage >= limit:
            st.error("⚠️ Free user limit reached. Please register/login for more.")
            logger.warning("Free user API limit reached")
            st.stop()
    else:
        email = st.session_state.logged_in_user
        role = get_user_role(email)
        usage = get_api_calls(email)
        limit = float("inf") if role == "admin" else 10
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"Logged in as {email} ({role})")
            st.markdown(f"**API calls used:** {usage} / {limit if limit != float('inf') else '∞'}")
            logger.debug(f"Logged-in user {email} API usage: {usage}/{limit}")
        with col2:
            if st.button("Logout"):
                logger.info(f"User {email} logged out")
                st.session_state.logged_in_user = None
                st.session_state.drafts = {}
                st.rerun()

        if limit != float("inf") and usage >= limit:
            st.error("⚠️ API call limit reached. Contact admin for more access.")
            logger.warning(f"API call limit reached for user: {email}")
            st.stop()

        # Admin panel for admin users
        if role == "admin":
            with st.expander("Admin Panel", expanded=False):
                admin_panel()

    # Input section
    col1, col2 = st.columns(2)
    with col1:
        topic = st.text_input("🧠 Topic / Product / Feature", placeholder="e.g. Smart AI Writing Tool")
        hashtags = st.text_input("🐦 Twitter Hashtags", placeholder="e.g. #AI #Productivity #SocialMedia")
    with col2:
        insight = st.text_area("💼 LinkedIn Insight / Story", placeholder="Share a short professional insight or story…")
        tone = st.selectbox("🎨 Select Tone for Posts", TONE_OPTIONS, index=1)
    
    if not topic.strip():
        st.warning("Please enter a topic to enable generation.")
        logger.warning("Topic input is empty")
    
    if st.button("🚀 Generate All Drafts") and topic.strip():
        logger.info("Generating drafts for all platforms")
        with st.spinner("Generating all drafts…"):
            try:
                tasks = [generate_platform_drafts(p, {
                    "topic": topic,
                    "hashtags": hashtags,
                    "insight": insight,
                    "tone": tone
                }, PROMPT_TEMPLATES) for p in PROMPT_TEMPLATES]
                results = asyncio.run(asyncio.gather(*tasks))
                for p, d in zip(PROMPT_TEMPLATES, results):
                    st.session_state.drafts[p] = d
                st.info("✅ Drafts generated successfully. Scroll down to review them.")
                logger.debug("Drafts generated successfully for all platforms")
                if st.session_state.logged_in_user is None:
                    st.session_state.api_call_count += 1
                    logger.debug(f"Incremented free user API call count: {st.session_state.api_call_count}")
                else:
                    increment_api_calls(st.session_state.logged_in_user)
                    logger.debug(f"Incremented API calls for user: {st.session_state.logged_in_user}")
            except Exception as e:
                st.error(f"Generation failed: {e}")
                logger.error(f"Draft generation failed: {e}")

    st.markdown("---")

    # Tabs for drafts and scheduled posts
    tabs = st.tabs(["🐦 Twitter", "💼 LinkedIn", "📸 Instagram", "⏰ Scheduled Posts"] if st.session_state.logged_in_user else ["🐦 Twitter", "💼 LinkedIn", "📸 Instagram"])
    
    for tab, platform in zip(tabs[:3], PROMPT_TEMPLATES):
        with tab:
            st.subheader(f"{platform.capitalize()} Drafts")
            drafts = st.session_state.drafts.get(platform, [])
            if not drafts:
                st.info(f"No drafts generated yet for {platform.capitalize()}.")
                logger.debug(f"No drafts available for {platform}")
            else:
                for i, draft in enumerate(drafts, 1):
                    st.markdown(f"**Draft {i}:**")
                    draft_key = f"{platform}_{i}_edit"
                    edited_draft = st.text_area(f"Edit Draft {i}", value=draft, key=draft_key, height=100)
                    if edited_draft != draft:
                        st.session_state.drafts[platform][i-1] = edited_draft
                        logger.debug(f"Draft {i} edited for {platform}")
                    col1, col2 = st.columns([0.85, 0.15])
                    with col1:
                        st.markdown(f"**Content:** {edited_draft}")
                    with col2:
                        components.html(f"""
                            <button onclick="navigator.clipboard.writeText(`{edited_draft.replace('`', '\\`')}`);alert('Copied!');">
                                Copy
                            </button>
                        """, height=35)
                    with st.expander(f"📅 Schedule Draft {i}"):
                        try:
                            col1, col2 = st.columns(2)
                            with col1:
                                schedule_date = st.date_input("📅 Date", key=f"{platform}_{i}_date")
                            with col2:
                                schedule_time_input = st.time_input("⏰ Time (IST)", key=f"{platform}_{i}_clock")
                            # Add reminder minutes input
                            reminder_minutes = st.number_input(
                                "🔔 Reminder (minutes before post)",
                                min_value=5,
                                max_value=1440,  # 1 day max
                                value=60,  # Default to 60 minutes
                                step=5,
                                key=f"{platform}_{i}_reminder"
                            )
                            schedule_time = datetime.combine(schedule_date, schedule_time_input).replace(tzinfo=IST)
                            if st.button(f"Schedule", key=f"{platform}_{i}_btn"):
                                if st.session_state.logged_in_user:
                                    if schedule_time < datetime.now(IST):
                                        st.error("Schedule time must be in the future.")
                                        logger.warning(f"Attempt to schedule post in the past: {schedule_time}")
                                    else:
                                        schedule_post(
                                            st.session_state.logged_in_user,
                                            platform,
                                            edited_draft,
                                            schedule_time,  # Pass datetime object, converted to IST in schedule_post
                                            reminder_minutes
                                        )
                                        st.success(f"Draft scheduled for {schedule_time.strftime('%Y-%m-%d %H:%M:%S %Z')} with reminder {reminder_minutes} minutes before")
                                        logger.info(f"Draft scheduled for {st.session_state.logged_in_user} on {platform} at {schedule_time} with {reminder_minutes} min reminder")
                                        st.rerun()
                                else:
                                    st.warning("Login required to schedule posts.")
                                    logger.warning("Attempt to schedule post without login")
                        except Exception as e:
                            st.error(f"Invalid schedule input: {e}")
                            logger.error(f"Invalid schedule input: {e}")
                    st.markdown("---")

    if st.session_state.logged_in_user:
        with tabs[3]:
            st.subheader("⏰ Your Scheduled Posts")
            posts = get_user_scheduled_posts(st.session_state.logged_in_user)
            if not posts:
                st.info("You have no scheduled posts.")
                logger.debug("No scheduled posts found")
            else:
                for post in posts:
                    post_id, platform, content, sched_time, reminder_minutes = post
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**Platform:** {platform.capitalize()}")
                        st.markdown(f"**Scheduled Time (IST):** {sched_time}")
                        st.markdown(f"**Reminder:** {reminder_minutes} minutes before")
                        st.markdown(f"**Content:** {content}")
                    with col2:
                        if st.button(f"Delete Post ID {post_id}", key=f"del_{post_id}"):
                            delete_scheduled_post(post_id)
                            st.success("Scheduled post deleted.")
                            logger.info(f"Scheduled post {post_id} deleted by {st.session_state.logged_in_user}")
                            st.rerun()
                    st.markdown("---")

    if st.session_state.drafts:
        try:
            df = pd.DataFrame({p: v for p, v in st.session_state.drafts.items()})
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download All Drafts as CSV",
                data=csv,
                file_name="ai_social_media_drafts.csv",
                mime="text/csv"
            )
            logger.debug("Download button for drafts CSV rendered")
        except Exception as e:
            st.error(f"Error preparing download file: {e}")
            logger.error(f"Error preparing download file: {e}")