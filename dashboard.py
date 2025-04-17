# import streamlit as st
# import pandas as pd
# import matplotlib.pyplot as plt
# # Load data
# df = pd.read_csv("room_bookings.csv")
# df["date"] = pd.to_datetime(df["date"])
# st.title("Hotel Room Analytics")
# st.subheader("Raw Booking Data")
# st.dataframe(df)
# st.subheader("Occupancy Trend Over Time")
# chart_data = df.groupby("date")["occupancy"].sum()
# st.line_chart(chart_data)
# st.subheader("Average Occupancy by Room Type")
# avg_by_type = df.groupby("room_type")["occupancy"].mean().sort_values(ascending=False)
# st.bar_chart(avg_by_type)
# st.caption("Powered by Streamlit – Mock Data")

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import base64
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, Image
import os

# --- Load data ---
members = pd.read_csv("members.csv")
screenings = pd.read_csv("screenings.csv")
today = datetime.today()
# --- Helper functions ---
def normalize(text):
   return text.strip().lower()
def parse_history(history_str):
   history = {}
   if pd.isna(history_str):
       return history
   for entry in history_str.split(";"):
       if ":" in entry:
           screening, date = entry.split(":")
           history[normalize(screening)] = datetime.strptime(date.strip(), "%Y-%m-%d")
   return history
def get_screening_status(member):
   age = member["age"]
   gender = member["gender"]
   diabetic = member["diabetic"]
   history = parse_history(member["screening_history"])
   eligible, completed = [], []
   for _, row in screenings.iterrows():
       screening = row["screening"].strip()
       normalized_name = normalize(screening)
       if not (row["min_age"] <= age <= row["max_age"]): continue
       if row["gender"] not in ("All", gender): continue
       if row.get("diabetic_only", False) and not diabetic: continue
       last_done = history.get(normalized_name)
       if last_done:
           next_due = last_done + timedelta(days=365 * row["refresh_years"])
           if today < next_due:
               completed.append({"Screening": screening, "Last Done": last_done.date(), "Next Available": next_due.date()})
               continue
       eligible.append({"Screening": screening, "Importance": row["importance"]})
   sorted_eligible = sorted(eligible, key=lambda x: -x["Importance"])
   return pd.DataFrame(sorted_eligible[:3]), pd.DataFrame(sorted_eligible[3:]), pd.DataFrame(completed)
   
# --- PDF Generator ---
# def create_pdf(member, top_screenings, glossary, facility):
#     pdf = FPDF()
#     pdf.add_page()
#     pdf.set_auto_page_break(auto=True, margin=15)
#     # --- Fedhealth logo ---
#     try:
#         pdf.image("fedhealth_logo.png", x=150, y=10, w=40)
#     except:
#         pass
#     # --- Title Header Block ---
#     pdf.set_font("Arial", 'B', 16)
#     pdf.ln(20)
#     pdf.cell(0, 10, "Personal Care Benefit Report", ln=True, align='L')
#     pdf.set_font("Arial", '', 11)
#     pdf.ln(5)
#     pdf.multi_cell(0, 7, f"""
# Dear {member['name']},
# This document outlines your top recommended health screenings, selected for you based on your age, gender, and health status. All of these are fully covered by Fedhealth at no extra cost to you.
# Prioritizing preventative screenings empowers early detection, which significantly improves treatment outcomes and helps you stay healthy for longer.
# """)
#     # --- Top 3 Screenings Section ---
#     pdf.set_font("Arial", 'B', 12)
#     pdf.cell(0, 8, "Your Top 3 Recommended Screenings:", ln=True)
#     pdf.set_font("Arial", '', 11)
#     for s in top_screenings:
#         pdf.cell(0, 8, f" - {s['Screening']} (Importance: {s['Importance']})", ln=True)
#     # --- Facility Details ---
#     pdf.ln(8)
#     pdf.set_font("Arial", 'B', 12)
#     pdf.cell(0, 8, "Nearest Medical Facility:", ln=True)
#     pdf.set_font("Arial", '', 11)
#     pdf.multi_cell(0, 7, f"{facility['name']}\n{facility['address']}\nTel: {facility['phone']}\nEmail: {facility['email']}")
#     # --- Glossary Section ---
#     pdf.ln(8)
#     pdf.set_font("Arial", 'B', 12)
#     pdf.cell(0, 8, "Glossary of Screenings:", ln=True)
#     pdf.set_font("Arial", '', 11)
#     for term, desc in glossary.items():
#         pdf.multi_cell(0, 7, f"{term}: {desc}")
#         pdf.ln(1)
#     # --- Closing ---
#     pdf.ln(5)
#     pdf.set_font("Arial", 'I', 10)
#     pdf.set_text_color(100, 100, 100)
#     pdf.cell(0, 10, "This report was generated for personal use as part of the Fedhealth Personal Care Benefit initiative.", ln=True)
#     # Save PDF
#     filename = f"Fedhealth_Screening_Recommendations_{member['name']}.pdf"
#     pdf.output(filename)
#     return filename 

def create_reportlab_pdf(member, screenings, score, glossary, clinic, logo_path, output_path):
   doc = SimpleDocTemplate(output_path, pagesize=A4,
                           rightMargin=30, leftMargin=30,
                           topMargin=30, bottomMargin=20)
   styles = getSampleStyleSheet()
   story = []
   # --- Header: Logo and Title ---
   if os.path.exists(logo_path):
       logo = Image(logo_path, width=100, height=85)
       story.append(logo)
   story.append(Spacer(1, 12))
   title = Paragraph(f"<font size=16 color='#00539B'><b>Personal Care Benefit Report</b></font>", styles['Title'])
   story.append(title)
   story.append(Spacer(1, 12))
   # --- Intro Text ---
   intro_text = f"""
<font size=10>Dear {member['name']},</font><br/><br/>
<font size=10>
   This personalized report outlines your most important recommended health screenings based on your demographic profile.
   All these benefits are available at no cost to you through Fedhealth. Early detection saves lives and reduces long-term health costs.
</font>
   """
   story.append(Paragraph(intro_text, styles["Normal"]))
   story.append(Spacer(1, 10))
   # --- Health Priority Score ---
   story.append(Paragraph(f"<b>Health Priority Score:</b> <font size=12 color='green'><b>{score}/100</b></font>", styles["Normal"]))
   story.append(Spacer(1, 6))
   # --- Reward Box ---
   reward_text = Paragraph(
       "<para align=center><font size=11 color='white'><b>Complete all 3 recommended screenings this year and earn a R800 wellness voucher!</b></font></para>",
       styles["Normal"]
   )
   reward_table = Table([[reward_text]], colWidths=[460])
   reward_table.setStyle(TableStyle([
       ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0071CE')),
       ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#00539B')),
       ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
       ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
       ('TOPPADDING', (0, 0), (-1, -1), 8),
       ('BOTTOMPADDING', (0, 0), (-1, -1), 8)
   ]))
   story.append(reward_table)
   story.append(Spacer(1, 12))
   # --- Top Screenings Table ---
   story.append(Paragraph("<b>Top 3 Screenings:</b>", styles["Heading4"]))
   table_data = [["Screening", "Importance", "Last Done", "Next Available"]]
   for s in screenings:
       table_data.append([
           s["Screening"],
           str(s["Importance"]),
           s.get("Last Done", "—"),
           s.get("Next Available", "—")
       ])
   table = Table(table_data, colWidths=[200, 80, 100, 100])
   table.setStyle(TableStyle([
       ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00539B')),
       ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
       ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
       ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
       ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
       ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#E6F2FA")])
   ]))
   story.append(table)
   story.append(Spacer(1, 12))
   # --- Clinic Info ---
   story.append(Paragraph("<b>Nearest Medical Facility:</b>", styles["Heading4"]))
   clinic_info = f"""
<font size=10>{clinic['name']}<br/>
   {clinic['address']}<br/>
   Tel: {clinic['phone']}<br/>
   Email: <a href='mailto:{clinic['email']}'>{clinic['email']}</a><br/>
<a href='{clinic['booking_link']}'>Click here to book your screenings</a></font>
   """
   story.append(Paragraph(clinic_info, styles["Normal"]))
   story.append(Spacer(1, 12))
   # --- Glossary ---
   story.append(Paragraph("<b>Glossary:</b>", styles["Heading4"]))
   for term, desc in glossary.items():
       story.append(Paragraph(f"<b>{term}:</b> {desc}", styles["Normal"]))
       story.append(Spacer(1, 4))
   # --- Footer Note ---
   story.append(Spacer(1, 10))
   footer = Paragraph("<font size=9 color=gray>This report was generated by Fedhealth as part of the Personal Care Benefit program.</font>", styles["Normal"])
   story.append(footer)
   doc.build(story)

def download_pdf_button(filepath):
   with open(filepath, "rb") as f:
       base64_pdf = base64.b64encode(f.read()).decode('utf-8')
       href = f'<a href="data:application/pdf;base64,{base64_pdf}" download="{filepath}">📄 Download Your PDF Report</a>'
       st.markdown(href, unsafe_allow_html=True)
# --- Page Styling ---
st.markdown("""
<style>
       .main { background-color: #E6F2FA; }
       h1 { color: #00539B; }
       .block-container { padding-top: 2rem; }
       .stTable th { background-color: #0071CE; color: white; }
</style>
""", unsafe_allow_html=True)
# --- UI ---
st.image("fedhealth_logo.jpg", width=180)
st.title("Personal Care Benefit Screening Dashboard")
selected_name = st.selectbox("Select Member", members["name"])
member = members[members["name"] == selected_name].iloc[0]
st.markdown(
   f"**👤 Member:** `{member['name']}` &nbsp;&nbsp;&nbsp; "
   f"**🎂 Age:** `{member['age']}` &nbsp;&nbsp;&nbsp; "
   f"**⚧ Gender:** `{member['gender']}` &nbsp;&nbsp;&nbsp; "
   f"**💉 Diabetic:** `{ 'Yes' if member['diabetic'] else 'No' }`"
)
st.markdown("---")
# --- Process ---
priority_df, additional_df, completed_df = get_screening_status(member)
st.markdown("### ✅ Top 3 Priority Screenings")
st.table(priority_df if not priority_df.empty else pd.DataFrame([{"Message": "No eligible screenings"}]))
st.markdown("### 📋 Additional Available Screenings")
st.table(additional_df if not additional_df.empty else pd.DataFrame([{"Message": "None"}]))
st.markdown("### 🗂️ Already Completed Screenings")
st.table(completed_df if not completed_df.empty else pd.DataFrame([{"Message": "None"}]))
# --- Download PDF section ---
if not priority_df.empty:
   glossary = {
       "Pap Smear": "A test for cervical cancer in women.",
       "HPV PCR Test": "Detects HPV, a virus linked to cervical cancer.",
       "Cholesterol Screening": "Checks for cholesterol levels to assess heart disease risk.",
       "HRA: Wellness Screening": "General risk assessment based on lifestyle and vitals.",
       "AI Diabetic Retinopathy Screening": "Eye screening to prevent diabetic complications."
   }
   facility_info = {
       "name": "Netcare Christiaan Barnard Memorial Hospital",
       "address": "Rua Bartholomeu Dias Plain, Foreshore, Cape Town, 8001",
       "phone": "021 555 1234",
       "email": "screenings@netcare.co.za",
       "booking_link": "https://www.netcare.co.za/netcare-hospitals/patient-information/hospital-pre-admission"
   }
#    file = create_pdf(member, priority_df.to_dict(orient="records"), glossary, facility_info)
file = f"Fedhealth_Report_{member['name']}.pdf"

health_priority_score = 82 # set arbitrarily for now

create_reportlab_pdf(
   member=member,
   screenings=priority_df.to_dict(orient="records"),
   score=health_priority_score,  # You can use a fixed score for now, e.g. 82
   glossary=glossary,
   clinic=facility_info,
   logo_path="fedhealth_logo.png",
   output_path=file
)
st.markdown("### 📄 Download Your Personalized PDF")
download_pdf_button(file)
