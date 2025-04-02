import streamlit as st
import pandas as pd
import os
import random
import gspread
from gspread_dataframe import get_as_dataframe
from oauth2client.service_account import ServiceAccountCredentials

# 🔐 Google Sheets Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
gc = gspread.authorize(credentials)

# Load student data from Google Sheets
students_sheet = gc.open("SiriSolverData").worksheet("Students")
students_df = get_as_dataframe(students_sheet).dropna(how='all')

# Local database paths
DAILY_CHALLENGES_DB = "data/daily_challenges.csv"
DAILY_SUBMISSIONS_DB = "data/daily_submissions.csv"
LEADERBOARD_DB = "data/leaderboard.csv"

# Ensure folders exist
UPLOADS_FOLDER = "uploads"
os.makedirs(UPLOADS_FOLDER, exist_ok=True)

# Ensure submissions database exists
if not os.path.exists(DAILY_SUBMISSIONS_DB):
    pd.DataFrame(columns=["Student ID", "Challenge ID", "Submission Text", "File Submission", "Reviewed"]).to_csv(DAILY_SUBMISSIONS_DB, index=False)

# Helpers
def load_daily_challenges():
    return pd.read_csv(DAILY_CHALLENGES_DB) if os.path.exists(DAILY_CHALLENGES_DB) else pd.DataFrame()

def load_leaderboard():
    return pd.read_csv(LEADERBOARD_DB) if os.path.exists(LEADERBOARD_DB) else pd.DataFrame()

def save_daily_submission(student_id, challenge_id, submission_text, file_submission=None):
    submissions = pd.read_csv(DAILY_SUBMISSIONS_DB) if os.path.exists(DAILY_SUBMISSIONS_DB) else pd.DataFrame()
    submissions = submissions[~((submissions["Student ID"] == student_id) & (submissions["Challenge ID"] == challenge_id))]
    new_entry = pd.DataFrame([[student_id, challenge_id, submission_text, file_submission, "Pending"]],
                             columns=["Student ID", "Challenge ID", "Submission Text", "File Submission", "Reviewed"])
    submissions = pd.concat([submissions, new_entry])
    submissions.to_csv(DAILY_SUBMISSIONS_DB, index=False)

# 🎮 Student Dashboard UI
def student_dashboard():
    st.subheader("🎮 Welcome to Your Siri Solver Dashboard")

    student_id = st.text_input("Enter Your Student ID")

    if student_id:
        student_row = students_df[students_df["Student ID"] == student_id]

        if student_row.empty:
            st.error("Invalid Student ID! Please check with your CSE.")
            return

        student_name = student_row["Name"].values[0]
        xp_points = int(student_row["XP Points"].values[0])
        level = int(student_row["Level"].values[0])
        umeme_points = int(student_row["Umeme Points"].values[0])

        st.write(f"🧑‍🎓 **{student_name}** | 🎯 XP: {xp_points} | ⚡ Umeme Points: {umeme_points} | 🏆 Level: {level}")

        # 🎲 Daily Challenge
        st.subheader("🎲 Daily Challenge")
        daily_challenges = load_daily_challenges()

        if not daily_challenges.empty:
            day_seed = pd.Timestamp.now().day
            challenge = daily_challenges.iloc[day_seed % len(daily_challenges)]
            challenge_id = challenge["Challenge ID"]
            st.write(f"**Challenge:** {challenge['Description']}")

            submissions = pd.read_csv(DAILY_SUBMISSIONS_DB)
            already_submitted = submissions[
                (submissions["Student ID"] == student_id) & (submissions["Challenge ID"] == challenge_id)
            ]

            if not already_submitted.empty:
                st.success("✅ Submission received! Waiting for review.")
            else:
                st.subheader("📤 Submit Proof of Completion")
                text_entry = st.text_area("Describe how you completed the challenge")
                uploaded_file = st.file_uploader("Upload file (image/audio/video)", type=["jpg", "png", "mp3", "mp4"])

                file_path = None
                if uploaded_file:
                    file_path = os.path.join(UPLOADS_FOLDER, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                if st.button("Submit Challenge Proof"):
                    if text_entry or file_path:
                        save_daily_submission(student_id, challenge_id, text_entry, file_path)
                        st.success("✅ Submission recorded! Awaiting review.")
                        st.rerun()
                    else:
                        st.warning("Please enter text or upload a file.")

        else:
            st.warning("⚠️ No daily challenges available.")

        # 🏆 Leaderboard
        st.subheader("🏅 Class Leaderboard")
        leaderboard = load_leaderboard()
        if not leaderboard.empty:
            st.write("🔝 **Top 5 XP Earners**")
            top_xp = leaderboard.sort_values("XP Points", ascending=False).head(5)
            st.dataframe(top_xp)

            st.write("⚡ **Top 5 Umeme Earners**")
            top_umeme = leaderboard.sort_values("Umeme Points", ascending=False).head(5)
            st.dataframe(top_umeme)
        else:
            st.info("No leaderboard data yet.")
