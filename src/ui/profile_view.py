from __future__ import annotations

import streamlit as st
from src.database.models import MemoryRecord, UserProfile
from src.database.store import CareStore


def render_onboarding(store: CareStore, user_id: str, default_name: str = "") -> None:
    st.markdown("### Welcome to CareCompanion! 🌿")
    st.markdown(
        "To provide you with safe, personalized wellness coaching calibrated specifically "
        "to your body and habits, please complete your initial health profile."
    )

    with st.form("onboarding_form"):
        st.markdown("#### 1. Baseline Vitals")
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name", value=default_name or "User")
            age = st.number_input("Age", min_value=12, max_value=120, value=28)
            sex = st.selectbox("Sex", ["prefer_not_to_say", "female", "male", "other"])
        with col2:
            units = st.selectbox("Unit System", ["metric", "imperial"], format_func=lambda u: "Metric (kg, cm)" if u == "metric" else "Imperial (lbs, in)")
            weight_label = "Current Weight (kg)" if units == "metric" else "Current Weight (lbs)"
            height_label = "Height (cm)" if units == "metric" else "Height (inches)"
            current_weight = st.number_input(weight_label, min_value=20.0, max_value=350.0, value=75.0, step=0.5)
            height = st.number_input(height_label, min_value=40.0, max_value=250.0, value=175.0, step=1.0)

        st.markdown("#### 2. Health & Lifestyle")
        col3, col4 = st.columns(2)
        with col3:
            activity_level = st.selectbox(
                "Activity Level",
                ["sedentary", "lightly_active", "moderately_active", "very_active"],
                format_func=lambda a: {
                    "sedentary": "Sedentary (desk job, minimal exercise)",
                    "lightly_active": "Lightly Active (1-3 days/week)",
                    "moderately_active": "Moderately Active (3-5 days/week)",
                    "very_active": "Very Active (6-7 days/week, heavy)",
                }.get(a, a),
            )
            allergies = st.text_input("Allergies or Intolerances", placeholder="e.g. Peanuts, lactose, none")
            medications = st.text_input("Current Medications", placeholder="e.g. None")
        with col4:
            dietary_preference = st.selectbox(
                "Dietary Preference",
                ["any", "non_vegetarian", "vegetarian", "vegan", "pescatarian", "keto"],
                format_func=lambda d: {
                    "any": "No Restrictions",
                    "non_vegetarian": "Non-Vegetarian",
                    "vegetarian": "Vegetarian",
                    "vegan": "Vegan",
                    "pescatarian": "Pescatarian",
                    "keto": "Keto / Low-Carb",
                }.get(d, d),
            )
            medical_conditions = st.text_input("Medical Conditions", placeholder="e.g. Hypertension, asthma, none")
            injuries_limitations = st.text_input("Injuries or Physical Limitations", placeholder="e.g. Knee pain, none")

        st.markdown("#### 3. Sleep & Goals")
        col5, col6 = st.columns(2)
        with col5:
            sleep_hours = st.slider("Target Sleep (hours/night)", 4.0, 12.0, 7.5, 0.5)
            sleep_quality = st.selectbox("Current Sleep Quality", ["Poor", "Fair", "Good", "Excellent"], index=2)
        with col6:
            goals = st.multiselect(
                "Select Wellness Goals",
                [
                    "Weight management",
                    "Muscle building",
                    "Improving fitness",
                    "Better sleep",
                    "Improving daily activity",
                    "Nutrition improvement",
                    "Stress management",
                    "General wellness",
                ],
                default=["Improving fitness", "Better sleep"],
            )

        lifestyle_notes = st.text_area("Any additional lifestyle notes for your coach?", "")

        submitted = st.form_submit_button("Complete Onboarding & Start Coaching", type="primary", use_container_width=True)

        if submitted:
            if not full_name.strip():
                st.error("Please provide your name.")
                return

            profile = UserProfile(
                user_id=user_id,
                full_name=full_name.strip(),
                age=int(age),
                sex=sex,
                unit_preference=units,
                height=float(height),
                current_weight=float(current_weight),
                activity_level=activity_level,
                dietary_preference=dietary_preference,
                allergies=allergies.strip(),
                medical_conditions=medical_conditions.strip(),
                medications=medications.strip(),
                injuries_limitations=injuries_limitations.strip(),
                sleep_duration_hours=float(sleep_hours),
                sleep_quality=sleep_quality,
                goals=goals,
                primary_goal=goals[0] if goals else "General wellness",
                lifestyle_notes=lifestyle_notes.strip(),
                onboarding_completed=True,
            )
            store.save_profile(profile)

            # Seed initial memory
            unit_str = "lbs" if units == "imperial" else "kg"
            store.add_memory(
                MemoryRecord(
                    user_id=user_id,
                    memory_type="health",
                    memory_key="current_weight",
                    memory_content=f"User's weight is {current_weight} {unit_str}.",
                    confidence=0.9,
                    confirmed=True,
                    is_current=True,
                )
            )
            store.add_memory(
                MemoryRecord(
                    user_id=user_id,
                    memory_type="preference",
                    memory_key="name",
                    memory_content=f"Call me {full_name.strip()}.",
                    confidence=0.9,
                    confirmed=True,
                    is_current=True,
                )
            )
            st.success("Onboarding complete! Your personalized coach is ready.")
            st.rerun()


def render_profile(store: CareStore, user_id: str) -> None:
    profile = store.get_profile(user_id)
    if not profile or not profile.onboarding_completed:
        render_onboarding(store, user_id)
        return

    st.markdown("## 👤 Personal Health Profile")
    st.caption("Strict single-user account data. Your coach tailors guidance exclusively to this profile.")

    # Top metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Name & Age", f"{profile.full_name}", f"{profile.age or '--'} yrs")
    with c2:
        unit = "lbs" if profile.unit_preference == "imperial" else "kg"
        st.metric("Current Weight", f"{profile.current_weight or '--'} {unit}")
    with c3:
        h_unit = "in" if profile.unit_preference == "imperial" else "cm"
        bmi_str = "--"
        if profile.current_weight and profile.height and profile.height > 0:
            h_m = profile.height / 100.0 if profile.unit_preference == "metric" else profile.height * 0.0254
            w_kg = profile.current_weight if profile.unit_preference == "metric" else profile.current_weight * 0.453592
            bmi_val = w_kg / (h_m * h_m)
            bmi_str = f"BMI {bmi_val:.1f}"
        st.metric("Height", f"{profile.height or '--'} {h_unit}", bmi_str)
    with c4:
        st.metric("Sleep Target", f"{profile.sleep_duration_hours or '--'} hrs", profile.sleep_quality or "Good")

    # Goals and Lifestyle
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Active Goals")
        if profile.goals:
            for g in profile.goals:
                st.markdown(f"- **{g}**")
        else:
            st.caption("No specific goals selected.")

    with col_b:
        st.markdown("#### Activity & Nutrition")
        st.markdown(f"- **Activity Level:** {profile.activity_level.replace('_', ' ').title()}")
        st.markdown(f"- **Dietary Preference:** {profile.dietary_preference.replace('_', ' ').title()}")
        st.markdown(f"- **Units:** {profile.unit_preference.title()}")

    # Medical / Safety
    st.markdown("#### Health & Safety Notes")
    m1, m2 = st.columns(2)
    with m1:
        st.markdown(f"**Allergies:** {profile.allergies or 'None reported'}")
        st.markdown(f"**Medical Conditions:** {profile.medical_conditions or 'None reported'}")
    with m2:
        st.markdown(f"**Medications:** {profile.medications or 'None'}")
        st.markdown(f"**Injuries / Limitations:** {profile.injuries_limitations or 'None reported'}")

    st.markdown("---")
    with st.expander("✎ Edit Profile Details"):
        with st.form("edit_profile_form"):
            e_name = st.text_input("Full Name", value=profile.full_name)
            e_age = st.number_input("Age", min_value=12, max_value=120, value=profile.age or 28)
            e_weight = st.number_input("Current Weight", min_value=20.0, max_value=400.0, value=profile.current_weight or 75.0, step=0.5)
            e_height = st.number_input("Height", min_value=40.0, max_value=260.0, value=profile.height or 175.0, step=1.0)
            e_diet = st.selectbox(
                "Dietary Preference",
                ["any", "non_vegetarian", "vegetarian", "vegan", "pescatarian", "keto"],
                index=["any", "non_vegetarian", "vegetarian", "vegan", "pescatarian", "keto"].index(profile.dietary_preference) if profile.dietary_preference in ["any", "non_vegetarian", "vegetarian", "vegan", "pescatarian", "keto"] else 0,
            )
            e_allergies = st.text_input("Allergies", value=profile.allergies or "")
            e_conditions = st.text_input("Medical Conditions", value=profile.medical_conditions or "")
            e_notes = st.text_area("Lifestyle Notes", value=profile.lifestyle_notes or "")

            if st.form_submit_button("Save Changes", type="primary"):
                updated = store.update_profile(
                    user_id=user_id,
                    full_name=e_name.strip(),
                    age=int(e_age),
                    current_weight=float(e_weight),
                    height=float(e_height),
                    dietary_preference=e_diet,
                    allergies=e_allergies.strip(),
                    medical_conditions=e_conditions.strip(),
                    lifestyle_notes=e_notes.strip(),
                )
                # Sync weight into memory
                u_str = "lbs" if profile.unit_preference == "imperial" else "kg"
                store.add_memory(
                    MemoryRecord(
                        user_id=user_id,
                        memory_type="health",
                        memory_key="current_weight",
                        memory_content=f"User's weight is {e_weight} {u_str}.",
                        confidence=0.9,
                        confirmed=True,
                        is_current=True,
                    )
                )
                st.success("Profile updated and synced with memory!")
                st.rerun()
